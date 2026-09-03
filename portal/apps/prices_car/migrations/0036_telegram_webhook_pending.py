# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('prices_car', '0035_dealcalctelegramsettings_bot_username'),
    ]

    operations = [
        migrations.AddField(
            model_name='dealcalctelegramsettings',
            name='webhook_secret',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Заголовок X-Telegram-Bot-Api-Secret-Token. Сгенерируется при сохранении, если пусто.',
                max_length=128,
                verbose_name='Секрет webhook',
            ),
        ),
        migrations.CreateModel(
            name='DealCalcTelegramPendingAction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chat_id', models.CharField(db_index=True, max_length=64, verbose_name='Chat ID')),
                ('action', models.CharField(max_length=64, verbose_name='Действие')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('calc', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='telegram_pending_actions',
                    to='prices_car.carcalculations',
                    verbose_name='КП',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='deal_calc_telegram_pending',
                    to='auth.user',
                    verbose_name='Пользователь',
                )),
            ],
            options={
                'verbose_name': 'Telegram: ожидание комментария КП',
                'verbose_name_plural': 'Telegram: ожидания комментария КП',
                'db_table': 'prices_car_deal_calc_telegram_pending',
            },
        ),
    ]
