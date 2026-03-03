# Generated manually

from django.db import migrations, models
import django.db.models.deletion
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('online', '0003_records_online_doc'),
        ('refs', '0124_refcarsorganizationfiles_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonalDataConsent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(blank=True, db_index=True, max_length=64, unique=True, verbose_name='Уникальный токен')),
                ('last_name', models.CharField(default='', max_length=100, verbose_name='Фамилия')),
                ('first_name', models.CharField(default='', max_length=100, verbose_name='Имя')),
                ('middle_name', models.CharField(blank=True, default='', max_length=100, verbose_name='Отчество')),
                ('phone', models.CharField(default='', max_length=20, verbose_name='Номер телефона')),
                ('email', models.EmailField(blank=True, default='', max_length=254, verbose_name='Email')),
                ('date_created', models.DateTimeField(default=datetime.datetime.now, verbose_name='Дата и время создания ссылки')),
                ('date_opened', models.DateTimeField(blank=True, null=True, verbose_name='Дата и время открытия ссылки')),
                ('date_confirmed', models.DateTimeField(blank=True, null=True, verbose_name='Дата и время подтверждения')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP адрес')),
                ('user_agent', models.TextField(blank=True, default='', verbose_name='User Agent')),
                ('confirmed', models.BooleanField(default=False, verbose_name='Подтверждено')),
                ('revoked', models.BooleanField(default=False, verbose_name='Отозвано')),
                ('date_revoked', models.DateTimeField(blank=True, null=True, verbose_name='Дата и время отзыва')),
                ('consent_text', models.TextField(blank=True, default='', verbose_name='Текст согласия')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Комментарий')),
                ('customer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='refs.refcustomer', verbose_name='Клиент')),
                ('unit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='refs.refunit', verbose_name='Подразделение')),
            ],
            options={
                'verbose_name': 'Согласие на обработку персональных данных',
                'verbose_name_plural': 'Согласия на обработку персональных данных',
                'db_table': 'personal_data_consent',
                'ordering': ['-date_created'],
            },
        ),
    ]

