from floodsens.logger import logger
from osgeo import gdal, gdalconst, ogr
import numpy as np
import geopandas as gpd


def rasterize(shape_path, raster_path, out_path, no_data=-9999):
    """Takes shapefile and turns it into a raster with the same resolution, 
    projection and geotransform as in the provided raster. Returns None if 
    processing is skipped due to errors.
    
    Parameters
    ----------
    shape_path:     str or PosixPath
                    path to shapefile to be transformed
    raster_path:    str or PosixPath
                    path to raster that provides target projection, geotransform
                    and resolution. Tested for GeoTIFF and JP2000
    out_path:       str or PosixPath
                    path at which resulting output is saved
    no_data:        int, float or np.nan
                    no data value for output raster
    
    Returns:
    ----------
    out_path:       PosixPath
                    path to output raster. Return None if processing was skipped.

    """
    if isinstance(raster_path, list):
        if len(raster_path) == 1:
            raster_path = raster_path[0]
        else:
            logger.warning(f"Multiple Rasters provided for label rasterization. Label Processing skipped!")
            return None

    ds = gdal.Open(str(raster_path), gdalconst.GA_ReadOnly)

    gt = ds.GetGeoTransform()
    x_res = ds.RasterXSize
    y_res = ds.RasterYSize
    raster_xmin = gt[0]
    raster_ymax = gt[3]
    raster_xmax = raster_xmin + gt[1] * ds.RasterXSize
    raster_ymin = raster_ymax + gt[5] * ds.RasterYSize    

    shapefile = ogr.Open(str(shape_path))
    shapefile_layer = shapefile.GetLayer()

    gdf = gpd.read_file(shape_path)
    shape_extent = gdf.geometry.total_bounds
    shp_xmin, shp_ymin = shape_extent[0], shape_extent[2]
    shp_xmax, shp_ymax = shape_extent[1], shape_extent[3]    

    logger.info(f"Raster extent [{raster_xmin},{raster_xmax},{raster_xmin},{raster_ymax}] and Label extent [{shape_extent[0]},{shape_extent[1]},{shape_extent[2]},{shape_extent[3]}]")

    # if (shp_xmin > raster_xmax or shp_xmax < raster_xmin or shp_ymax < raster_ymin or shp_ymin > raster_ymax):
    #     logger.warning("The shapefile and raster do not overlap. Label processing skipped!")
    #     return None    

    driver = gdal.GetDriverByName('GTiff')
    driver.Register()
    target_ds = driver.Create(str(out_path), x_res, y_res, 1, gdalconst.GDT_Byte)
    target_ds.SetProjection(ds.GetProjection())
    target_ds.SetGeoTransform(gt)
    band = target_ds.GetRasterBand(1)
    band.SetNoDataValue(no_data)
    band.FlushCache()
    gdal.RasterizeLayer(target_ds, [1], shapefile_layer)
    target_ds = None

    return out_path

def binarize(label_path, out_path):
    """Takes rasterized labels and creates a raster with binary entries. All entries larger than 0
    will be assigned 1 while all negative values are assigned the value of 0.
    
    Parameters
    ----------
    label_path:     str or PosixPath
                    path to raster GeoTIFF file
    out_path:       str or PosixPath
                    path at which resulting output is saved
    
    Return
    ----------
    out_path:       PosixPath
                    path of computed output
    """
    ds = gdal.Open(str(label_path))
    arr = ds.ReadAsArray()
    arr = np.where(arr>0, 1, 0)
    gt = ds.GetGeoTransform()
    proj = ds.GetProjection()
    driver = gdal.GetDriverByName('GTiff')
    driver.Register()
    outds = driver.Create(str(out_path),
                         xsize = arr.shape[1],
                         ysize = arr.shape[0],
                         bands = 1)
    outds.SetProjection(proj)
    outds.SetGeoTransform(gt)
    outds.GetRasterBand(1).WriteArray(arr)
    outds = None

    return out_path
