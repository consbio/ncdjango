import os
from importlib import import_module

import numpy
import six
from clover.netcdf.crs import set_crs
from clover.netcdf.variable import SpatialCoordinateVariables
from clover.render.renderers.stretched import StretchedRenderer
from clover.utilities.color import Color
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from netCDF4 import Dataset
from numpy.ma.core import is_masked
from rasterio.dtypes import is_ndarray
from shapely.geometry import shape

from ncdjango.geoprocessing import params
from ncdjango.geoprocessing.data import is_raster
from ncdjango.geoprocessing.params import ParameterNotValidError
from ncdjango.geoprocessing.workflow import Workflow
from ncdjango.models import SERVICE_DATA_ROOT, Service, Variable, ProcessingResultService

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
    for param in task.inputs:
        if param.name in inputs:
            if isinstance(param, (params.RasterParameter, params.NdArrayParameter)):
                inputs[param.name] = params.RegisteredDatasetParameter(param.name).clean(inputs[param.name])

            elif isinstance(param, params.FeatureParameter):
                try:
                    inputs[param.name] = shape(inputs[param.name])
                except (ValueError, AttributeError, KeyError):
                    raise ParameterNotValidError

            elif isinstance(param, params.ListParameter):
                if isinstance(param.param_type, (params.RasterParameter, params.NdArrayParameter)):
                    inputs[param.name] = [
                        params.RegisteredDatasetParameter(param.name).clean(x) for x in inputs[param.name]
                    ]

                elif isinstance(param.param_type, params.FeatureParameter):
                    try:
                        inputs[param.name] = [shape(x) for x in inputs[param.name]]
                    except (ValueError, AttributeError, KeyError):
                        raise ParameterNotValidError

    return task.validate_inputs(inputs)


def process_web_outputs(results, job, publish_raster_results=False, renderer_or_fn=None):
    outputs = results.format_args()

    for k, v in six.iteritems(outputs):
        if is_raster(v) and publish_raster_results:
            service_name = '{0}/{1}'.format(job.uuid, k)
            rel_path = '{}.nc'.format(service_name)
            abs_path = os.path.join(SERVICE_DATA_ROOT, rel_path)
            os.makedirs(os.path.dirname(abs_path))

            with Dataset(abs_path, 'w', format='NETCDF4') as ds:
                if v.extent.projection.is_latlong():
                    x_var = 'longitude'
                    y_var = 'latitude'
                else:
                    x_var = 'x'
                    y_var = 'y'

                coord_vars = SpatialCoordinateVariables.from_bbox(v.extent, *reversed(v.shape))
                coord_vars.add_to_dataset(ds, x_var, y_var)

                fill_value = v.fill_value if is_masked(v) else None
                data_var = ds.createVariable('data', v.dtype, dimensions=(y_var, x_var), fill_value=fill_value)
                data_var[:] = v
                set_crs(ds, 'data', v.extent.projection)

            if callable(renderer_or_fn):
                renderer = renderer_or_fn(v)
            elif renderer_or_fn is None:
                renderer = StretchedRenderer(
                    [(numpy.min(v).item(), Color(0, 0, 0)), (numpy.max(v).item(), Color(255, 255, 255))]
                )
            else:
                renderer = renderer_or_fn

            with transaction.atomic():
                service = Service.objects.create(
                    name=service_name,
                    description='This service has been automatically generated from the result of a geoprocessing job.',
                    data_path=rel_path,
                    projection=v.extent.projection.srs,
                    full_extent=v.extent,
                    initial_extent=v.extent,
                )
                Variable.objects.create(
                    service=service,
                    index=0,
                    variable='data',
                    projection=v.extent.projection.srs,
                    x_dimension=x_var,
                    y_dimension=y_var,
                    name='data',
                    renderer=renderer,
                    full_extent=v.extent
                )
                ProcessingResultService.objects.create(job=job, service=service)

            outputs[k] = service_name

        elif is_ndarray(v):
            if v.size < numpy.get_printoptions()['threshold']:
                outputs[k] = v.tolist()
            else:
                outputs[k] = str(v)

    return outputs
