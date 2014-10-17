import logging
from netCDF4 import Dataset
import os
import shutil
from tempfile import mkdtemp
from zipfile import ZipFile

from clover.geometry.bbox import BBox
from django.conf.urls import url
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import File
from django.core.files.storage import default_storage
from django.db.transaction import atomic
from django.utils.six import BytesIO
import numpy
from ocgis import Inspect
from ocgis.exc import OcgException, CFException
import pyproj
from tastypie import fields
from tastypie.authentication import SessionAuthentication, MultiAuthentication, ApiKeyAuthentication
from tastypie.authorization import DjangoAuthorization
from tastypie.exceptions import ImmediateHttpResponse, NotFound
from tastypie.http import HttpBadRequest
from tastypie.resources import ModelResource
from tastypie.serializers import Serializer
from tastypie.utils import trailing_slash

from ncdjango.interfaces.arcgis_extended.utils import get_renderer_from_definition
from ncdjango.models import TemporaryFile, Service, Variable, SERVICE_DATA_ROOT


logger = logging.getLogger(__name__)


class TemporaryFileResource(ModelResource):
    uuid = fields.CharField(attribute='uuid', readonly=True)

    class Meta:
        queryset = TemporaryFile.objects.all()
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get', 'delete']
        resource_name = 'temporary-files'
        authentication = MultiAuthentication(SessionAuthentication(), ApiKeyAuthentication())
        authorization = DjangoAuthorization()
        fields = ['uuid', 'date', 'filename']
        detail_uri_name = 'uuid'
        serializer = Serializer(formats=['json', 'jsonp'])

    def _convert_number(self, number):
        """Converts a number to float or int as appropriate"""

        number = float(number)
        return int(number) if number.is_integer() else float(number)

    def prepend_urls(self):
        return [
            url(
                r"^(?P<resource_name>%s)/(?P<%s>.*?)/inspect%s$" % (
                    self._meta.resource_name, self._meta.detail_uri_name, trailing_slash()
                ),
                self.wrap_view('inspect'), name='temporary_file_inspect'
            )
        ]

    def inspect(self, request, **kwargs):
        self.is_authenticated(request)

        bundle = self.build_bundle(request=request)
        obj = self.obj_get(bundle, **self.remove_api_resource_names(kwargs))

        temp_dir = None

        try:
            if obj.extension == 'nc':
                dataset_path = obj.file.name
            elif obj.extension == 'zip':
                temp_dir = mkdtemp()
                zf = ZipFile(obj.file.name)

                try:
                    nc_name = None

                    for name in zf.namelist():
                        if name[-3:] == '.nc':
                            nc_name = name

                    if nc_name:
                        zf.extract(nc_name, temp_dir)
                        dataset_path = os.path.join(temp_dir, nc_name)
                    else:
                        raise ImmediateHttpResponse(HttpBadRequest('No .nc file found in zip archive.'))
                finally:
                    zf.close()
            else:
                raise ImmediateHttpResponse(HttpBadRequest('Unsupported file format.'))

            dataset_info = Inspect(dataset_path)
            dataset = Dataset(dataset_path)
            data = {
                'dimensions': {},
                'variables': {}
            }

            for dimension in dataset_info.meta['dimensions'].items():
                data['dimensions'][dimension[0]] = {
                    'length': dimension[1].get('len'),
                    'is_unlimited': dimension[1].get('isunlimited', False)
                }

                if dimension[0] in dataset_info.meta['variables']:
                    data['dimensions'][dimension[0]].update({
                        'attributes': dataset_info.meta['variables'][dimension[0]].get('attrs'),
                        'min': self._convert_number(numpy.amin(dataset.variables[dimension[0]][:])),
                        'max': self._convert_number(numpy.amax(dataset.variables[dimension[0]][:]))
                    })

            for variable in dataset_info.meta['variables'].items():
                if variable[0] not in data['dimensions'] and len(variable[1].get('dimensions', [])) >= 2:
                    try:
                        variable_info = Inspect(dataset_path, variable=variable[0])
                    except (ValueError, CFException, KeyError):
                        variable_info = None

                    variable_data = dataset.variables[variable[0]][:]
                    data['variables'][variable[0]] = {
                        'dimensions': list(variable[1].get('dimensions') or []),
                        'attributes': variable[1].get('attrs'),
                        'proj4': variable_info.ds.spatial.crs.sr.ExportToProj4() if variable_info else None,
                        'min': self._convert_number(numpy.min(variable_data)),
                        'max': self._convert_number(numpy.max(variable_data))
                    }

                    if variable_info:
                        try:
                            data['variables'][variable[0]].update({
                                'time': {
                                    'extent': [x.isoformat(' ') for x in variable_info.ds.temporal.extent_datetime],
                                    'calendar': variable_info.ds.temporal.calendar,
                                    'units': variable_info.ds.temporal.units,
                                    'count': variable_info.ds.temporal.shape[0],
                                    'resolution': (
                                        int(variable_info.ds.temporal.resolution) if
                                        variable_info.ds.temporal.resolution else None
                                    )
                                }
                            })
                        except (OcgException, CFException):
                            pass

                        try:
                            data['variables'][variable[0]].update({
                                'extent': [self._convert_number(x) for x in variable_info.ds.spatial.grid.extent or []],
                                'resolution': variable_info.ds.spatial.grid.resolution
                            })
                        except (OcgException, CFException):
                            pass
                    else:
                        variable_info = dataset.variables[variable[0]]
                        if 'proj4' in variable_info.ncattrs():
                            data['variables'][variable[0]]['proj4'] = variable_info.proj4

            bundle.data = data
            return self.create_response(request, bundle)

        finally:
            try:
                if temp_dir is not None:
                    shutil.rmtree(temp_dir)
            except (IOError, OSError):
                pass


