import floodsens.preprocessing as preprocessing
import floodsens.inference as inference
import floodsens.utils as utils
import floodsens.ndwi as ndwi
from floodsens.logger import logger
from floodsens.utils import FloodsensModel

from pathlib import Path

class Project():

    def __init__(self, project_folder, sentinel_archives, model, date, aoi):
        self.date = date
        self.aoi = aoi
        self.sentinel_archives = sentinel_archives
        self.channels = None
        self.model = model
        self.project_folder = Path(project_folder)

    def __repr__(self) -> str:
        return f"{self.project_folder.name}"

    @classmethod
    def from_folder(self, path):

        # Check if Sentinel Images available in correct folder & load
        project_folder = Path(path)
        sentinel_folder = project_folder/"Sentinel Archives"
        if not sentinel_folder.exists():
            raise FileNotFoundError(f"Error when loading Sentinel-2 archives. \"Sentinel Archives\" folder does not exist. Please place Sentinel-2 archives in \"Sentinel Archives\" folder.")

        sentinel_archives = [Path(x) for x in (project_folder/"Sentinel Archives").iterdir() if x.suffix == ".zip"]
        if len(sentinel_archives) == 0:
            logger.warn(f"No Sentinel Images available in {project_folder}")
        elif len(sentinel_archives) >= 1:
            sentinel_archives = sentinel_archives
            logger.info(f"{len(sentinel_archives)} Sentinel-2 archives found.")
        else:
            raise RuntimeError(f"Error occured while loading Sentinel-2 archives.")

        # Extract AOI and time from Sentinel-2 names
        date, aoi = utils.extract_metadata(sentinel_archives)

        # Check if models available & load
        models = [Path(x) for x in (project_folder/"Models").iterdir() if x.suffix == ".tar"]
        if len(models) == 0:
            model = None
            logger.warn(f"No models available")
        elif len(models) == 1:
            model = FloodsensModel(models[0])
            logger.info(f"Model sucessfully loaded. Model name is {model.name}")
        elif len(models) > 1:
            logger.warn(f"Multiple models available. Please load manually using Project.load_model method.")

        return Project(project_folder, sentinel_archives, model, date, aoi)

    @classmethod
    def from_aoi(self, aoi, time, project_folder, filter_mode="date"):
        # Get Sentinel candidates

        # Filter candidates according to filter_mode

        # Download remaining candidates

        # Set model?

        raise NotImplementedError(f"This feature has not been implemented yet.")
        

    def load_model(self, path):
        self.model = FloodsensModel(path)

    def download_sentinel2(self):
        self.zips = utils.download_sentinel2(self.aoi, self.time)
        logger.info(f"{len(self.zips)} Sentinel-2 archives downloaded.")

    def run_floodsens(self, aoi_name="NewAOI"):
        # Check if model is loaded
        

        # Check if Sentinel Images are available
        

        # Run preprocessing
        preprocessed_tiles = preprocessing.run_multiple_default_preprocessing(self.project_folder, self.sentinel_archives, delete_all=False, set_type="inference")
        
        # Run inference
        inferred_tiles = inference.run_inference(self.model.path, preprocessed_tiles, self.model.channels, cuda=False, sigmoid_end=True)
        
        # Create output maps
        out_name = f"{self.project_folder}/{aoi_name}/FloodSENS_results.tif"
        inference.create_map(preprocessed_tiles, inferred_tiles, out_path=out_name)
        # Clean intermediate products


    def run_ndwi(self, threshold):
        # Check if Sentinel Images are available
        if len(self.sentinel_archives) == 0:
            raise FileNotFoundError(f"No Sentinel-2 archives found. Please download Sentinel-2 archives first.")

        # Extract B08 and B03 from Sentinel archives
        ndwi_path = ndwi.compute_ndwi(self.sentinel_archives, threshold, self.project_folder)
        

    def save_tci(self):
        # Check if Sentinel Images are available

        # Extract TCI Images from archives

        # Merge TCI Images

        # Clean intermediate products
        pass

    def performance_report(self):
        pass
