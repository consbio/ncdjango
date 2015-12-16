import os
from importlib import import_module

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from ncdjango.geoprocessing.workflow import Workflow

REGISTERED_JOBS = getattr(settings, 'NC_REGISTERED_JOBS', {})


def get_task_instance(job_name):
    if job_name not in REGISTERED_JOBS:
        return None

    job_info = REGISTERED_JOBS[job_name]

    if not isinstance(job_info, dict) or 'type' not in job_info:
        raise ImproperlyConfigured('NC_REGISTERED_JOBS configuration is invalid.')

    if job_info['type'] == 'task':
        class_path = job_info.get('task')
        if not class_path:
            raise ImproperlyConfigured('Registered job {} does not specify a task.'.format(job_name))

        try:
            module_name, class_name = class_path.rsplit('.', 1)
            module = import_module(module_name)
            cls = getattr(module, class_name)
        except (ImportError, ValueError, AttributeError):
            raise ImproperlyConfigured('{} is not a valid task.'.format(class_path))

        return cls()
    elif job_info['type'] == 'workflow':
        path = job_info.get('path')
        if not path or not os.path.isfile(path):
            raise ImproperlyConfigured('The workflow {} does not exist.'.format(path))

        with open(path, 'r') as f:
            return Workflow.from_json(f.read())
    else:
        raise ImproperlyConfigured('Invalid job type: {}'.format(job_info['type']))


def process_web_inputs(task, inputs):
    pass
