from setuptools import setup

setup(
    name='ncdjango',
    description='A map server for NetCDF data',
    keywords='netcdf,django,map server',
    version='1.1.1',
    packages=[
        'ncdjango', 'ncdjango.geoprocessing', 'ncdjango.geoprocessing.tasks', 'ncdjango.migrations',
        'ncdjango.interfaces', 'ncdjango.interfaces.arcgis', 'ncdjango.interfaces.arcgis_extended',
        'ncdjango.interfaces.data'
    ],
    install_requires=[
        'requests', 'Django==2.2.*', 'Pillow>=7.2.0', 'Shapely>=1.7.0', 'django-tastypie==0.14.*',
        'netCDF4>=1.5.3', 'numpy>=1.19.0', 'pyproj>=1.9.4', 'fiona', 'trefoil', 'ply>=3.11',
        'celery>=4.4.6', 'djangorestframework', 'pytest-django'
    ],
    dependency_links=['https://github.com/consbio/trefoil/archive/main.zip'],
    url='https://github.com/consbio/ncdjango',
    license='BSD',
)
