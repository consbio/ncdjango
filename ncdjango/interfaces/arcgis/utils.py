from datetime import datetime, timedelta
from django.utils.timezone import utc


def date_to_timestamp(date_obj):
    return int((date_obj - datetime.utcfromtimestamp(0).replace(tzinfo=utc)).total_seconds() * 1000)


def timestamp_to_date(timestamp):
    return datetime.utcfromtimestamp(0).replace(tzinfo=utc) + timedelta(seconds=int(timestamp / 1000))


def extent_to_envelope(extent, wkid):
    extent = {k: getattr(extent, k) for k in ('xmin', 'ymin', 'xmax', 'ymax')}
    extent['spatialReference'] = {'wkid': wkid}
    return extent