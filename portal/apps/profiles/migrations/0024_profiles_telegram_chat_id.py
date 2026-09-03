# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0023_profiles_eco_price_increase'),
    ]

    operations = [
        migrations.AddField(
            model_name='profiles',
            name='telegram_chat_id',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Личный chat_id для уведомлений и кнопок согласования КП. Узнать: напишите боту /start, затем @userinfobot → Id.',
                max_length=64,
                verbose_name='Telegram chat ID',
            ),
        ),
    ]
