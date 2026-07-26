from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auction_avito', '0013_offer_handed_to_work'),
    ]

    operations = [
        migrations.AddField(
            model_name='avitoauctionsettings',
            name='min_bid_amount',
            field=models.PositiveIntegerField(
                blank=True,
                help_text=(
                    'Автоставка не делается, если рассчитанная ставка ниже этого порога '
                    '(фильтр «мелочи» по выкупаемым лотам). Пусто = без ограничения.'
                ),
                null=True,
                verbose_name='Минимальная ставка, ₽',
            ),
        ),
        migrations.AlterField(
            model_name='avitolotoffer',
            name='manual_max_bid',
            field=models.PositiveIntegerField(
                blank=True,
                help_text=(
                    'Если задано — жёсткий потолок: автоставка не может превысить эту сумму, '
                    'даже если расчётный выкуп выше. Приоритет у ручного потолка.'
                ),
                null=True,
                verbose_name='Макс. ставка вручную (потолок автоставки)',
            ),
        ),
    ]
