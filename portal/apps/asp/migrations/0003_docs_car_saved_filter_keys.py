# Generated manually for docs agreement/shipment saved filters

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('asp', '0002_disposition_saved_filter_key'),
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
                ],
                db_index=True,
                max_length=32,
                verbose_name='Ключ отчёта',
            ),
        ),
    ]
