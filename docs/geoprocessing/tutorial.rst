Getting Started
===============

This tutorial covers the basics of creating a task, making it available through the REST API, and running it through
that API.

Creating a task
---------------

First, let's create a task:

.. code-block:: python

    from ncdjango.geoprocessing.params import IntParameter
    from ncdjango.geoprocessing.workflow import Task

    class SumInts(Task):
        name = 'sum_numbers'

        inputs = [
            IntParameter('int1', required=True),
            IntParameter('int2', required=True)
        ]

        outputs = [
            IntParameter('sum')
        ]

        def execute(self, int1, int2):
            return int1 + int2

.. note::
    The ``name`` property is not strictly required except when serializing workflows to JSON or looking up tasks by
    name.

This task take two integers, adds them together and returns the result. When this task is called, it will automatically
check for required inputs and validate the types of incoming parameters.

Running the task from Python
----------------------------

We can run our task from Python, by calling an instance of it:

    >>> t = SumInts()
    >>> result = t(int1=3, int2=5)
    >>> result
    <ncdjango.geoprocessing.params.ParameterCollection object at 0x11fa830b8>
    >>> result['sum']
    8

.. note::
    Tasks must be called with keyword arguments. Positional arguments are not allowed.

.. note::
    Tasks always return a ``ParameterCollection`` object, which can be used like a dictionary to retrieve actual result
    values.

We can also get our task class by name:

    >>> Task.by_name('sum_numbers')
    <class 'SumInts'>

This is useful when using tasks as plugins, in which case their locations may be unknown.

Registering the task with the web API
-------------------------------------

Now that we have a working task, let's make it accessible over the web. To do this, we'll need to add an entry to the
project ``settings.py`` file:

.. code-block:: python

    NC_REGISTERED_JOBS = {
        'sum_numbers': {
            'type': 'task',
            'task': 'myapp.ncdjango_tasks.SumNumbersTask'
        }
    }

This tells ncdjango to add our task to the web API as a job called ``sum_numbers``.

Running the task from the web
-----------------------------

Once the task is registered as a job, we can run it through the REST API. Open
http://127.0.0.1:8001/geoprocessing/rest/jobs/ in your browser to interact with the API. Submitting a job requires two
fields: the job name (``sum_numbers`` in our case) and the job inputs, as a JSON object. For example:

.. code-block:: json

    {
        "int1": 3,
        "int3": 5
    }

You will receive a response like this:

.. code-block:: json

    {
        "uuid": "aa346c90-68e5-4d19-a7f3-a54f6b87ec34",
        "job":"generate_scores",
        "created": "2016-09-02T23:36:10.768937Z",
        "status": "pending",
        "inputs": "{\"int1\": 3, \"int2\": 5}",
        "outputs": "{}"
    }

Now we can use the ``uuid`` value to query the job stats as it runs. The status will move from ``pending`` (the job
has been queued) to ``started`` (the job is running) and finally to ``success`` (the job is done).

.. code-block:: text

    http://127.0.0.1:8001/geoprocessing/rest/jobs/<uuid>/

.. code-block:: json

    {
        "uuid": "aa346c90-68e5-4d19-a7f3-a54f6b87ec34",
        "job": "generate_scores",
        "created": "2016-09-02T23:36:10.768937Z",
        "status": "success",
        "inputs": "{\"int1\": 3, \"int2\": 5}",
        "outputs":"{\"sum\": 8}"
    }

By parsing the returned JSON object once the job has completed, we can access the output value from the task.

.. note::
    Geoprocessing jobs will not run unless celery has been configured for the project and a celery worker is running
    and consuming tasks. http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html
