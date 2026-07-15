# Generated manually for mykors app
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='MykorsCarSyncState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('car_id', models.IntegerField(db_index=True, verbose_name='ID авто на портале')),
                ('vin', models.CharField(db_index=True, max_length=18, verbose_name='VIN')),
                ('payload_hash', models.CharField(blank=True, default='', max_length=64, verbose_name='Hash payload')),
                ('remote_id', models.IntegerField(blank=True, null=True, verbose_name='ID в MyKors')),
                ('last_synced_at', models.DateTimeField(blank=True, null=True, verbose_name='Последняя попытка')),
                ('last_ok', models.BooleanField(default=False, verbose_name='Успешно')),
                ('last_http_status', models.IntegerField(blank=True, null=True, verbose_name='HTTP status')),
                ('last_error', models.TextField(blank=True, default='', verbose_name='Ошибка')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Статус выгрузки авто в MyKors',
                'verbose_name_plural': 'Статусы выгрузки авто в MyKors',
                'db_table': 'mykors_car_sync_state',
            },
        ),
        migrations.AddIndex(
            model_name='mykorscarsyncstate',
            index=models.Index(fields=['last_ok', 'last_synced_at'], name='mykors_car__last_ok_7d0a3e_idx'),
        ),
        migrations.AddConstraint(
            model_name='mykorscarsyncstate',
            constraint=models.UniqueConstraint(fields=('car_id',), name='mykors_carsync_car_id_uniq'),
        ),
    ]
