import json
import math
import mimetypes
import os
import shutil
import tempfile

from numpy.ma.core import is_masked
from six.moves.urllib.error import URLError
from six.moves.urllib.parse import unquote
from PIL import Image
from clover.geometry.bbox import BBox
from clover.render.renderers.classified import ClassifiedRenderer
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.files import File
from django.http.response import HttpResponseBadRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
import netCDF4
from django.views.generic.edit import ProcessFormView, FormMixin
import numpy
import pyproj
from shapely.geometry import Point
import six
from ncdjango.exceptions import ConfigurationError
from ncdjango.forms import TemporaryFileForm
from ncdjango.geoimage import GeoImage
from ncdjango.models import Service, SERVICE_DATA_ROOT, TemporaryFile
from ncdjango.utils import project_geometry

FORCE_WEBP = getattr(settings, 'NC_FORCE_WEBP', False)
ENABLE_STRIDING = getattr(settings, 'NC_ENABLE_STRIDING', False)


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

    def get_grid_for_variable(self, variable, time_index=None, x_slice=None, y_slice=None):
        data = self.open_dataset(self.service).variables[variable.variable]

        valid_dimensions = (variable.y_dimension, variable.x_dimension)
        if time_index is not None:
            valid_dimensions = (variable.time_dimension,) + valid_dimensions

        dimensions = list(data.dimensions)
        slices = []

        for dimension in data.dimensions:
            if dimension in valid_dimensions:
                if x_slice and dimension == variable.x_dimension:
                    slices.append(slice(*x_slice))
                elif y_slice and dimension == variable.y_dimension:
                    slices.append(slice(*y_slice))
                elif dimension == variable.time_dimension and time_index is not None:
                    slices.append(time_index)
                    dimensions.remove(dimension)
                else:
                    slices.append(slice(None))
            else:
                slices.append(0)
                dimensions.remove(dimension)

        try:
            data = data[tuple(slices)]
        except IndexError:
            return numpy.array([])

        transpose_args = [dimensions.index(variable.y_dimension), dimensions.index(variable.x_dimension)]
        data = data.transpose(*transpose_args)

        return data

    def get_grid_spatial_dimensions(self, variable):
        """Returns (width, height) for the given variable"""

        data = self.open_dataset(self.service).variables[variable.variable]
        dimensions = list(data.dimensions)
        return data.shape[dimensions.index(variable.x_dimension)], data.shape[dimensions.index(variable.y_dimension)]

    def is_row_major(self, variable):
        data = self.open_dataset(self.service).variables[variable.variable]
        dimensions = list(data.dimensions)
        return dimensions.index(variable.y_dimension) < dimensions.index(variable.x_dimension)

    def is_y_increasing(self, variable):
        y_variable = self.open_dataset(self.service).variables.get(variable.y_dimension)
        return y_variable and y_variable[1] > y_variable[0]


