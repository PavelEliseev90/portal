# Generated manually for DealCalcTelegramSettings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0033_alter_carcalculationukapproval_approved_kvp'),
    ]

    operations = [
        migrations.CreateModel(
            name='DealCalcTelegramSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enabled', models.BooleanField(default=False, help_text='Параллельно email. Ошибки Telegram не влияют на почту и согласование.', verbose_name='Включить Telegram по КП')),
                ('bot_token', models.CharField(blank=True, default='', help_text='Если пусто — берётся DEAL_CALC_TELEGRAM_BOT_TOKEN из окружения.', max_length=256, verbose_name='Токен бота')),
                ('chat_ids', models.CharField(blank=True, default='', help_text='Если пусто — DEAL_CALC_TELEGRAM_CHAT_IDS из окружения.', max_length=512, verbose_name='Chat ID (через запятую)')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
            ],
            options={
                'verbose_name': 'Telegram: согласование КП',
                'verbose_name_plural': 'Telegram: согласование КП',
                'db_table': 'prices_car_deal_calc_telegram_settings',
            },
        ),
    ]
