from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auction_avito', '0006_avitoauctionsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='avitolotoffer',
            name='outcome_code',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                help_text='waiting_seller | won | lost | no_selection | canceled | unknown',
                max_length=40,
                verbose_name='Код итога',
            ),
        ),
        migrations.AddField(
            model_name='avitolotoffer',
            name='outcome_title',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Как на Maxposter: «Аукцион завершен» и т.п.',
                max_length=300,
                verbose_name='Заголовок итога',
            ),
        ),
        migrations.AddField(
            model_name='avitolotoffer',
            name='outcome_detail',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Напр. «Ждём решения продавца…»',
                verbose_name='Подробности итога',
            ),
        ),
        migrations.AddField(
            model_name='avitolotoffer',
            name='outcome_raw',
            field=models.TextField(blank=True, default='', verbose_name='Сырой текст/JSON итога'),
        ),
        migrations.AddField(
            model_name='avitolotoffer',
            name='outcome_synced_at',
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                null=True,
                verbose_name='Итог синхронизирован',
            ),
        ),
        migrations.AddField(
            model_name='avitolotoffer',
            name='win_email_sent_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Письмо о победе отправлено',
            ),
        ),
        migrations.AddField(
            model_name='avitoauctionsettings',
            name='win_notify_emails',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Адреса через запятую или с новой строки. Письмо уходит один раз при outcome=won.',
                verbose_name='Email при выигрыше лота',
            ),
        ),
        migrations.AddField(
            model_name='avitoauctionsettings',
            name='outcome_poll_enabled',
            field=models.BooleanField(
                default=True,
                help_text='Парсер забирает очередь лотов со ставкой и обновляет статус решения продавца.',
                verbose_name='Опрашивать итоги завершённых лотов',
            ),
        ),
        migrations.AddIndex(
            model_name='avitolotoffer',
            index=models.Index(
                fields=['outcome_code', 'outcome_synced_at'],
                name='avitoLotOff_outcome_7c0c0a_idx',
            ),
        ),
    ]
