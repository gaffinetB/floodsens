"""Module containing all DEM related functions. Includes download and processing."""
import subprocess
from pathlib import Path
from pysheds.grid import Grid
import pysheds.io
import numpy as np
from osgeo import gdal
from osgeo import gdalconst
import demloader as dl
from floodsens.logger import logger

def download_dem(s2_path, out_dir, out_name="10_DEM.tif"):
    """Download DEM from AWS and return path to file.

    Parameters:
        s2_path (str): Path to Sentinel-2 file
        out_dir (str): Path to output directory
        out_name (str): Name of output file

    Returns:
        dem_path (str): Path to DEM file"""
    prefixes = dl.prefixes.get_from_raster(s2_path, 30)
    dem_path = dl.download.from_aws(prefixes, 30, f"{out_dir}/{out_name}")
    return dem_path

def slope(dem_path, out_dir, out_name="11_Slope.tif"):
    """Calculate slope using gdaldem and write to disk. Return path to file.
    
    Parameters:
        dem_path (str): Path to DEM file
        out_dir (str): Path to output directory
        out_name (str): Name of output file
    
    Returns:
        out_path (str): Path to output file
        """
    out_path = Path(out_dir)/out_name
    subprocess.call(['gdaldem', 'slope', '-p', str(dem_path), str(out_path)])
    return out_path

def flow_accumulation(dem_path, out_dir, out_name="12_Flowaccumulation.tif"):
    """
    Calculate flow accumulation using pysheds and write to disk. Return path to file.

    Parameters:
        dem_path (str): Path to DEM file
        out_dir (str): Path to output directory
        out_name (str): Name of output file
    
    Returns:
        out_path (str): Path to output file
    """
    dem_path = str(dem_path)
    grid = Grid.from_raster(dem_path)
    logger.debug("Grid created")
    dem = grid.read_raster(dem_path)
    dem = grid.fill_depressions(dem)
    dem = grid.resolve_flats(dem)
    dem = grid.flowdir(dem)
    flowaccumulation = grid.accumulation(dem)
    logger.debug(f"Flow accumulation calculated with shape: {flowaccumulation.shape}")

    out_path = f"{out_dir}/{out_name}"
    pysheds.io.to_raster(flowaccumulation, out_path)
    logger.info("Flow accumulation written to disk at " + str(out_path) + "!")

    return out_path

def hand(dem_path, out_dir, out_name="13_HAND.tif"):
    """Calculate HAND using pysheds and write to disk. Return path to file.
    
    Parameters:
        dem_path (str): Path to DEM file
        out_dir (str): Path to output directory
        out_name (str): Name of output file
    
    Returns:
        out_path (str): Path to output file"""
    dem_path = str(dem_path)
    grid = Grid.from_raster(dem_path)
    dem = gdal.Open(str(dem_path), gdal.GA_ReadOnly).ReadAsArray()
    dem = grid.read_raster(dem_path)
    dem = grid.fill_depressions(dem)
    dem = grid.resolve_flats(dem)
    flow_direction = grid.flowdir(dem)
    flow_accumulation_raster = grid.accumulation(flow_direction)

    hand_raster = grid.compute_hand(flow_direction, dem, flow_accumulation_raster>1)

    out_path = f"{out_dir}/{out_name}"
    pysheds.io.to_raster(hand_raster, out_path)
    logger.info(f"HAND calculated and written to disk at {out_path}!")

    return out_path

def twi(dem_path, flow_accumulation_path, out_dir, out_name="14_TWI.tif", save_slope=True):
    """Calculate TWI using pysheds and write to disk. Return path to file.
    Computes slope as a by-product which is saved to disk if save_slope is True.
    
    Parameters:
        dem_path (str): Path to DEM file
        flow_accumulation_path (str): Path to flow accumulation file
        out_dir (str): Path to output directory
        out_name (str): Name of output file
        save_slope (bool): Save slope to disk or not
        
    Returns:
        out_path (str): Path to output file"""
    dem_path = str(dem_path)
    flow_accumulation_array = gdal.Open(str(flow_accumulation_path), gdal.GA_ReadOnly).ReadAsArray()
    dem = gdal.Open(str(dem_path), gdal.GA_ReadOnly)

    if save_slope:
        slope_degrees = gdal.DEMProcessing(f"{out_dir}/11_Slope.tif", dem, "slope", computeEdges=True)
    else:
        slope_path = f"{str(out_dir)}/_twi_slope.tif"
        slope_degrees = gdal.DEMProcessing(slope_path, dem, "slope", computeEdges=True)
        Path(slope_path).unlink()

    slope_degrees_array = slope_degrees.ReadAsArray()
    slope_radians_array = np.radians(slope_degrees_array)

    # twi_array = np.where(flow_accumulation_array==0, 0, np.log(flow_accumulation_array/np.tan(slope_radians_array)))
    twi_array = np.where(slope_radians_array==0, 0, np.log(flow_accumulation_array/np.tan(slope_radians_array)))

    out_path = f"{out_dir}/{out_name}"
    driver = gdal.GetDriverByName("GTiff")
    driver.Register()

    outds = driver.Create(str(out_path), dem.RasterXSize, dem.RasterYSize, 1, gdal.GDT_Float32)
    outds.SetGeoTransform(dem.GetGeoTransform())
    outds.SetProjection(dem.GetProjection())

    outband = outds.GetRasterBand(1)
    outband.WriteArray(twi_array)
    outband.SetNoDataValue(np.nan)
    outband.FlushCache()
    outband=0
    outds=0

    return out_path

def fix_hand(hand_path, overwrite=True):
    """Fix HAND raster by replacing NaN values with mean of surrounding cells.
    
    Parameters:
        hand_path (str): Path to HAND file
        overwrite (bool): Overwrite original file or create new file with "f" prefix
        
    Returns:
        out_path (str): Path to output file"""
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
