from django.db import migrations, models
import datetime
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('avtosalon', '0021_regcarsorganizationtaskfile'),
        ('refs', '0110_auction_winner_email_auction_winner_name_and_more'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='SmsAuthSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(blank=True, default='', max_length=32, verbose_name='Телефон (как введен)')),
                ('phone_normalized', models.CharField(db_index=True, max_length=16, verbose_name='Телефон (нормализованный)')),
                ('code_hash', models.CharField(blank=True, default='', max_length=255, verbose_name='Хэш кода')),
                ('is_verified', models.BooleanField(default=False, verbose_name='Код подтвержден')),
                ('attempts_count', models.IntegerField(default=0, verbose_name='Количество попыток ввода')),
                ('max_attempts', models.IntegerField(default=5, verbose_name='Максимум попыток ввода')),
                ('consent_personal_data', models.BooleanField(default=False, verbose_name='Согласие на ПДн')),
                ('consent_personal_data_at', models.DateTimeField(blank=True, null=True, verbose_name='Время согласия ПДн')),
                ('consent_personal_data_ip', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP согласия ПДн')),
                ('consent_ads', models.BooleanField(default=False, verbose_name='Согласие на рекламные рассылки')),
                ('consent_ads_at', models.DateTimeField(blank=True, null=True, verbose_name='Время согласия на рассылки')),
                ('consent_ads_ip', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP согласия на рассылки')),
                ('created_at', models.DateTimeField(default=datetime.datetime.now, verbose_name='Создано')),
                ('code_sent_at', models.DateTimeField(blank=True, null=True, verbose_name='Код отправлен')),
                ('code_expires_at', models.DateTimeField(blank=True, null=True, verbose_name='Код действует до')),
                ('verified_at', models.DateTimeField(blank=True, null=True, verbose_name='Код подтвержден в')),
                ('request_ip', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP запроса')),
                ('request_user_agent', models.TextField(blank=True, default='', verbose_name='User-Agent')),
                ('car', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sms_auth_sessions', to='refs.refcarsorganization', verbose_name='Автомобиль')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sms_auth_sessions', to='auth.user', verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'SMS авторизация',
                'verbose_name_plural': 'SMS авторизации',
                'db_table': 'sms_auth_session',
            },
        ),
        migrations.AddIndex(
            model_name='smsauthsession',
            index=models.Index(fields=['phone_normalized'], name='sms_auth_se_phone_n_a994ea_idx'),
        ),
        migrations.AddIndex(
            model_name='smsauthsession',
            index=models.Index(fields=['created_at'], name='sms_auth_se_created_435c3f_idx'),
        ),
        migrations.AddIndex(
            model_name='smsauthsession',
            index=models.Index(fields=['is_verified'], name='sms_auth_se_is_veri_3ec4a1_idx'),
        ),
    ]
