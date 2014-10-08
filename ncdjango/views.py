import json
import os
import shutil
import tempfile
from urllib.error import URLError
from urllib.parse import unquote
from PIL import Image
from clover.geometry.bbox import BBox
from clover.render.renderers.classified import ClassifiedRenderer
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.cache import get_cache
from django.core.files import File
from django.core.files.storage import default_storage
from django.http.response import HttpResponseBadRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
import time
import netCDF4
from django.views.generic.edit import ProcessFormView, FormMixin, CreateView
import numpy
import pyproj
from shapely.geometry import Point
import six
from ncdjango.exceptions import ConfigurationError
from ncdjango.forms import TemporaryFileForm
from ncdjango.geoimage import GeoImage
from ncdjango.models import Service, SERVICE_DATA_ROOT, TemporaryFile
from ncdjango.utils import project_geometry, proj4_to_wkt

CACHE_FULL_EXTENT = getattr(settings, 'NC_CACHE_FULL_EXTENT', False)
FULL_EXTENT_CACHE = getattr(settings, 'NC_FULL_EXTENT_CACHE', 'default')
FULL_EXTENT_CACHE_TIMEOUT = getattr(settings, 'NC_CACHE_FULL_EXTENT_TIMEOUT', 60)

FULL_EXTENT_CACHE_KEY = "ncdjango_full_extent_{hash}"
FULL_EXTENT_PENDING_KEY = "ncdjango_full_extent_pending_{hash}"


