from django import forms
from django.core.exceptions import ValidationError
import six
from ncdjango.interfaces.arcgis.form_fields import BoundingBoxField, SrField, TimeField, DynamicLayersField


class GetImageForm(forms.Form):
    """Form used to handle export requests according to: http://resources.arcgis.com/en/help/rest/apiref/export.html"""

    FIELD_MAP = {
        'f': 'response_format',
        'imagesr': 'image_projection',
        'bboxsr': 'bbox_projection',
        'format': 'image_format',
        'layerdefs': 'layer_definitions',
        'layertimeoptions': 'layer_time_options',
        'dynamiclayers': 'dynamic_layers',
        'gdbversion': 'gdb_version'
    }

    RESPONSE_FORMAT_CHOICES = (
        ('html', 'HTML'),
        ('json', 'JSON'),
        ('image', 'Image'),
        ('kmz', 'KMZ')
    )
    
    IMAGE_FORMAT_CHOICES = (
        ('png', 'PNG'),
        ('png8', 'PNG8'),
        ('png24', 'PNG24'),
        ('jpg', 'JPEG'),
        ('pdf', 'PDF'),
        ('bmp', 'BMP'),
        ('gif', "GIF"),
        ('svg', "SVG"),
        ('png32', "PNG32")
    )

    response_format = forms.ChoiceField(choices=RESPONSE_FORMAT_CHOICES)
    bbox = BoundingBoxField()
    size = forms.CharField()
    dpi = forms.CharField()  # Unused
    image_projection = SrField()
    bbox_projection = SrField()
    image_format = forms.CharField()
    layer_definitions = forms.CharField(required=False)  # Unused
    layers = forms.CharField(required=False)
    transparent = forms.BooleanField()
    time = TimeField(required=False)
    layer_time_options = forms.CharField(required=False)
    dynamic_layers = DynamicLayersField(required=False)
    gdb_version = forms.CharField(required=False)  # Unused
    map_scale = forms.FloatField(required=False)  # Unused

    def clean_size(self):
        data = self.cleaned_data['size']
        try:
            width, height = [int(x) for x in data.split(',')]
        except ValueError:
            raise ValidationError('Invalid size parameter')

        return width, height

    def clean(self):
        cleaned_data = super(GetImageForm, self).clean()
        bbox = cleaned_data.get('bbox')
        bbox_projection = cleaned_data.get('bbox_projection')

        if bbox and bbox_projection:
            bbox.projection = bbox_projection

        return cleaned_data

    @classmethod
    def map_parameters(cls, params):
        """Maps parameters to form field names"""

        d = {}
        for k, v in six.iteritems(params):
            d[cls.FIELD_MAP.get(k, k)] = v
        return d