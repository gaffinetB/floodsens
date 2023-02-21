"""
!!!MEANT FOR A SINGLE EVENT MEANING A SINGLE SENTINEL ARCHIVE!!!
"""

class Event(object):
    def __init__(self, sentinel_archive, model, inferred_raster, ndwi_raster, true_color_raster, aoi, date):
        self.sentinel_archive = sentinel_archive
        self.model = model
        self.inferred_raster = inferred_raster
        self.ndwi_raster = ndwi_raster
        # NOTE Untested line below
        self.true_color_raster = utils.extract(self.sentinel_archive, self.event_dir, ("TCI", "10m"))
        self.date, self.aoi = utils.extract_metadata(self.sentinel_archive)

    def __repr__(self) -> str:
        return f"TODO {self.date}"

    def run_floodsense(self):
        # TODO
        raise NotImplementedError(f"This feature has not been implemented yet.")

    def run_ndwi(self):
        # TODO
        raise NotImplementedError(f"This feature has not been implemented yet.")
        