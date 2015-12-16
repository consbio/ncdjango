# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import uuid
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ncdjango', '0002_auto_20141001_1050'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcessingJob',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('uuid', models.CharField(max_length=36, default=uuid.uuid4, db_index=True)),
                ('job', models.CharField(max_length=100)),
                ('user_host', models.CharField(max_length=32)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('celery_id', models.CharField(max_length=100)),
                ('inputs', models.TextField(default='{}')),
                ('outputs', models.TextField(default='{}')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='service',
            name='data_path',
            field=models.FilePathField(max_length=1024, path='/var/ncdjango/services/', recursive=True),
        ),
        migrations.AlterField(
            model_name='temporaryfile',
            name='file',
            field=models.FileField(max_length=1024, upload_to='/tmp'),
        ),
        migrations.AlterUniqueTogether(
            name='variable',
            unique_together=set([('variable', 'service')]),
        ),
    ]
