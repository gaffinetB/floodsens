from pysheds.grid import Grid
from pathlib import Path
import numpy as np
from osgeo import gdal
from osgeo import gdalconst
import subprocess

def slope(dem_path, out_dir):
    out_path = Path(out_dir)/"11_Slope.tif"
    subprocess.call(['gdaldem', 'slope', '-p', str(dem_path), str(out_path)])
    return out_path

def flow_accumulation(dem_path, out_dir, out_name="12_Flowaccumulation.tif"):
    """
    Reads DEM at dem_path. Computes flow accumulation and saves in out_dir.
    Returns flow accumuation array for further computations.

    Parameters
    ----------
    dem_path :  string or PosixPath
                path to input dem in .tif format
    out_dir :   string or PosixPath
                output directory for flow accumulation raster

    Returns
    ----------
    flow_accumulation_array:    ndarray
                ndarray of the computed flow accumulation
    """
    grid = Grid.from_raster(dem_path, data_name='dem')
    dem = grid.dem

    grid.fill_depressions(data='dem', out_name='flooded_dem')
    
    grid.resolve_flats(data='flooded_dem', out_name='inflated_dem')
    
    grid.flowdir(data='inflated_dem', out_name='dir')
    
    flow_accumulation_array = grid.accumulation(data='dir', inplace=False)
    
    out_path = out_dir/out_name
    driver = gdal.GetDriverByName('GTiff')
    driver.Register()

    outds = driver.Create(str(out_path), xsize=dem.shape[1], ysize=dem.shape[0],
                          bands=1, eType=gdal.GDT_Float32)
    
    ds = gdal.Open(str(dem_path), gdal.GA_ReadOnly)
    outds.SetGeoTransform(ds.GetGeoTransform())
    outds.SetProjection(ds.GetProjection())

    outband = outds.GetRasterBand(1)
    outband.WriteArray(flow_accumulation_array)
    outband.SetNoDataValue(np.nan)
    outband.FlushCache()
    outband = None
    outds = None    
    
    return grid, out_path

def hand(grid, dem_path, flow_accumulation_path, out_dir, out_name="13_HAND.tif"):
    flow_accumulation_array = gdal.Open(str(flow_accumulation_path)).ReadAsArray()

    HAND = grid.compute_hand('dir', 'dem', flow_accumulation_array>1, inplace=False)
    out_path = out_dir/out_name
    driver = gdal.GetDriverByName('GTiff')
    driver.Register()
    outds = driver.Create(str(out_path), xsize=grid.dem.shape[1], ysize=grid.dem.shape[0],
                          bands=1, eType=gdal.GDT_Float32)
    ds = gdal.Open(str(dem_path))
    outds.SetGeoTransform(ds.GetGeoTransform())
    outds.SetProjection(ds.GetProjection())

    outband = outds.GetRasterBand(1)
    outband.WriteArray(HAND)
    outband.SetNoDataValue(np.nan)
    outband.FlushCache()
    outband = None
    outds = None

    return out_path

def twi(dem_path, flow_accumulation_path, out_dir, out_name="14_TWI.tif"):
    flow_accumulation_array = gdal.Open(str(flow_accumulation_path)).ReadAsArray()

    dem = gdal.Open(str(dem_path))
    slope_degrees = gdal.DEMProcessing("slope.tif", dem, "slope", computeEdges=True)
    array_slope_degrees = slope_degrees.ReadAsArray()
    array_slope_radians = np.radians(array_slope_degrees)
    TWI = np.where(array_slope_radians==0, 0, np.log(flow_accumulation_array/np.tan(array_slope_radians)))
    out_path = out_dir/out_name
    driver = gdal.GetDriverByName('GTiff')
    driver.Register()
    dem_array = dem.ReadAsArray()
    outds = driver.Create(str(out_path), xsize=dem_array.shape[1], ysize=dem_array.shape[0],
                          bands=1, eType=gdal.GDT_Float32)

    outds.SetGeoTransform(dem.GetGeoTransform())
    outds.SetProjection(dem.GetProjection())

    outband = outds.GetRasterBand(1)
    outband.WriteArray(TWI)
    outband.SetNoDataValue(np.nan)
    outband.FlushCache()
    outband = None
    outds = None

    return out_path

def fix_hand(hand_path, overwrite=True):
    hand_ds = gdal.Open(str(hand_path))
    hand_proj = hand_ds.GetProjection()
    hand_gt = hand_ds.GetGeoTransform()

    hand_array = hand_ds.ReadAsArray()
    for i in range(hand_array.shape[0]):
        for k in range(hand_array.shape[1]):
            if np.isnan(hand_array[i,k]):
                hand_array[i,k] = np.nanmean(hand_array[i-2:i+3, k-2:k+3])
    hand_array = np.where(np.isnan(hand_array), 0, hand_array)

    if overwrite: out_path = hand_path
    else: out_path = hand_path.parent/f"f{hand_path.name}"
    
    driver = gdal.GetDriverByName("GTiff")
    driver.Register()
    outds = driver.Create(str(out_path),
                    xsize=hand_array.shape[1],
                    ysize=hand_array.shape[0],
                    bands=1,
                    eType=gdalconst.GDT_Float32)
    outds.SetProjection(hand_proj)
    outds.SetGeoTransform(hand_gt)

    outds.GetRasterBand(1).WriteArray(hand_array)
    outds = None    
