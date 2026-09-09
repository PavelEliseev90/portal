# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='EstimationBriefFactor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=64, unique=True, verbose_name='Код')),
                ('label', models.CharField(max_length=200, verbose_name='Название')),
                ('group', models.CharField(blank=True, default='', max_length=64, verbose_name='Группа')),
                ('weight', models.FloatField(default=0, help_text='Плюс повышает оценку (к 5★), минус понижает. База шкалы 3.5.', verbose_name='Вес')),
                ('objection', models.CharField(blank=True, default='', max_length=300, verbose_name='Возражение клиента')),
                ('answer', models.TextField(blank=True, default='', verbose_name='Ответ / аргументация')),
                ('sort', models.IntegerField(default=0, verbose_name='Порядок')),
                ('active', models.BooleanField(default=True, verbose_name='Участвует в шкале')),
            ],
            options={
                'verbose_name': 'Сводка клиенту: фактор шкалы',
                'verbose_name_plural': 'Сводка клиенту: факторы шкалы',
                'db_table': 'estimationBriefFactor',
                'ordering': ['sort', 'id'],
            },
        ),
    ]
