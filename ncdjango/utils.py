from bisect import bisect_left
from functools import wraps, partial
import os
import re
import osgeo
import pyproj
from shapely.ops import transform

EPSG_RE = re.compile(r'\+init=epsg:([0-9]+)')
PYPROJ_EPSG_FILE_RE = re.compile(r'<([0-9]+)([^<]+)<')


def auto_memoize(func):
    """
    Based on django.util.functional.memoize. Automatically memoizes instace methods for the lifespan of an object.
    Only works with methods taking non-keword arguments. Note that the args to the function must be usable as
    dictionary keys. Also, the first argument MUST be self. This decorator will not work for functions or class
    methods, only object methods.
    """

    @wraps(func)
    def wrapper(*args):
        inst = args[0]
        inst._memoized_values = getattr(inst, '_memoized_values', {})
        key = (func, args[1:])
        if key not in inst._memoized_values:
            inst._memoized_values[key] = func(*args)
        return inst._memoized_values[key]
    return wrapper


def best_fit(li, value):
    """For a sorted list li, returns the closest item to value"""

    index = min(bisect_left(li, value), len(li) - 1)

    if index in (0, len(li)):
        return index

    if li[index] - value < value - li[index-1]:
        return index
    else:
        return index-1


def proj4_to_epsg(projection):
    """Attempts to convert a PROJ4 projection object to an EPSG code and returns None if conversion fails"""

    def make_definition(value):
        return {x.strip().lower() for x in value.split('+') if x}

    # Use the EPSG in the definition if available
    match = EPSG_RE.search(projection.srs)
    if match:
        return int(match.group(1))

    # Otherwise, try to look up the EPSG from the pyproj data file
    pyproj_data_dir = os.path.join(os.path.dirname(pyproj.__file__), 'data')
    pyproj_epsg_file = os.path.join(pyproj_data_dir, 'epsg')
    if os.path.exists(pyproj_epsg_file):
        definition = make_definition(projection.srs)
        f = open(pyproj_epsg_file, 'r')
        for line in f.readlines():
            match = PYPROJ_EPSG_FILE_RE.search(line)
            if match:
                file_definition = make_definition(match.group(2))
                if definition == file_definition:
                    return int(match.group(1))
    return None


def wkt_to_proj4(wkt):
    """Converts a well-known text string to a pyproj.Proj object"""

    srs = osgeo.osr.SpatialReference()
    srs.ImportFromWkt(wkt)

    return pyproj.Proj(str(srs.ExportToProj4()))


def proj4_to_wkt(projection):
    """Converts a pyproj.Proj object to a well-known text string"""

    srs = osgeo.osr.SpatialReference()
    srs.ImportFromProj4(projection.srs)

    return srs.ExportToWkt()


def project_geometry(geometry, source, target):
    """Projects a shapely geometry object from the source to the target projection."""

    project = partial(
        pyproj.transform,
        source,
        target
    )

    return transform(project, geometry)