from datetime import datetime
import json
from clover.geometry.bbox import BBox
from django import forms
from django.core.exceptions import ValidationError
import pyproj
from shapely.geometry import MultiPoint
from shapely.geometry.base import BaseGeometry
from shapely.geometry.multilinestring import MultiLineString
from shapely.geometry.point import Point
from shapely.geometry.polygon import LinearRing, Polygon
from ncdjango.interfaces.arcgis.utils import timestamp_to_date, date_to_timestamp
from ncdjango.interfaces.arcgis.wkid import wkid_to_proj
from ncdjango.utils import proj4_to_epsg


class BoundingBoxField(forms.Field):
    """Bounding box with associated projection information"""

    def to_python(self, value):
        if not value or isinstance(value, BBox):
            return value

        try:
            projection = None
            if 'xmin' in value:
                data = json.loads(value)
                values = [data[k] for k in ('xmin', 'ymin', 'xmax', 'ymax')]
                if 'spatialReference' in data:
                    projection = SrField().to_python(json.dumps(data.get('spatialReference')))
            else:
                values = [float(x.strip()) for x in value.split(',')]

            return BBox(values, projection=projection)
        except ValueError:
            raise ValidationError('Invalid bbox')

    def prepare_value(self, value):
        if not value:
            return value

        return value.as_list()


class GeometryField(forms.Field):
    """Esri geometry"""

    def to_python(self, value):
        """
        This assumes the value has been preprocessed into a dictionary of the form:
        {'type': <geometry_type>, 'geometry': <raw_geometry>}
        """

        if not value or isinstance(value, BaseGeometry):
            return value

        geometry_type = value['type']
        geometry = value['geometry']

        try:
            if geometry_type == 'esriGeometryPoint':
                if 'x' in geometry:
                    data = json.loads(geometry)
                    x, y = data['x'], data['y']
                else:
                    x, y = [float(val) for val in geometry.split(',')]
                return Point(x, y)

            elif geometry_type == 'esriGeometryMultipoint':
                data = json.loads(geometry)
                return MultiPoint([(p['0'], p['1']) for p in data['points']])

            elif geometry_type == 'esriGeometryPolyline':
                data = json.loads(geometry)
                return MultiLineString([((l[0][0], l[0][1]), (l[1][0], l[1][1])) for l in data['paths']])

            elif geometry_type == 'esriGeometryPolygon':
                data = json.loads(geometry)
                rings = [LinearRing([(p[0], p[1]) for p in r]) for r in data['rings']]
                return Polygon([r for r in rings if not r.is_ccw], interiors=[r for r in rings if r.is_ccw])

            elif geometry_type == 'esriGeometryEnvelope':
                if 'xmin' in geometry:
                    data = json.loads(geometry)
                    xmin, ymin, xmax, ymax = [data[k] for k in ('xmin', 'ymin', 'xmax', 'ymax')]
                else:
                    xmin, ymin, xmax, ymax = [float(val) for val in geometry.split(',')]
                return MultiPoint([(xmin, ymin), (xmax, ymax)]).envelope

            else:
                raise ValueError
        except ValueError:
            raise ValidationError('Invalid geometry')

    def prepare_value(self, value):
        raise NotImplementedError


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
                return pyproj.Proj('+init=epsg:{}'.format(wkid))
            elif wkid in wkid_to_proj:
                return pyproj.Proj(str(wkid_to_proj[wkid]))
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
        if not value or isinstance(value, (datetime, tuple, list)):
            return value

        try:
            if ',' in value:
                return tuple([timestamp_to_date(int(x)) for x in value.split(',')])
            else:
                return datetime(int(value))
        except ValueError:
            return None

    def prepare_value(self, value):
        if not value:
            return value

        if isinstance(value, (tuple, list)):
            return ",".join([str(date_to_timestamp(x)) for x in value])
        else:
            return str(date_to_timestamp(value))


class DynamicLayersField(forms.Field):
    """Dynamic layers options"""

    def to_python(self, value):
        if not value or isinstance(value, (dict, list)):
            return value

        try:
            return json.loads(value)
        except ValueError:
            raise ValidationError('Invalid dynamic layers parameter')

    def prepare_value(self, value):
        if not value:
            return value

        return json.dumps(value)