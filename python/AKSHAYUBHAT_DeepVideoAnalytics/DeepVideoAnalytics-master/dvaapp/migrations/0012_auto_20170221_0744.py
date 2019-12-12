# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-21 07:44
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dvaapp', '0011_auto_20170130_2313'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='uploader',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='frame',
            name='time_seconds',
            field=models.FloatField(),
        ),
    ]
