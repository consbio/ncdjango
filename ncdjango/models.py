from django.conf import settings
from django.db import models
from ncdjango.fields import BoundingBoxField, RasterRendererField

SERVICE_DATA_ROOT = getattr(settings, 'NC_SERVICE_DATA_ROOT', '/var/ncdjango/services/')


class Folder(models.Model):
    name = models.CharField(max_length=100, db_index=True)


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
    folder = models.ForeignKey(Folder)
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