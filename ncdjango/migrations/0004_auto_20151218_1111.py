# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ncdjango', '0003_auto_20151215_1801'),
    ]

    operations = [
        migrations.RenameField(
            model_name='processingjob',
            old_name='user_host',
            new_name='user_ip',
        ),
        migrations.AlterField(
            model_name='service',
            name='data_path',
            field=models.FilePathField(recursive=True, max_length=1024, path='C:/Users/nik.molnar/Documents/projects/seedsource/materials/ncdjango/services/'),
        ),
        migrations.AlterField(
            model_name='temporaryfile',
            name='file',
            field=models.FileField(max_length=1024, upload_to='C:/Users/nik.molnar/Documents/projects/seedsource/materials/ncdjango/tmp/'),
        ),
    ]
