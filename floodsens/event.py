"""The event module contains the Event class which represents a single event.
All processing methods are called from the Event class."""
from pathlib import Path, PurePath
import shutil
import yaml
import floodsens.preprocessing as preprocessing
import floodsens.inference as inference
from floodsens.logger import logger
from floodsens.model import FloodsensModel

class Event():
    """Event class to manage a single event. The event class contains all processing methods.

    Arguments:
        event_folder {str, Path} -- Path to the event folder. Created if it does not exist.
        sentinel_archives {str, Path, list} -- Path to the Sentinel archive(s).
        (optional) model {FloodsensModel} -- FloodsensModel instance.
        (optional) name {str} -- Name of the event. Defaults to the name of the event folder.
        (optional) inferred_raster {str, Path} -- Path to the inferred raster. Defaults to None.
        (optional) ndwi_raster {str, Path} -- Path to the NDWI raster. Defaults to None."""
    def __init__(self, event_folder, sentinel_archives, model, name=None, inferred_raster=None, ndwi_raster=None):
        self.event_folder = Path(event_folder)
        if not self.event_folder.exists():
            self.event_folder.mkdir(parents=True, exist_ok=True)
        self.name = name if name is not None else self.event_folder.name

        if isinstance(sentinel_archives, PurePath) or isinstance(sentinel_archives, str):
            self.sentinel_archives = [Path(sentinel_archives)]
        elif isinstance(sentinel_archives, list):
            self.sentinel_archives = [Path(archive) for archive in sentinel_archives]
        else:
            raise ValueError(f"sentinel_archives must be of type str, pathlib Path, or list. Got {type(sentinel_archives)} instead.")

        self.model = model if isinstance(model, FloodsensModel) else None
        self.inferred_raster = Path(inferred_raster) if inferred_raster is not None else None
        self.ndwi_raster = Path(ndwi_raster) if ndwi_raster is not None else None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.event_folder}, {self.sentinel_archives}, {self.model}, {self.inferred_raster}, {self.ndwi_raster})'

    def __str__(self) -> str:
        output = f"Event folder: {self.event_folder}\n"
        output += f"\tNumber of Sentinel archives: {len(self.sentinel_archives)}\n"

        if self.inferred_raster:
            output += f"\tInferred raster: {self.inferred_raster}\n"

        if self.ndwi_raster:
            output += f"\tNDWI raster: {self.ndwi_raster}\n\n"

        output += f"\tModel: {self.model.name}"

        return output

    def run_floodsens(self):
        """Run FloodSENS on the event. This method will run preprocessing, inference, and postprocessing.
        The output raster will be saved to the event folder with file name "FloodSENS_results.tif".
        """
        if self.model is None or not isinstance(self.model, FloodsensModel):
            raise ValueError(f"Model not found at {self.model} or not of type FloodsensModel.")

        if self.inferred_raster is not None:
            logger.warning(f"{self.inferred_raster} already exists and will be overwritten if you choose to continue.")
            interrupt = input("Do you want to continue? (y/n): ")
            if interrupt.lower() == "n":
                logger.info("Stopping FloodSENS run.")
                return
            logger.info("Continuing FloodSENS run. This may take a while...")

        preprocessed_tiles_folder = preprocessing.run_default_preprocessing(self.event_folder, self.sentinel_archives, delete_all=True)
        logger.info(f"Successfully preprocessed {len(self.sentinel_archives)} Sentinel Archives.")
        inferred_tiles_folder = inference.run_inference(self.model.path, preprocessed_tiles_folder, self.model.channels, cuda=False, sigmoid_end=True)
        logger.info(f"Successfully ran inference on {len(self.sentinel_archives)} Sentinel Archives.")
        out_name = f"{self.event_folder}/FloodSENS_results.tif"
        inference.create_map(preprocessed_tiles_folder, inferred_tiles_folder, out_path=out_name)
        self.inferred_raster = Path(out_name)
        logger.info(f"Successfully created output map for {len(self.sentinel_archives)} Sentinel Archvies.")

        shutil.rmtree(preprocessed_tiles_folder.parent)

        logger.info("Successfully cleaned up intermediate products.")
        logger.info(f"Successfully ran FloodSENS on {self.sentinel_archives}.")

        self.save_to_yaml()

    def run_ndwi(self): #TODO: Implement NDWI
        raise NotImplementedError("This feature has not been implemented yet.")

    def extract_truecolor(self):
        raise NotImplementedError("This feature has not been implemented yet.")

    def generate_training_data(self, label_path=None):
        preprocessed_tiles_folder = preprocessing.run_default_preprocessing(self.event_folder, [self.sentinel_archives], delete_all=True)
        logger.info(f"Successfully preprocessed {len(self.sentinel_archives)} Sentinel Archives. Tiles saved to {preprocessed_tiles_folder}.")

        if label_path is not None:
            label_path = Path(label_path)
            # TODO Rasterize, Binarize, Tile
            raise NotImplementedError("This feature has not been implemented yet.")

        return preprocessed_tiles_folder

    def save_to_yaml(self):
        """Save the event to a YAML file. This file can be used to recreate the event instance.
        The file will be named "event_checkpoint.yaml" and saved to the event folder."""
        filename = f"{self.event_folder}/event_checkpoint.yaml"

        event_data = self.__dict__

        with open(filename, "w") as ostream:
            yaml.dump(event_data, ostream)

    @classmethod
    def from_yaml(cls, yaml_path):
        """Restore an Event instance from a YAML file.

        Arguments:
            yaml_path {str, Path} -- Path to the YAML file."""
        with open(yaml_path, "r") as istream:
            data = yaml.load(istream, yaml.Loader)

        # model_data = data.pop("model")
        # model = FloodsensModel(**model_data)
        # data["model"] = model

        return cls(**data)
