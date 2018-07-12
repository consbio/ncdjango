def extent_to_envelope(extent, wkid):
    extent = {k: getattr(extent, k) for k in ('xmin', 'ymin', 'xmax', 'ymax')}
    extent['spatialReference'] = {'wkid': wkid}
    return extent
