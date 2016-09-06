Settings
========

NC_ALLOW_BEST_FIT_TIME_INDEX
----------------------------

If ``True`` (default), find the closest valid time step to the timestamp given. If ``False``, exact timestamps are
required, and a timestamp which doesn't match any time step in the dataset will be considered invalid.

.. code-block:: python

    NC_ALLOW_BEST_FIT_TIME_INDEX = True

NC_ARCGIS_BASE_URL
------------------

The base URL for the :doc:`ArcGIS REST API <../interfaces/arcgis>` interface. Defaults to ``arcgis/rest/``

.. code-block:: python

    NC_ARCGIS_BASE_URL = 'arcgis/rest/'

NC_ENABLE_STRIDING
------------------

Stride data if the data resolution is larger than the requested image resolution. Defaults to ``False``.

.. code-block:: python

    NC_ENABLE_STRIDING = False

NC_FORCE_WEBP
-------------

Return ``WebP``-formatted images instead of PNG if the browser supports it, regardless of requested format. Defaults to
``False``.

.. code-block:: python

    NC_FORCE_WEBP = False

NC_INSTALLED_INTERFACES
-----------------------

A list of web services interfaces to enable. By default, this is the :doc:`ArcGIS REST API <../interfaces/arcgis>` (plus
the :ref:`extended ArcGIS API <arcgis-extended>`) and the :doc:`data <../interfaces/data>` interface.

.. code-block:: python

    NC_INSTALLED_INTERFACES = (
        'ncdjango.interfaces.data',
        'ncdjango.interfaces.arcgis_extended',
        'ncdjango.interfaces.arcgis'
    )

.. _setting-max-temporary-service-age:

NC_MAX_TEMPORARY_SERVICE_AGE
----------------------------

The length of time (in seconds) to keep a temporary service (usually created as the result of a geoprocessing job)
before automatically deleting it. Defaults to ``43200`` seconds (12 hours).

.. code-block:: python

    NC_MAX_TEMPORARY_SERVICE_AGE = 43200  # 12 hours


NC_MAX_UNIQUE_VALUES
--------------------

The maximum number of unique values for a dataset to return through the :doc:`data <../interfaces/data>` interface.
Defaults to ``100``.

.. code-block:: python

    NC_MAX_UNIQUE_VALUES = 100

.. _setting-registered-jobs:

NC_REGISTERED_JOBS
------------------

A list of geoprocessing jobs to make available to clients. This should be a dictionary with the following format:

.. code-block:: python

    NC_REGISTERED_JOBS = {
        '<name>': {  # Name used for the API
            'type': '<task|workflow>',  # Job type: 'task' or 'workflow'
            'task': '<module path to task class>',  # If type is task
            'path': '<absolute path to workflow definition file>',  # If type is workflow
            'publish_raster_results': True,  # Automatically publish raster outputs as services?
            'results_renderer': StretchedRenderer([
                (0, Color(240, 59, 32)),
                (50, Color(254, 178, 76)),
                (100, Color(255, 237, 160))
            ])  # Renderer definition for automatically published services
        }
    }

.. _setting-service-data-root:

NC_SERVICE_DATA_ROOT
--------------------

The root location of NetCDF datasets. Defaults to ``/var/ncdjango/services/``.

.. code-block:: python

    NC_SERVICE_DATA_ROOT = '/var/ncdjango/services/'

NC_TEMPORARY_FILE_LOCATION
--------------------------

The location to store temporary files (uploads). Defaults to ``/tmp``.

.. code-block:: python

    NC_TEMPORARY_FILE_LOCATION = '/tmp'

.. _setting-warp-max-depth:

NC_WARP_MAX_DEPTH
-----------------

The maximum recursion depth to use when generating the mesh used to warp output images to the requested projection.
Defaults to ``5``.

.. code-block:: python

    NC_WARP_MAX_DEPTH = 5

NC_WARP_PROJECTION_THRESHOLD
----------------------------

The tolerance (in pixels) to use when warping images to the requested projection. Defaults to ``1.5``. When warping
the image, a mesh of varying size is used. The size is determined by recursively subdividing a line and comparing the
projected midpoint to a "guessed" midpoint. The subdivision stops when the difference is within the tolerance, or
``:ref:`setting-warp-max-depth``` is reached.

.. code-block:: python

    NC_WARP_PROJECTION_THRESHOLD = 1.5
