# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ncdjango', '0003_auto_20151110_1906'),
    ]

    operations = [
        migrations.AddField(
            model_name='processingjob',
            name='job',
            field=models.CharField(max_length=100, default=''),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='service',
            name='data_path',
            field=models.FilePathField(path='/var/ncdjango/services/', max_length=1024, recursive=True),
        ),
        migrations.AlterUniqueTogether(
            name='variable',
            unique_together=set([('variable', 'service')]),
        ),
    ]
