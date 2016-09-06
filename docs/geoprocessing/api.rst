REST API
========

The REST API allows clients to run tasks and workflows as jobs, query job status as they run, and retrieve results
once jobs are finished.

Registering Jobs
----------------

A job is simply a task or workflow that has been made available through the REST API. Tasks and workflows are made
available as jobs with the :ref:`setting-registered-jobs` setting. The ``NC_REGISTERED_JOBS`` is a dictionary of
registered jobs:

.. code-block:: python

    NC_REGISTERED_JOBS = {
        'task_job': {
            'type': 'task,
            'task': 'myapp.ncdjango_tasks.SomeTask'
        },
        'workflow_job': {
            'type': 'workflow',
            'path': os.path.join(BASE_DIR, 'myapp/workflows/some_workflow.json')
        }
    }

A basic job registration requires three things:

    1. The job name (this is the dictionary key). This is the name that client will use when running the job.

    2. The job type. This is either ``task`` or ``workflow``.

    3.  The task, or path to the workflow file. For tasks, this is a module path. For workflows, it's the absolute path
        to the workflow's JSON file.

Automatically Publishing Results
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Jobs can be optionally configured to publish raster results as map services by adding an extra key to the job
configuration:

.. code-block:: python

    NC_REGISTERED_JOBS = {
        'some_job': {
            'type': 'task',
            'task': 'myapp.ncdjango_tasks.SomeTask',
            'publish_raster_results': True
        }
    }

If the job returns raster results, ncdjango will automatically write the results to NetCDF datasets and publish them as
temporary services. It will then return the newly created service name as the value of those output field.

By default, a black-to-white gradient will be used as the default renderer for the service. You can also specify
a renderer to use for published results:

.. code-block:: python

    from clover.render.renderers.stretched import StretchedRenderer
    from clover.utilities.color import Color

    NC_REGISTERED_JOBS = {
        'some_job': {
            'type': 'task',
            'task': 'myapp.ncdjango_tasks.SomeTask',
            'publish_raster_results': True,
            'results_renderer': StretchedRenderer([
                (0, Color(255, 0, 0)),
                (100, Color(0, 0, 255))
            ])
        }
    }

.. note::

    See https://github.com/consbio/clover/tree/master/clover/render/renderers for more information on available
    renderers.

``results_renderer`` can also be a function which returns a renderer. The function will be called with the output
raster.

.. code-block:: python

    NC_REGISTERED_JOBS = {
        'some_job': {
            'type': 'task',
            'task': 'myapp.ncdjango_tasks.SomeTask',
            'publish_raster_results': True,
            'results_renderer': lambda raster: StretchedRenderer([
                (raster.min(), Color(255, 0, 0)),
                (raster.max(), Color(0, 0, 255))
            ])
        }
    }

Cleaning up Temporary Services
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To clean up temporary services. Run the celery task ``ncdjango.geoprocessing.celery_tasks.cleanup_temporary_services``.
You can run this directly as a function, in the background as a celery task, or set it up to run periodically using
`celery beat <http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html>`_. The function will delete any
temporary services older than :ref:`setting-max-temporary-service-age`.


Using the API
-------------

The API allows clients to do two things: execute jobs, and query job status, including outputs once the job has
completed.

Execute a Job
^^^^^^^^^^^^^

To execute a job, make a ``POST`` request to ``/geoprocessing/rest/jobs/``` with two fields: the
registered job name, and JSON-encoded inputs:

.. code-block:: json

    {
        "job": "some_job",
        "inputs": "{\"in\": 5}"
    }

.. note::

    The ``inputs`` field must be a string containing an encoded JSON object, rather than part of the JSON object used
    for the request.

.. note::

    If you have `CSRF protection <https://docs.djangoproject.com/en/1.8/ref/csrf/>`_ enabled, you will also need to
    send a valid CSRF token using the ``X-CSRFToken`` header, or sending a ``csrfmiddlewaretoken`` form parameter.

The API will return information about the newly created job, including the UUID which can be used to query job status:

.. code-block:: json

    {
        "uuid": "aa346c90-68e5-4d19-a7f3-a54f6b87ec34",
        "job":"some_job",
        "created": "2016-09-02T23:36:10.768937Z",
        "status": "pending",
        "inputs": "{\"in\": 5}",
        "outputs": "{}"
    }

Query Job Status
^^^^^^^^^^^^^^^^

To query job status, make a ``GET`` request to ``/geoprocessing/rest/jobs/<uuid>/``` using the ``uuid`` value returned
from the initial request to execute the job. The response will be identical, but the status will change as the job
executes and finishes, and after it's succeeded, outputs will be provided.

.. code-block:: text

    GET /geoprocessing/rest/jobs/aa346c90-68e5-4d19-a7f3-a54f6b87ec34/

.. code-block:: json

    {
        "uuid": "aa346c90-68e5-4d19-a7f3-a54f6b87ec34",
        "job":"some_job",
        "created": "2016-09-02T23:36:10.768937Z",
        "status": "started",
        "inputs": "{\"in\": 5}",
        "outputs": "{}"
    }

A jQuery Example
^^^^^^^^^^^^^^^^

.. code-block:: javascript

    var data = {
        job: 'some_job',
        inputs: JSON.stringify({'in': 5})
    };

    $.post('/geoprocessing/rest/jobs/', data).success(function(data) {
        pollJobStatus(data.uuid);
    });

    function pollJobStatus(uuid) {
        $.get('/geoprocessing/rest/jobs/' + uuid + '/').success(function(data) {
            if (data.status === 'success') {
                var outputs = JSON.parse(data.outputs);
                // Do something with job outputs
            }
            else if (data.status === 'pending' || data.status === 'started') {
                setTimeout(function() { pollJobStatus(uuid) }, 1000);
            }
            else {
                // Handle error
            }
        });
    }