class ServiceResource(ModelResource):
    data_path = fields.CharField(attribute='data_path', readonly=True)
    variables = fields.ToManyField(
        'ncdjango.api.VariableResource', attribute='variable_set', full=True, full_list=False, related_name='service',
        null=True
    )

    class Meta:
        queryset = Service.objects.all()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'post', 'put', 'patch', 'delete']
        resource_name = 'services'
        authentication = MultiAuthentication(SessionAuthentication(), ApiKeyAuthentication())
        authorization = DjangoAuthorization()
        fields = [
            'id', 'name', 'description', 'data_path', 'projection', 'full_extent', 'initial_extent', 'supports_time',
            'time_start', 'time_end', 'render_top_layer_only', 'time_interval', 'time_interval_units', 'calendar'
        ]
        serializer = Serializer(formats=['json', 'jsonp'])
        filtering = {
            'name': ['exact', 'in']
        }

    def dehydrate_full_extent(self, bundle):
        return bundle.obj.full_extent.as_list()

    def dehydrate_initial_extent(self, bundle):
        return bundle.obj.initial_extent.as_list()

    def hydrate_full_extent(self, bundle):
        if bundle.data.get('full_extent'):
            bundle.data['full_extent'] = BBox(bundle.data['full_extent'])

        return bundle

    def hydrate_initial_extent(self, bundle):
        if bundle.data.get('initial_extent'):
            bundle.data['initial_extent'] = BBox(bundle.data['initial_extent'])

        return bundle

    @atomic
    def obj_create(self, bundle, **kwargs):
        bundle = super(ServiceResource, self).obj_create(bundle, **kwargs)

        projection = pyproj.Proj(str(bundle.obj.projection))
        bundle.obj.full_extent.projection = projection
        bundle.obj.initial_extent.projection = projection
        for variable in bundle.obj.variable_set.all():
            variable.full_extent.projection = projection

        if bundle.data.get('tmp_file'):
            tmp_file = TemporaryFileResource().get_via_uri(bundle.data['tmp_file'], request=bundle.request)
            tmp_file.file.open()

            if tmp_file.extension.lower() == "zip":
                zf = ZipFile(tmp_file.file, 'r')
                nc_name = None
                for name in zf.namelist():
                    if name[-3:].lower() == ".nc":
                        nc_name = name
                        break
                if not nc_name:
                    raise ImmediateHttpResponse(HttpBadRequest('Could not find .nc file in zip archive'))
                fp = File(BytesIO(zf.read(name)))
            else:
                fp = File(tmp_file.file)
            fp.open()

            base_filename = tmp_file.filename[:-len(tmp_file.extension)-1]
            name = default_storage.save(
                "{0}{1}/{2}.nc".format(SERVICE_DATA_ROOT, bundle.obj.name, base_filename), fp
            )

            bundle.obj.data_path = name[len(SERVICE_DATA_ROOT):]
            bundle.obj.save()
            tmp_file.delete()

            return bundle
        else:
            raise ImmediateHttpResponse(HttpBadRequest("Missing required 'tmp_file' parameter"))

    def obj_delete(self, bundle, **kwargs):
        if not hasattr(bundle.obj, 'delete'):
            try:
                bundle.obj = self.obj_get(bundle=bundle, **kwargs)
            except ObjectDoesNotExist:
                raise NotFound("A model instance matching the provided arguments could not be found.")

        data_file = os.path.join(SERVICE_DATA_ROOT, bundle.obj.data_path)

        with atomic():
            super(ServiceResource, self).obj_delete(bundle, **kwargs)

        if bundle.request.GET.get('delete_data', 'false').lower().strip() == "true":
            try:
                os.remove(data_file)
            except OSError:
                logger.warn('Could not delete file {}'.format(data_file))


class VariableResource(ModelResource):
    service = fields.ToOneField(ServiceResource, attribute='service', full=False)

    class Meta:
        queryset = Variable.objects.all()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'post', 'put', 'patch', 'delete']
        resource_name = 'variables'
        authentication = MultiAuthentication(SessionAuthentication(), ApiKeyAuthentication())
        authorization = DjangoAuthorization()
        fields = [
            'id', 'index', 'variable', 'projection', 'x_dimension', 'y_dimension', 'name', 'description', 'renderer',
            'full_extent', 'supports_time', 'time_dimension', 'time_start', 'time_end', 'time_steps'
        ]
        serializer = Serializer(formats=['json', 'jsonp'])
        filtering = {
            'name': ['exact'],
            'service': ['exact'],
            'service__name': ['exact']
        }

    def dehydrate_full_extent(self, bundle):
        return bundle.obj.full_extent.as_list()

    def hydrate_full_extent(self, bundle):
        if bundle.data.get('full_extent'):
            bundle.data['full_extent'] = BBox(bundle.data['full_extent'])

        return bundle

    def hydrate_renderer(self, bundle):
        if bundle.data.get('renderer'):
            bundle.data['renderer'] = get_renderer_from_definition(bundle.data['renderer'])

        return bundle

    def save(self, bundle, skip_errors=False):
        if not bundle.obj.projection:
            bundle.obj.projection = bundle.obj.service.projection

        bundle.obj.full_extent.projection = pyproj.Proj(str(bundle.obj.projection))

        return super(VariableResource, self).save(bundle, skip_errors=skip_errors)