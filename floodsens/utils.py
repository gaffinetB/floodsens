import re
import torch
import shutil
import itertools
import zipfile
import geopandas as gpd
from pathlib import Path

from floodsens.logger import logger


def download_sentinel2() -> list:
    # TODO with Google Earth Engine
    raise NotImplementedError("Download Sentinel-2 images from Copernicus Open Access Hub")

def extract_metadata(paths): #FIXME Only for single image at the moment
    time, zone = re.search(r'_(\d+)T.+_T(.....)_', paths[0].name).group(1, 2)

    utm_df = gpd.read_file("src/sentinel_zones/sentinel_2_index_shapefile.shp")
    utm_df = utm_df[utm_df.Name == zone]
    aoi = utm_df.geometry.bounds.values[0]

    logger.info(f"AOI and time extracted from Sentinel-2 images")

    return time, aoi

def extract(zip_path, extract_dir, extract_list, cleanup=True):
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
            raise ValueError(f"Filtering zip archive failed. Unexpected match ambiguity: {match}")
        
    extracted_files = []
    for extractable_file in extractable_files:
        zip_file.extract(extractable_file, extract_dir)
        extractable_file = Path(extractable_file)
        extracted_file = extract_dir/extractable_file.name
        (extract_dir/extractable_file).rename(extracted_file)
        
        extracted_files.append(extracted_file)
        
    if cleanup: shutil.rmtree(extract_dir/f"{zip_path.stem}.SAFE")
    
    extracted_files.sort()
    return extracted_files

