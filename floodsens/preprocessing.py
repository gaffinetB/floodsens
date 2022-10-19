import time
import zipfile
from osgeo import gdal
from osgeo import gdalconst
from pathlib import Path
from floodsens._tile import singleraster_tiling
from floodsens._download import get_copernicus_dem
from floodsens._process import flow_accumulation, hand, slope, twi
from floodsens._reproject import reproject_set, reproject_from_raster
from floodsens.constants import EXTRACT_DICT
import demloader as dl


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

    try: 
        _rm_tree(project_dir/f"{zip_path.stem}.SAFE")
    except:
        print(f"No folder found to remove at {project_dir/f'{zip_path.stem}.SAFE'}")
    
    if len(extracted_paths) == 0:
        print(f"Prameters used: {extract_dict}, files extracted: {extracted_paths}, files in zip: {filtered_files}")
        raise ValueError(f"No files extracted from {zip_path}")

    return extracted_paths

def download_dem(s2_path, out_dir):
    prefixes = dl.prefixes.get_from_raster(s2_path, 30)
    dem_path = dl.download.from_aws(prefixes, 30, f"{out_dir}/10_DEM.tif")
    # dem_path = get_copernicus_dem(s2_path, out_dir)
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

def convert(s2_paths, folder):
    folder = Path(folder)
    new_paths = []
    for s2_path in s2_paths:
        tif_path = folder/f"{s2_path.stem}.tif"
        gdal.Translate(str(tif_path), str(s2_path))
        new_paths.append(tif_path)
        s2_path.unlink()
    
    return new_paths

def reproject(*raster_paths, target_raster_path=None, nan_value=-9999, output_type=gdalconst.GDT_Float32): # Needed for resolution change
    if target_raster_path is None:
        target_raster_path = raster_paths[0]
    
    reprojected_raster_paths = reproject_set(target_raster_path, nan_value, *raster_paths, output_type=output_type)
    
    return reprojected_raster_paths

def stack(out_dir, *input_paths, data_type=None):
    options = gdal.BuildVRTOptions(separate=True, srcNodata=-9999, VRTNodata=-9999)
    to_merge = [str(x) for x in input_paths]
    if data_type is None: stem = out_dir.stem
    else: stem = data_type

    vrt_path = out_dir/f"{stem}.vrt"

    out_path = out_dir/f"{stem}.tif"
    vrt = gdal.BuildVRT(str(vrt_path), to_merge, options=options)
    gdal.Translate(str(out_path), vrt)

    if vrt_path.exists(): vrt_path.unlink()

    return out_path

def merge(out_path, *input_paths):
    options = gdal.BuildVRTOptions(separate=False, srcNodata=-9999, VRTNodata=-9999) # TODO Avoid hardcoding
    x = [str(x) for x in input_paths]
    var = gdal.BuildVRT("combo.vrt", x, options=options)
    var = None

    gdal.Translate(str(out_path), 'combo.vrt')
    Path('combo.vrt').unlink()

    return out_path

def tile(*raster_paths, tile_size=244, data_type="stacked"):
    tile_dir = singleraster_tiling(tile_size, *raster_paths, data_type=data_type)
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

    # reprojected_raster_paths = reproject(*all_paths_list, target_raster_path = target_raster_path)
    reprojected_raster_paths = all_paths_list
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

