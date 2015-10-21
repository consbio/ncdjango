# ncdjango
A Django app which provides various web interfaces to NetCDF data. The currently implemented interfaces are:
[ArcGIS Server REST API](http://resources.arcgis.com/en/help/rest/apiref/index.html?mapserver.html) (partial); an extended 
ArcGIS Server REST API, which includes support for custom styling per request; and a data API for various query and classify 
operations.

Other interfaces will be added in the future. A WMS interface is a likely addition at some point, but for now, there is no 
timeline or active development in this direction.

# Installation & Setup
Install with ```pip install git+https://github.com/consbio/ncdjango.git```.

Add ```ncdjango``` and ```tastypie``` to your ```INSTALLED_APPS```. Add two additional settings to your ```settings.py```:

```python
NC_SERVICE_DATA_ROOT = '<root location for NetCDF data>'
NC_TEMPORARY_FILE_LOCATION = '<temp file directory>'
```
