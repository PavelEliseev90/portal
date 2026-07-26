# Generated manually for cap_bid_by_seller_wish

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auction_avito', '0014_settings_min_bid_and_manual_ceiling'),
    ]

    operations = [
        migrations.AddField(
            model_name='avitoauctionsettings',
            name='cap_bid_by_seller_wish',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Если включено, автоставка не ставится, когда рассчитанная сумма '
                    'превышает minPrice (желание/пожелание продавца) по лоту.'
                ),
                verbose_name='Не выше пожелания продавца',
            ),
        ),
    ]
