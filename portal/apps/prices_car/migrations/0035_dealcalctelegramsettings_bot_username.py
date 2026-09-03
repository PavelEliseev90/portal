# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0034_dealcalctelegramsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='dealcalctelegramsettings',
            name='bot_username',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Для подсказки в профиле: ссылка t.me/…',
                max_length=128,
                verbose_name='Username бота (без @)',
            ),
        ),
        migrations.AlterField(
            model_name='dealcalctelegramsettings',
            name='chat_ids',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Опциональный тестовый/общий канал. Личные уведомления — через telegram_chat_id в профиле пользователя. Если пусто — DEAL_CALC_TELEGRAM_CHAT_IDS из окружения.',
                max_length=512,
                verbose_name='Общие chat ID (через запятую)',
            ),
        ),
    ]
