import json
from PIL import Image
from clover.render.renderers.classified import ClassifiedRenderer
from clover.render.renderers.legend import LegendElement
from clover.render.renderers.stretched import StretchedRenderer
from clover.utilities.color import Color
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
import pyproj
import six
from ncdjango.config import RenderConfiguration, IdentifyConfiguration, LegendConfiguration, ImageConfiguration
from ncdjango.exceptions import ConfigurationError
from ncdjango.interfaces.arcgis.forms import GetImageForm, IdentifyForm
from ncdjango.interfaces.arcgis.utils import date_to_timestamp, extent_to_envelope
from ncdjango.models import Service, Variable
from ncdjango.utils import proj4_to_epsg
from ncdjango.views import GetImageViewBase, IdentifyViewBase, LegendViewBase, FORCE_WEBP

ALLOW_BEST_FIT_TIME_INDEX = getattr(settings, 'NC_ALLOW_BEST_FIT_TIME_INDEX', True)

TRANSPARENT_BACKGROUND_COLOR = Color(255, 255, 255, 0)
DEFAULT_BACKGROUND_COLOR = Color(255, 255, 255)
SUPPORTED_IMAGE_FORMATS = ('PNG', 'PNG8', 'PNG24', 'PNG32', 'JPEG', 'GIF', 'BMP')

TIME_UNITS_MAP = {
    'milliseconds': 'esriTimeUnitsMilliseconds',
    'seconds': 'esriTimeUnitsSeconds',
    'minutes': 'esriTimeUnitsMinutes',
    'hours': 'esriTimeUnitsHours',
    'days': 'esriTimeUnitsDays',
    'weeks': 'esriTimeUnitsWeeks',
    'months': 'esriTimeUnitsMonths',
    'years': 'esriTimeUnitsYears',
    'decades': 'esriTimeUnitsDecades',
    'centuries': 'esriTimeUnitsCenturies'
}


class MapServiceListView(ListView):
    model = Service

    def render_to_response(self, context, **response_kwargs):
        data = {
            'currentVersion': '10.1',
            'folders': [f for f, _ in [s.name.rsplit('/', 1) for s in self.object_list.all() if '/' in s.name]],
            'services': [{'name': s.name, 'type': 'MapServer'} for s in self.object_list.all()]
        }

        return HttpResponse(json.dumps(data), content_type='application/json')


class MapServiceDetailView(DetailView):
    model = Service
    slug_field = 'name'
    slug_url_kwarg = 'service_name'

    def render_to_response(self, context, **response_kwargs):
        epsg = proj4_to_epsg(pyproj.Proj(str(self.object.projection)))
        if epsg:
            full_extent = self.object.full_extent
            initial_extent = self.object.initial_extent
        else:
            epsg = 102100
            projection = pyproj.Proj('+units=m +init=epsg:3857')
            full_extent = self.object.full_extent.project(projection)
            initial_extent = self.object.initial_extent.project(projection)

        data = {
            'currentVersion': '10.1',
            'serviceDescription': self.object.description,
            'mapName': self.object.name,
            'description': self.object.description,
            'copyrightText': '',
            'supportsDynamicLayers': True,
            'layers': [
                {
                    'id': v.index,
                    'name': v.name,
                    'defaultVisibility': True,
                    'parentLayerId': -1,
                    'subLayerIds': None,
                    'minScale': 0,
                    'maxScale': 0
                } for v in self.object.variable_set.all()
            ],
            'spatialReference': {'wkid': epsg},
            'singleFusedMapCache': False,
            'initialExtent': extent_to_envelope(initial_extent, epsg),
            'fullExtent': extent_to_envelope(full_extent, epsg),
            'supportedImageFormatTypes': ','.join(SUPPORTED_IMAGE_FORMATS),
            'capabilities': 'Map,Query',
            'supportedQueryFormat': 'JSON'
        }

        if self.object.supports_time:
            data['timeInfo'] = {
                'timeExtent': [date_to_timestamp(self.object.time_start), date_to_timestamp(self.object.time_end)],
                'timeRelation': 'esriTimeRelationOverlaps',
                'defaultTimeInterval': self.object.time_interval,
                'defaultTimeIntervalUnits': TIME_UNITS_MAP.get(self.object.time_interval_units),
                'hasLiveData': False
            }

        return HttpResponse(json.dumps(data), content_type='application/json')


class LayerListView(ListView):
    model = Variable

    def get_queryset(self):
        queryset = super(LayerListView, self).get_queryset()
        return queryset.filter(service__name=self.kwargs.get('service_name'))

    def render_to_response(self, context, **response_kwargs):
        data = {
            'layers': [LayerDetailView.get_layer_data(v) for v in self.object_list.all()]
        }

        return HttpResponse(json.dumps(data), content_type="application/json")


