import numpy as np
from pathlib import Path
from osgeo import gdal

def multiraster_tiling(tile_size, *raster_paths, data_type=None):
    """
    Tiles rasters located at "*raster_paths" creating tiles of provided 
    "tile_size". Before tiling all rasters are reprojected based on meta data
    in "target_path".

    Parameters
    ----------
    tile_size :     integer
                    size in terms of pixels for tiles
    target_path :   string or PosixPath
                    path to raster that is used to reproject all other rasters
    *raster_paths : string or PosixPath
                    paths to rasters to be tiled together into multi band tiles
    tile_dir :      string or PosixPath
                    path to directeory into which all tiles are being saved
    overlap :       float
                    controls the overlap between two neighbouring tiles.
                    e.g:    overlap=0.1 means the overlap of two neighbouring
                            tiles corresponds to 10% of the tile size
    normalize :     TODO should distinguish between different normalization approaches
    """
    result_dir = Path(raster_paths[0]).parent
    tile_dir = result_dir/"tiles"/data_type
    out_dir = Path(tile_dir)
    out_dir.mkdir(exist_ok=True, parents=True)

    target_raster = gdal.Open(str(raster_paths[0]))
    target_geotransform = target_raster.GetGeoTransform()
    target_projection = target_raster.GetProjection()
    xmax, ymax = target_raster.RasterXSize, target_raster.RasterYSize

    full_array = np.ndarray([0, ymax, xmax])

    if len(raster_paths) == 1:
        ds_path = raster_paths[0]
        full_array = gdal.Open(str(ds_path)).ReadAsArray()
        if len(full_array.shape) < 3: full_array = np.expand_dims(full_array, axis=0)
    
    else:
        for ds_path in raster_paths:
            ds_array = gdal.Open(str(ds_path)).ReadAsArray()
            
            if len(ds_array.shape) < 3: ds_array = np.expand_dims(ds_array, axis=0)

            try: full_array = np.concatenate((full_array, ds_array), axis=0)
            except:
                raise RuntimeError("Invalid raster dimensions for multiraster tiling")
            ds_array = None
    
    bands = full_array.shape[0]

    xi, yi, tile_size = 0, 0, tile_size
    while xi+tile_size <= ymax:
        while yi+tile_size <= xmax:
            sarr = full_array[:, xi:xi+tile_size, yi:yi+tile_size]
            name = f'Tile_{xi}-{yi}.tif'
            out_geotransform = (target_geotransform[0]+yi*target_geotransform[1],
                                target_geotransform[1],
                                target_geotransform[2],
                                target_geotransform[3] +
                                xi*target_geotransform[5],
                                target_geotransform[4],
                                target_geotransform[5])

            driver = gdal.GetDriverByName('GTiff')
            driver.Register()
            outds = driver.Create(f'{out_dir}/{name}',
                                  xsize=sarr.shape[1],
                                  ysize=sarr.shape[2],
                                  bands=bands,
                                  eType=gdal.GDT_Float32)
            outds.SetProjection(target_projection)
            outds.SetGeoTransform(out_geotransform)

            for band in range(bands):
                outds.GetRasterBand(band+1).WriteArray(sarr[band])
            
            outds = None

            yi += tile_size
        xi += tile_size
        yi = 0
    
    return tile_dir
