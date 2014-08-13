from zipfile import ZipFile
from clover.geometry.bbox import BBox
from django.core.files.base import File
from django.core.files.storage import default_storage
from django.db.transaction import commit_on_success
from django.utils.six import BytesIO
import pyproj
from tastypie import fields
from tastypie.authentication import SessionAuthentication
from tastypie.authorization import DjangoAuthorization
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpBadRequest
from tastypie.resources import ModelResource
from tastypie.serializers import Serializer
from ncdjango.interfaces.arcgis_extended.utils import get_renderer_from_definition
from ncdjango.models import TemporaryFile, Service, Variable, SERVICE_DATA_ROOT


class TemporaryFileResource(ModelResource):
    uuid = fields.CharField(attribute='uuid', readonly=True)

    class Meta:
        queryset = TemporaryFile.objects.all()
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get', 'delete']
        resource_name = 'temporary-files'
        authentication = SessionAuthentication()
        authorization = DjangoAuthorization()
        fields = ['uuid', 'date', 'filename']
        detail_uri_name = 'uuid'
        serializer = Serializer(formats=['json', 'jsonp'])


class ServiceResource(ModelResource):
    data_path = fields.CharField(attribute='data_path', readonly=True)
    variables = fields.ToManyField(
        'ncdjango.api.VariableResource', attribute='variable_set', full=True, full_list=False, related_name='service'
    )

    class Meta:
        queryset = Service.objects.all()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'post', 'put', 'patch', 'delete']
        resource_name = 'services'
        authentication = SessionAuthentication()
        authorization = DjangoAuthorization()
        fields = [
            'id', 'name', 'description', 'data_path', 'projection', 'full_extent', 'initial_extent', 'x_dimension',
            'y_dimension', 'supports_time', 'time_dimension', 'time_start', 'time_end', 'time_interval',
            'time_interval_units', 'calendar', 'render_top_layer_only'
        ]
        serializer = Serializer(formats=['json', 'jsonp'])

    def dehydrate_full_extent(self, bundle):
        return bundle.obj.full_extent.as_list()

    def dehydrate_initial_extent(self, bundle):
        return bundle.obj.initial_extent.as_list()

    def hydrate_full_extent(self, bundle):
        bundle.data['full_extent'] = BBox(bundle.data['full_extent'])
        return bundle

    def hydrate_initial_extent(self, bundle):
        bundle.data['initial_extent'] = BBox(bundle.data['initial_extent'])
        return bundle

    @commit_on_success
    def obj_create(self, bundle, **kwargs):
        bundle = super(ServiceResource, self).obj_create(bundle, **kwargs)

        projection = pyproj.Proj(bundle.obj.projection)
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


class VariableResource(ModelResource):
    service = fields.ToOneField(ServiceResource, attribute='service', full=False)

    class Meta:
        queryset = Variable.objects.all()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'post', 'put', 'patch', 'delete']
        resource_name = 'variables'
        authentication = SessionAuthentication()
        authorization = DjangoAuthorization()
        fields = [
            'id', 'index', 'variable', 'name', 'description', 'renderer', 'full_extent', 'supports_time', 'time_start',
            'time_end', 'time_steps'
        ]
        serializer = Serializer(formats=['json', 'jsonp'])

    def dehydrate_full_extent(self, bundle):
        return bundle.obj.full_extent.as_list()

    def hydrate_full_extent(self, bundle):
        bundle.data['full_extent'] = BBox(bundle.data['full_extent'])
        return bundle

    def hydrate_renderer(self, bundle):
        bundle.data['renderer'] = get_renderer_from_definition(bundle.data['renderer'])
        return bundle