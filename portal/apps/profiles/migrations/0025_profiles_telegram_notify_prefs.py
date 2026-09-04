# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0024_profiles_telegram_chat_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='profiles',
            name='telegram_notify_pending',
            field=models.BooleanField(
                default=True,
                help_text='Карточки КП, ожидающие согласования директором / УК.',
                verbose_name='Telegram: требуется согласование',
            ),
        ),
        migrations.AddField(
            model_name='profiles',
            name='telegram_notify_auto_approved',
            field=models.BooleanField(
                default=True,
                help_text='Оповещения, когда КП согласовано автоматически по правилам.',
                verbose_name='Telegram: автоматически согласованные',
            ),
        ),
        migrations.AddField(
            model_name='profiles',
            name='telegram_notify_results',
            field=models.BooleanField(
                default=True,
                help_text='Согласовано / отклонено / отправлено в УК.',
                verbose_name='Telegram: результаты согласования',
            ),
        ),
    ]
