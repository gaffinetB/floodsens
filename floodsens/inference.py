import tifffile
import pickle
import torch
import glob
import pandas as pd
import numpy as np
from osgeo import gdal
from pathlib import Path

def choose_model():
    model_paths = [x for x in Path('models').iterdir() if x.is_dir()]
    print("Available models:\n", *[f"\t{k+1}) {x.name}\n" for k, x in enumerate(model_paths)])
    model_idx = int(input("Type Number of model to load it\n"))

    model_path = model_paths[model_idx-1]/"model.pth.tar"
    model = torch.load(model_path)
    
    return model

def run_inference(model, input_tiles_folder):
    model.eval()

    batch = []
    input_tiles = list(input_tiles_folder.iterdir())
    for tile in input_tiles:
        image = tifffile.imread(tile)
        # image = (image-means)/stds # How to get stats without Azure connection?
        image = np.moveaxis(image, -1, 0)
        batch.append(image)

    x_batch = torch.from_numpy(np.array(batch))
    x_batch = torch.Tensor.float(x_batch)

    # NOTE Importance map part
    # activation = {}
    # def get_activation(name):
    #     def hook(output):
    #         activation[name] = output.detach()
    #     return hook

    y_hat = model(x_batch)

    input_array, output_array = [], []
    output_tiles_folder = input_tiles_folder.parent/"out_tiles"
    output_tiles_folder.mkdir()

    for i, m in enumerate(y_hat):
        input_name = input_tiles[i].stem
        output_name = f"{input_name}_yhat.pkl"
        output_path = output_tiles_folder/output_name

        result_dict = {}
        result_dict['map'] = m.detach().numpy()
        pickle.dump(result_dict, open(output_path, 'wb'))

        input_array.append(f"{input_name}.tif")
        output_array.append(output_name)       
    
    df = pd.DataFrame.from_dict({'input_tiles': input_array, 'output_tiles': output_array})
    return df

def create_map(tiles_df, out_dir=None):
    if out_dir is None: out_dir = Path('.')
    NoData_value = -9999

    for row in tiles_df.iterrows():
        input_tile = row['input_tiles']
        output_tile = row['output_tiles']

        inferred_result = pickle.load(open(output_tile), 'rb')
        inferred_map_array = inferred_result['map'][0,:,:]

        input_raster = gdal.Open(str(input_tile))
        gt = input_raster.GetGeoTransform()
        proj = input_raster.GetProjection()
        x_res, y_res = input_raster.RasterXSize, input_raster.RasterYSize


        out_name = output_tile.name
        driver = gdal.GetDriverByName('GTiff')
        driver.Register()
        out_ds = driver.Create(f"{out_name}_map.tif", x_res, y_res, 1, gdal.GDT_Float32)
        out_ds.SetGeoTransform(gt)
        out_ds.SetProjection(proj)
        band = out_ds.GetRasterBand(1)
        band.SetNoDataValue(NoData_value)
        band.WriteArray(inferred_map_array)
        out_ds = None

    output_map_path = out_dir/'map.tif'
    map_tiles = glob.glob('*map.tif')
    vrt_options = gdal.BuildVRTOptions()
    map_vrt = gdal.BuildVRT('inferred_map.vrt', map_tiles, options=vrt_options)
    gdal.Translate(str(output_map_path), map_vrt)

    # TODO Include below options cleanly in gdal.Translate() call
    # subprocess.call(['gdal_translate', '-of', 'COG', 'map.vrt', directory/'map.tif', '--config', 'CHECK_DISK_FREE_SPACE', 'NO'])
    output_map_ds = gdal.Open(str(output_map_path))
    
    return output_map_ds
