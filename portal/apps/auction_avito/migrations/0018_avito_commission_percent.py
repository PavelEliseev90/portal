# Generated manually

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auction_avito', '0017_widen_vehicle_and_autoteka_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='avitoauctionsettings',
            name='avito_commission_percent',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                help_text='Процент от цены выкупа после финансирования (например 2.30). Складывается с фиксированной суммой.',
                max_digits=6,
                verbose_name='Комиссия Авито, %',
            ),
        ),
    ]
