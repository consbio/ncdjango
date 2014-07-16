from PIL import Image
from django.conf import settings
from django.core.cache import get_cache
from django.http.response import HttpResponseBadRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View
import time
import netCDF4
import numpy
import six
from ncdjango.exceptions import ConfigurationError
from ncdjango.geoimage import GeoImage
from ncdjango.models import Service

CACHE_FULL_EXTENT = getattr(settings, 'NC_CACHE_FULL_EXTENT', False)
FULL_EXTENT_CACHE = getattr(settings, 'NC_FULL_EXTENT_CACHE', 'default')
FULL_EXTENT_CACHE_TIMEOUT = getattr(settings, 'NC_CACHE_FULL_EXTENT_TIMEOUT', 60)

FULL_EXTENT_CACHE_KEY = "ncdjango_full_extent_{hash}"
FULL_EXTENT_PENDING_KEY = "ncdjango_full_extent_pending_{hash}"


class GetImageViewBase(View):
    """Base view for handling image render requests. This view is implemented by specific interfaces."""

    http_method_names = ['get', 'post', 'head', 'options']

    def __init__(self, *args, **kwargs):
        self.service = None
        self.dataset = None

        super(GetImageViewBase, self).__init__(*args, **kwargs)

    def _open_dataset(self, service):
        """Opens and returns the NetCDF dataset associated with a service, or returns a previously-opened dataset"""

        if not self.dataset:
            self.dataset = netCDF4.Dataset(service.data_path, 'r')
        return self.dataset

    def _close_dataset(self):
        if self.dataset:
            self.dataset.close()
            self.dataset = None

    def _image_to_cache(self, image):
        buffer = six.StringIO()
        image.save(buffer, "png")
        return buffer.getvalue()

    def _cache_to_image(self, bytes):
        return Image.open(six.StringIO(bytes))

    def get_render_configurations(self, request, **kwargs):
        """
        This method should be implemented by the interface view class to process an incoming request and return a list
        of RenderConfiguration objects (one per variable to render). When rendering multiple variables, the first
        variable in the returned list will be placed at the top of the final image.
        """

        raise NotImplementedError

    def get_service_name(self, request, *args, **kwargs):
        """
        This method should be implemented by the interface view class to return the service name based on the request
        and URL parameters (provided as args and kwargs.
        """

        raise NotImplementedError

    def format_image(self, image, image_format):
        """Returns an image in the request format"""

        if image_format in ('png', 'jpg', 'jpeg', 'gif', 'bmp'):
            buffer = six.StringIO()
            image.save(buffer, image_format)
            return buffer.getvalue(), "image/{}".format(image_format)
        else:
            raise ValueError('Unsupported format: {}'.format(image_format))

    def create_response(self, request, image, mimetype):
        """Returns a response object for the given image. Can be overridden to return different responses."""

        return HttpResponse(content=image, mimetype=mimetype)

    def get_full_extent_image(self, config):
        if CACHE_FULL_EXTENT:
            cache = get_cache(FULL_EXTENT_CACHE)
            cache_wait_start = time.time()

            while time.time() - cache_wait_start > FULL_EXTENT_CACHE_TIMEOUT:
                image = cache.get(FULL_EXTENT_CACHE_KEY.format(hash=config.hash))
                if image:
                    return self._cache_to_image(image)  # The full extent has already been rendered
                elif cache.get(FULL_EXTENT_PENDING_KEY.format(hash=config.hash)):
                    time.sleep(0.1)  # The full extent render is pending; wait and try again
                    continue
                else:
                    break  # No full extent and no render pending

            cache.set(FULL_EXTENT_PENDING_KEY.format(hash=config.hash), True)

        try:
            v = self._open_dataset(self.service).variables[config.variable.name]
            variable = config.variable
            service = variable.service
            time_enabled = service.supports_time and variable.supports_time
            data = v[:]
            row_major_order = (
                v.dimensions.index(service.y_dimension) < v.dimensions.index(service.x_dimension)
            )

            valid_dimensions = (service.y_dimension, service.x_dimension)
            if time_enabled:
                valid_dimensions = (service.time_dimension,) + valid_dimensions

            dimensions = list(v.dimensions)
            for dimension in v.dimensions:
                if not dimension in valid_dimensions:
                    data = numpy.rollaxis(data, dimensions.index(dimension))[0]
                    dimensions.remove(dimension)

            transpose_args = [dimensions.index(service.y_dimension), dimensions.index(service.x_dimension)]
            if time_enabled:
                transpose_args.append(dimensions.index(service.time_dimension))
                data = data.transpose(*transpose_args)[:, :, config.time_index]
            else:
                data = data.transpose(*transpose_args)

            if hasattr(data, 'fill_value'):
                config.renderer.fill_value = data.fill_value

            image = config.renderer.render_image(data, row_major_order=row_major_order)

            #  If y values are increasing, the rendered image needs to be flipped vertically
            y_variable = self._open_dataset(self.service).variables.get(service.y_dimension)
            if y_variable and y_variable[1] > y_variable[0]:
                image = image.transpose(Image.FLIP_TOP_BOTTOM)

            if CACHE_FULL_EXTENT:
                cache.set(FULL_EXTENT_CACHE_KEY.format(hash=config.hash), self._image_to_cache(image))

            return image
        finally:
            self._close_dataset()
            if CACHE_FULL_EXTENT:
                cache.delete(FULL_EXTENT_PENDING_KEY.format(hash=config))

    def handle_request(self, request, **kwargs):
        try:
            configurations = self.get_render_configurations(request, **kwargs)
            if not configurations:
                return HttpResponse()

            full_extent_image = None
            extent = None
            size = None
            background_color = None
            image_format = None

            for config in reversed(self.get_render_configurations(request, **kwargs)):
                image = self.get_full_extent_image(config)

                if full_extent_image:
                    full_extent_image.paste(image, None)
                else:
                    full_extent_image = image
                    extent = config.extent
                    size = config.size
                    background_color = config.background_color
                    image_format = config.image_format

            final_image = Image.new('RGBA', size, background_color)
            full_extent_image = GeoImage(full_extent_image, configurations[0].variable)
            final_image.paste(full_extent_image.warp(extent, size), None)
            final_image, mimetype = self.format_image(final_image, image_format)

            return self.create_response(request, final_image, mimetype)

        except ConfigurationError:
            return HttpResponseBadRequest()
        finally:
            self._close_dataset()

    def dispatch(self, request, *args, **kwargs):
        self.service = get_object_or_404(Service, name=self.get_service_name(request, *args, **kwargs))
        return super(GetImageViewBase, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self.handle_request(request, **request.GET.dict())

    def post(self, request, *args, **kwargs):
        return self.handle_request(request, **request.POST.dict())