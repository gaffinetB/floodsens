from osgeo import gdal
import numpy as np
from pathlib import Path


def _get_information(raster_path):
    """
    Extracts geotransform, projection, nan value and output boundaries from
    raster and returns it in a dictionary which also includes the raster
    itself.

    Parameters
    ----------
    raster_path :   str or PosixPath
                    path to raster for which information should be extracted

    Returns
    ----------
    information :   dict
                    dictionary containing the following key, value pairs:
                        "raster": raster (gdal.Dataset)
                        "projection": projection (str)
                        "geotransform": geotransform (tuple, 6 values)
                        "output_bounds": outputBbox (tuple, 4 values)
                        "nan_value": raster_NA_value (nan or int or float)
    """
    if not Path(raster_path).exists():
        print(f"{raster_path} does not exist!")
    raster = gdal.Open(str(raster_path), gdal.GA_ReadOnly)
    if raster is None:
        print(f"Opening {raster_path} failed resulting in NoneType")
    raster_band1 = raster.GetRasterBand(1)
    projection = raster.GetProjection()
    geotransform = raster.GetGeoTransform()

    raster_NA_value = raster_band1.GetNoDataValue()

    minX, maxY = geotransform[0], geotransform[3]
    maxX = minX + geotransform[1] * raster.RasterXSize
    minY = maxY + geotransform[5] * raster.RasterYSize

    outputBbox = (minX, minY, maxX, maxY)

    information = {
        "raster": raster,
        "path": Path(raster.GetDescription()),
        "projection": projection,
        "geotransform": geotransform,
        "output_bounds": outputBbox,
        "nan_value": raster_NA_value
    }

    return information

def reproject_from_parameters(source_path, target_information, target_nan, out_dir=None, xRes=None, yRes=None):
    """
    Reproject raster at source_path based on information provided through 
    target information which is a dictionary.
    """
    if out_dir is None:
        out_dir = source_path.parent
    source_path = Path(source_path)
    source_information = _get_information(source_path)

    if xRes is None: xRes = abs(target_information["geotransform"][1]) 
    if yRes is None: yRes = abs(target_information["geotransform"][5]) 

    aoWarpOptions = gdal.WarpOptions(resampleAlg=gdal.gdalconst.GRA_Bilinear,
                                     srcSRS=source_information["projection"],
                                     dstSRS=target_information["projection"],
                                     xRes=xRes,
                                     yRes=yRes,
                                     outputBounds=target_information["output_bounds"],
                                     srcNodata=source_information["nan_value"],
                                     dstNodata=target_nan)

    out_path = out_dir/f"{source_path.name}"

    reprojected_raster = gdal.Warp(str(out_path),
                                   source_information["raster"],
                                   options=aoWarpOptions)

    return out_path

def reproject_from_raster(source_path, target_path, target_nan, out_dir=None, xRes=None, yRes=None):
    """
    Reprojects raster at source_path and reprojects in using information from
    raster at target_path.
    """
    source_path, target_path = Path(source_path), Path(target_path)
    if out_dir is None:
        out_dir = source_path.parent
    else:
        out_dir = Path(out_dir)

    if target_nan is None:
        # target_nan = float('nan')
        target_nan = np.nan

    target_information = _get_information(target_path)
    out_path = reproject_from_parameters(source_path, target_information, target_nan, out_dir=out_dir, xRes=xRes, yRes=yRes)
    return out_path

def reproject_set(target_path, nan, *raster_paths):
    
    reprojected_rasters = []
    for raster_path in raster_paths:
        reprojected_path = reproject_from_raster(
            raster_path, target_path, nan, out_dir=Path(raster_path).parent)
        reprojected_rasters.append(str(reprojected_path))
    
    return reprojected_rasters
