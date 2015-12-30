# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ncdjango', '0002_auto_20141001_1050'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcessingJob',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.CharField(default=uuid.uuid4, max_length=36, db_index=True)),
                ('job', models.CharField(max_length=100)),
                ('user_ip', models.CharField(max_length=32)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('celery_id', models.CharField(max_length=100)),
                ('inputs', models.TextField(default='{}')),
                ('outputs', models.TextField(default='{}')),
                ('user', models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.SET_NULL)),
            ],
        ),
        migrations.CreateModel(
            name='ProcessingResultService',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_temporary', models.BooleanField(default=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('job', models.ForeignKey(to='ncdjango.ProcessingJob')),
            ],
        ),
        migrations.AlterField(
            model_name='service',
            name='data_path',
            field=models.FilePathField(path='C:/Users/nik.molnar/Documents/projects/seedsource/materials/ncdjango/services/', max_length=1024, recursive=True),
        ),
        migrations.AlterField(
            model_name='temporaryfile',
            name='file',
            field=models.FileField(upload_to='C:/Users/nik.molnar/Documents/projects/seedsource/materials/ncdjango/tmp/', max_length=1024),
        ),
        migrations.AlterUniqueTogether(
            name='variable',
            unique_together=set([('variable', 'service')]),
        ),
        migrations.AddField(
            model_name='processingresultservice',
            name='service',
            field=models.ForeignKey(to='ncdjango.Service'),
        ),
    ]
