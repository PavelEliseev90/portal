from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estimation_engine', '0011_merge_rule_body_and_package_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='preparationworkpackage',
            name='estimation_reduction_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                help_text='На сколько снижается оценка автомобиля при применении этого пакета.',
                max_digits=14,
                verbose_name='Сумма снижения оценки, ₽',
            ),
        ),
    ]
