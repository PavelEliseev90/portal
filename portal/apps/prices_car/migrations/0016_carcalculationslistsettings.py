from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('prices_car', '0015_brandkm_km_min_dc_remove_index_rdo'),
    ]

    operations = [
        migrations.CreateModel(
            name='CarCalculationsListSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('columns', models.JSONField(blank=True, default=list, help_text='Упорядоченный список ключей видимых столбцов', verbose_name='Столбцы')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='car_calculations_list_settings', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Настройки таблицы калькуляций',
                'verbose_name_plural': 'Настройки таблиц калькуляций',
                'db_table': 'prices_car_calc_list_settings',
            },
        ),
    ]
