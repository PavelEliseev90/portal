# PriceCarBrand model (brands with marks and models)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('refs', '0128_reftyperepair_dop_alter_refcarsorganization_min_km'),
        ('prices_car', '0001_brand_km'),
    ]

    operations = [
        migrations.CreateModel(
            name='PriceCarBrand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Название бренда')),
                ('marks', models.ManyToManyField(
                    blank=True,
                    help_text='Марки, входящие в этот бренд',
                    related_name='price_car_brands',
                    to='refs.autorumark',
                    verbose_name='Марки Автору',
                )),
                ('models_included', models.ManyToManyField(
                    blank=True,
                    help_text='Конкретные модели (если пусто — учитываются все модели выбранных марок)',
                    related_name='price_car_brands',
                    to='refs.autorumodel',
                    verbose_name='Модели в бренде',
                )),
            ],
            options={
                'verbose_name': 'Бренд (ценообразование)',
                'verbose_name_plural': 'Бренды (ценообразование)',
                'db_table': 'prices_car_brand',
                'ordering': ['name'],
            },
        ),
    ]
