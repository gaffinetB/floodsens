import numpy as np
from pathlib import Path
from osgeo import gdal


def singleraster_tiling(tile_size, raster_path, data_type=None):
    """
    Tiles raster located at "raster_path" creating tiles of provided "tile_size".

    Arguments:
        tile_size (int):    
            Size of resulting tiles expressed in number of pixels
        raster_path (str or Path):  
            Path to raster to be tiled
        data_type (str):
            Used to create name for folder containing the tiles. 
            Folder name will be: ./tiles/<data_type>/ 
    """
    result_dir = Path(raster_path).parent
    out_dir = result_dir/"tiles"/data_type
    out_dir.mkdir(exist_ok=True, parents=True)
    
    ds = gdal.Open(str(raster_path))

    gt = ds.GetGeoTransform()
    proj = ds.GetProjection()    
    xmax, ymax = ds.RasterXSize, ds.RasterYSize
    

    xi, yi, tile_size = 0, 0, tile_size
    while xi+tile_size <= ymax:
        while yi+tile_size <= xmax:
            sarr = ds.ReadAsArray(yi, xi, tile_size, tile_size)
            bands = sarr.shape[0]
            name = f'Tile_{xi}-{yi}.tif'
            out_gt = (gt[0]+yi*gt[1], gt[1], gt[2],
                                gt[3]+xi*gt[5],gt[4],gt[5])

            driver = gdal.GetDriverByName('GTiff')
            driver.Register()
            outds = driver.Create(f'{out_dir}/{name}',
                                  xsize=sarr.shape[1],
                                  ysize=sarr.shape[2],
                                  bands=bands,
                                  eType=gdal.GDT_Float32)
            outds.SetProjection(proj)
            outds.SetGeoTransform(out_gt)

            for band in range(bands):
                outds.GetRasterBand(band+1).WriteArray(sarr[band])
            
            outds = None

            yi += tile_size
        xi += tile_size
        yi = 0
    
    return out_dir

