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

def run_inference(model_path, input_tiles_folder, channels, mini_batch_size=4, cuda=True, sigmoid_end=True):

    if cuda is True: model_dict = torch.load(model_path)
    else: model_dict = torch.load(model_path, map_location=torch.device('cpu'))
    
    model_weights = model_dict['model_state_dict']
    model = MainNET(in_channels=len(model_dict['model_means']), out_channels=1)
    model.load_state_dict(model_weights)
    model.eval()

    means, stds = model_dict['model_means'], model_dict['model_stds']
    means = np.expand_dims(means, axis=(1, 2))
    stds = np.expand_dims(stds, axis=(1, 2))
    
    input_tiles_folder = Path(input_tiles_folder)
    tiles = list(input_tiles_folder.iterdir())
    
    m = len(tiles)
    mini_batches = []
    num_complete_minibatches = math.floor(m / mini_batch_size)

    for k in range(0, num_complete_minibatches):
        mini_batch = tiles[k*mini_batch_size:(k+1)*mini_batch_size]
        mini_batches.append(mini_batch)

    if m % mini_batch_size != 0:
        mini_batch = tiles[-(m - mini_batch_size*math.floor(m/mini_batch_size)):]
        mini_batches.append(mini_batch)
    
    num_mini_batches = len(mini_batches)
    for k, mini_batch in enumerate(mini_batches):
        batch = []
        
        for tile in mini_batch:
            in_image = tifffile.imread(tile)
            in_image = np.moveaxis(in_image, -1, 0)
            image = np.empty((0, in_image.shape[1], in_image.shape[2]))
            
            for channel in channels:
                image = np.append(image, np.expand_dims(in_image[channel], axis=0), axis=0)
            
            image = (image-means)/stds
            batch.append(image)
        
        x_batch = torch.from_numpy(np.array(batch))
        x_batch = torch.Tensor.float(x_batch)
        
        activation = {}
        def get_activation(name):
            def hook(model, input, output):
                activation[name] = output.detach()
            return hook

        model.predown.fc[3].register_forward_hook(get_activation('importance_weights'))

        y_hat = model(x_batch)
        if sigmoid_end: y_hat = torch.sigmoid(y_hat)
        
        input_array, output_array, importance_array = [], [], []
        output_tiles_folder = input_tiles_folder.parent/"out_tiles"
        output_tiles_folder.mkdir(exist_ok=True)

        for i, m in enumerate(y_hat):
            input_name = mini_batch[i].stem
            output_path = output_tiles_folder/f"yhat_{input_name}.pkl"

            result_dict = {}
            result_dict['map'] = m.detach().numpy()
            imp = activation['importance_weights'][i]
            result_dict['importances'] = list(imp.numpy())
            pickle.dump(result_dict, open(output_path, 'wb'))

            input_array.append(str(input_tiles_folder/f"{input_name}.tif"))
            output_array.append(str(output_path))
            importance_array.append(list(imp.numpy()))

        print(f"{100*k/num_mini_batches:.2f}% Completion", end='\r')
    
    df = pd.DataFrame.from_dict({'input_file': input_array,
                                'output_file': output_array,
                                'importances': importance_array})

    return output_tiles_folder


def create_map(tile_dir, inferred_dir, out_path, clean=True):
    input_tiles = [str(x) for x in tile_dir.iterdir()]
    input_tiles.sort()
    out_tiles = [str(x) for x in inferred_dir.iterdir()]
    out_tiles.sort()
    tiles_dict = {'input_tiles': input_tiles, 'output_tiles': out_tiles}
    tiles_df = pd.DataFrame.from_dict(tiles_dict)

    NoData_value = -9999


    out_path = Path(out_path)
    out_path.parent.mkdir(exist_ok=True)
    
    for row in tiles_df.iterrows():
        input_tile = row[1]['input_tiles']
        inferred_tile = row[1]['output_tiles']
        
        inferred_result = pickle.load(open(inferred_tile, 'rb'))
        inferred_map_array = inferred_result['map'][0,:,:]
        inferred_imp_array = inferred_result['importances']

        input_raster = gdal.Open(str(input_tile))
        gt = input_raster.GetGeoTransform()
        proj = input_raster.GetProjection()
        x_res, y_res = input_raster.RasterXSize, input_raster.RasterYSize

        tile_basename = Path(inferred_tile).stem
        driver = gdal.GetDriverByName('GTiff')
        driver.Register()
                
        out_ds = driver.Create(str(out_path.parent/f"{tile_basename}_map.tif"), x_res, y_res, 1, gdal.GDT_Float32)
        out_ds.SetGeoTransform(gt)
        out_ds.SetProjection(proj)
        band = out_ds.GetRasterBand(1)
        band.SetNoDataValue(NoData_value)
        band.WriteArray(inferred_map_array)
        out_ds = None


        gt_imp = list(gt)
        gt_imp[1] = gt[1] * x_res
        gt_imp[5] = gt[5] * y_res
        gt_imp = tuple(gt_imp)

        bands = len(inferred_imp_array)

        importances_ds = gdal.GetDriverByName('GTiff').Create(str(out_path.parent/f"{tile_basename}_imp.tif"), 1, 1, bands, gdal.GDT_Float32)
        importances_ds.SetProjection(proj)
        importances_ds.SetGeoTransform(gt_imp)

        for band_number in range(bands):
            band = importances_ds.GetRasterBand(band_number+1)
            band.SetNoDataValue(NoData_value)
            band.WriteArray(np.array([[inferred_imp_array[band_number]]])) #this should be a scalar; does it work?
            band.FlushCache()
        importances_ds = None




    map_tiles =  [str(x) for x in out_path.parent.iterdir() if x.is_file() and x.name.startswith('yhat_') and x.name.endswith('_map.tif')] # glob.glob('*map.tif')
    vrt_options = gdal.BuildVRTOptions()
    map_vrt = gdal.BuildVRT('inferred_map.vrt', map_tiles, options=vrt_options)
    gdal.Translate(str(out_path), map_vrt)

    imp_tiles = [str(x) for x in out_path.parent.iterdir() if x.is_file() and x.name.startswith('yhat_') and x.name.endswith('_imp.tif')]
    vrt_options = gdal.BuildVRTOptions()
    imp_vrt = gdal.BuildVRT('channel_importances.vrt', imp_tiles, options=vrt_options)
    gdal.Translate(str(out_path.parent/'channel_importances.tif'), imp_vrt)

    if clean:
        for map_tile in map_tiles:
            Path(map_tile).unlink()
        for imp_tile in imp_tiles:
            Path(imp_tile).unlink()


    # TODO Include below options cleanly in gdal.Translate() call
    # subprocess.call(['gdal_translate', '-of', 'COG', 'map.vrt', directory/'map.tif', '--config', 'CHECK_DISK_FREE_SPACE', 'NO'])
    
    return out_path
