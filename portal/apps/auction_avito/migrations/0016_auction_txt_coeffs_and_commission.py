from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auction_avito', '0015_settings_cap_bid_by_seller_wish'),
    ]

    operations = [
        migrations.AddField(
            model_name='avitoauctionsettings',
            name='txt_coeff_200',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='ИРЦ токсичного стока для ЦГ до 200 тыс. ₽. Пусто — из настроек ДЦ.',
                max_digits=8,
                null=True,
                verbose_name='ТХТ коэф. ЦГ 200',
            ),
        ),
        migrations.AddField(
            model_name='avitoauctionsettings',
            name='txt_coeff_400',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=8, null=True,
                verbose_name='ТХТ коэф. ЦГ 400',
            ),
        ),
        migrations.AddField(
            model_name='avitoauctionsettings',
            name='txt_coeff_700',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=8, null=True,
                verbose_name='ТХТ коэф. ЦГ 700',
            ),
        ),
        migrations.AddField(
            model_name='avitoauctionsettings',
            name='txt_coeff_1200',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=8, null=True,
                verbose_name='ТХТ коэф. ЦГ 1 200',
            ),
        ),
        migrations.AddField(
            model_name='avitoauctionsettings',
            name='txt_coeff_2000',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=8, null=True,
                verbose_name='ТХТ коэф. ЦГ 2 000',
            ),
        ),
        migrations.AddField(
            model_name='avitoauctionsettings',
            name='txt_coeff_3000',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=8, null=True,
                verbose_name='ТХТ коэф. ЦГ 3 000',
            ),
        ),
        migrations.AddField(
            model_name='avitoauctionsettings',
            name='txt_coeff_5000',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=8, null=True,
                verbose_name='ТХТ коэф. ЦГ 5 000',
            ),
        ),
        migrations.AddField(
            model_name='avitoauctionsettings',
            name='txt_coeff_5001',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=8, null=True,
                verbose_name='ТХТ коэф. ЦГ 5 000+',
            ),
        ),
        migrations.AddField(
            model_name='avitoauctionsettings',
            name='avito_commission',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Фиксированная сумма, вычитается из цены выкупа после финансирования.',
                verbose_name='Комиссия Авито, ₽',
            ),
        ),
    ]
