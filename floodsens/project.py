"""project module containing the Project class to manage multiple models and events."""
from pathlib import Path
import yaml
from floodsens.logger import logger
from floodsens.model import FloodsensModel
from floodsens.event import Event

class Project():
    """Project class to manage multiple models and events.
    A project instance can contain multiple events in its attribute event_collection.
    To access the processing methods the event must be activated by calling the activate_event 
    method. If a single event is passed to the constructor, it will be activated automatically.

    Arguments:
        project_folder {str, Path} -- Path to the project folder.
        (optional) models {dict, list, FloodsensModel} -- Dictionary of FloodsensModel, list of FloodsensModel, or single FloodsensModel.
        (optional) event_collection {dict, list, Event} -- Dictionary of events, list of events, or single event.
        (optional) event {Event} -- Event to be activated."""
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

        self.save_to_yaml()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.project_folder}, {self.event_collection}, {self.models})'

    def __str__(self) -> str:
        # print the project folder
        output = f"Project folder:\n\t{self.project_folder}\n\n"

        # print the models details
        output += "Models:\n"
        for name, _ in self.models.items():
            output += f"\t{name}:\n"
            # output += f"\t\t{model}\n"

        # print the event details
        output += "\nActivated Event:\n"
        output += f"\t{self.event.name}\n\n"
        # output += f"\t{self.event}\n\n"

        # print the event collection details
        output += "Event collection:\n"
        for name, _ in self.event_collection.items():
            output += f"\t{name}\n"
            # output += f"\t\t{event}\n"

        return output

    @classmethod
    def from_yaml(cls, filename):
        """Load a Project object from a yaml file.

        Arguments:
            filename {str, Path} -- Path to the yaml file."""
        with open(filename, "r") as istream:
            data = yaml.load(istream, Loader=yaml.Loader)

        return cls(**data)

    def save_to_yaml(self, overwrite=False):
        """Save the Project object to a yaml file. Can be loaded with the from_yaml method.

        Arguments:
            overwrite {bool} -- Overwrite existing project folder.
        """
        filename = self.project_folder/"project_checkpoint.yaml"
        if not overwrite and filename.exists():
            logger.warning(f"\"{filename.parent}\" project folder already exists. Load the project from this file or start new project in separate folder.")
            interrupt = input("Do you want to overwrite the existing project? (y/n): ")
            if interrupt.lower() == "y":
                logger.info("Overwriting existing project.")
            else:
                logger.info("Existing without overwriting.")
                return

        project_data = self.__dict__

        with open(filename, "w") as ostream:
            yaml.dump(project_data, ostream)

    def activate_event(self, event_name):
        """Activate an event from the event_collection that matches the event_name.

        Arguments:
            event_name {str} -- Name of the event to be activated."""
        self.event = self.event_collection[event_name]
        logger.info(f"Event {self.event.name} activated.")

    def choose_event(self):
        """Shows a list of all events in the event_collection and lets the user choose one.
        Chosen event will be activated."""
        for i, event in enumerate(self.event_collection.keys()):
            print(f"{i+1}: {event}")
        choice = int(input("Choose an event by entering corresponding integer: "))
        self.activate_event(list(self.event_collection.keys())[choice-1])

    def load_models(self, model_folder):
        """Load models from a folder and its subfolders.
        All models must be saved as .tar files.

        Arguments:
            model_folder {str, Path} -- Path to the folder containing the models."""
        loaded_models = {}
        model_paths = list(Path(model_folder).rglob("*.tar"))
        for model_path in model_paths:
            model = FloodsensModel(model_path)
            loaded_models[model.name] = model

        self.models = loaded_models
        logger.info(f"{len(self.models)} models loaded.")

        for model in self.models.values():
            logger.info(f"Model {model.name} loaded.")

    def download_sentinel2(self): #TODO with Google Earth Engine
        """ WARNING NOT IMPLEMENTED"""
        raise NotImplementedError("Not implemented. Please download Sentinel-2 images manually (e.g. from Copernicus Open Access Hub)")

    def load_event(self, yaml_path):
        """Load an existing event from a yaml file.

        Arguments:
            yaml_path {str, Path} -- Path to the yaml file containing the event."""
        event = Event.from_yaml(yaml_path)
        self.event_collection[event.name] = event
        return event

    def add_event(self, event_name, sentinel_archives, model=None):
        """Add a new event to the event_collection.

        Arguments:
            event_name {str} -- Name of the event.
            sentinel_archives {list} -- List of Sentinel-2 archives.
            model {FloodsensModel} -- Model to be used for the event. If None, the user will be asked to choose a model."""
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

        event.save_to_yaml()
        return event
