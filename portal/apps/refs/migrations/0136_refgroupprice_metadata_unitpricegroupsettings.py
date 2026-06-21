# Generated manually for price group settings history model

import django.db.models.deletion
from django.db import migrations, models


def seed_price_groups_and_migrate_settings(apps, schema_editor):
    from refs.price_groups import PRICE_GROUP_CODE_BY_RANGE, seed_price_groups
    from refs.unit_price_group_settings import copy_unit_price_range_to_settings

    seed_price_groups()

    RefUnit = apps.get_model('refs', 'RefUnit')
    RefGroupPrice = apps.get_model('refs', 'RefGroupPrice')
    UnitPriceGroupSettings = apps.get_model('refs', 'UnitPriceGroupSettings')

    code_to_group = {
        group.code: group
        for group in RefGroupPrice.objects.exclude(code='')
    }

    for unit in RefUnit.objects.all().iterator():
        for price_range in PRICE_GROUP_CODE_BY_RANGE.keys():
            price_group = code_to_group.get(str(price_range))
            if not price_group:
                continue
            if UnitPriceGroupSettings.objects.filter(unit_id=unit.pk, price_group_id=price_group.pk).exists():
                continue
            row = copy_unit_price_range_to_settings(unit, price_group)
            UnitPriceGroupSettings.objects.create(
                unit_id=unit.pk,
                price_group_id=price_group.pk,
                ratio_1c_test_price=row.ratio_1c_test_price,
                ratio_1c_rdo=row.ratio_1c_rdo,
                ratio_1c_kor=row.ratio_1c_kor,
                ratio_1c_txt=row.ratio_1c_txt,
                ratio_avtohub_test_price=row.ratio_avtohub_test_price,
                ratio_avtohub_rdo=row.ratio_avtohub_rdo,
                ratio_avtohub_kor=row.ratio_avtohub_kor,
                ratio_avtohub_txt=row.ratio_avtohub_txt,
                percent_txt=row.percent_txt,
                percent_torg_txt=row.percent_torg_txt,
                discount_tt=row.discount_tt,
                discount_torg=row.discount_torg,
                auto_strategy=row.auto_strategy,
                auto_active=row.auto_active,
                autohub_mode_kor=row.autohub_mode_kor,
                autohub_mode_rdo=row.autohub_mode_rdo,
                autohub_mode_test=row.autohub_mode_test,
                autohub_mode_txt=row.autohub_mode_txt,
                eval_type_id=row.eval_type_id,
                lock_eval_change_after_stage=row.lock_eval_change_after_stage,
                deny_manual_price=row.deny_manual_price,
                deny_discount=row.deny_discount,
                correction_kor=row.correction_kor,
                correction_kor_1c=row.correction_kor_1c,
                correction_kor_express=row.correction_kor_express,
                correction_rdo=row.correction_rdo,
                correction_rdo_1c=row.correction_rdo_1c,
                correction_rdo_express=row.correction_rdo_express,
                correction_test=row.correction_test,
                correction_test_1c=row.correction_test_1c,
                correction_test_express=row.correction_test_express,
                correction_txt=row.correction_txt,
                correction_txt_1c=row.correction_txt_1c,
                correction_txt_express=row.correction_txt_express,
                max_discount_tradein=row.max_discount_tradein,
                max_discount_bargain_percent=row.max_discount_bargain_percent,
                marketing=row.marketing,
                no_limit_max_manual=row.no_limit_max_manual,
                reset_manual_prices=row.reset_manual_prices,
                delay_repricing_new_stage=row.delay_repricing_new_stage,
                check_price_rule_before_sale=row.check_price_rule_before_sale,
                check_open_tasks=row.check_open_tasks,
                markup_base=row.markup_base,
                markup_kor=row.markup_kor,
                markup_rdo=row.markup_rdo,
                markup_test=row.markup_test,
                markup_txt=row.markup_txt,
                calc_by_days_in_sale=row.calc_by_days_in_sale,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('refs', '0135_refstatusavailability_refstatusransom_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='refgroupprice',
            name='code',
            field=models.CharField(blank=True, db_index=True, default='', max_length=10, verbose_name='Код ЦГ'),
        ),
        migrations.AddField(
            model_name='refgroupprice',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Активна'),
        ),
        migrations.AddField(
            model_name='refgroupprice',
            name='label_1c',
            field=models.CharField(blank=True, default='', max_length=20, verbose_name='Наименование для 1С'),
        ),
        migrations.AddField(
            model_name='refgroupprice',
            name='max_price_rub',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Макс. цена, руб'),
        ),
        migrations.AddField(
            model_name='refgroupprice',
            name='min_price_rub',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Мин. цена, руб'),
        ),
        migrations.AddField(
            model_name='refgroupprice',
            name='sort_order',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Порядок'),
        ),
        migrations.AlterModelOptions(
            name='refgroupprice',
            options={'ordering': ['sort_order', 'code', 'name'], 'verbose_name': 'Ценовая категория', 'verbose_name_plural': 'Ценовые категории'},
        ),
        migrations.CreateModel(
            name='UnitPriceGroupSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Дата создания')),
                ('ratio_1c_test_price', models.FloatField(blank=True, default=0.0, null=True, verbose_name='ИРЦ Тест прайс 1С')),
                ('ratio_1c_rdo', models.FloatField(blank=True, default=0.0, null=True, verbose_name='ИРЦ РДО 1С')),
                ('ratio_1c_kor', models.FloatField(blank=True, default=0.0, null=True, verbose_name='ИРЦ коррекция 1С')),
                ('ratio_1c_txt', models.FloatField(blank=True, default=0.0, null=True, verbose_name='ИРЦ ТХТ 1С')),
                ('ratio_avtohub_test_price', models.FloatField(blank=True, default=0.0, null=True, verbose_name='ИРЦ Автохаб Тест прайс')),
                ('ratio_avtohub_rdo', models.FloatField(blank=True, default=0.0, null=True, verbose_name='ИРЦ Автохаб РДО')),
                ('ratio_avtohub_kor', models.FloatField(blank=True, default=0.0, null=True, verbose_name='ИРЦ Автохаб коррекция')),
                ('ratio_avtohub_txt', models.FloatField(blank=True, default=0.0, null=True, verbose_name='ИРЦ Автохаб ТХТ')),
                ('percent_txt', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Процент наценки к СС ТХТ')),
                ('percent_torg_txt', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Процент наценки торг к СС ТХТ')),
                ('discount_tt', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Скидка Trade-In')),
                ('discount_torg', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Скидка торг')),
                ('auto_strategy', models.BooleanField(default=False, verbose_name='Автостратегия цены')),
                ('auto_active', models.BooleanField(default=False, verbose_name='Активна')),
                ('autohub_mode_kor', models.CharField(blank=True, choices=[('ПЦП', 'ПЦП'), ('ЦНА', 'ЦНА'), ('АвитоОценка', 'АвитоОценка')], default='', max_length=20, verbose_name='Вариант использования Автохаб Коррекция')),
                ('autohub_mode_rdo', models.CharField(blank=True, choices=[('ПЦП', 'ПЦП'), ('ЦНА', 'ЦНА'), ('АвитоОценка', 'АвитоОценка')], default='', max_length=20, verbose_name='Вариант использования Автохаб РДО')),
                ('autohub_mode_test', models.CharField(blank=True, choices=[('ПЦП', 'ПЦП'), ('ЦНА', 'ЦНА'), ('АвитоОценка', 'АвитоОценка')], default='', max_length=20, verbose_name='Вариант использования Автохаб Тест прайс')),
                ('autohub_mode_txt', models.CharField(blank=True, choices=[('ПЦП', 'ПЦП'), ('ЦНА', 'ЦНА'), ('АвитоОценка', 'АвитоОценка')], default='', max_length=20, verbose_name='Вариант использования Автохаб ТХТ')),
                ('lock_eval_change_after_stage', models.BooleanField(default=False, verbose_name='Запрет изменения варианта управления ценой после перехода на новый этап')),
                ('deny_manual_price', models.BooleanField(default=False, verbose_name='Запрет на ручной ввод')),
                ('deny_discount', models.BooleanField(default=False, verbose_name='Запрет скидки')),
                ('correction_kor', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Корректировка Коррекция')),
                ('correction_kor_1c', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Корректировка Коррекция 1С')),
                ('correction_kor_express', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Корректировка Коррекция Экспресс')),
                ('correction_rdo', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Корректировка РДО')),
                ('correction_rdo_1c', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Корректировка РДО 1С')),
                ('correction_rdo_express', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Корректировка РДО Экспресс')),
                ('correction_test', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Корректировка Тест прайс')),
                ('correction_test_1c', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Корректировка Тест прайс 1С')),
                ('correction_test_express', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Корректировка Тест прайс Экспресс')),
                ('correction_txt', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Корректировка ТХТ')),
                ('correction_txt_1c', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Корректировка ТХТ 1С')),
                ('correction_txt_express', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Корректировка ТХТ Экспресс')),
                ('max_discount_tradein', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Максимальная скидка за TradeIn')),
                ('max_discount_bargain_percent', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Максимальная скидка торг в процентах')),
                ('marketing', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Маркетинг')),
                ('no_limit_max_manual', models.BooleanField(default=False, verbose_name='Не ограничивать максимальную ручную цену стратегией')),
                ('reset_manual_prices', models.BooleanField(default=False, verbose_name='Обнуление ручных цен')),
                ('delay_repricing_new_stage', models.BooleanField(default=False, verbose_name='Отсрочка переоценки в новом этапе')),
                ('check_price_rule_before_sale', models.BooleanField(default=False, verbose_name='Проверка выполнения ценового правила при продаже')),
                ('check_open_tasks', models.BooleanField(default=False, verbose_name='Проверка не закрытых задач')),
                ('markup_base', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Процент наценки')),
                ('markup_kor', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Процент наценки Коррекция')),
                ('markup_rdo', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Процент наценки РДО')),
                ('markup_test', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Процент наценки Тест прайс')),
                ('markup_txt', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Процент наценки ТХТ')),
                ('calc_by_days_in_sale', models.BooleanField(default=False, verbose_name='Расчет по дням в продаже')),
                ('eval_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='refs.reftypeevaluationcarsorganization', verbose_name='Выводить в продажу по правилу')),
                ('price_group', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='unit_settings', to='refs.refgroupprice', verbose_name='Ценовая группа')),
                ('unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='price_group_settings', to='refs.refunit', verbose_name='Подразделение')),
            ],
            options={
                'verbose_name': 'Настройки ДЦ по ценовой группе',
                'verbose_name_plural': 'Настройки ДЦ по ценовым группам',
                'db_table': 'unitPriceGroupSettings',
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='unitpricegroupsettings',
            index=models.Index(fields=['unit', 'price_group', '-created_at'], name='unitPriceGr_unit_id_7a8f2d_idx'),
        ),
        migrations.RunPython(seed_price_groups_and_migrate_settings, migrations.RunPython.noop),
    ]
