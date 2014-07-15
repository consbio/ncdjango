from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from ncdjango.fields import BoundingBoxField, RasterRendererField
from ncdjango.utils import auto_memoize

SERVICE_DATA_ROOT = getattr(settings, 'NC_SERVICE_DATA_ROOT', '/var/ncdjango/services/')


class Service(models.Model):
    """Map service"""

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

    name = models.CharField(max_length=256, db_index=True)
    description = models.TextField(null=True)
    data_path = models.FilePathField(SERVICE_DATA_ROOT)
    projection = models.TextField()  # PROJ4 definition
    full_extent = BoundingBoxField()
    initial_extent = BoundingBoxField()
    x_dimension = models.CharField(max_length=256)
    y_dimension = models.CharField(max_length=256)
    supports_time = models.BooleanField(default=False)
    time_dimension = models.CharField(max_length=256, null=True)
    time_start = models.DateTimeField(null=True)
    time_end = models.DateTimeField(null=True)
    time_interval = models.PositiveIntegerField(null=True)
    time_interval_units = models.CharField(max_length=15, choices=TIME_UNITS_CHOICES, null=True)
    calendar = models.CharField(max_length=10, choices=CALENDAR_CHOICES, null=True)
    render_top_layer_only = models.BooleanField(default=True)

    @property
    @auto_memoize
    def time_steps(self):
        """Valid time steps for this service as a list of datetime objects."""

        if not self.supports_time:
            return []

        if self.calendar == 'standard':
            units = self.time_interval_units
            interval = self.time_interval
            steps = [self.time_start]

            if units in ('years', 'decades', 'centuries'):
                if units == 'years':
                    years = 1
                elif units == 'decades':
                    years = 10
                else:
                    years = 100

                next_value = lambda x: x.replace(year=x.year + years)
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
                elif units == 'months':
                    delta = timedelta(months=interval)
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

        return super(Service, self).save(*args, **kwargs)


class Variable(models.Model):
    """A variable/layer in a map service. Each service may have one or more variables."""

    service = models.ForeignKey(Service)
    index = models.PositiveIntegerField()
    variable = models.CharField(max_length=256)
    name = models.CharField(max_length=256)
    renderer = RasterRendererField()
    full_extent = BoundingBoxField()
    supports_time = models.BooleanField(default=False)
    time_start = models.DateTimeField(null=True)
    time_end = models.DateTimeField(null=True)
    time_steps = models.PositiveIntegerField(null=True)