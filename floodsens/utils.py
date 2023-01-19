import re
import torch
import shutil
import itertools
import zipfile
import geopandas as gpd
from pathlib import Path

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

def extract(zip_path, extract_dir, extract_list):
    extract_dir = Path(extract_dir)
    zip_file = zipfile.ZipFile(zip_path, 'r')

    extractable_files = []
    for file in zip_file.namelist():
        match = list(filter(lambda x: all([x[0][0] in x[1], x[0][1] in x[1]]), zip(extract_list, itertools.repeat(file))))
        
        if len(match) == 0:
            continue
        if len(match) == 1:
            extractable_files.append(match[0][1])
        if len(match) > 1:
            raise ValueError(f"Filtering zip archive failed. Unexpected matche ambiguity: {filtered_files}")
        
    extracted_files = []
    for extractable_file in extractable_files:
        zip_file.extract(extractable_file, extract_dir)
        extractable_file = Path(extractable_file)
        extracted_file = extract_dir/extractable_file.name
        (extract_dir/extractable_file).rename(extracted_file)
        
        extracted_files.append(extracted_file)
        
    [shutil.rmtree(x) for x in extract_dir.iterdir() if x.is_dir()]
    extracted_files.sort()
    return extracted_files
