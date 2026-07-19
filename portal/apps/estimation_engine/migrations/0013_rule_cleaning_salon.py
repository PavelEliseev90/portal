from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estimation_engine', '0012_package_estimation_reduction'),
    ]

    operations = [
        migrations.AddField(
            model_name='estimationrule',
            name='cleaning_level',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', 'Любая'),
                    ('0', 'Не требуется'),
                    ('3', 'Лёгкая'),
                    ('2', 'Средняя'),
                    ('1', 'Сложная'),
                ],
                default='',
                help_text='Как cleaning_int в осмотре салона. Пусто = не учитывать.',
                max_length=8,
                verbose_name='Степень химчистки',
            ),
        ),
        migrations.AddField(
            model_name='estimationrule',
            name='salon_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', 'Любой'),
                    ('0', 'Ткань'),
                    ('1', 'Кожа'),
                ],
                default='',
                help_text='Как type_salon_int: 0 — ткань, 1 — кожа. Пусто = не учитывать.',
                max_length=8,
                verbose_name='Вариант салона',
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
                ],
                default='damage_type_count',
                max_length=32,
                verbose_name='Поле',
            ),
        ),
    ]