class ServiceView(View):
    """Base view for map service requests"""

    http_method_names = ['get', 'post', 'head', 'options']

    def __init__(self, *args, **kwargs):
        self.service = None

        super(ServiceView, self).__init__(*args, **kwargs)

    def get_service_name(self, request, *args, **kwargs):
        """
        This method should be implemented by the interface view class to return the service name based on the request
        and URL parameters (provided as args and kwargs.
        """

        raise NotImplementedError

    def handle_request(self, request, **kwargs):
        """This method is called in response to either a GET or POST with GET or POST data respectively"""

        raise NotImplementedError

    def dispatch(self, request, *args, **kwargs):
        self.service = get_object_or_404(Service, name=self.get_service_name(request, *args, **kwargs))
        return super(ServiceView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self.handle_request(request, **request.GET.dict())

    def post(self, request, *args, **kwargs):
        return self.handle_request(request, **request.POST.dict())


class NetCdfDatasetMixin(object):
    """View mixin for handling NetCDF datasets"""

    def __init__(self, *args, **kwargs):
        self.dataset = None

        super(NetCdfDatasetMixin, self).__init__(*args, **kwargs)

    def open_dataset(self, service):
        """Opens and returns the NetCDF dataset associated with a service, or returns a previously-opened dataset"""

        if not self.dataset:
            path = os.path.join(SERVICE_DATA_ROOT, service.data_path)
            self.dataset = netCDF4.Dataset(path, 'r')
        return self.dataset

    def close_dataset(self):
        if self.dataset:
            self.dataset.close()
            self.dataset = None

    def get_grid_for_variable(self, variable, time_index=None):
        netcdf_variable = self.open_dataset(self.service).variables[variable.variable]
        data = netcdf_variable[:]

        valid_dimensions = (variable.y_dimension, variable.x_dimension)
        if time_index is not None:
            valid_dimensions = (variable.time_dimension,) + valid_dimensions

        dimensions = list(netcdf_variable.dimensions)
        for dimension in netcdf_variable.dimensions:
            if not dimension in valid_dimensions:
                data = numpy.rollaxis(data, dimensions.index(dimension))[0]
                dimensions.remove(dimension)

        transpose_args = [dimensions.index(variable.y_dimension), dimensions.index(variable.x_dimension)]
        if time_index is not None:
            transpose_args.append(dimensions.index(variable.time_dimension))
            data = data.transpose(*transpose_args)[:, :, time_index]
        else:
            data = data.transpose(*transpose_args)

        return data

    def is_row_major(self, variable):
        netcdf_variable = self.open_dataset(self.service).variables[variable.variable]
        return (
            netcdf_variable.dimensions.index(
                variable.y_dimension) < netcdf_variable.dimensions.index(variable.x_dimension
            )
        )

    def is_y_increasing(self, variable):
        y_variable = self.open_dataset(self.service).variables.get(variable.y_dimension)
        return y_variable and y_variable[1] > y_variable[0]


class GetImageViewBase(NetCdfDatasetMixin, ServiceView):
    """Base view for handling image render requests. This view is implemented by specific interfaces."""

    def _image_to_cache(self, image):
        buffer = six.BytesIO()
        image.save(buffer, "png")
        return buffer.getvalue()

    def _cache_to_image(self, bytes):
        return Image.open(six.BytesIO(bytes))

    def _normalize_bbox(self, bbox, size):
        """Returns this bbox normalized to match the ratio of the given size."""

        bbox_ratio = float(bbox.width) / float(bbox.height)
        size_ratio = float(size[0]) / float(size[1])

        if round(size_ratio, 4) == round(bbox_ratio, 4):
            return bbox
        else:
            if bbox.height * size_ratio >= bbox.width:
                diff = bbox.height*size_ratio - bbox.width
                return BBox((bbox.xmin - diff/2, bbox.ymin, bbox.xmax + diff/2, bbox.ymax), bbox.projection)
            else:
                diff = abs(bbox.width/size_ratio - bbox.height)
                return BBox((bbox.xmin, bbox.ymin - diff/2, bbox.xmax, bbox.ymax + diff/2), bbox.projection)

    def get_render_configurations(self, request, **kwargs):
        """
        This method should be implemented by the interface view class to process an incoming request and return a list
        of RenderConfiguration objects (one per variable to render). When rendering multiple variables, the first
        variable in the returned list will be placed at the top of the final image.
        """

        raise NotImplementedError

    def format_image(self, image, image_format):
        """Returns an image in the request format"""

        if image_format in ('png', 'jpg', 'jpeg', 'gif', 'bmp'):
            buffer = six.BytesIO()
            image.save(buffer, image_format)
            return buffer.getvalue(), "image/{}".format(image_format)
        else:
            raise ValueError('Unsupported format: {}'.format(image_format))

    def create_response(self, request, image, content_type):
        """Returns a response object for the given image. Can be overridden to return different responses."""

        return HttpResponse(content=image, content_type=content_type)

    def get_full_extent_image(self, config):
        config_hash = config.hash

        if CACHE_FULL_EXTENT:
            cache = get_cache(FULL_EXTENT_CACHE)
            cache_wait_start = time.time()

            while time.time() - cache_wait_start < FULL_EXTENT_CACHE_TIMEOUT:
                image = cache.get(FULL_EXTENT_CACHE_KEY.format(hash=config_hash))
                if image:
                    return self._cache_to_image(image)  # The full extent has already been rendered
                elif cache.get(FULL_EXTENT_PENDING_KEY.format(hash=config_hash)):
                    time.sleep(0.1)  # The full extent render is pending; wait and try again
                    continue
                else:
                    break  # No full extent and no render pending
            cache.set(FULL_EXTENT_PENDING_KEY.format(hash=config_hash), True)

        try:
            variable = config.variable
            service = variable.service

            if service.supports_time and variable.supports_time:
                time_index = config.time_index or 0
            else:
                time_index = None

            data = self.get_grid_for_variable(variable, time_index=time_index)

            if hasattr(data, 'fill_value'):
                config.renderer.fill_value = data.fill_value

            image = config.renderer.render_image(data, row_major_order=self.is_row_major(variable))

            #  If y values are increasing, the rendered image needs to be flipped vertically
            if self.is_y_increasing(variable):
                image = image.transpose(Image.FLIP_TOP_BOTTOM)

            if CACHE_FULL_EXTENT:
                cache.set(FULL_EXTENT_CACHE_KEY.format(hash=config_hash), self._image_to_cache(image))

            return image
        finally:
            if CACHE_FULL_EXTENT:
                cache.delete(FULL_EXTENT_PENDING_KEY.format(hash=config_hash))
            self.close_dataset()

    def handle_request(self, request, **kwargs):
        try:
            configurations = self.get_render_configurations(request, **kwargs)
            if not configurations:
                return HttpResponse()

            base_config = configurations[0]
            extent = self._normalize_bbox(base_config.extent, base_config.size)
            size = base_config.size
            final_image = Image.new('RGBA', size, base_config.background_color.to_tuple())

            for config in reversed(configurations):
                image = GeoImage(self.get_full_extent_image(config), config.variable.full_extent)
                final_image.paste(image.warp(extent, size).image, None)

            final_image, content_type = self.format_image(final_image, base_config.image_format)

            return self.create_response(request, final_image, content_type)

        except ConfigurationError:
            return HttpResponseBadRequest()
        finally:
            self.close_dataset()


class IdentifyViewBase(NetCdfDatasetMixin, ServiceView):
    """Base view for handling identify requests. This view is implemented by specific interfaces."""

    def serialize_data(self, data):
        """
        Implemented by interface class to serialize identify results. Should return serialized data and
        content MIME type.
        """

        raise NotImplementedError

    def get_identify_configurations(self, request, **kwargs):
        """
        This method should be implemented by the interface view class to process an incoming request and return a list
        of IdentifyConfiguration objects (one per variable to identify).
        """

        raise NotImplementedError

    def create_response(self, request, content, content_type):
        """Returns a response object for the request. Can be overridden to return different responses."""

        return HttpResponse(content=content, content_type=content_type)

    def handle_request(self, request, **kwargs):
        try:
            configurations = self.get_identify_configurations(request, **kwargs)
            if not configurations:
                return HttpResponse()

            data = {}

            for config in configurations:
                variable = config.variable
                service = variable.service

                if service.supports_time and variable.supports_time:
                    time_index = config.time_index or 0
                else:
                    time_index = None

                geometry = project_geometry(config.geometry, config.projection, pyproj.Proj(self.service.projection))
                assert isinstance(geometry, Point)  # Only point-based identify is supported
                variable_data = self.get_grid_for_variable(config.variable, time_index=time_index)

                cell_size = (
                    float(variable.full_extent.width) / variable_data.shape[1],
                    float(variable.full_extent.height) / variable_data.shape[0]
                )

                cell_index = [
                    int(float(geometry.x-variable.full_extent.xmin) / cell_size[0]),
                    int(float(geometry.y-variable.full_extent.ymin) / cell_size[1])
                ]
                if not self.is_y_increasing(variable):
                    cell_index[1] = variable_data.shape[0] - cell_index[1] - 1

                if variable_data.shape[1] > cell_index[0] >= 0 and variable_data.shape[0] > cell_index[1] >= 0:
                    data[variable] = float(variable_data[cell_index[1]][cell_index[0]])

            data, content_type = self.serialize_data(data)
            return self.create_response(request, data, content_type=content_type)

        except ConfigurationError:
            return HttpResponseBadRequest()
        finally:
            self.close_dataset()


class LegendViewBase(NetCdfDatasetMixin, ServiceView):
    def serialize_data(self, data):
        """
        Implemented by interface class to serialize identify results. Should return serialized data and
        content MIME type.
        """

        raise NotImplementedError

    def get_legend_configurations(self, request, **kwargs):
        """
        This method should be implemented by the interface view class to process an incoming request and return a list
        of LegendConfiguration objects (one per variable to identify).
        """

        raise NotImplementedError

    def create_response(self, request, content, content_type):
        """Returns a response object for the request. Can be overridden to return different responses."""

        return HttpResponse(content=content, content_type=content_type)

    def handle_request(self, request, **kwargs):
        dataset = self.open_dataset(self.service)

        try:
            configurations = self.get_legend_configurations(request, **kwargs)
            if not configurations:
                return HttpResponse()

            data = {}

            for config in configurations:
                kwargs = {}
                if isinstance(config.renderer, ClassifiedRenderer):
                    min_value = numpy.min(dataset.variables[config.variable.variable][:])
                    kwargs['min_value'] = min_value

                data[config.variable] = config.renderer.get_legend(*config.size)

            data, content_type = self.serialize_data(data)
            return self.create_response(request, data,content_type=content_type)
        finally:
            self.close_dataset()


class TemporaryFileUploadViewBase(View):
    @method_decorator(login_required)
    @method_decorator(permission_required('ncdjango.add_temporaryfile'))
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(TemporaryFileUploadViewBase, self).dispatch(request, *args, **kwargs)

    def process_temporary_file(self, tmp_file):
        """Truncates the filename if necessary, saves the model, and returns a response"""

        #Truncate filename if necessary
        if len(tmp_file.filename) > 100:
            base_filename = tmp_file.filename[:tmp_file.filename.rfind(".")]
            tmp_file.filename = "%s.%s" % (base_filename[:99-len(tmp_file.extension)], tmp_file.extension)

        tmp_file.save()

        data = {
            'uuid': str(tmp_file.uuid)
        }

        response = HttpResponse(json.dumps(data), status=201)
        response['Content-type'] = "text/plain"

        return response


class TemporaryFileUploadFormView(FormMixin, TemporaryFileUploadViewBase, ProcessFormView):
    form_class = TemporaryFileForm

    def form_valid(self, form):
        tmp_file = form.save(commit=False)
        tmp_file.filename = self.request.FILES['file'].name
        tmp_file.filesize = self.request.FILES['file'].size

        return self.process_temporary_file(tmp_file)

    def form_invalid(self, form):
        return HttpResponseBadRequest()


class TemporaryFileUploadUrlView(TemporaryFileUploadViewBase):
    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        try:
            return super(TemporaryFileUploadUrlView, self).dispatch(request, *args, **kwargs)
        except URLError as e:
            return HttpResponseBadRequest(e.reason)

    def download_file(self, url):
        filename = url.split('/')[-1].split('?')[0]
        url_f = six.moves.urllib.request.urlopen(url)
        f = tempfile.TemporaryFile()
        shutil.copyfileobj(url_f, f)

        tmp_file = TemporaryFile(
            filename=filename
        )
        tmp_file.file.save(filename, File(f), save=False)
        tmp_file.filesize = tmp_file.file.size

        return tmp_file

    def get(self, request):
        if request.GET.get('url'):
            return self.process_temporary_file(self.download_file(unquote(request.GET.get('url'))))
        else:
            raise HttpResponseBadRequest()

    def post(self, request):
        if request.POST.get('url'):
            return self.process_temporary_file(self.download_file(request.POST.get('url')))
        else:
            return self.get(request)