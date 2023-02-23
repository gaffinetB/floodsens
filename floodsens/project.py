import floodsens.preprocessing as preprocessing
import floodsens.inference as inference
import floodsens.utils as utils
import floodsens.ndwi as ndwi
from floodsens.logger import logger
from floodsens.model import FloodsensModel
from floodsens.event import Event

from pathlib import Path

class Project(object):

    def __init__(self, project_folder, events, models):
        self.project_folder = Path(project_folder)
        self.events = events if events is not None else []
        self.models = models if models is not None else []

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.project_folder}, {self.events}, {self.models})'.format(self=self)


    @classmethod
    def from_json(self, filename):
        with open(filename, "r") as f:
            data = json.load(f)
        
        return Project(**data)


    # @classmethod
    # def from_folder(self, path):
    #     # Check if project folder exists
    #     if self.project_folder.exists():
    #         logger.info(f"Loading project from {self.project_folder}")
    #     else:
    #         raise FileNotFoundError(f"Project folder does not exist. Please create a project folder at {self.project_folder}.")

    #     # TODO
    #     raise NotImplementedError("Loading project from folder not implemented yet.")
    #     # Check if Sentinel Images available in correct folder & load
    #     project_folder = Path(path)
    #     sentinel_folder = project_folder/"Sentinel Archives"
    #     if not sentinel_folder.exists():
    #         raise FileNotFoundError(f"Error when loading Sentinel-2 archives. \"Sentinel Archives\" folder does not exist. Please place Sentinel-2 archives in \"Sentinel Archives\" folder.")

    #     sentinel_archives = [Path(x) for x in (project_folder/"Sentinel Archives").iterdir() if x.suffix == ".zip"]
    #     if len(sentinel_archives) == 0:
    #         logger.warn(f"No Sentinel Images available in {project_folder}")
    #     elif len(sentinel_archives) >= 1:
    #         sentinel_archives = sentinel_archives
    #         logger.info(f"{len(sentinel_archives)} Sentinel-2 archives found.")
    #     else:
    #         raise RuntimeError(f"Error occured while loading Sentinel-2 archives.")

    #     # Extract AOI and time from Sentinel-2 names
    #     date, aoi = utils.extract_metadata(sentinel_archives)

    #     # Check if models available & load
    #     if not (project_folder/"Models").exists():
    #         logger.warn("No models available. Please place models in \"Models\" folder.")
    #         return Project(project_folder, sentinel_archives, None, date, aoi)
        
    #     models = [FloodsensModel(Path(x)) for x in (project_folder/"Models").iterdir() if x.suffix == ".tar"]
        
    #     return Project(project_folder, sentinel_archives, models, date, aoi)

    @classmethod
    def from_aoi(self, aoi, time, project_folder, filter_mode="date"):
        # Get Sentinel candidates
        # Filter candidates according to filter_mode
        # Download remaining candidates
        raise NotImplementedError(f"This feature has not been implemented yet.")

    def load_models(self, model_folder):
        self.models = [FloodsensModel(Path(x)) for x in Path(model_folder).iterdir() if x.suffix == ".tar"]
        logger.info(f"{len(self.models)} models loaded.")
        for model in self.models:
            logger.info(f"Model {model.name} loaded.")

    def download_sentinel2(self):
        raise NotImplementedError("Download Sentinel-2 images from Copernicus Open Access Hub")

    def initialize_event(self, name, sentinel_archive, model):
        event_folder = self.project_folder/f"Event_{name}"
        event = Event(event_folder, sentinel_archive, model)
        self.events.append(event)
        return event
