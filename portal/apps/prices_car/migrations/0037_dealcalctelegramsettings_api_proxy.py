# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0036_telegram_webhook_pending'),
    ]

    operations = [
        migrations.AddField(
            model_name='dealcalctelegramsettings',
            name='api_proxy',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Если с сервера нет доступа к Telegram: http://host:port или http://user:pass@host:port. Пусто — DEAL_CALC_TELEGRAM_PROXY из окружения.',
                max_length=512,
                verbose_name='Прокси для api.telegram.org',
            ),
        ),
    ]
