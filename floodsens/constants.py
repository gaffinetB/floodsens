"""Default list for extracting bands from Sentinel-2 images."""
EXTRACT_DICT = {"10m": ["B02","B03","B04","B08"],
                "20m": ["B05","B06","B07","B11","B12"]}

EXTRACT_LIST = (("B02", "10m"),
                ("B03", "10m"),
                ("B04", "10m"),
                ("B08", "10m"),
                ("B05", "20m"),
                ("B06", "20m"),
                ("B07", "20m"),
                ("B11", "20m"),
                ("B12", "20m"))
