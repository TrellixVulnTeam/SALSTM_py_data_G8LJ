# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-01-17 08:06
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dvaapp', '0002_auto_20170117_0802'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='uploaded',
            field=models.BooleanField(default=False),
        ),
    ]
