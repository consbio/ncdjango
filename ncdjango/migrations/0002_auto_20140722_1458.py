# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ncdjango', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='variable',
            name='description',
            field=models.TextField(null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='service',
            name='data_path',
            field=models.FilePathField(verbose_name='C:/ncdjango/services/', recursive=True),
        ),
    ]
