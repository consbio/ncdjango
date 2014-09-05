from datetime import timedelta
import logging
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete
from ncdjango.fields import BoundingBoxField, RasterRendererField
from ncdjango.utils import auto_memoize

logger = logging.getLogger(__name__)

SERVICE_DATA_ROOT = getattr(settings, 'NC_SERVICE_DATA_ROOT', '/var/ncdjango/services/')
TEMPORARY_FILE_LOCATION = getattr(settings, 'NC_TEMPORARY_FILE_LOCATION', '/tmp')


class Service(models.Model):
    """Map service"""

    name = models.CharField(max_length=256, db_index=True, unique=True)
    description = models.TextField(null=True)
    data_path = models.FilePathField(SERVICE_DATA_ROOT, recursive=True)
    projection = models.TextField()  # PROJ4 definition
    full_extent = BoundingBoxField()
    initial_extent = BoundingBoxField()
    supports_time = models.BooleanField(default=False)
    time_start = models.DateTimeField(null=True)
    time_end = models.DateTimeField(null=True)
    render_top_layer_only = models.BooleanField(default=True)


class Variable(models.Model):
    """A variable/layer in a map service. Each service may have one or more variables."""

    CALENDAR_CHOICES = (
        ('standard', 'Standard Gregorian'),
        ('noleap', 'Standard, no leap years'),
        ('360', '360-day years')
    )

    TIME_UNITS_CHOICES = (
        ('milliseconds', 'Milliseconds'),
        ('seconds', 'Seconds'),
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years'),
        ('decades', 'Decades'),
        ('centuries', 'Centuries')
    )

    service = models.ForeignKey(Service)
    index = models.PositiveIntegerField()
    variable = models.CharField(max_length=256)
    projection = models.TextField()  # PROJ4 definition
    x_dimension = models.CharField(max_length=256)
    y_dimension = models.CharField(max_length=256)
    name = models.CharField(max_length=256, db_index=True)
    description = models.TextField(null=True)
    renderer = RasterRendererField()
    full_extent = BoundingBoxField()
    supports_time = models.BooleanField(default=False)
    time_dimension = models.CharField(max_length=256, null=True)
    time_start = models.DateTimeField(null=True)
    time_end = models.DateTimeField(null=True)
    time_steps = models.PositiveIntegerField(null=True)
    time_interval = models.PositiveIntegerField(null=True)
    time_interval_units = models.CharField(max_length=15, choices=TIME_UNITS_CHOICES, null=True)
    calendar = models.CharField(max_length=10, choices=CALENDAR_CHOICES, null=True)

    @property
    @auto_memoize
    def time_stops(self):
        """Valid time steps for this service as a list of datetime objects."""

        if not self.supports_time:
            return []

        if self.calendar == 'standard':
            units = self.time_interval_units
            interval = self.time_interval
            steps = [self.time_start]

            if units in ('years', 'decades', 'centuries'):
                if units == 'years':
                    years = interval
                elif units == 'decades':
                    years = 10 * interval
                else:
                    years = 100 * interval

                next_value = lambda x: x.replace(year=x.year + years)
            elif units == 'months':
                next_value = lambda x: x.replace(
                    year=x.year + (x.month+interval-1) // 12,
                    month=(x.month+interval) % 12 or 12
                )
            else:
                if units == 'milliseconds':
                    delta = timedelta(milliseconds=interval)
                elif units == 'seconds':
                    delta = timedelta(seconds=interval)
                elif units == 'minutes':
                    delta = timedelta(minutes=interval)
                elif units == 'hours':
                    delta = timedelta(hours=interval)
                elif units == 'days':
                    delta = timedelta(days=interval)
                elif units == 'weeks':
                    delta = timedelta(weeks=interval)
                else:
                    raise ValidationError(
                        "Service has an invalid time_interval_units: {}".format(self.time_interval_units)
                    )

                next_value = lambda x: x + delta

            while steps[-1] < self.time_end:
                value = next_value(steps[-1])
                if value > self.time_end:
                    break
                steps.append(value)
            return steps

        else:
            # TODO
            raise NotImplementedError

    def save(self, *args, **kwargs):
        has_required_time_fields = (
            self.time_dimension and self.time_start and self.time_end and self.time_interval and
            self.time_interval_units and self.calendar
        )
        if self.supports_time and not has_required_time_fields:
            raise ValidationError("Service supports time but is missing one or more time-related fields")

        return super(Variable, self).save(*args, **kwargs)


class TemporaryFile(models.Model):
    """A temporary file upload"""

    uuid = models.CharField(max_length=36, default=uuid.uuid4)
    date = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=100)
    filesize = models.BigIntegerField()
    file = models.FileField(upload_to=TEMPORARY_FILE_LOCATION, max_length=1024)

    @property
    def extension(self):
        if self.filename.find(".") != -1:
            return self.filename[self.filename.rfind(".")+1:]
        else:
            return ""


def temporary_file_deleted(sender, instance, **kwargs):
    if instance.file.name:
        try:
            instance.file.delete(save=False)
        except IOError:
            logger.exception("Error deleting temporary file: %s" % instance.file.name)
post_delete.connect(temporary_file_deleted, sender=TemporaryFile)