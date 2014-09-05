# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid
import ncdjango.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256, db_index=True, unique=True)),
                ('description', models.TextField(null=True)),
                ('data_path', models.FilePathField(recursive=True, verbose_name='C:/ncdjango/services/')),
                ('projection', models.TextField()),
                ('full_extent', ncdjango.fields.BoundingBoxField()),
                ('initial_extent', ncdjango.fields.BoundingBoxField()),
                ('supports_time', models.BooleanField(default=False)),
                ('time_start', models.DateTimeField(null=True)),
                ('time_end', models.DateTimeField(null=True)),
                ('render_top_layer_only', models.BooleanField(default=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TemporaryFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.CharField(max_length=36, default=uuid.uuid4)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('filename', models.CharField(max_length=100)),
                ('filesize', models.BigIntegerField()),
                ('file', models.FileField(max_length=1024, upload_to='C:/ncdjango/temp/')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Variable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('index', models.PositiveIntegerField()),
                ('variable', models.CharField(max_length=256)),
                ('projection', models.TextField()),
                ('x_dimension', models.CharField(max_length=256)),
                ('y_dimension', models.CharField(max_length=256)),
                ('name', models.CharField(max_length=256, db_index=True)),
                ('description', models.TextField(null=True)),
                ('renderer', ncdjango.fields.RasterRendererField()),
                ('full_extent', ncdjango.fields.BoundingBoxField()),
                ('supports_time', models.BooleanField(default=False)),
                ('time_dimension', models.CharField(max_length=256, null=True)),
                ('time_start', models.DateTimeField(null=True)),
                ('time_end', models.DateTimeField(null=True)),
                ('time_steps', models.PositiveIntegerField(null=True)),
                ('time_interval', models.PositiveIntegerField(null=True)),
                ('time_interval_units', models.CharField(max_length=15, choices=[('milliseconds', 'Milliseconds'), ('seconds', 'Seconds'), ('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months'), ('years', 'Years'), ('decades', 'Decades'), ('centuries', 'Centuries')], null=True)),
                ('calendar', models.CharField(max_length=10, choices=[('standard', 'Standard Gregorian'), ('noleap', 'Standard, no leap years'), ('360', '360-day years')], null=True)),
                ('service', models.ForeignKey(to='ncdjango.Service')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
