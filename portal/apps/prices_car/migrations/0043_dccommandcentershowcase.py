# Generated manually for DcCommandCenterShowcase (Command Center data mart snapshot)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('refs', '0047_refratingcarsorganization_refstatuscarsorganization_and_more'),
        ('prices_car', '0042_dcmonthlyplan_money_plans'),
    ]

    operations = [
        migrations.CreateModel(
            name='DcCommandCenterShowcase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month', models.DateField(db_index=True, help_text='Первое число месяца, напр. 2026-09-01', verbose_name='Месяц (период)')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Время обновления витрины')),
                ('plan_dc_qty', models.PositiveIntegerField(default=0, verbose_name='План ДЦ, шт.')),
                ('plan_importer_qty', models.PositiveIntegerField(default=0, verbose_name='План импортера, шт.')),
                ('target_plan', models.PositiveIntegerField(default=0, verbose_name='Целевой план (макс), шт.')),
                ('contracts_count', models.PositiveIntegerField(default=0, verbose_name='Фактически законтрактовано, шт.')),
                ('run_rate', models.FloatField(default=0.0, verbose_name='Прогноз выполнения (Run-rate), шт.')),
                ('pace_pct', models.FloatField(default=0.0, verbose_name='Темп выполнения плана, %')),
                ('pace_status', models.CharField(default='no_plan', max_length=32, verbose_name='Статус темпа')),
                ('pace_label', models.CharField(default='План не задан', max_length=64, verbose_name='Подпись темпа')),
                ('pace_class', models.CharField(default='secondary', max_length=32, verbose_name='CSS класс темпа')),
                ('pace_delta_label', models.CharField(default='нет плана', max_length=32, verbose_name='Дельта темпа')),
                ('gap', models.PositiveIntegerField(default=0, verbose_name='Отставание до плана, шт.')),
                ('plan_km_rub', models.BigIntegerField(default=0, verbose_name='План по КМ, ₽')),
                ('plan_revenue_rub', models.BigIntegerField(default=0, verbose_name='План по выручке, ₽')),
                ('fact_km', models.BigIntegerField(default=0, verbose_name='Факт КМ, ₽')),
                ('fact_revenue', models.BigIntegerField(default=0, verbose_name='Факт выручки, ₽')),
                ('km_run_rate', models.BigIntegerField(default=0, verbose_name='Прогноз КМ (Run-rate), ₽')),
                ('km_pace_pct', models.FloatField(default=0.0, verbose_name='Темп выполнения КМ, %')),
                ('quadrant_key', models.CharField(default='no_money_plan', max_length=32, verbose_name='Ключ квадранта')),
                ('quadrant_label', models.CharField(default='План КМ не задан', max_length=64, verbose_name='Название квадранта')),
                ('quadrant_badge_class', models.CharField(default='secondary', max_length=32, verbose_name='CSS класс квадранта')),
                ('quadrant_desc', models.CharField(blank=True, default='', max_length=255, verbose_name='Описание квадранта')),
                ('stock_total', models.PositiveIntegerField(default=0, verbose_name='Всего новых авто на складе')),
                ('yellow_count', models.PositiveIntegerField(default=0, verbose_name='Желтые авто (>45 дн)')),
                ('consignment_overdue', models.PositiveIntegerField(default=0, verbose_name='Просроченная консигнация (>90 дн)')),
                ('consignment_warning', models.PositiveIntegerField(default=0, verbose_name='Подходит срок консигнации (75-90 дн)')),
                ('missed_count', models.PositiveIntegerField(default=0, verbose_name='Упущенные сделки (РЛК/отказы)')),
                ('is_autopilot', models.BooleanField(default=False, verbose_name='Автопилот дисконтов')),
                ('autopilot_rules_count', models.PositiveIntegerField(default=0, verbose_name='Активных правил автопилота')),
                ('tactic', models.CharField(default='balanced', max_length=32, verbose_name='Тактика ДЦ')),
                ('tactic_label', models.CharField(default='Сбалансированная', max_length=64, verbose_name='Название тактики')),
                ('recs_count', models.PositiveIntegerField(default=0, verbose_name='Количество рекомендаций')),
                ('has_recs', models.BooleanField(default=False, verbose_name='Есть рекомендации')),
                ('needs_attention', models.BooleanField(default=False, verbose_name='Требует внимания')),
                ('top_rec_title', models.CharField(blank=True, default='', max_length=255, verbose_name='Заголовок главной рекомендации')),
                ('top_rec_badge', models.CharField(blank=True, default='', max_length=64, verbose_name='Бейдж главной рекомендации')),
                ('top_rec_badge_class', models.CharField(blank=True, default='', max_length=32, verbose_name='CSS класс главной рекомендации')),
                ('recommendations_json', models.JSONField(blank=True, default=list, verbose_name='Рекомендации (JSON)')),
                ('unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='command_center_showcases', to='refs.refunit', verbose_name='Подразделение ДЦ')),
            ],
            options={
                'verbose_name': 'Витрина Центра управления ДЦ',
                'verbose_name_plural': 'Витрины Центра управления ДЦ',
                'db_table': 'prices_car_dc_command_center_showcase',
                'ordering': ['unit__city__name', 'unit__name'],
            },
        ),
        migrations.AddConstraint(
            model_name='dccommandcentershowcase',
            constraint=models.UniqueConstraint(fields=('unit', 'month'), name='prices_car_dc_showcase_unit_month_uniq'),
        ),
    ]
