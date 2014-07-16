import json
from clover.geometry.bbox import BBox
from clover.render.renderers import RasterRenderer
from clover.render.renderers.classified import ClassifiedRenderer
from clover.render.renderers.stretched import StretchedRenderer
from clover.render.renderers.unique import UniqueValuesRenderer
from clover.utilities.color import Color
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.six import with_metaclass
from django.utils.translation import ugettext_lazy as _
import pyproj


class BoundingBoxField(with_metaclass(models.SubfieldBase, models.TextField)):
    description = _('Bounding box with associated projection information')

    def to_python(self, value):
        if not value or isinstance(value, BBox):
            return value

        try:
            data = json.loads(value)
            projection = pyproj.Proj(data.get('proj4')) if 'proj4' in data else None

            return BBox(
                (data['xmin'], data['ymin'], data['xmax'], data['ymax']), projection=projection
            )
        except (ValueError, KeyError):
            raise ValidationError("")

    def get_prep_value(self, value):
        if not value:
            return value

        return json.dumps({
            'xmin': value.xmin,
            'ymin': value.ymin,
            'xmax': value.xmax,
            'ymax': value.ymax,
            'proj4': value.projection
        })


class RasterRendererField(with_metaclass(models.SubfieldBase, models.TextField)):
    description = _('A class to generate images from raster data')

    def to_python(self, value):
        if not value or isinstance(value, RasterRenderer):
            return value

        try:
            data = json.loads(value)
            name = data['name']
            kwargs = {
                'colormap': [(c[0], Color(*c[1])) for c in data['colormap']],
                'fill_value': data.get('fill_value'),
                'background_color': data.get('background_color')
            }

            if name == "stretched":
                cls = StretchedRenderer
                kwargs.update({
                    'method': data.get('method', 'linear'),
                    'colorspace': data.get('colorspace', 'hsv')
                })
            elif name == "classified":
                cls = ClassifiedRenderer
            elif name == "unique":
                cls = UniqueValuesRenderer
                kwargs.update({
                    'labels': data['labels']
                })
        except (ValueError, KeyError):
            raise ValidationError("")

        return cls(**kwargs)

    def get_prep_value(self, value):
        if not value:
            return value

        params = {}

        if isinstance(value, StretchedRenderer):
            name = "stretched"
            params = {
                'method': value.method,
                'colorspace': value.colorspace
            }
        elif isinstance(value, ClassifiedRenderer):
            name = "classified"
        elif isinstance(value, UniqueValuesRenderer):
            name = "unique"
            params = {
                'labels': value.labels
            }
        else:
            raise ValidationError("")

        params.update({
            'colormap': [(c[0], c[1].to_tuple()) for c in value.colormap],
            'fill_value': value.background_color,
            'background_color': value.background_color.to_tuple(),
        })

        return json.dumps({'name': name, 'params': params})