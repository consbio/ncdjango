from setuptools import setup

setup(
    name='ncdjango',
    description='A map server for NetCDF data',
    keywords='netcdf,django,map server',
    version='0.5.2',
    packages=[
        'ncdjango', 'ncdjango.geoprocessing', 'ncdjango.geoprocessing.tasks', 'ncdjango.migrations',
        'ncdjango.interfaces', 'ncdjango.interfaces.arcgis', 'ncdjango.interfaces.arcgis_extended',
        'ncdjango.interfaces.data'
    ],
    install_requires=[
        'six', 'requests', 'Django>=1.8.0,<1.12.0', 'Pillow>=2.9.0', 'Shapely>=1.3.2', 'django-tastypie>=0.14.0',
        'netCDF4>=1.1.6', 'numpy>=1.8.1', 'pyproj>=1.9.4', 'fiona', 'rasterio>=0.28.0', 'trefoil', 'ply>=3.8',
        'celery>=3.1.19', 'djangorestframework', 'pytest-django'
    ],
    url='https://github.com/consbio/ncdjango',
    license='BSD',
)
