Interfaces
==========

Ncdjango has two built-in interfaces. The first is a partial implementation of the
:doc:`ArcGIS Server Rest API <arcgis>` (http://resources.arcgis.com/en/help/rest/apiref/index.html?mapserver.html).
The second is a simple :doc:`data <data>` API for querying things like value range, classifications of data, and data
through time (for time-enabled datasets) at a single point.

You can also add your own interface, which is explained in :doc:`custom`.

.. toctree::
    :maxdepth: 2

    arcgis
    data
    custom
