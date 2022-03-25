import time
import zipfile
from osgeo import gdal
from pathlib import Path
from floodsens._tile import multiraster_tiling
from floodsens._download import get_copernicus_dem
from floodsens._process import flow_accumulation, hand, slope, twi
from floodsens._reproject import reproject_set, reproject_from_raster
from floodsens.constants import EXTRACT_DICT


def _rm_tree(path):
    path = Path(path)
    for child in path.glob('*'):
        if child.is_file():
            child.unlink()
        else:
            _rm_tree(child)
    path.rmdir()

def _filter_zip(zip_path, extract_dict, return_type='list'):
    files = zipfile.ZipFile(zip_path, 'r').namelist()
    
    filtered_list = []
    filtered_dict = {}
    for key in extract_dict.keys():
        for value in extract_dict[key]:
            matched_files = [x for x in files if key in x and value in x]
            if len(matched_files) == 1:
                matched_file = matched_files[0]
                filtered_list.append(matched_file)
                filtered_dict[value] = matched_file
            elif len(matched_files) == 0:
                continue
            else:
                raise ValueError(f"Filtering zip archive failed.. matched_files = {matched_files}")

    if return_type == 'list':
        return filtered_list
    elif return_type == 'dict':
        return filtered_dict
    else:
        return None

def extract(zip_path, project_dir, extract_dict):
    project_dir = Path(project_dir)
    filtered_files = _filter_zip(zip_path, extract_dict, return_type="list")
    zip_file = zipfile.ZipFile(zip_path, 'r')
    
    extracted_paths = []
    for file in filtered_files:
        zip_file.extract(file, project_dir)
        file = project_dir/file
        new_name = project_dir/file.name
        file.rename(new_name)
        extracted_paths.append(new_name)

    extracted_paths.sort()

    _rm_tree(project_dir/f"{zip_path.stem}.SAFE")

    return extracted_paths

def download_dem(s2_path, out_dir):
    dem_path = get_copernicus_dem(s2_path, out_dir)
    return dem_path

def clip_dem(dem_path, target_raster_path, project_dir):
    reproject_from_raster(dem_path, target_raster_path, -9999, project_dir, xRes=30.0, yRes=30.0)
    return dem_path

def process_dem(dem_path, out_dir, return_type='list'):
    dem_path = Path(dem_path)
    
    slope_path = slope(dem_path, out_dir)

    grid, fa_path = flow_accumulation(dem_path, out_dir, out_name=f"FA.tif")

    hand_path = hand(grid, dem_path, fa_path, out_dir, out_name=f"HAND.tif")

    twi_path = twi(dem_path, fa_path, out_dir, out_name=f"TWI.tif")

    if return_type == 'dict':
        paths_dict = {"dem": dem_path, 
                        "slope": slope_path, 
                        "fa": fa_path, 
                        "hand": hand_path, 
                        "twi": twi_path}
        return paths_dict
    if return_type == 'list':
        paths_list = [dem_path, slope_path, fa_path, hand_path, twi_path]
        return paths_list
    
    return None

def reproject(*raster_paths, target_raster_path=None, nan_value=-9999): # Needed for resolution change
    if target_raster_path is None:
        target_raster_path = raster_paths[0]
    
    reprojected_raster_paths = reproject_set(target_raster_path, nan_value, *raster_paths)
    
    return reprojected_raster_paths

def stack(out_dir, *input_paths):
    options = gdal.BuildVRTOptions(separate=True)
    to_merge = [str(x) for x in input_paths]
    vrt_path = out_dir/f"{out_dir.stem}.vrt"

    out_path = out_dir/f"{out_dir.stem}.tif"
    vrt = gdal.BuildVRT(str(vrt_path), to_merge, options=options)
    gdal.Translate(str(out_path), vrt)

    if vrt_path.exists(): vrt_path.unlink()

    return out_path

def tile(*raster_paths, tile_size=244, data_type="stacked"):
    tile_dir = multiraster_tiling(tile_size, *raster_paths, data_type=data_type)
    return tile_dir

def run_default_preprocessing(project_dir, s2_zip_path, extract_dict=None, delete_all=True):
    Mtic, mtic = time.time(), time.time()
    
    print(f"o---o---o---o---o---o---o\tNot Started \t\t\t(0/7 - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
    if extract_dict is None:
        extract_dict = EXTRACT_DICT
    s2_paths_list = extract(s2_zip_path, project_dir, extract_dict)
    target_raster_path = s2_paths_list[0]
    print(f"•---o---o---o---o---o---o\tSentinel bands extracted \t(1/7 - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
    mtic=time.time()

    dem_path = download_dem(target_raster_path, project_dir)
    print(f"•---•---o---o---o---o---o\tDEM downloaded \t\t\t(2/7 - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
    mtic=time.time()
    dem_path = clip_dem(dem_path, target_raster_path, project_dir)
    print(f"•---•---•---o---o---o---o\tDEM clipped \t\t\t(3/7 - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
    mtic=time.time()
    dem_paths_list = process_dem(dem_path, project_dir)
    all_paths_list = s2_paths_list + dem_paths_list
    print(f"•---•---•---•---o---o---o\tDEM processed \t\t\t(4/7 - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
    mtic=time.time()

    reprojected_raster_paths = reproject(*all_paths_list, target_raster_path = target_raster_path)
    print(f"•---•---•---•---•---o---o\tReprojections completed \t(5/7 - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
    mtic=time.time()

    stacked_path = stack(project_dir, *reprojected_raster_paths)
    print(f"•---•---•---•---•---•---o\tAll bands stacked \t\t(6/7 - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
    mtic=time.time()
    
    tile_dir = tile(stacked_path)
    print(f"•---•---•---•---•---•---•\tTiles ready for inference \t(7/7 - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")

    if delete_all:
        for s2_path in s2_paths_list:
            Path(s2_path).unlink()
        
        for dem_path in dem_paths_list:
            Path(dem_path).unlink()
        
        Path(stacked_path).unlink()
        print("Unnecessary project files removed.")


    return tile_dir
