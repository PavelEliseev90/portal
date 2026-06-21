from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('register', '0220_regestimationssettings_diagnostic_extra_by_price_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='author',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='interactive_price_recalc_history',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Пользователь',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='estimation',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='price_recalc_history',
                to='register.reginteractivocenka',
                verbose_name='Оценка',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='trigger',
            field=models.CharField(blank=True, default='', max_length=150, null=True, verbose_name='Событие'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='is_success',
            field=models.BooleanField(default=True, verbose_name='Успешно'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='error_message',
            field=models.TextField(blank=True, default='', verbose_name='Ошибка'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='raw_calculation_json',
            field=models.JSONField(blank=True, default=dict, verbose_name='Ответ расчёта (JSON)'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='discount_torg',
            field=models.FloatField(blank=True, default=0.0, null=True, verbose_name='Скидка торг'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='finance_price',
            field=models.FloatField(blank=True, default=0.0, null=True, verbose_name='Финансирование'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='zachita_ot_ubitka',
            field=models.FloatField(blank=True, default=0.0, null=True, verbose_name='Защита от убытка'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='price_auto_1',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Автоматическая 1'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='price_auto_2',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Автоматическая 2'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='price_auto_3',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Автоматическая 3'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='price_auto_bcp_1',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='БЦП 1'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='price_auto_bcp_2',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='БЦП 2'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='price_auto_bcp_3',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='БЦП 3'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='price_zna_1',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='ЦНА 1'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='price_zna_2',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='ЦНА 2'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='price_zna_3',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='ЦНА 3'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='price_before_kd',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Согласованная до КД'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='price_after_kd',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Согласованная после КД'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='price_bcp',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='БЦП согласованный'),
        ),
        migrations.AlterField(
            model_name='reginteractivocenkaprice',
            name='date',
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Дата'),
        ),
        migrations.AlterField(
            model_name='reginteractivocenkaprice',
            name='page_soglasovanie',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='price_recalc_history',
                to='register.reginteractivocenkasoglasovanie',
                verbose_name='Согласование',
            ),
        ),
        migrations.AlterField(
            model_name='reginteractivocenkaprice',
            name='user',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='history_user',
                to='refs.refstaff',
                verbose_name='Автор (RefStaff)',
            ),
        ),
        migrations.AddIndex(
            model_name='reginteractivocenkaprice',
            index=models.Index(fields=['estimation', '-date'], name='regInterac_estimat_6a8f21_idx'),
        ),
        migrations.AddIndex(
            model_name='reginteractivocenkaprice',
            index=models.Index(fields=['page_soglasovanie', '-date'], name='regInterac_page_so_0d4b62_idx'),
        ),
    ]
