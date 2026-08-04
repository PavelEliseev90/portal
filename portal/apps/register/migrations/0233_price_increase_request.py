# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('register', '0232_rename_reginteract_price_c_autohub_idx_reginteract_price_c_71565e_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkasoglasovanie',
            name='price_increase_request_amount',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Запрос повышения: желаемая цена'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkasoglasovanie',
            name='price_increase_request_comment',
            field=models.CharField(blank=True, default='', max_length=5120, null=True, verbose_name='Запрос повышения: комментарий'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkasoglasovanie',
            name='price_increase_request_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Запрос повышения: дата'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkasoglasovanie',
            name='price_increase_request_user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='price_increase_request_user',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Запрос повышения: кто запросил',
            ),
        ),
        migrations.CreateModel(
            name='RegInteractivOcenkaPriceIncreaseRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('desired_price', models.IntegerField(default=0, verbose_name='Желаемая цена')),
                ('comment', models.CharField(blank=True, default='', max_length=5120, verbose_name='Комментарий')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата запроса')),
                ('soglasovanie', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='price_increase_requests',
                    to='register.reginteractivocenkasoglasovanie',
                    verbose_name='Согласование',
                )),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='eco_price_increase_requests',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Кто запросил',
                )),
            ],
            options={
                'verbose_name': 'Запрос повышения цены',
                'verbose_name_plural': 'Запросы повышения цены',
                'db_table': 'regInteractivOcenkaPriceIncreaseRequest',
                'ordering': ['-created_at'],
            },
        ),
    ]
