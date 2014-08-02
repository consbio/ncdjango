import json
from clover.render.renderers import RasterRenderer
from django import forms
from django.core.exceptions import ValidationError
import six
from ncdjango.interfaces.arcgis_extended.utils import get_renderer_from_definition


class StyleField(forms.Field):
    """Custom renderer configurations"""

    def to_python(self, value):
        if not value or isinstance(value, RasterRenderer):
            return value

        try:
            style_configurations = json.loads(value)
            return {int(k): get_renderer_from_definition(v) for k, v in six.iteritems(style_configurations)}
        except ValueError as e:
            raise ValidationError("Invalid renderer configuration: {}".format(e))

    def prepare_value(self, value):
        raise NotImplementedError