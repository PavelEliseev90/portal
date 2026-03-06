# Manual migration: BrandKM model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('refs', '0128_reftyperepair_dop_alter_refcarsorganization_min_km'),
    ]

    operations = [
        migrations.CreateModel(
            name='BrandKM',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('km', models.PositiveIntegerField(default=0, help_text='Значение пробега (км) на период', verbose_name='Км')),
                ('month', models.DateField(help_text='Месяц, на который устанавливается значение (обычно первый день месяца, напр. 2025-02-01)', verbose_name='Месяц (период)')),
                ('brand', models.ForeignKey(limit_choices_to={'avtosalon': True}, on_delete=django.db.models.deletion.CASCADE, related_name='brand_km_values', to='refs.autorumark', verbose_name='Марка')),
            ],
            options={
                'verbose_name': 'Км по марке на месяц',
                'verbose_name_plural': 'Км по маркам на месяц',
                'db_table': 'prices_car_brand_km',
                'ordering': ['brand', '-month'],
            },
        ),
        migrations.AddConstraint(
            model_name='brandkm',
            constraint=models.UniqueConstraint(fields=('brand', 'month'), name='prices_car_brand_km_brand_month_uniq'),
        ),
    ]
