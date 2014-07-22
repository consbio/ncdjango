from datetime import datetime, timedelta
import json
from clover.geometry.bbox import BBox
from django import forms
from django.core.exceptions import ValidationError
import pyproj
from ncdjango.interfaces.arcgis.utils import timestamp_to_date, date_to_timestamp
from ncdjango.interfaces.arcgis.wkid import wkid_to_proj
from ncdjango.utils import proj4_to_epsg


class BoundingBoxField(forms.Field):
    """Bounding box with associated projection information"""

    def to_python(self, value):
        if not value or isinstance(value, BBox):
            return value

        try:
            values = [float(x.strip()) for x in value.split(',')]
            return BBox(values)
        except ValueError:
            raise ValidationError('Invalid bbox')

    def prepare_value(self, value):
        if not value:
            return value

        return value.as_list()


class SrField(forms.Field):
    """Spatial reference field"""

    def to_python(self, value):
        if not value or isinstance(value, pyproj.Proj):
            return value

        try:
            obj = json.loads(value)

            if isinstance(obj, int):
                wkid = obj
            elif isinstance(obj, dict) and obj.get('wkid'):
                wkid = obj['wkid']
            else:
                raise ValidationError('SR must have a wkid parameter.')

            # Well-known ids below 32767 have a corresponding EPSG
            if wkid < 32767:
                return pyproj.Proj("+init=epsg:{}".format(wkid))
            elif wkid in wkid_to_proj:
                return pyproj.Proj(wkid_to_proj[wkid])
            else:
                raise RuntimeError
        except ValueError:
            raise ValidationError('Invalid SR')
        except RuntimeError:
            raise ValidationError('Projection not supported')

    def prepare_value(self, value):
        if not value or not isinstance(value, pyproj.Proj):
            return value

        epsg = proj4_to_epsg(value)
        if epsg:
            return str(epsg)
        else:
            raise ValidationError('Could not convert projection to EPSG/WKID')


class TimeField(forms.Field):
    """Single timestamp or extent"""

    def to_python(self, value):
        if not value or isinstance(value, [datetime, tuple, list]):
            return value

        try:
            if ',' in value:
                return tuple([timestamp_to_date(int(x)) for x in value.split(',')])
            else:
                return datetime(int(value))
        except ValueError:
            raise ValidationError('Invalid time value(s)')

    def prepare_value(self, value):
        if not value:
            return value

        if isinstance(value, [tuple, list]):
            return ",".join([str(date_to_timestamp(x)) for x in value])
        else:
            return str(date_to_timestamp(value))


class DynamicLayersField(forms.Field):
    """Dynamic layers options"""

    def to_python(self, value):
        if not value or isinstance(value, [dict, list]):
            return value

        try:
            return json.loads(value)
        except ValueError:
            raise ValidationError('Invalid dynamic layers parameter')

    def prepare_value(self, value):
        if not value:
            return value

        return json.dumps(value)