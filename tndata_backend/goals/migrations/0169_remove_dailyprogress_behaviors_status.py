# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-09-13 15:11
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('goals', '0168_auto_20160907_2115'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dailyprogress',
            name='behaviors_status',
        ),
    ]
