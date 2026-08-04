# Generated manually for AvitoVenue.unit + win RLK fields on offer

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('refs', '0144_pricegroupstagedays'),
        ('documents', '0701_alter_doсrecomendation_kod_recomendation'),
        ('auction_avito', '0018_avito_commission_percent'),
    ]

    operations = [
        migrations.AddField(
            model_name='avitovenue',
            name='unit',
            field=models.ForeignKey(
                blank=True,
                help_text='ДЦ для создания рабочего листа в 1С при выигрыше лота на этой площадке.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='avito_venues',
                to='refs.refunit',
                verbose_name='Подразделение',
            ),
        ),
        migrations.AddField(
            model_name='avitolotoffer',
            name='win_rlk',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='avito_win_offers',
                to='documents.docrlk',
                verbose_name='РЛ созданный при выигрыше',
            ),
        ),
        migrations.AddField(
            model_name='avitolotoffer',
            name='win_rlk_uin',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='UIN РЛ 1С'),
        ),
        migrations.AddField(
            model_name='avitolotoffer',
            name='win_rlk_number',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='Номер РЛ 1С'),
        ),
        migrations.AddField(
            model_name='avitolotoffer',
            name='win_rlk_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Дата РЛ 1С'),
        ),
        migrations.AddField(
            model_name='avitolotoffer',
            name='win_rlk_created_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='РЛ отправлен/создан в 1С'),
        ),
        migrations.AddField(
            model_name='avitolotoffer',
            name='win_rlk_error',
            field=models.TextField(blank=True, default='', verbose_name='Ошибка создания РЛ'),
        ),
    ]
