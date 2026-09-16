# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('asp', '0003_docs_car_saved_filter_keys'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reportsavedfilter',
            name='report_key',
            field=models.CharField(
                choices=[
                    ('margin', 'Кумулятивная маржа'),
                    ('stock', 'Остатки'),
                    ('accepted', 'Принятые'),
                    ('disposition', 'Диспозиция'),
                    ('docs_agreement', 'Соглашения о покупке'),
                    ('docs_shipment', 'Отгрузки автомобилей'),
                    ('docs_rlk', 'Рабочие листы ОП'),
                ],
                db_index=True,
                max_length=32,
                verbose_name='Ключ отчёта',
            ),
        ),
    ]
