# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ncdjango', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='variable',
            name='calendar',
        ),
        migrations.RemoveField(
            model_name='variable',
            name='time_interval',
        ),
        migrations.RemoveField(
            model_name='variable',
            name='time_interval_units',
        ),
        migrations.AddField(
            model_name='service',
            name='calendar',
            field=models.CharField(null=True, max_length=10, choices=[('standard', 'Standard Gregorian'), ('noleap', 'Standard, no leap years'), ('360', '360-day years')]),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='service',
            name='time_interval',
            field=models.PositiveIntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='service',
            name='time_interval_units',
            field=models.CharField(null=True, max_length=15, choices=[('milliseconds', 'Milliseconds'), ('seconds', 'Seconds'), ('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months'), ('years', 'Years'), ('decades', 'Decades'), ('centuries', 'Centuries')]),
            preserve_default=True,
        ),
    ]
