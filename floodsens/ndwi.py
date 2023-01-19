import floodsens.preprocessing as preprocessing
from osgeo import gdal
from pathlib import Path

def compute_ndwi(archives, threshold, project_dir):
    temp_dir = Path(f"{project_dir}/temp")
    temp_dir.mkdir(exist_ok=True)

    ndwi_paths = []
    for k, archive in enumerate(archives):
        # Setup save path
        ndwi_path = Path(f"{temp_dir}/ndwi_{k}.tif")

        # Extract B08 and B03 from archive
        extracted_bands = preprocessing.extract(archive, project_dir, {"10m": "B03", "10m": "B08"})

        # Read B08 and B03 as arrays with gdal
        b03 = gdal.Open(extracted_bands[0])
        b03_arr = b03.ReadAsArray()
        b08 = gdal.Open(extracted_bands[1])
        b08_arr = b08.ReadAsArray()

        # Compute NDWI
        ndwi = (b08_arr - b03_arr) / (b08_arr + b03_arr)

        # Save NDWI to disk with gdal
        driver = gdal.GetDriverByName("GTiff")
        driver.Register()
        ndwi_ds = driver.Create(ndwi_path, ndwi.shape[1], ndwi.shape[0], 1, gdal.GDT_Float32)
        ndwi_ds.GetRasterBand(1).WriteArray(ndwi)

        # Set projection and geotransform based on B03
        ndwi_ds.SetProjection(b03.GetProjection())
        ndwi_ds.SetGeoTransform(b03.GetGeoTransform())

        # Save ndwi_ds to disk
        ndwi_ds.FlushCache()

        ndwi_paths.append(str(ndwi_path))
    
    # Create vrt from ndwi_paths
    gdal.BuildVRT(str(temp_dir/"ndwi.vrt"), ndwi_paths, vrt_options=gdal.BuildVRTOptions())
    merged_ndwi_path = str(temp_dir/"ndwi.tif")
    gdal.Translate(merged_ndwi_path, str(temp_dir/"ndwi.vrt"), format="GTiff")

    return merged_ndwi_path
