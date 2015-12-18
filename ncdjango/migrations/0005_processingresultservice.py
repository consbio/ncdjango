# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ncdjango', '0004_auto_20151218_1111'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcessingResultService',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_temporary', models.BooleanField(default=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('job', models.ForeignKey(to='ncdjango.ProcessingJob')),
                ('service', models.ForeignKey(to='ncdjango.Service')),
            ],
        ),
    ]
