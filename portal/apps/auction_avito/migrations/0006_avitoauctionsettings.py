from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auction_avito', '0005_avitobidhistory_comment'),
    ]

    operations = [
        migrations.CreateModel(
            name='AvitoAuctionSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('auto_bid_enabled', models.BooleanField(
                    default=False,
                    help_text='Глобальный выключатель. Парсер/воркер ставит только если включено.',
                    verbose_name='Автоставки включены',
                )),
                ('mileage_min', models.PositiveIntegerField(
                    blank=True,
                    help_text='Пусто = без нижней границы.',
                    null=True,
                    verbose_name='Пробег от, км',
                )),
                ('mileage_max', models.PositiveIntegerField(
                    blank=True,
                    help_text='Пусто = без верхней границы.',
                    null=True,
                    verbose_name='Пробег до, км',
                )),
                ('year_min', models.PositiveSmallIntegerField(
                    blank=True,
                    null=True,
                    verbose_name='Год выпуска от',
                )),
                ('year_max', models.PositiveSmallIntegerField(
                    blank=True,
                    null=True,
                    verbose_name='Год выпуска до',
                )),
                ('block_taxi', models.BooleanField(
                    default=True,
                    verbose_name='Не ставить на такси (taxi)',
                )),
                ('block_carsharing', models.BooleanField(
                    default=True,
                    verbose_name='Не ставить на каршеринг (carsharing)',
                )),
                ('block_mileage_twisted', models.BooleanField(
                    default=True,
                    verbose_name='Не ставить при скрученном пробеге (mileageTwisted)',
                )),
                ('bid_round_to', models.PositiveIntegerField(
                    default=1000,
                    help_text='maxBid + minBidStep округляется вверх до этого шага (обычно 1000).',
                    verbose_name='Округление ставки вверх до',
                )),
                ('weight_test_price', models.DecimalField(
                    decimal_places=3,
                    default=Decimal('1'),
                    max_digits=6,
                    verbose_name='Вес этапа «Тест-прайс»',
                )),
                ('weight_rdo', models.DecimalField(
                    decimal_places=3,
                    default=Decimal('0.55'),
                    max_digits=6,
                    verbose_name='Вес этапа «РДО»',
                )),
                ('weight_kor', models.DecimalField(
                    decimal_places=3,
                    default=Decimal('0.25'),
                    max_digits=6,
                    verbose_name='Вес этапа «Коррекция»',
                )),
                ('weight_txt', models.DecimalField(
                    decimal_places=3,
                    default=Decimal('0.05'),
                    max_digits=6,
                    verbose_name='Вес этапа «ТХТ»',
                )),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
            ],
            options={
                'verbose_name': 'Настройки аукциона Авито',
                'verbose_name_plural': 'Настройки аукциона Авито',
                'db_table': 'avitoAuctionSettings',
            },
        ),
    ]
