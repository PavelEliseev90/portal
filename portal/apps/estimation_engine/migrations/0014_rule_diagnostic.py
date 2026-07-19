from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estimation_engine', '0013_rule_cleaning_salon'),
    ]

    operations = [
        migrations.AddField(
            model_name='estimationrule',
            name='diagnostic_system',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', 'Любая система'),
                    ('engine', 'Двигатель'),
                    ('system_og', 'Система выпуска ОГ'),
                    ('gear', 'КПП'),
                    ('suspension', 'Подвеска'),
                    ('conditioner', 'Кондиционер'),
                ],
                default='',
                help_text='Узел из тест-драйва / диагностики. Пусто = не учитывать.',
                max_length=32,
                verbose_name='Система диагностики',
            ),
        ),
        migrations.AddField(
            model_name='estimationrule',
            name='diagnostic_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', 'Любой статус'),
                    ('1', 'Исправен'),
                    ('0', 'Не исправен'),
                    ('2', 'Есть замечания'),
                ],
                default='',
                help_text='0 — не исправен, 1 — исправен, 2 — есть замечания. Имеет смысл вместе с системой.',
                max_length=8,
                verbose_name='Статус диагностики',
            ),
        ),
        migrations.AlterField(
            model_name='estimationrulecondition',
            name='field',
            field=models.CharField(
                choices=[
                    ('damage_type_count', 'Кол-во по типу повреждения'),
                    ('damage_count', 'Кол-во повреждений (всего)'),
                    ('element_code', 'Код элемента'),
                    ('section', 'Раздел'),
                    ('price_group', 'Ценовая группа'),
                    ('body_type', 'Тип кузова'),
                    ('paint_type', 'Тип краски'),
                    ('under_instrument', 'Под прибор'),
                    ('windshield_heat', 'Подогрев лобового'),
                    ('windshield_projection', 'Проекция на лобовое'),
                    ('cleaning_level', 'Степень химчистки'),
                    ('salon_type', 'Вариант салона'),
                    ('diagnostic_system', 'Система диагностики'),
                    ('diagnostic_status', 'Статус диагностики'),
                ],
                default='damage_type_count',
                max_length=32,
                verbose_name='Поле',
            ),
        ),
    ]
