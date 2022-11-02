from setuptools import setup, find_packages

# python setup.py sdist
# twine upload dist/*

setup(
    name = "floodsens",
    version = "0.1.7",
    author = "Ben Gaffinet",
    author_email = "ben@gaffinet.lu",
    packages = find_packages(include=['floodsens'], exclude=['tests', 'notebooks']),
    include_package_data = True,
    test_suite = 'tests',
    install_requires = [
        'gdal',
        'rasterio',
        'boto3',
        'botocore',
        'pyproj',
        'pysheds==0.2.7',
        'numpy',
        'torch',
        'torchvision',
        'tifffile',
        'pandas'
    ],
    dependency_links = [],
    description = "Flood Segmentation on Sentinel-2 images based on Machine Learning Models",
    license = 'GPLv3',
    keywords = "flood gis sentinel copernicus ai",
    url = "https://github.com/gaffinetB/floodsens",
    classifiers = ['Development Status :: 2 - Pre-Alpha',
                   'Topic :: Scientific/Engineering :: Artificial Intelligence',
                   'Topic :: Scientific/Engineering :: GIS',
                   'Intended Audience :: Science/Research',
                   'Programming Language :: Python :: 3.6']
)