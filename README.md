# FloodSENS Library

FloodSENS is a Machine Learning Project with the goal to identify floods in optical satellite data (Sentinel-2) even in the presence of clouds.
The present library allows the user to run inference on any Sentinel-2 data product with processing level L2A. A digital elevation model is automatically downloaded and additional quantities dervied, namely: Slope; Flow Accumulation, Height Above Nearest Drainage; Topographic Wetness Index. All 5 DEM based bands are required to run inference and can be produced using this library.

The trained models ready for inference can be downloaded at **TODO Coming soon**.

## Installation

FloodSENS inference library is available on PyPi.org and hence installable with pip vis `pip install floodsens`.
Before running the pip command GDAL needs to be installed on the computer system.

## Intended Use

The core of the library is the `Project` class which includes all needed methods to go from the initial Sentinel-2 data in zip format to the final map resulting from inference in GeoTIFF format. Down below is a code snippet to perform a full inference run.

```Python
import floodsens as fs

# Inputs required by the user:
project_dir = "example_project/"
sentinel_path = "example_project/zip/S2A_example.zip"
model_path = "example_project/models/Model_exampleA/model.pth"
output_path = "exmaple_project/output_map.tif"

# Running the library as intended:
project = fs.project.Project(project_dir, sentinel_path)
project.default_processing()
project.choose_model(model_path)
project.run_inference()
project.save_map(output_path)
```

Code to run individual steps of preprocessing is available in `floodsens.preprocessing`.

## Example Results

**TODO**