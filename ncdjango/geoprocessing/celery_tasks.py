import copy
import json
import logging
import os
from datetime import timedelta
from importlib import import_module

import errno
import six
from celery.task import task
from clover.render.renderers import RasterRenderer
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils.timezone import now

from ncdjango.geoprocessing.utils import get_task_instance, process_web_inputs, process_web_outputs, REGISTERED_JOBS
from ncdjango.models import ProcessingJob, ProcessingResultService, SERVICE_DATA_ROOT

logger = logging.getLogger(__name__)

MAX_TEMPORARY_SERVICE_AGE = getattr(settings, 'NC_MAX_TEMPORARY_SERVICE_AGE', 43200)  # 12 hours


@task(bind=True)
def run_job(self, job_name, inputs):
    job_info = REGISTERED_JOBS[job_name]
    results_renderer = job_info.get('results_renderer')

    if isinstance(results_renderer, six.string_types):
        try:
            module_name, class_name = results_renderer.rsplit('.', 1)
            module = import_module(module_name)
            results_renderer = getattr(module, class_name)
        except (ImportError, ValueError, AttributeError):
            raise ImproperlyConfigured('Could not import {}'.format(results_renderer))

    if not any((results_renderer is None, callable(results_renderer), isinstance(results_renderer, RasterRenderer))):
        raise ImproperlyConfigured('Invalid renderer: {}'.format(results_renderer))

    t = get_task_instance(job_name)
    results = t(**process_web_inputs(t, copy.copy(inputs)))
    publish_raster_results = job_info.get('publish_raster_results', False)

    job = ProcessingJob.objects.get(celery_id=self.request.id)
    job.outputs=json.dumps(process_web_outputs(results, job, publish_raster_results, results_renderer))
    job.save()


@task
def cleanup_temporary_services():
    cutoff = now() - timedelta(seconds=MAX_TEMPORARY_SERVICE_AGE)
    services = ProcessingResultService.objects.filter(is_temporary=True, created__lt=cutoff)
    files_to_delete = []

    with transaction.atomic():
        for service in services:
            files_to_delete.append(os.path.join(SERVICE_DATA_ROOT, service.service.data_path))
            service.service.delete()

    for path in files_to_delete:
        try:
            os.remove(path)
            os.rmdir(os.path.dirname(path))  # Delete the enclosing directory, if empty
        except OSError as e:
            if e.errno != errno.ENOTEMPTY:
                logger.warn('Error deleting temporary service data: {}'.format(str(e)))

