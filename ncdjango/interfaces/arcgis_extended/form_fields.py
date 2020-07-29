import json

from django import forms
from django.core.exceptions import ValidationError
from trefoil.render.renderers import RasterRenderer

from .utils import get_renderer_from_definition


class StyleField(forms.Field):
    """Custom renderer configurations"""

    def to_python(self, value):
        if not value or isinstance(value, RasterRenderer):
            return value

        try:
            return {int(k): get_renderer_from_definition(v) for k, v in json.loads(value).items()}
        except ValueError as e:
            raise ValidationError("Invalid renderer configuration: {}".format(e))

    def prepare_value(self, value):
        raise NotImplementedError
