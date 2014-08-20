# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ncdjango', '0003_auto_20140811_0948'),
    ]

    operations = [
        migrations.AddField(
            model_name='variable',
            name='projection',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='temporaryfile',
            name='date',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='temporaryfile',
            name='file',
            field=models.FileField(max_length=1024, upload_to='C:/ncdjango/temp/'),
        ),
    ]
