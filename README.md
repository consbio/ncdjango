# ncdjango

Ncdjango turns [Django](https://www.djangoproject.com/) projects into map servers backed by
[NetCDF](http://www.unidata.ucar.edu/software/netcdf/docs/faq.html#whatisit) datasets. It can be added Django project
to provide various web interfaces to NetCDF data and geoprocessing tools written in Python which operate on NetCDF data.

# Why?
This project grew out of a need for a map server capable of delivering time-series raster data from NetCDF data, with
enough extensibility to support different web APIs for the same map service. The result is a Django app which adds a
range of map service capabilities to a Django project. Currently, ncdjango includes a partial implementation of the
[ArcGIS REST API](http://resources.arcgis.com/en/help/rest/apiref/) with the added feature of per-request styling.
It also includes a data interface which can provide summary information about service data and generate class breaks
(equal, quantile, or natural breaks) based on the service data.

Ncdjango provides an admin API for creating and managing map services, and a geoprocessing framework which allows
clients to execute processing jobs against NetCDF result. Job results can be automatically published as new services,
meaning that a web client could call a geoprocessing job, and upon its completion, show the processed results in a map.

# Use cases
Ncdjango is used to provide map services of NetCDF data for [Data Basin](https://databasin.org). Data Basin users can
upload NetCDF datasets and view and share them in a web map, all with no programming or server coniguration. Example:
[NARCCAP Monthly Average Maximum Daily Temperature](https://databasin.org/maps/new#datasets=7445377234b84b279225f8ebdd31d3ff)

It is also used in the [Seedlot Selection Tool](https://seedlotselectiontool.org/sst/) both to provide map services
of NetCDF data, and to implement the geoprocessing needs for the tool and map services of the results.

# Documentation
Full documentation available [here](http://ncdjango.readthedocs.io/en/latest/).