class LayerDetailView(DetailView):
    model = Variable

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        service_name = self.kwargs.get('service_name')
        layer_index = self.kwargs.get('layer_index')

        return get_object_or_404(queryset, service__name=service_name, index=layer_index)

    def render_to_response(self, context, **response_kwargs):
        data = {'currentVersion': '10.1'}
        data.update(self.get_layer_data(self.object))
        return HttpResponse(json.dumps(data), content_type='application/json')

    @staticmethod
    def get_layer_data(variable):
        epsg = proj4_to_epsg(variable.full_extent.projection)
        if epsg:
            full_extent = variable.full_extent
        else:
            epsg = 102100
            projection = pyproj.Proj('+units=m +init=epsg:3857')
            full_extent = variable.full_extent.project(projection)

        data = {
            'id': variable.index,
            'name': variable.name,
            'type': 'Raster Layer',
            'description': variable.description,
            'geometryType': None,
            'hasZ': False,
            'hasM': False,
            'copyrightText': None,
            'parentLayer': None,
            'subLayers': None,
            'minScale': 0,
            'maxScale': 0,
            'defaultVisibility': True,
            'extent': extent_to_envelope(full_extent, epsg),
            'displayField': variable.variable,
            'maxRecordCount': 1000,
            'supportsStatistics': False,
            'supportsAdvancedQueries': False,
            'capabilities': 'Map,Query',
            'supportedQueryFormats': 'JSON',
            'isDataVersioned': False
        }

        if variable.supports_time:
            data['timeInfo'] = {
                'timeExtent': [date_to_timestamp(variable.time_start), date_to_timestamp(variable.time_end)],
                'timeInterval': variable.service.time_interval,
                'timeIntervalUnits': TIME_UNITS_MAP.get(variable.service.time_interval_units),
                'exportOptions': {
                    'useTime': True,
                    'timeDataCumulative': False
                },
                'hasLiveData': False
            }

        return data


class ArcGISMapServerMixin(object):
    def __init__(self, *args, **kwargs):
        self.form_data = {}

        return super(ArcGISMapServerMixin, self).__init__(*args, **kwargs)

    def process_form_data(self, defaults, data):
        form_params = defaults
        form_params.update(self.form_class.map_parameters(data))
        form = self.form_class(form_params)
        if form.is_valid():
            self.form_data = form.cleaned_data
            return self.form_data
        else:
            raise ConfigurationError

    def get_variable_set(self, variable_set, data):
        """Filters the given variable set based on request parameters"""

        if data.get('dynamic_layers'):
            variable_set = []  # TODO
        elif data.get('layers'):
            op, layer_ids = data['layers'].split(':', 1)
            op = op.lower()
            layer_ids = [int(x) for x in layer_ids.split(',')]

            if op in ('show', 'include'):
                variable_set = [x for x in variable_set if x.index in layer_ids]
            elif op in ('hide', 'exclude'):
                variable_set = [x for x in variable_set if x.index not in layer_ids]
        elif self.service.render_top_layer_only:
            variable_set = [variable_set[0]]

        return variable_set

    def apply_time_to_configurations(self, configurations, data):
        """Applies the correct time index to configurations"""

        time_value = None
        if data.get('time'):
            time_value = data['time']

            # Only single time values are supported. For extents, just grab the first value
            if isinstance(data['time'], (tuple, list)):
                time_value = time_value[0]

        if time_value:
            for config in configurations:
                config.set_time_index_from_datetime(time_value, best_fit=ALLOW_BEST_FIT_TIME_INDEX)

        return configurations


