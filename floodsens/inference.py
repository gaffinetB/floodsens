import tifffile
import pickle
import torch
import math
from floodsens.model import MainNET
import pandas as pd
import numpy as np
from osgeo import gdal
from pathlib import Path

def choose_model():
    model_paths = [x for x in Path('models').iterdir() if x.is_dir()]
    print("Available models:\n", *[f"\t{k+1}) {x.name}\n" for k, x in enumerate(model_paths)])
    model_idx = int(input("Type Number of model to load it\n"))
    model_path = model_paths[int(model_idx)-1]/"model.pth.tar"
    return model_path

def run_inference(model_path, input_tiles_folder, mini_batch_size = 4, cuda=True):
    if cuda is True: model_dict = torch.load(model_path)
    else: model_dict = torch.load(model_path, map_location=torch.device('cpu'))    
    
    means, stds = model_dict['model_means'], model_dict['model_stds']
    model = MainNET(len(means), 1)
    model.load_state_dict(model_dict['model_state_dict'])
    model.eval()

    input_tiles = list(input_tiles_folder.iterdir())

    # Create mini batch array
    m = len(input_tiles)
    mini_batches = []
    num_complete_minibatches = math.floor(m / mini_batch_size)

    for k in range(0, num_complete_minibatches):
        mini_batch = input_tiles[k*mini_batch_size:(k+1)*mini_batch_size]
        mini_batches.append(mini_batch)

    if m % mini_batch_size != 0:
        mini_batch = input_tiles[-(m - mini_batch_size*math.floor(m/mini_batch_size)):]
        mini_batches.append(mini_batch)

    # Process mini batches
    num_mini_batches = len(mini_batches)
    for k, mini_batch in enumerate(mini_batches):
        batch = []
        for tile in mini_batch:
            image = tifffile.imread(tile)
            image = (image-means)/stds # How to get stats without Azure connection?
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
        output_tiles_folder.mkdir(exist_ok=True)

        for i, m in enumerate(y_hat):
            input_name = mini_batch[i].stem
            output_path = output_tiles_folder/f"{input_name}_yhat.pkl"

            result_dict = {}
            result_dict['map'] = m.detach().numpy()
            pickle.dump(result_dict, open(output_path, 'wb'))

            input_array.append(str(input_tiles_folder/f"{input_name}.tif"))
            output_array.append(str(output_path))

        print(f"{100*k/num_mini_batches:.2f}% Completion", end='\r')

    return output_tiles_folder

def create_map(tile_dir, inferred_dir, out_dir='map/', out_path='merged_map.tif'):
    input_tiles = [str(x) for x in tile_dir.iterdir()]
    out_tiles = [str(x) for x in inferred_dir.iterdir()]
    tiles_dict = {'input_tiles': input_tiles, 'output_tiles': out_tiles}
    tiles_df = pd.DataFrame.from_dict(tiles_dict)

    NoData_value = -9999

    out_dir = Path(out_dir)
    out_dir.mkdir(exist_ok=True)

    for row in tiles_df.iterrows():
        input_tile = row[1]['input_tiles']
        inferred_tile = row[1]['output_tiles']
        
        inferred_result = pickle.load(open(inferred_tile, 'rb'))
        inferred_map_array = inferred_result['map'][0,:,:]

        input_raster = gdal.Open(str(input_tile))
        gt = input_raster.GetGeoTransform()
        proj = input_raster.GetProjection()
        x_res, y_res = input_raster.RasterXSize, input_raster.RasterYSize

        out_name = Path(inferred_tile).stem
        driver = gdal.GetDriverByName('GTiff')
        driver.Register()
                
        out_ds = driver.Create(str(out_dir/f"{out_name}_map.tif"), x_res, y_res, 1, gdal.GDT_Float32)
        out_ds.SetGeoTransform(gt)
        out_ds.SetProjection(proj)
        band = out_ds.GetRasterBand(1)
        band.SetNoDataValue(NoData_value)
        band.WriteArray(inferred_map_array)
        out_ds = None

    map_tiles =  [str(x) for x in out_dir.iterdir()] # glob.glob('*map.tif')
    vrt_options = gdal.BuildVRTOptions()
    map_vrt = gdal.BuildVRT('inferred_map.vrt', map_tiles, options=vrt_options)
    gdal.Translate(str(out_path), map_vrt)

    # TODO Include below options cleanly in gdal.Translate() call
    # subprocess.call(['gdal_translate', '-of', 'COG', 'map.vrt', directory/'map.tif', '--config', 'CHECK_DISK_FREE_SPACE', 'NO'])
    
    return out_path
