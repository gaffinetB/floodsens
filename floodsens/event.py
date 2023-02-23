"""
!!!MEANT FOR A SINGLE EVENT MEANING A SINGLE SENTINEL ARCHIVE!!!
"""
import yaml
from pathlib import Path, PurePath
import floodsens.utils as utils
import floodsens.preprocessing as preprocessing
import floodsens.inference as inference
from floodsens.logger import logger
from floodsens.model import FloodsensModel

class Event(object):
    def __init__(self, event_folder, sentinel_archive, model, inferred_raster=None, ndwi_raster=None, true_color_raster=None, aoi=None, date=None):
        self.event_folder = Path(event_folder)
        if not self.event_folder.exists():
            self.event_folder.mkdir(parents=True, exist_ok=True)
        self.sentinel_archive = Path(sentinel_archive)
        self.model = model if isinstance(model, FloodsensModel) else None
        self.inferred_raster = Path(inferred_raster) if inferred_raster is not None else None
        self.ndwi_raster = Path(ndwi_raster) if ndwi_raster is not None else None
        # NOTE Extract for TCI not working yet
        # self.true_color_raster = utils.extract(self.sentinel_archive, self.event_dir, ("TCI", "10m"))
        # self.date, self.aoi = utils.extract_metadata(self.sentinel_archive)

    def __repr__(self) -> str:
        # return f'{self.__class__.__name__}({self.event_folder}, {self.sentinel_archive}, {self.model}, {self.inferred_raster}, {self.ndwi_raster}, {self.aoi}, {self.date})'.format(self=self)
        return f'{self.__class__.__name__}({self.event_folder}, {self.sentinel_archive}, {self.model}, {self.inferred_raster}, {self.ndwi_raster})'.format(self=self)

    def run_floodsens(self):
        if self.model is None or not isinstance(self.model, FloodsensModel):
            raise ValueError(f"Model not found at {self.model.path} or not of type FloodsensModel.")

        if self.inferred_raster is not None:
            logger.warn(f"Overwriting existing inferred raster at {self.inferred_raster}.")

        preprocessed_tiles = preprocessing.run_multiple_default_preprocessing(self.event_folder, [self.sentinel_archive], delete_all=True, set_type="inference")
        logger.info(f"Successfully preprocessed {self.sentinel_archive.name}.")
        inferred_tiles = inference.run_inference(self.model.path, preprocessed_tiles, self.model.channels, cuda=False, sigmoid_end=True)
        logger.info(f"Successfully ran inference on {self.sentinel_archive.name}.")
        out_name = f"{self.event_folder}/{aoi_name}/FloodSENS_results.tif"
        inference.create_map(preprocessed_tiles, inferred_tiles, out_path=out_name)
        self.inferred_raster = Path(out_name)
        logger.info(f"Successfully created output map for {self.sentinel_archive.name}.")
        
        for preprocessed_tile in preprocessed_tiles:
            preprocessed_tile.unlink()
        
        for inferred_tile in inferred_tiles:
            inferred_tile.unlink()
        
        preprocessed_tiles[0].parent.rmdir()
        inferred_tiles[0].parent.rmdir()

        logger.info(f"Successfully cleaned up intermediate products for {self.sentinel_archive.name}.")
        logger.info(f"Successfully ran FloodSENS on {self.sentinel_archive.name}.") 

    def run_ndwi(self):
        # TODO
        raise NotImplementedError(f"This feature has not been implemented yet.")

    def save_to_yaml(self):
        filename = f"{self.event_folder}/event_checkpoint.yaml"
        
        event_data = self.__dict__
        model_data = event_data.pop("model")
        event_data["model"] = model_data.__dict__
        
        with open(filename, "w") as f:
            yaml.dump(event_data, f)
    
    @classmethod
    def from_yaml(self, filename):
        with open(filename, "r") as f:
            data = yaml.load(f, Loader)
        
        model_data = data.pop("model")
        model = FloodsensModel(**model_data)
        data["model"] = model
        
        return cls(**data)
