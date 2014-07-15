from PIL import Image
from clover.utilities.color import Color
from django.conf import settings
from ncdjango.config import RenderConfiguration
from ncdjango.exceptions import ConfigurationError
from ncdjango.interfaces.arcgis.forms import GetImageForm
from ncdjango.views import GetImageViewBase

ALLOW_BEST_FIT_TIME_INDEX = getattr(settings, 'NC_ALLOW_BEST_FIT_TIME_INDEX', True)

TRANSPARENT_BACKGROUND_COLOR = Color(255, 255, 255, 0)
DEFAULT_BACKGROUND_COLOR = Color(255, 255, 255)


class GetImageView(GetImageViewBase):
    def __init__(self, *args, **kwargs):
        self.service = None
        super(GetImageView, self).__init__(*args, **kwargs)

    def _get_form_defaults(self):
        """Returns default values for the get image form"""

        return {
            'response_format': 'html',
            'bbox': self.service.full_extent,
            'size': (400, 400),
            'dpi': 200,
            'image_projection': self.service.projection,
            'bbox_projection': self.service.projection,
            'image_format': 'png',
            'transparent': True
        }

    def get_service_name(self, request, *args, **kwargs):
        return kwargs['service_name']

    def format_image(self, image, image_format):
        """Returns an image in the request format"""

        if image_format in ('png8', 'png24'):
            alpha = image.split()[-1]
            image = image.convert('RGB')
            if image_format == 'png8':
                image.convert('P', palette=Image.ADAPTIVE, colors=255)
            image.paste(255, Image.eval(alpha, lambda x: 255 if x <= 128 else 0))
            image_format = 'png'
        elif image_format == 'png32':
            image_format = 'png'

        return super(GetImageView, self).format_image(image, image_format)

    def get_render_configurations(self, request, **kwargs):
        """Render image interface"""

        form_params = self._get_form_defaults().update(GetImageForm.map_parameters(kwargs))
        form = GetImageForm(form_params)
        if form.is_valid():
            data = form.cleaned_data
        else:
            raise ConfigurationError

        variable_set = self.service.variable_set.order_by('index')
        config_params = {
            'bbox': data['bbox'],
            'size': data['size'],
            'image_format': data['image_format'],
            'background_color': TRANSPARENT_BACKGROUND_COLOR if data.get('transparent') else DEFAULT_BACKGROUND_COLOR
        }

        if data.get('time'):
            time_value = data['time']
            # Only single time values are supported. For extents, just grab the first value
            if isinstance(data['time'], [tuple, list]):
                time_value = time_value[0]

        if data.get('dynamic_layers'):
            configurations = []  # TODO
        elif data.get('layers'):
            configurations = []  # TODO
        elif self.service.render_top_layer_only:

            configurations = [RenderConfiguration(variable_set[0], **config_params)]
        else:
            configurations = []  # TODO

        for config in configurations:
            config.set_time_index_from_datetime(time_value, best_fit=ALLOW_BEST_FIT_TIME_INDEX)
