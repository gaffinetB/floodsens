import re
import torch
import geopandas as gpd

from floodsens.logger import logger

class FloodsensModel():
    def __init__(self, path, device="cpu"):
        model_dict = torch.load(path, map_location=torch.device(device))
        self.path = path
        self.name = path.stem
        self.means = model_dict["model_means"]
        self.stds = model_dict["model_stds"]
        
        if len(self.stds) == 14:
            self.channels = [0,1,2,3,4,5,6,7,8,9,10,11,12,13]
    
    def __repr__(self):
        return f"Model Name: \t{self.name}\n Number of channels: \t{len(self.channels)}\nLocation: \t{self.path}"
        

def download_sentinel2() -> list:
    # TODO
    raise NotImplementedError("Download Sentinel-2 images from Copernicus Open Access Hub")

def extract_metadata(paths): #FIXME Only for single image at the moment
    time, zone = re.search(r'_(\d+)T.+_T(.....)_', paths[0].name).group(1, 2)

    utm_df = gpd.read_file("src/sentinel_zones/sentinel_2_index_shapefile.shp")
    utm_df = utm_df[utm_df.Name == zone]
    aoi = utm_df.geometry.bounds.values[0]

    logger.info(f"AOI and time extracted from Sentinel-2 images")

    return time, aoi