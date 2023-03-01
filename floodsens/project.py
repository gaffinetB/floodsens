import floodsens.preprocessing as preprocessing
import floodsens.inference as inference
import floodsens.utils as utils
import floodsens.ndwi as ndwi
from floodsens.logger import logger
from floodsens.model import FloodsensModel
from floodsens.event import Event

from pathlib import Path
import yaml

class Project(object):
    def __init__(self, project_folder, models=None, event_collection=None, event=None):
        self.project_folder = Path(project_folder)

        if not self.project_folder.exists():
            self.project_folder.mkdir(parents=True)

        if models is None:
            self.models = {}
        elif isinstance(models, dict):
            self.models = models
        elif isinstance(models, list):
            self.models = {model.name: model for model in models}
        elif isinstance(models, FloodsensModel):
            self.models = {models.name: models}
        else:
            raise ValueError(f"models must be of type dict, list, or FloodsensModel. Got {type(models)} instead.")

        if event_collection is None:
            self.event_collection = {}
        elif isinstance(event_collection, dict):
            self.event_collection = event_collection
        elif isinstance(event_collection, list):
            self.event_collection = {event.name: event for event in event_collection}
        elif isinstance(event_collection, Event):
            self.event_collection = {event_collection.name: event_collection}
        else:
            raise ValueError(f"event_collection must be of type dict, list, or Event. Got {type(event_collection)} instead.")

        if event is not None:
            self.event = event

        self.save_to_yaml(True)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.project_folder}, {self.event_collection}, {self.models})'

    def __str__(self) -> str:
        # print the project folder
        output = f"Project folder: {self.project_folder}\n"

        # print the event details
        output += f"Activated Event:\n"
        output += f"\t{self.event}\n\n"

        # print the event collection details
        output += f"Event collection:\n"
        for name, event in self.event_collection.items():
            output += f"\t{name}:\n"
            output += f"\t\t{event}\n"

        # print the models details
        output += f"Models:\n"
        for name, model in self.models.items():
            output += f"\t{name}:\n"
            output += f"\t\t{model}\n"

        return output

    @classmethod
    def from_yaml(cls, filename):
        with open(filename, "r") as f:
            data = yaml.load(f, Loader=yaml.Loader)

        return cls(**data)

    def save_to_yaml(self, overwrite=False):
        filename = self.project_folder/"project_checkpoint.yaml"
        if not overwrite and filename.exists():
            raise FileExistsError(f"\"{filename.parent}\" project folder already exists. Load the project from this file or start new project in separate folder.")

        project_data = self.__dict__

        with open(filename, "w") as f:
            yaml.dump(project_data, f)

    def activate_event(self, event_name):
        self.event = self.event_collection[event_name]
        logger.info(f"Event {self.event.name} activated.")

    def choose_event(self):
        for i, event in enumerate(self.event_collection.keys()):
            print(f"{i+1}: {event}")
        choice = int(input("Choose an event by entering corresponding integer: "))
        self.activate_event(list(self.event_collection.keys())[choice-1])

    def load_models(self, model_folder):
        loaded_models = {}
        model_paths = [x for x in Path(model_folder).iterdir() if x.suffix == ".tar"]
        for model_path in model_paths:
            model = FloodsensModel(model_path)
            loaded_models[model.name] = model

        self.models = loaded_models
        logger.info(f"{len(self.models)} models loaded.")

        for model in self.models.values():
            logger.info(f"Model {model.name} loaded.")

    def download_sentinel2(self): #TODO with Google Earth Engine
        raise NotImplementedError("Download Sentinel-2 images from Copernicus Open Access Hub")

    def load_event(self, yaml_path):
        event = Event.from_yaml(yaml_path)
        self.event_collection[event.name] = event
        return event

    def add_event(self, event_name, sentinel_archives, model=None):
        event_folder = self.project_folder/event_name

        if model is None and len(self.models) > 0:
            for i, model_name in enumerate(self.models.keys()):
                print(f"{i+1}: {model_name}")
            choice = int(input("Choose a model by entering corresponding integer: "))
            model = self.models[list(self.models.keys())[choice-1]]

        event = Event(event_folder, sentinel_archives, model)
        self.event_collection[event.name] = event

        if len(self.event_collection) == 1:
            self.event = event

        # event.save_to_yaml()
        return event
