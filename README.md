# FloodSENS Inference Library

FloodSENS is a Machine Learning Project to detect flood extends in optical satellite data. The current version is limited to Sentinel-2 data and most models are meant for cloudfree conditions.

The `floodsens` inference library allows the user to run inference on Sentinel-2 data products with processing level L2A. A digital elevation model is automatically downloaded and additional quantities dervied, namely: Slope; Flow Accumulation, Height Above Nearest Drainage; Topographic Wetness Index. The current version uses all 5 DEM based bands which contains some level of redundancy.

The trained models ready for inference can be downloaded at:

https://services.rss-hydro.lu/nextcloud/index.php/s/5kCMGB8SDQsgxMd.

## Installation & Prerequisites

1. **GDAL** is required. Consult https://gdal.org/index.html to download and install it.
1. Install floodsens with pip using command line `pip install floodsens`
1. Sentinel-2 images are required. (Available with free registration on https://scihub.copernicus.eu/)

## Intended Use (version `0.2.1`)
The library has a `Project` and an `Event` class that allows users to organise their data and call the processing methods. 

### Using only `Event` class

A quick and minimal way to apply a model is to initialize a `Event` instance and run the `run_floodsens` methods as shown below:

```python
from floodsens.event import Event
from floodsens.model import FloodsensModel

model = FloodsensModel("path/to/model.tar")
sentinel_archives = [
    "path/to/example_archive1.zip",
    "path/to/example_archive2.zip"
]

event = Event("path/to/event_folder/", sentinel_archives, model)
event.run_floodsens()
```

A GeoTIFF raster containing the results will be saved in `event_folder` under the name `FloodSENS_results.tif` and a `event_checkpoint.yaml` is saved to disk. Existing events can be loaded with `Event.from_yaml("path/to/event_checkpoint.yaml")` which will create an `event` instance that contains the information about the used model and what types of processing has been applied.

### Using `Project` class

The `Project` class is a collection of models, events and a project folder. Below is an example on how the class is meant to be used for simple processing.

```Python
from floodsens.event import Project

project = Project("path/to/project_folder")
project.load_models("path/to/model_folder")
project.add_event("example_event", sentinel_archives)

project.event.run_floodsens()
project.save_to_yaml()
```
It is important to call `load_models` first. The models need to be packages with `.tar` file extension to be discovered, make sure to **extract any models that are compressed as `zip` file**.
The `add_event` method is listing all loaded models and prompts the user to choose from a list by entering the corresponding number, this is purely a quality of life feature.

If you have an existing event that you want to add to a project you can do so with the `project.load_event` method.
