# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ncdjango', '0002_auto_20141001_1050'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcessingJob',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('uuid', models.CharField(default=uuid.uuid4, max_length=32, db_index=True)),
                ('user_host', models.CharField(max_length=32)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_update', models.DateTimeField(auto_now=True)),
                ('celery_id', models.CharField(max_length=100)),
                ('status', models.CharField(max_length=15, choices=[('pending', 'Pending'), ('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed')])),
                ('inputs', models.TextField(default='{}')),
                ('outputs', models.TextField(default='{}')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True, on_delete=django.db.models.deletion.SET_NULL)),
            ],
        ),
        migrations.AlterField(
            model_name='service',
            name='data_path',
            field=models.FilePathField(path='/var/ncdjango/services/', recursive=True),
        ),
        migrations.AlterField(
            model_name='temporaryfile',
            name='file',
            field=models.FileField(max_length=1024, upload_to='/tmp'),
        ),
        migrations.AlterIndexTogether(
            name='processingjob',
            index_together=set([('status', 'created')]),
        ),
    ]
