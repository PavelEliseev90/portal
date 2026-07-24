# Generated manually for monitor / per-lot max bid / per-dealer emails

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auction_avito', '0010_merge_autobid_and_outcome_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='avitolotoffer',
            name='manual_max_bid',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='Если задано — автоставка идёт до этого порога, даже если он выше расчётного выкупа.',
                null=True,
                verbose_name='Макс. ставка вручную (потолок автоставки)',
            ),
        ),
        migrations.AddField(
            model_name='avitobidderaccount',
            name='win_notify_emails',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Адреса этой площадки через запятую или с новой строки. Если пусто — берётся общий список из настроек.',
                verbose_name='Email при выигрыше (площадка)',
            ),
        ),
        migrations.AlterField(
            model_name='avitoauctionsettings',
            name='win_notify_emails',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Общий список, если у площадки (AvitoBidderAccount) свои адреса не заданы. Письмо уходит один раз при outcome=won.',
                verbose_name='Email при выигрыше лота (общий fallback)',
            ),
        ),
    ]
