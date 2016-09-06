Geoprocessing
=============

The geoprocessing module provides a framework for providing a web interface to geoprocessing jobs which operate on
NetCDF data. The core components are: :doc:`tasks <tasks>`, which have defined inputs and outputs and perform some
function; :doc:`workflows <workflows>`, which are pipelines of tasks; and a :doc:`web API <api>` to allow clients to
submit a job with inputs for processing, monitor the job status, and retrieve outputs upon completion.

.. toctree::
    :maxdepth: 2

    tutorial
    tasks
    workflows
    api