class GetImageView(ArcGISMapServerMixin, GetImageViewBase):
    form_class = GetImageForm

    def _get_form_defaults(self):
        """Returns default values for the get image form"""

        return {
            'response_format': 'html',
            'bbox': self.service.full_extent,
            'size': '400,400',
            'dpi': 200,
            'image_projection': pyproj.Proj(str(self.service.projection)),
            'bbox_projection': pyproj.Proj(str(self.service.projection)),
            'image_format': 'png',
            'transparent': True
        }

    def get_service_name(self, request, *args, **kwargs):
        return kwargs['service_name']

    def format_image(self, image, image_format, **kwargs):
        """Returns an image in the request format"""

        image_format = image_format.lower()
        accept = self.request.META['HTTP_ACCEPT'].split(',')

        if FORCE_WEBP and 'image/webp' in accept:
            image_format = 'webp'
        elif image_format == 'png8':
            alpha = image.split()[-1]
            image = image.convert('RGB')
            image = image.convert('P', palette=Image.ADAPTIVE, colors=255)
            image.paste(255, Image.eval(alpha, lambda x: 255 if x <= 128 else 0))
            image_format = 'png'
            kwargs['transparency'] = 255
        elif image_format in ('png32', 'png24'):
            image_format = 'png'

        return super(GetImageView, self).format_image(image, image_format, **kwargs)

    def get_render_configurations(self, request, **kwargs):
        """Render image interface"""

        data = self.process_form_data(self._get_form_defaults(), kwargs)
        variable_set = self.get_variable_set(self.service.variable_set.order_by('index'), data)

        base_config = ImageConfiguration(
            extent=data['bbox'],
            size=data['size'],
            image_format=data['image_format'],
            background_color=TRANSPARENT_BACKGROUND_COLOR if data.get('transparent') else DEFAULT_BACKGROUND_COLOR
        )

        return base_config, self.apply_time_to_configurations([RenderConfiguration(v) for v in variable_set], data)


class IdentifyView(ArcGISMapServerMixin, IdentifyViewBase):
    form_class = IdentifyForm

    def _get_form_defaults(self):
        """Returns default values for the identify form"""

        return {
            'response_format': 'html',
            'geometry_type': 'esriGeometryPoint',
            'projection': pyproj.Proj(str(self.service.projection)),
            'return_geometry': True,
            'maximum_allowable_offset': 2,
            'geometry_precision': 3,
            'return_z': False,
            'return_m': False
        }

    def serialize_data(self, data):
        output = {
            'results': [
                {
                    'layerId': variable.index,
                    'layerName': variable.name,
                    'value': value,
                    'displayFieldName': variable.name,
                    'attributes': {
                        'Pixel value': value
                    }
                }
                for variable, value in six.iteritems(data)
            ]
        }

        return json.dumps(output), 'application/json'

    def get_service_name(self, request, *args, **kwargs):
        return kwargs['service_name']

    def get_identify_configurations(self, request, **kwargs):
        data = self.process_form_data(self._get_form_defaults(), kwargs)
        variable_set = self.get_variable_set(self.service.variable_set.order_by('index'), data)

        config_params = {
            'geometry': data['geometry'],
            'projection': data['projection']
        }

        return self.apply_time_to_configurations(
            [IdentifyConfiguration(v, **config_params) for v in variable_set], data
        )


class LegendView(ArcGISMapServerMixin, LegendViewBase):
    def set_legend_sizes(self, configurations):
        for config in configurations:
            if isinstance(config.renderer, StretchedRenderer):
                config.size = (20, 60)
            elif isinstance(config.renderer, ClassifiedRenderer):
                config.size = (20, 20)
            else:
                config.size = (36, 20)
        return configurations

    def serialize_data(self, data):
        def get_legend_elements(elements):
            # Stretched legends need to be split into several elements
            if len(elements) == 1 and len(elements[0].labels) > 1:
                element = elements[0]
                labels = element.labels

                #Split into multiple images
                full_image = element.image
                top_image = Image.new('RGBA', (20, 20), color=(0, 0, 0, 0))
                top_image.paste(full_image.crop((0, 0, 20, 20)))
                middle_image = Image.new('RGBA', (20, 20), color=(0, 0, 0, 0))
                middle_image.paste(full_image.crop((0, 20, 20, 40)))
                bottom_image = Image.new('RGBA', (20, 20), color=(0, 0, 0, 0))
                bottom_image.paste(full_image.crop((0, 40, 20, 60)))

                elements = [
                    LegendElement(top_image, [1], [labels[-1]]),
                    LegendElement(middle_image, [.5], ['']),
                    LegendElement(bottom_image, [0], [labels[0]])
                ]

            return [
                {
                    'label': element.labels[0],
                    'url': None,  # TODO
                    'imageData': element.image_base64,
                    'contentType': 'image/png',
                    'height': element.image.size[1] if element.image else None,
                    'width': element.image.size[0] if element.image else None
                } for element in elements
            ]

        output = {
            'layers': [
                {
                    'layerId': variable.index,
                    'layerName': variable.name,
                    'layerType': 'Raster Layer',
                    'minScale': 0,
                    'maxScale': 0,
                    'legend': get_legend_elements(elements)
                }
                for variable, elements in six.iteritems(data)
            ]
        }

        return json.dumps(output), 'application/json'

    def get_service_name(self, request, *args, **kwargs):
        return kwargs['service_name']

    def get_legend_configurations(self, request, **kwargs):
        configurations = [LegendConfiguration(v) for v in self.service.variable_set.all().order_by('index')]
        return self.set_legend_sizes(configurations)
