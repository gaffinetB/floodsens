import time
import shutil
from pathlib import Path
from osgeo import gdal
from osgeo import gdalconst
from floodsens._tile import singleraster_tiling
from floodsens._dem import flow_accumulation, hand, slope, twi, download_dem
from floodsens._reproject import reproject_set, reproject_from_raster
from floodsens.utils import extract
from floodsens.logger import logger
from floodsens.constants import EXTRACT_LIST


def clip_dem(dem_path, target_raster_path, project_dir):
    reproject_from_raster(dem_path, target_raster_path, -9999, project_dir, xRes=30.0, yRes=30.0)
    return dem_path

def process_dem(dem_path, out_dir):
    dem_path = Path(dem_path)
    slope_path = slope(dem_path, out_dir)
    fa_path = flow_accumulation(dem_path, out_dir, out_name="FA.tif")
    hand_path = hand(dem_path, out_dir, out_name="HAND.tif")
    twi_path = twi(dem_path, fa_path, out_dir, out_name="TWI.tif")

    paths_list = [dem_path, slope_path, fa_path, hand_path, twi_path]
    return paths_list

def convert_to_tif(s2_paths, folder):
    folder = Path(folder)
    new_paths = []
    for s2_path in s2_paths:
        tif_path = folder/f"{s2_path.stem}.tif"
        gdal.Translate(str(tif_path), str(s2_path))
        new_paths.append(tif_path)
        s2_path.unlink()

    return new_paths

def reproject_resample(*raster_paths, target_raster_path=None, nan_value=-9999, output_type=gdalconst.GDT_Float32): # Needed for resolution change
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

def run_default_preprocessing(project_dir, s2_zip_paths, extract_list=None, delete_all=True):
    Mtic, mtic = time.time(), time.time()
    num_images, num_steps = len(s2_zip_paths), 7*len(s2_zip_paths)+2
    project_dir = Path(project_dir)

    logger.info(f"Not Started \t\t\t(0/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
    if extract_list is None:
        extract_list = EXTRACT_LIST

    s2_list, dem_list, extract_folder_list, stacked_inference_paths = [], [], [], []

    for k, s2_zip_path in enumerate(s2_zip_paths):
        step_folder = project_dir/s2_zip_path.stem
        step_folder.mkdir(parents=True, exist_ok=True)
        extract_folder_list.append(step_folder)

        step_s2_list = extract(s2_zip_path, step_folder, extract_list)
        logger.info(f"Sentinel bands extracted \t({7*k+1}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
        mtic=time.time()

        step_s2_list = convert_to_tif(step_s2_list, step_folder)
        s2_list.extend(step_s2_list)
        step_target_raster_path = step_s2_list[0]
        logger.info(f"Sentinel images converted \t({7*k+2}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
        mtic=time.time()

        step_dem_path = download_dem(step_target_raster_path, step_folder)
        logger.info(f"DEM downloaded \t\t\t({7*k+3}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
        mtic=time.time()

        step_dem_path = clip_dem(step_dem_path, step_target_raster_path, step_folder)
        logger.info(f"DEM clipped \t\t\t({7*k+4}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
        mtic=time.time()

        step_dem_list = process_dem(step_dem_path, step_folder)
        logger.info(f"DEM processed \t\t\t({7*k+5}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
        mtic=time.time()

        step_dem_list = reproject_resample(*step_dem_list, target_raster_path=step_target_raster_path)
        step_s2_list = reproject_resample(*step_s2_list, target_raster_path=step_target_raster_path)
        logger.info(f"Reprojections completed \t({7*k+6}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
        mtic=time.time()

        step_all_paths = step_s2_list + step_dem_list
        step_stacked_path = stack(step_folder, *step_all_paths)
        stacked_inference_paths.append(step_stacked_path)
        stacked_paths = stacked_inference_paths
        logger.info(f"All bands stacked \t\t({7*k+7}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
        mtic=time.time()

    merged_path = merge(project_dir/f"{project_dir.name}.tif", *stacked_inference_paths)
    logger.info(f"Stacked Paths merged \t\t({7*num_images+1}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")
    mtic=time.time()

    tile_dir = singleraster_tiling(244, merged_path, data_type="stacked")
    logger.info(f"Tiles ready for inference \t({7*num_images+2}/{num_steps} - {time.time()-mtic:.2f}s|{time.time()-Mtic:.2f}s)")

    if delete_all:
        for s2_path in s2_list:
            Path(s2_path).unlink()

        for dem_path in dem_list:
            Path(dem_path).unlink()

        for stacked_path in stacked_paths:
            Path(stacked_path).unlink()

        Path(merged_path).unlink()

        for extract_folder in extract_folder_list:
            shutil.rmtree(extract_folder)

        logger.info("Unnecessary project files removed.")

    return tile_dir
