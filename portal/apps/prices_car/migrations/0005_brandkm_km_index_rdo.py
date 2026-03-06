# BrandKM: add km_index_rdo (decimal, 2 places) for RDO

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0004_pricecarkmdiscount'),
    ]

    operations = [
        migrations.AddField(
            model_name='brandkm',
            name='km_index_rdo',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                default=0,
                help_text='Индекс км для РДО (число с 2 знаками после запятой)',
                max_digits=12,
                null=True,
                verbose_name='Индекс Км для РДО',
            ),
        ),
    ]
