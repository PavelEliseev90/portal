# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auction_avito', '0002_avitolotimage_file_avitolotimage_source_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AvitoVenue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dealer_id', models.PositiveIntegerField(db_index=True, unique=True, verbose_name='dealerId')),
                ('name', models.CharField(blank=True, default='', max_length=500, verbose_name='Наименование')),
                ('city', models.CharField(blank=True, default='', max_length=200, verbose_name='Город')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
            ],
            options={
                'verbose_name': 'Площадка Авито',
                'verbose_name_plural': 'Площадки Авито',
                'db_table': 'avitoVenue',
                'ordering': ['city', 'name', 'dealer_id'],
            },
        ),
        migrations.AddField(
            model_name='avitolot',
            name='venue',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lots',
                to='auction_avito.avitovenue',
                verbose_name='Площадка',
            ),
        ),
    ]
