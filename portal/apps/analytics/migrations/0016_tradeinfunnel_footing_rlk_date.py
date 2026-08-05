# Generated manually for TradeInFunnel.footing_rlk_date

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0015_tradeinfunnel_rlk_uin_tradeinfunnel_source_bu'),
    ]

    operations = [
        migrations.AddField(
            model_name='tradeinfunnel',
            name='footing_rlk_date',
            field=models.DateTimeField(
                blank=True,
                help_text='Дата РЛ ОП (источник / footing)',
                null=True,
            ),
        ),
    ]
