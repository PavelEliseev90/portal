# Generated manually - device_type and user_agent for PageViewLog

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('changelog', '0002_pageviewlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='pageviewlog',
            name='device_type',
            field=models.CharField(blank=True, db_index=True, max_length=20, verbose_name='Тип устройства'),
        ),
        migrations.AddField(
            model_name='pageviewlog',
            name='user_agent',
            field=models.CharField(blank=True, max_length=512, verbose_name='User-Agent'),
        ),
    ]
