# Generated manually for Command Center plans, tactics, key models, and extended discounts

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('refs', '0047_refratingcarsorganization_refstatuscarsorganization_and_more'),
        ('prices_car', '0039_merge_telegram_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='pricecarbrand',
            name='free_consignment_days',
            field=models.PositiveIntegerField(
                default=90,
                help_text='Срок бесплатного хранения/консигнации от импортера (в днях)',
                verbose_name='Бесплатный срок консигнации (дней)',
            ),
        ),
        migrations.AddField(
            model_name='pricecarkmdiscount',
            name='comment',
            field=models.CharField(
                blank=True,
                default='',
                max_length=512,
                verbose_name='Комментарий / Обоснование',
            ),
        ),
        migrations.AddField(
            model_name='pricecarkmdiscount',
            name='is_key_model',
            field=models.BooleanField(
                default=False,
                help_text='Применять только к ключевым моделям ДЦ на текущий месяц',
                verbose_name='Только для ключевых моделей',
            ),
        ),
        migrations.AddField(
            model_name='pricecarkmdiscount',
            name='is_yellow_car',
            field=models.BooleanField(
                default=False,
                help_text='Применять только к автомобилям со сданным рапортом / признаком желтого',
                verbose_name='Только для желтых авто',
            ),
        ),
        migrations.AddField(
            model_name='pricecarkmdiscount',
            name='type_sale',
            field=models.ForeignKey(
                blank=True,
                help_text='Если пусто — действует для всех каналов продаж',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='price_car_km_discounts',
                to='refs.reftypesalecarsorganization',
                verbose_name='Канал продажи',
            ),
        ),
        migrations.AddField(
            model_name='pricecarkmdiscount',
            name='unit',
            field=models.ForeignKey(
                blank=True,
                help_text='Если пусто — действует для всех ДЦ бренда',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='price_car_km_discounts',
                to='refs.refunit',
                verbose_name='Подразделение ДЦ',
            ),
        ),
        migrations.CreateModel(
            name='DcMonthlyPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month', models.DateField(help_text='Первое число месяца, напр. 2025-09-01', verbose_name='Месяц (период)')),
                ('plan_dc_qty', models.PositiveIntegerField(default=0, verbose_name='План ДЦ, шт.')),
                ('plan_importer_qty', models.PositiveIntegerField(default=0, verbose_name='План импортера, шт.')),
                ('tactic', models.CharField(choices=[('max_margin', 'Максимальная маржа'), ('balanced', 'Умеренный (баланс)'), ('max_volume', 'Максимальные штуки')], default='balanced', max_length=32, verbose_name='Тактика ДЦ')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Автор изменений')),
                ('unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dc_pricing_monthly_plans', to='refs.refunit', verbose_name='Подразделение ДЦ')),
            ],
            options={
                'verbose_name': 'План ДЦ на месяц',
                'verbose_name_plural': 'Планы ДЦ на месяц',
                'db_table': 'prices_car_dc_monthly_plan',
                'ordering': ['-month', 'unit'],
            },
        ),
        migrations.CreateModel(
            name='DcKeyModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('target_qty', models.PositiveIntegerField(blank=True, default=0, verbose_name='Целевой объем, шт.')),
                ('comment', models.CharField(blank=True, default='', max_length=512, verbose_name='Комментарий')),
                ('model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dc_key_models', to='refs.autorumodel', verbose_name='Модель')),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='key_models', to='prices_car.dcmonthlyplan', verbose_name='План ДЦ')),
            ],
            options={
                'verbose_name': 'Ключевая модель ДЦ на месяц',
                'verbose_name_plural': 'Ключевые модели ДЦ на месяц',
                'db_table': 'prices_car_dc_key_model',
                'ordering': ['plan', 'model'],
            },
        ),
        migrations.AddConstraint(
            model_name='dcmonthlyplan',
            constraint=models.UniqueConstraint(fields=('unit', 'month'), name='prices_car_dc_monthly_plan_unit_month_uniq'),
        ),
        migrations.AddConstraint(
            model_name='dckeymodel',
            constraint=models.UniqueConstraint(fields=('plan', 'model'), name='prices_car_dc_key_model_plan_model_uniq'),
        ),
        migrations.AddField(
            model_name='kmcar',
            name='km_auto_6',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='КМ Вариант 6 (Smart АвтоК)'),
        ),
    ]