def run_multiple_default_preprocessing(project_dir, s2_zip_paths, extract_dict=None, set_type='inference', delete_all=True):
    Mtic, mtic = time.time(), time.time()
    num_images, num_steps = len(s2_zip_paths), 7*len(s2_zip_paths)+2
    project_dir = Path(project_dir)

    print(f"o---o---o---o---o---o---o\tNot Started \t\t\t(0/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
    if extract_dict is None:
        extract_dict = EXTRACT_DICT

    s2_list, dem_list = [], []
    stacked_training_s2_paths, stacked_training_dem_paths, stacked_inference_paths = [], [], []
    for k, s2_zip_path in enumerate(s2_zip_paths):
        step_folder = project_dir/s2_zip_path.stem
        step_folder.mkdir(parents=True, exist_ok=True)
        
        step_s2_list = extract(s2_zip_path, step_folder, extract_dict)
        print(f"•---o---o---o---o---o---o\tSentinel bands extracted \t({7*k+1}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
        mtic=time.time()

        step_s2_list = convert(step_s2_list, step_folder)
        s2_list.extend(step_s2_list)
        step_target_raster_path = step_s2_list[0]
        print(f"•---•---•---•---o---o---o\tSentinel images converted \t({7*k+2}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
        mtic=time.time()

        step_dem_path = download_dem(step_target_raster_path, step_folder)
        print(f"•---•---o---o---o---o---o\tDEM downloaded \t\t\t({7*k+3}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
        mtic=time.time()

        step_dem_path = clip_dem(step_dem_path, step_target_raster_path, step_folder)
        print(f"•---•---•---o---o---o---o\tDEM clipped \t\t\t({7*k+4}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
        mtic=time.time()

        step_dem_list = process_dem(step_dem_path, step_folder)
        print(f"•---•---•---•---o---o---o\tDEM processed \t\t\t({7*k+5}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
        mtic=time.time()

        step_dem_list = reproject(*step_dem_list, target_raster_path=step_target_raster_path)
        step_s2_list = reproject(*step_s2_list, target_raster_path=step_target_raster_path)
        print(f"•---•---•---•---•---o---o\tReprojections completed \t({7*k+6}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
        mtic=time.time()

        if set_type == 'inference':
            step_all_paths = step_s2_list + step_dem_list
            step_stacked_path = stack(step_folder, *step_all_paths)
            stacked_inference_paths.append(step_stacked_path)
            stacked_paths = stacked_inference_paths
            print(f"•---•---•---•---•---•---o\tAll bands stacked \t\t({7*k+7}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
            mtic=time.time()
        
        elif set_type == 'training':
            step_stacked_s2_path = stack(step_folder, *step_s2_list, data_type='S2-stack')
            step_stacked_dem_path = stack(step_folder, *step_dem_list, data_type='DEM-stack')
            stacked_training_s2_paths.append(step_stacked_s2_path)
            stacked_training_dem_paths.append(step_stacked_dem_path)
            stacked_paths = stacked_training_s2_paths + stacked_training_dem_paths
            print(f"•---•---•---•---•---•---o\tAll bands stacked \t\t({7*k+7}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
            mtic=time.time()

    if set_type == 'inference':
        merged_path = merge(project_dir/f"{project_dir.name}.tif", *stacked_inference_paths)
        print(f"•---•---•---•---•---•---•\tStacked Paths merged \t\t({7*num_images+1}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
        mtic=time.time()

        tile_dir = singleraster_tiling(244, merged_path, data_type="stacked")
        print(f"•---•---•---•---•---•---•\tTiles ready for inference \t({7*num_images+2}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")

    elif set_type == 'training':
        merged_dem_path = merge(project_dir/f"DEM-stack.tif", *stacked_training_dem_paths)
        merged_s2_path = merge(project_dir/f"S2-stack.tif", *stacked_training_s2_paths)
        print(f"•---•---•---•---•---•---•\tStacked Paths merged \t\t({7*num_images+1}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
        mtic=time.time()

        s2_tile_dir = singleraster_tiling(244, merged_s2_path, data_type="S2-stack")
        dem_tile_dir = singleraster_tiling(244, merged_dem_path, data_type="DEM-stack")
        tile_dir = (s2_tile_dir, dem_tile_dir)
        print(f"•---•---•---•---•---•---•\tTiles ready for inference \t({7*num_images+2}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")

    if delete_all:
        for s2_path in s2_list:
            Path(s2_path).unlink()

        for dem_path in dem_list:
            Path(dem_path).unlink()

        for stacked_path in stacked_paths:
            Path(stacked_path).unlink()

        if set_type == 'inference': Path(merged_path).unlink()
        if set_type == 'training':
            merged_dem_path.unlink()
            merged_s2_path.unlink()
            
        print("Unnecessary project files removed.")


    return tile_dir    
