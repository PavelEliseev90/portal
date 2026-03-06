# PriceCarStageKM: indices km by stage (RefStagePrice) and month

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('refs', '0042_refpricegroup_refstageprice_refstatuscars_and_more'),
        ('prices_car', '0005_brandkm_km_index_rdo'),
    ]

    operations = [
        migrations.CreateModel(
            name='PriceCarStageKM',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month', models.DateField(help_text='Месяц, на который устанавливается индекс (например, первый день месяца 2025-02-01)', verbose_name='Месяц (период)')),
                ('km_index', models.DecimalField(decimal_places=2, default=0, help_text='Индекс км (число с 2 знаками после запятой)', max_digits=12, verbose_name='Индекс Км')),
                ('stage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='price_car_km_indices', to='refs.refstageprice', verbose_name='Этап УС')),
            ],
            options={
                'verbose_name': 'Индекс Км по этапу УС',
                'verbose_name_plural': 'Индексы Км по этапам УС',
                'db_table': 'prices_car_stage_km',
                'ordering': ['stage', '-month'],
            },
        ),
        migrations.AddConstraint(
            model_name='pricecarstagekm',
            constraint=models.UniqueConstraint(fields=('stage', 'month'), name='prices_car_stage_km_stage_month_uniq'),
        ),
    ]
