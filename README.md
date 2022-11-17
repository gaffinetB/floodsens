# FloodSENS Inference Library

FloodSENS is a Machine Learning Project with the goal to detecting floods in optical satellite data (Sentinel-2) even in the presence of clouds.
The present library allows the user to run inference on Sentinel-2 data product with processing level L2A. A digital elevation model is automatically downloaded and additional quantities dervied, namely: Slope; Flow Accumulation, Height Above Nearest Drainage; Topographic Wetness Index. All 5 DEM based bands are required to run inference and can be produced using this library.

The trained models ready for inference can be downloaded at:

https://services.rss-hydro.lu/nextcloud/index.php/s/5kCMGB8SDQsgxMd.

## Installation & Prerequisites

1. **GDAL** is required. Consult https://gdal.org/index.html to download and install it.
1. Install floodsens with pip -> `pip install floodsens`
1. Sentinel-2 images are required which can be downloaded on https://scihub.copernicus.eu/ which requires registration

## Intended Use (version `0.1.7`)

The core object of the library is the `Project` class which includes all needed methods to go from the initial Sentinel-2 data in zip format to the final map resulting from inference in GeoTIFF format. Down below is a code snippet to perform a full inference run.

```Python
# Import library
import floodsens as fs

# Inputs required by the user:
project_dir = "example_project/"
sentinel_path = "example_project/zip/S2A_example.zip"
model_path = "example_project/models/Model_exampleA/model.pth.tar"
output_path = "exmaple_project/output_map.tif"

# Running the library as intended:
project = fs.project.Project(project_dir, sentinel_path)
project.default_processing()
project.load_model(model_path)
project.run_inference()
project.save_map(output_path)
```

The result will be available as GeoTIFF at `output_path`.

## Example Use and Results

**TODO**