# ------------------------------------------------------------------------------
# DEM download  ----------------------------------------------------------------
# ------------------------------------------------------------------------------

"""
If run as main, the different functions get called based on the
input "TESTFILENAME" path. There are 3 relevant functions:

get_prefixes: This takes as input the name of the file to get
the DEM for, and it outputs a list of associated s3 paths providing
overlapping Copernicus DEM files.

download_coreg_from_prefix: This takes the list of Copernicus DEM
file paths and it downloads the associated DEM's before aggregating
them into a TIF file coregistered to the original input. It also
does some file creation and deletion in the process, in a folder
specified in variable TEMPPATH.

get_copernicus_dem: Calls both these functions subsequently to
create the DEM based on a given input GeoTiff.
"""
from botocore.config import Config
from botocore import UNSIGNED
from pathlib import Path
import boto3
import rasterio
from osgeo import gdal

from pyproj import Proj, transform


def _get_prefixes(raster_path):
    """
    Opens raster at provided location and extracts prefixes for S3 query.

    Parameters
    ----------
    raster_path :   string or PosixPath
                    path to raster to be opened and extracted

    Returns
    ----------
    prefixes :      list of strings
                    list of prefixes for S3 download
    """
    ds_raster = rasterio.open(str(raster_path))
    print(f"loaded raster:\t{ds_raster}")
    epsg = str(ds_raster.read_crs().to_epsg())
    zone_letter = 'N' if epsg[2] == '6' else 'S'

    if epsg[2] == '6':
        zone_letter = 'N'
    elif epsg[2] == '7':
        zone_letter = 'S'
    else:
        zone_letter = None
    #print('Zone Letter: ', zone_letter)
    bounds = ds_raster.bounds
    #print(bounds)
    #print(epsg)

    inProj = Proj(init='epsg:'+epsg) # not yet tested if also with utm
    outProj = Proj(init='epsg:4326')

    lower_left = transform(inProj,outProj,bounds.left,bounds.bottom)
    upper_right = transform(inProj,outProj,bounds.right,bounds.top)

    lower_left = lower_left[::-1]
    upper_right = upper_right[::-1]

    print(lower_left)
    print(upper_right)

    # in case Proj doesnt do utm natively
    #lower_left = utm.to_latlon(bounds.left, bounds.bottom, int(
    #    epsg[-2:]), zone_letter=zone_letter)
    #upper_right = utm.to_latlon(bounds.right, bounds.top, int(
    #    epsg[-2:]), zone_letter=zone_letter)

    if zone_letter == 'S':
        lower_left = list(lower_left)
        upper_right = list(upper_right)
        lower_left_temp = lower_left[0]
        upper_right_temp = upper_right[0]
        lower_left[0] = -(90. - upper_right_temp)
        upper_right[0] = -(90. - lower_left_temp)

    needed_northing = [int(lower_left[0])]
    if (int(lower_left[0]) - int(upper_right[0])) != 0:
        needed_northing.append(int(upper_right[0]))
    needed_easting = [int(lower_left[1])]
    if (int(lower_left[1]) - int(upper_right[1])) != 0:
        needed_easting.append(int(upper_right[1]))

    if zone_letter == 'S':
        needed_northing = list(
            range(min(needed_northing)-2, max(needed_northing)+1))
        needed_easting = list(
            range(min(needed_easting)-3, max(needed_easting)-2))
    elif zone_letter == 'N':
        needed_northing = list(
            range(min(needed_northing), max(needed_northing)+1))
        needed_easting = list(
            range(min(needed_easting)-2, max(needed_easting)+1))
    else:
        needed_northing = list(
            range(min(needed_northing), max(needed_northing)+1)
        )
        needed_easting = list(
            range(min(needed_easting), max(needed_easting)+1)
        )

    # POTENTIAL ASSUMPTION: NOT ON EQUATOR OR GREENWICH
    if needed_northing[0] >= 0:
        n_letter = 'N'
    else:
        n_letter = 'S'
        needed_northing = [abs(nn) for nn in needed_northing]

    if needed_easting[0] >= 0:
        e_letter = 'E'
    else:
        e_letter = 'W'
        needed_easting = [abs(ne) for ne in needed_easting]

    prefixes = []
    for north in needed_northing:
        north_string = str(north).zfill(2)
        for east in needed_easting:
            east_string = str(east).zfill(3)
            pfx = 'Copernicus_DSM_COG_10_' + n_letter + north_string + \
                '_00_' + e_letter + east_string + '_00_DEM'
            prefixes.append(pfx)

    return prefixes

def _download_coreg_from_prefix(prefixes,
                                out_dir='.',
                                coregfile=None,
                                sampling_alg=gdal.gdalconst.GRA_NearestNeighbour):
    
    out_dir = Path(out_dir)
    temp_dir = Path(out_dir)/"temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    fn_dem_combo_vrt = temp_dir/'combo.vrt'

    pfx = prefixes[0]
    fn_dem_utm_fin = out_dir/"10_DEM.tif"

    s3_resource = boto3.resource('s3', config=Config(signature_version=UNSIGNED))
    my_bucket = s3_resource.Bucket('copernicus-dem-30m')

    downloaded = []

    for pfx in prefixes:
        objs = my_bucket.objects.filter(Prefix=pfx)
        if len(list(objs.all())) > 0:
            for obj in objs:
                fn_dem = temp_dir/f"{pfx}.tif"
                my_bucket.download_file(obj.key, str(fn_dem))
                downloaded.append(str(temp_dir/f"{pfx}.tif"))

    if len(downloaded) > 1:
        gdal.BuildVRT(str(fn_dem_combo_vrt), downloaded)

    if coregfile is None:
        gdal.Translate(str(fn_dem_utm_fin), str(fn_dem_combo_vrt))
        [file_to_delete.unlink() for file_to_delete in Path(temp_dir).glob('*')]
        temp_dir.rmdir()

    if coregfile:
        raise NotImplementedError("Coregistration not correctly implemented. Skipped!")
        warp_options = gdal.WarpOptions(resampleAlg = sampling_alg)
        gdal.Warp(options = warp_options)

    return fn_dem_utm_fin

def get_copernicus_dem(raster_path, out_dir, coregister=None):
    """
    Test get_dem_prefixes and download_coreg_from_prefix here.

    Parameters
    ----------
    raster_path :   string or PosixPath 
                    Path to (preferably GeoTiff) file to specify the region
                    where to grab the Copernicus DEM.
    out_dir :       string or PosixPath
                    Path to directory to save output DEM.
    """
    prefixes = _get_prefixes(raster_path)
    if coregister is None:
        dem_path = _download_coreg_from_prefix(prefixes,
                                            out_dir=out_dir)
    
    else:
        dem_path = _download_coreg_from_prefix(prefixes,
                                            out_dir=out_dir,
                                            coregfile=raster_path,
                                            sampling_alg = gdal.gdalconst.GRA_Cubic)
    return dem_path
