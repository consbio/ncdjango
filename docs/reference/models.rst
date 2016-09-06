Models
======

.. py:module:: ncdjango.models

.. py:class:: Service

    A service maps to a single NetCDF dataset. Services contain general metadata (name, description), and information
    about the data extend, projection, and support for time.

    .. py:attribute:: name

        The service name to be presented via web interfaces.

    .. py:attribute:: description

        A description of the service, to be presented via web interfaces.

    .. py:attribute:: data_path

        The path to the NetCDF dataset, relative to :ref:`setting-service-data-root`.

    .. py:attribute:: projection

        The data projection, as a PROJ4 string.

    .. py:attribute:: full_extent

        A bounding box representing the full extent of the service data.

    .. py:attribute:: initial_extent

        A bounding box representing the initial extent of the service.

    .. py:attribute:: supports_time

        Does this service support time?

    .. py:attribute:: time_start

        The first time step available for this service.

    .. py:attribute:: time_end

        The last time step available for this service.

    .. py:attribute:: time_interval

        The number of ``time_interval_units`` between each step.

    .. py:attribute:: time_interval_units

        The units used for ``time_interval``. Can be one of:
            * ``milliseconds``
            * ``seconds``
            * ``minutes``
            * ``hours``
            * ``days``
            * ``weeks``
            * ``months``
            * ``years``
            * ``decades``
            * ``centuries``

    .. py:attribute:: calendar

        The calendar to use for time calculations. Can be one of:
            * ``standard`` (Standard, gregorian calendar)
            * ``noleap`` (Like the standard calendar, but without leap days)
            * ``360`` (Consistent calendar with 30-day months, 360-day years)

    .. py:attribute:: render_top_layer_only

        If ``True`` for multi-variable services, only the top layer will be rendered by default. Defaults to ``True``.

.. py:class:: Variable

    A variable in a map service. This is usually presented as a layer in a web interface. Each service may have one
    or more variables. Each variable maps to a variable in the NetCDF dataset.

    .. py:attribute:: time_stops

        Valid time steps for this service as a list of datetime objects. **(read-only)**

    .. py:attribute:: service

        Foreign key to the :any:`Service` model.

    .. py:attribute:: index

        Order of this variable in a list.

    .. py:attribute:: variable

        Name of the variable in the NetCDF dataset.

    .. py:attribute:: projection

        The data projection, as a PROJ4 string.

    .. py:attribute:: x_dimension

        The name of the x dimension of this variable in the NetCDF dataset.

    .. py:attribute:: y_dimension

        The name of the y dimension of this variable in the NetCDF dataset.

    .. py:attribute:: name

        The variable name to be presented via web interfaces.

    .. py:attribute:: description

        A description of the variable, to be presented via web interfaces.

    .. py:attribute:: renderer

        The default renderer to use for this variable. See
        https://github.com/consbio/clover/tree/master/clover/render/renderers for available renderers.

    .. py:attribute:: full_extent

        A bounding box representing the full extent of the variable data.

    .. py:attribute:: supports_time

        Does this variable support time?

    .. py:attribute:: time_dimension

        The name of the time dimension of this variable in the NetCDF dataset.

    .. py:attribute:: time_start

        The first time step available for this variable.

    .. py:attribute:: time_end

        The last time step available for this variable.

    .. py:attribute:: time_steps

        The number of time steps available for this variable.

.. py:class:: ProcessingJob

    An active, completed, or failed geoprocessing job.

    .. py:attribute:: status

        The status of the celery task for this job. **(read only)**

    .. py:attribute:: uuid

        A unique ID for this job. Usually provided to the client to query the job status.

    .. py:attribute:: job

        The registered name of the job. See :ref:`setting-registered-jobs`.

    .. py:attribute:: user

        A foreign key to the ``User`` model, or ``None`` if the user is not logged in.

    .. py:attribute:: user_ip

        The IP address of the user who initiated the job.

    .. py:attribute:: created

        When the job was created.

    .. py:attribute:: celery_id

        The celery task ID.

    .. py:attribute:: inputs

        A JSON representation of the job inputs.

    .. py:attribute:: outputs

        A JSON representation of the job outputs.

.. py:class:: ProcessingResultService

    A result service is created from the raster output of a geoprocessing job. This model tracks which services are
    automatically generated from job results.

    .. py:attribute:: job

        A foreign key to the :any:`ProcessingJob` model.

    .. py:attribute:: service

        A foreign key to the :any:`Service` model.

    .. py:attribute:: is_temporary

        Temporary services will be cleaned up when the
        ``ncdjango.geoprocessing.celery_tasks.cleanup_temporary_services`` celery task is run if they are older than
        :ref:`setting-max-temporary-service-age`.

    .. py:attribute:: created

        The date the result service was created.
