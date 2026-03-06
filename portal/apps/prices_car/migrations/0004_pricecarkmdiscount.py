# PriceCarKmDiscount: discount % for min Km by brand/model/modification/complectation/year, date range within one month

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('refs', '0128_reftyperepair_dop_alter_refcarsorganization_min_km'),
        ('prices_car', '0003_alter_brandkm_brand'),
    ]

    operations = [
        migrations.CreateModel(
            name='PriceCarKmDiscount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.PositiveSmallIntegerField(blank=True, help_text='Год выпуска автомобиля (опционально)', null=True, verbose_name='Год выпуска')),
                ('discount_percent', models.FloatField(help_text='Процент, на который изменяется минимальный Км (кумулятивная маржа)', verbose_name='Процент изменения мин. Км')),
                ('date_from', models.DateField(verbose_name='Действует с')),
                ('date_to', models.DateField(verbose_name='Действует по')),
                ('brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='km_discounts', to='prices_car.pricecarbrand', verbose_name='Бренд')),
                ('complectation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='price_car_km_discounts', to='refs.autorucomplectation', verbose_name='Комплектация')),
                ('model', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='price_car_km_discounts', to='refs.autorumodel', verbose_name='Модель')),
                ('modification', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='price_car_km_discounts', to='refs.autorumodification', verbose_name='Модификация')),
            ],
            options={
                'verbose_name': 'Дисконт Км',
                'verbose_name_plural': 'Дисконты Км',
                'db_table': 'prices_car_km_discount',
                'ordering': ['-date_from', 'brand'],
            },
        ),
    ]
