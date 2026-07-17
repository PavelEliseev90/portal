from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('estimation_engine', '0003_plan_package_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='preparationworkpackageline',
            name='unit_cost',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Временная цена до версионных прайсов. Для WORK обычно 0 — считается через ставку н/ч правила.',
                max_digits=14,
                verbose_name='Цена единицы (MVP)',
            ),
        ),
        migrations.CreateModel(
            name='EstimationRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('code', models.CharField(max_length=64, unique=True, verbose_name='Код')),
                ('name', models.CharField(max_length=512, verbose_name='Наименование')),
                ('description', models.TextField(blank=True, default='', verbose_name='Описание')),
                ('status', models.CharField(choices=[('draft', 'Черновик'), ('published', 'Опубликовано'), ('archived', 'Архив')], db_index=True, default='draft', max_length=16, verbose_name='Статус')),
                ('priority', models.PositiveIntegerField(default=100, help_text='Больше = важнее. При конфликте exclusive_group побеждает больший приоритет.', verbose_name='Приоритет')),
                ('exclusive_group', models.CharField(blank=True, db_index=True, default='', help_text='В одной группе срабатывает только одно правило (с макс. приоритетом).', max_length=64, verbose_name='Группа взаимоисключения')),
                ('section', models.CharField(blank=True, choices=[('', 'Любой раздел'), ('exterior', 'Внешний осмотр'), ('interior', 'Внутренний осмотр'), ('diagnostic', 'Диагностика'), ('common', 'Общий')], default='', max_length=32, verbose_name='Раздел осмотра')),
                ('element_code', models.CharField(blank=True, default='', help_text='Например: wing_fl, bumper_front', max_length=64, verbose_name='Код элемента')),
                ('damage_type', models.CharField(blank=True, default='', help_text='Например: dent, scratch, paint', max_length=64, verbose_name='Тип повреждения')),
                ('min_damage_count', models.PositiveIntegerField(default=1, verbose_name='Мин. кол-во повреждений')),
                ('body_type', models.CharField(blank=True, default='', max_length=64, verbose_name='Тип кузова')),
                ('price_group', models.CharField(blank=True, default='', help_text='Например: 2000, 4000', max_length=32, verbose_name='Ценовая группа')),
                ('paint_type', models.CharField(blank=True, default='', max_length=64, verbose_name='Тип краски')),
                ('under_instrument', models.BooleanField(default=False, help_text='Если включено — правило срабатывает только при факте under_instrument=true.', verbose_name='Только «под прибор»')),
                ('hour_rate', models.DecimalField(decimal_places=2, default=0, help_text='Для строк WORK в preview: нормочасы × ставка.', max_digits=12, verbose_name='Ставка н/ч, ₽')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Активно')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
            ],
            options={
                'verbose_name': 'Правило подбора пакетов',
                'verbose_name_plural': 'Правила подбора пакетов',
                'db_table': 'ee_estimation_rule',
                'ordering': ['-priority', 'code'],
            },
        ),
        migrations.CreateModel(
            name='EstimationRulePackage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('fixed_cost', models.DecimalField(blank=True, decimal_places=2, help_text='Если задано — в preview берётся эта сумма вместо построчного расчёта.', max_digits=14, null=True, verbose_name='Фикс. стоимость пакета, ₽')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активна')),
                ('package', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='rule_links', to='estimation_engine.preparationworkpackage', verbose_name='Пакет работ')),
                ('rule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rule_packages', to='estimation_engine.estimationrule', verbose_name='Правило')),
            ],
            options={
                'verbose_name': 'Пакет в правиле',
                'verbose_name_plural': 'Пакеты в правилах',
                'db_table': 'ee_estimation_rule_package',
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.AddField(
            model_name='estimationrule',
            name='packages',
            field=models.ManyToManyField(blank=True, related_name='rules', through='estimation_engine.EstimationRulePackage', to='estimation_engine.preparationworkpackage', verbose_name='Пакеты работ'),
        ),
        migrations.AddIndex(
            model_name='estimationrule',
            index=models.Index(fields=['status', 'is_active', 'priority'], name='ee_estimati_status_7a1c01_idx'),
        ),
        migrations.AddIndex(
            model_name='estimationrule',
            index=models.Index(fields=['exclusive_group', 'priority'], name='ee_estimati_exclusi_2b8e44_idx'),
        ),
        migrations.AddIndex(
            model_name='estimationrule',
            index=models.Index(fields=['section', 'element_code', 'damage_type'], name='ee_estimati_section_9d4f12_idx'),
        ),
        migrations.AddConstraint(
            model_name='estimationrulepackage',
            constraint=models.UniqueConstraint(fields=('rule', 'package'), name='ee_rule_package_unique'),
        ),
    ]
