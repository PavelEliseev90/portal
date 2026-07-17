from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def seed_damage_types(apps, schema_editor):
    DamageType = apps.get_model('estimation_engine', 'DamageType')
    rows = [
        ('dent', 'Вмятина', 'вмятина', 1, 10),
        ('dent_strong', 'Вмятина сильная', 'вмятина сильная', 2, 20),
        ('scratch', 'Царапина', 'царапина', 1, 30),
        ('scratch_strong', 'Царапина сильная', 'царапина сильная', 2, 40),
        ('rust', 'Ржавчина', 'ржавчина', 2, 50),
        ('rust_through', 'Ржавчина сквозная', 'ржавчина сквозная', 3, 60),
        ('paint', 'Покраска / скол ЛКП', 'окрас', 1, 70),
        ('chip', 'Скол', 'скол', 1, 80),
        ('crack', 'Трещина', 'трещина', 2, 90),
        ('replace', 'Замена элемента', 'замена', 3, 100),
    ]
    for code, name, legacy, severity, order in rows:
        DamageType.objects.update_or_create(
            code=code,
            defaults={
                'name': name,
                'legacy_label': legacy,
                'severity': severity,
                'sort_order': order,
                'is_active': True,
            },
        )


def unseed_damage_types(apps, schema_editor):
    DamageType = apps.get_model('estimation_engine', 'DamageType')
    DamageType.objects.filter(code__in=[
        'dent', 'dent_strong', 'scratch', 'scratch_strong',
        'rust', 'rust_through', 'paint', 'chip', 'crack', 'replace',
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('estimation_engine', '0004_estimation_rules_mvp'),
        ('register', '0211_alter_reginfobody_polygon'),
    ]

    operations = [
        migrations.CreateModel(
            name='SchemeElement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('code', models.CharField(max_length=64, unique=True, verbose_name='Код')),
                ('name', models.CharField(max_length=256, verbose_name='Наименование')),
                ('section', models.CharField(choices=[('exterior', 'Внешний осмотр'), ('interior', 'Внутренний осмотр'), ('diagnostic', 'Диагностика'), ('common', 'Общий')], db_index=True, default='exterior', max_length=32, verbose_name='Раздел')),
                ('description', models.CharField(blank=True, default='', max_length=512, verbose_name='Описание')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Активен')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
            ],
            options={
                'verbose_name': 'Элемент схемы',
                'verbose_name_plural': 'Элементы схемы',
                'db_table': 'ee_scheme_element',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='DamageType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('code', models.CharField(max_length=64, unique=True, verbose_name='Код')),
                ('name', models.CharField(max_length=128, verbose_name='Наименование')),
                ('legacy_label', models.CharField(blank=True, default='', help_text='Как называется в текущем UI осмотра, например «вмятина сильная».', max_length=128, verbose_name='Метка в legacy-оценке')),
                ('severity', models.PositiveSmallIntegerField(default=1, help_text='1 — лёгкая, выше — тяжелее', verbose_name='Тяжесть')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Активен')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
            ],
            options={
                'verbose_name': 'Тип повреждения',
                'verbose_name_plural': 'Типы повреждений',
                'db_table': 'ee_damage_type',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='SchemeElementPolygon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активна')),
                ('element', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='polygons', to='estimation_engine.schemeelement', verbose_name='Элемент')),
                ('info_body', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scheme_element_links', to='register.reginfobody', verbose_name='Полигон (RegInfoBody)')),
            ],
            options={
                'verbose_name': 'Полигон элемента',
                'verbose_name_plural': 'Полигоны элементов',
                'db_table': 'ee_scheme_element_polygon',
            },
        ),
        migrations.AddField(
            model_name='estimationrule',
            name='element',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rules', to='estimation_engine.schemeelement', verbose_name='Элемент схемы'),
        ),
        migrations.AddField(
            model_name='estimationrule',
            name='damage_type_ref',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rules', to='estimation_engine.damagetype', verbose_name='Тип повреждения'),
        ),
        migrations.AlterField(
            model_name='estimationrule',
            name='element_code',
            field=models.CharField(blank=True, default='', help_text='Заполняется из справочника; можно оставить пустым = любой элемент.', max_length=64, verbose_name='Код элемента (кэш)'),
        ),
        migrations.AlterField(
            model_name='estimationrule',
            name='damage_type',
            field=models.CharField(blank=True, default='', help_text='Заполняется из справочника.', max_length=64, verbose_name='Код повреждения (кэш)'),
        ),
        migrations.AddConstraint(
            model_name='schemeelementpolygon',
            constraint=models.UniqueConstraint(fields=('element', 'info_body'), name='ee_element_polygon_unique'),
        ),
        migrations.RunPython(seed_damage_types, unseed_damage_types),
    ]
