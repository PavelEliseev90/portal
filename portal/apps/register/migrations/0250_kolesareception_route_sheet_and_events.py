# Generated manually for 2KK route sheet + events

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import register.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('register', '0249_kolesareception_send_wheels_ib_uin'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkakolesareception',
            name='route_sheet_attached',
            field=models.BooleanField(
                db_index=True,
                default=False,
                verbose_name='Маршрутный лист прикреплён',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenkakolesareception',
            name='route_sheet_attached_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Дата прикрепления маршрутного листа',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenkakolesareception',
            name='route_sheet_attached_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='kolesa_reception_route_sheets',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Кто прикрепил маршрутный лист',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenkakolesareception',
            name='route_sheet_file',
            field=models.FileField(
                blank=True,
                null=True,
                storage=register.models.save_directory,
                upload_to='estimation_wheels/route_sheet/%Y/%m/%d/',
                verbose_name='Подписанный маршрутный лист',
            ),
        ),
        migrations.CreateModel(
            name='RegInteractivOcenkaKolesaReceptionEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(
                    choices=[
                        ('created', 'Создание приёмки'),
                        ('photo_add', 'Добавление фото'),
                        ('photo_delete', 'Удаление фото'),
                        ('route_sheet_add', 'Прикрепление маршрутного листа'),
                        ('route_sheet_delete', 'Удаление маршрутного листа'),
                        ('send', 'Отправка в БУ колёс'),
                        ('resend', 'Повторная отправка в БУ колёс'),
                        ('reset_send', 'Сброс признака отправки'),
                        ('save', 'Изменение реквизитов'),
                    ],
                    db_index=True,
                    max_length=32,
                    verbose_name='Тип события',
                )),
                ('message', models.CharField(blank=True, default='', max_length=1024, verbose_name='Описание')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Когда')),
                ('extra', models.JSONField(blank=True, default=dict, verbose_name='Доп. данные')),
                ('reception', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='events',
                    to='register.reginteractivocenkakolesareception',
                    verbose_name='Приёмка',
                )),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Пользователь',
                )),
            ],
            options={
                'verbose_name': 'Событие приёмки 2КК',
                'verbose_name_plural': 'События приёмки 2КК',
                'db_table': 'regInteractivOcenkaKolesaReceptionEvent',
                'ordering': ('-created_at', '-id'),
            },
        ),
    ]