class GetImageViewBase(NetCdfDatasetMixin, ServiceView):
    """Base view for handling image render requests. This view is implemented by specific interfaces."""

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
        This method should be implemented by the interface view class to process an incoming request and return an
        ImageConfiguration object and a list of RenderConfiguration objects (one per variable to render). When
        rendering multiple variables, the first variable in the returned list will be placed at the top of the final
        image.
        """

        raise NotImplementedError

    def format_image(self, image, image_format, **kwargs):
        """Returns an image in the request format"""

        if image_format in ('png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'):
            if image_format != 'webp' and FORCE_WEBP:
                # Always return WebP when supported by the browser
                accept = self.request.META['HTTP_ACCEPT'].split(',')
                if 'image/webp' in accept:
                    image = image.convert('RGBA')
                    image_format = 'webp'
                    kwargs = {'lossless': True}

            if image_format == 'png':
                kwargs['optimize'] = True
            elif image_format == 'jpg':
                image.convert('RGB')
                kwargs['progressive'] = True

            buffer = six.BytesIO()
            image.save(buffer, image_format, **kwargs)
            return buffer.getvalue(), "image/{}".format(image_format)
        else:
            raise ValueError('Unsupported format: {}'.format(image_format))

    def create_response(self, request, image, content_type):
        """Returns a response object for the given image. Can be overridden to return different responses."""

        return HttpResponse(content=image, content_type=content_type)

    def get_image(self, config, grid_bounds, size):
        variable = config.variable
        service = variable.service

        if service.supports_time and variable.supports_time:
            time_index = config.time_index or 0
        else:
            time_index = None

        data = self.get_grid_for_variable(
            variable, time_index=time_index, x_slice=(grid_bounds[0], grid_bounds[2]),
            y_slice=(grid_bounds[1], grid_bounds[3])
        )

        if ENABLE_STRIDING:
            y_scale = data.shape[0] / size[1]
            x_scale = data.shape[1] / size[0]

            if y_scale > 2:
                y_slice = slice(None, None, math.floor(y_scale))
            else:
                y_slice = slice(None, None, 1)

            if x_scale > 2:
                x_slice = slice(None, None, math.floor(x_scale))
            else:
                x_slice = slice(None, None, 1)

            data = data[y_slice, x_slice]

        if config.renderer.fill_value is None and hasattr(data, 'fill_value'):
            config.renderer.fill_value = data.fill_value

        image = config.renderer.render_image(data, row_major_order=self.is_row_major(variable)).convert('RGBA')

        #  If y values are increasing, the rendered image needs to be flipped vertically
        if self.is_y_increasing(variable):
            image = image.transpose(Image.FLIP_TOP_BOTTOM)

        return image

    def handle_request(self, request, **kwargs):
        try:
            base_config, configurations = self.get_render_configurations(request, **kwargs)

            extent = self._normalize_bbox(base_config.extent, base_config.size)
            size = base_config.size
            final_image = Image.new('RGBA', size, base_config.background_color.to_tuple())

            for config in reversed(configurations):
                native_extent = extent.project(pyproj.Proj(str(config.variable.projection)))
                dimensions = self.get_grid_spatial_dimensions(config.variable)

                cell_size = (
                    float(config.variable.full_extent.width) / dimensions[0],
                    float(config.variable.full_extent.height) / dimensions[1]
                )

                grid_bounds = [
                    int(math.floor(float(native_extent.xmin-config.variable.full_extent.xmin) / cell_size[0])) - 1,
                    int(math.floor(float(native_extent.ymin-config.variable.full_extent.ymin) / cell_size[1])) - 1,
                    int(math.ceil(float(native_extent.xmax-config.variable.full_extent.xmin) / cell_size[0])) + 1,
                    int(math.ceil(float(native_extent.ymax-config.variable.full_extent.ymin) / cell_size[1])) + 1
                ]

                grid_bounds = [
                    min(max(grid_bounds[0], 0), dimensions[0]),
                    min(max(grid_bounds[1], 0), dimensions[1]),
                    min(max(grid_bounds[2], 0), dimensions[0]),
                    min(max(grid_bounds[3], 0), dimensions[1])
                ]

                if not (grid_bounds[2] - grid_bounds[0] and grid_bounds[3] - grid_bounds[1]):
                    continue

                grid_extent = BBox((
                    config.variable.full_extent.xmin + grid_bounds[0]*cell_size[0],
                    config.variable.full_extent.ymin + grid_bounds[1]*cell_size[1],
                    config.variable.full_extent.xmin + grid_bounds[2]*cell_size[0],
                    config.variable.full_extent.ymin + grid_bounds[3]*cell_size[1]
                ), native_extent.projection)

                if not self.is_y_increasing(config.variable):
                    y_max = dimensions[1] - grid_bounds[1]
                    y_min = dimensions[1] - grid_bounds[3]
                    grid_bounds[1] = y_min
                    grid_bounds[3] = y_max

                image = GeoImage(self.get_image(config, grid_bounds, size), grid_extent)
                warped = image.warp(extent, size).image
                final_image.paste(warped, None, warped)

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

                geometry = project_geometry(
                    config.geometry, config.projection, pyproj.Proj(str(self.service.projection))
                )
                assert isinstance(geometry, Point)  # Only point-based identify is supported

                dimensions = self.get_grid_spatial_dimensions(config.variable)
                cell_size = (
                    float(variable.full_extent.width) / dimensions[0],
                    float(variable.full_extent.height) / dimensions[1]
                )
                cell_index = [
                    int(float(geometry.x-variable.full_extent.xmin) / cell_size[0]),
                    int(float(geometry.y-variable.full_extent.ymin) / cell_size[1])
                ]
                if not self.is_y_increasing(variable):
                    cell_index[1] = dimensions[1] - cell_index[1] - 1

                variable_data = self.get_grid_for_variable(
                    config.variable, time_index=time_index, x_slice=(cell_index[0], cell_index[0] + 1),
                    y_slice=(cell_index[1], cell_index[1] + 1)
                )

                if len(variable_data):
                    value = variable_data[0][0]
                    data[variable] = None if is_masked(value) else float(value)

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

        url_f = six.moves.urllib.request.urlopen(url)

        filename = url.split('?', 1)[0].split('/')[-1]
        if 'filename=' in url_f.info().get('Content-Disposition', ''):
            filename = url_f.info()['Content-Disposition'].split('filename=')[-1].strip('"\'')

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
            return HttpResponseBadRequest()

    def post(self, request):
        if request.POST.get('url'):
            return self.process_temporary_file(self.download_file(request.POST.get('url')))
        else:
            return self.get(request)


class TemporaryFileDownloadView(View):
    @method_decorator(login_required)
    @method_decorator(permission_required('ncdjango.download_temporaryfile'))
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(TemporaryFileDownloadView, self).dispatch(request, *args, **kwargs)

    def get(self, request, uuid):
        tmp_file = get_object_or_404(TemporaryFile, uuid=uuid)
        tmp_file.file.open('rb')

        return HttpResponse(tmp_file.file, content_type=mimetypes.guess_type(tmp_file.filename))
