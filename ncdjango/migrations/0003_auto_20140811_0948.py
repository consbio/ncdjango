# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('ncdjango', '0002_auto_20140722_1458'),
    ]

    operations = [
        migrations.CreateModel(
            name='TemporaryFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_created=True)),
                ('uuid', models.CharField(default=uuid.uuid4, max_length=36)),
                ('filename', models.CharField(max_length=100)),
                ('filesize', models.BigIntegerField()),
                ('file', models.FileField(upload_to='/tmp', max_length=1024)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='service',
            name='name',
            field=models.CharField(unique=True, db_index=True, max_length=256),
        ),
        migrations.AlterField(
            model_name='variable',
            name='name',
            field=models.CharField(db_index=True, max_length=256),
        ),
    ]
