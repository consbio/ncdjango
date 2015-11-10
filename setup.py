from setuptools import setup

setup(
    name='ncdjango',
    description='A map server for NetCDF data',
    keywords='netcdf,django,map server',
    version='0.2.0',
    packages=[
        'ncdjango', 'ncdjango.migrations', 'ncdjango.interfaces', 'ncdjango.interfaces.arcgis',
        'ncdjango.interfaces.arcgis_extended', 'ncdjango.interfaces.data'
    ],
    install_requires=[
        'clover', 'six', 'requests', 'Django>=1.7.0', 'Pillow>=2.7.0', 'Shapely>=1.3.2', 'GDAL>=1.11.0',
        'django-tastypie>=0.11.1', 'netCDF4>=1.1.6', 'numpy>=1.8.1', 'pyproj>=1.9.4', 'fiona', 'rasterio>=0.28.0',
        'ply>=3.8'
    ],
    url='https://github.com/consbio/ncdjango',
    license='BSD',
)
