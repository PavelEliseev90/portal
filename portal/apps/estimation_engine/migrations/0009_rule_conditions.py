from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('estimation_engine', '0008_rule_windshield_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='estimationrule',
            name='min_damage_count',
            field=models.PositiveIntegerField(
                default=0,
                help_text='0 = не проверять общий счётчик. Для счётчиков по типам используйте доп. условия.',
                verbose_name='Мин. кол-во повреждений (всего)',
            ),
        ),
        migrations.CreateModel(
            name='EstimationRuleCondition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('join_op', models.CharField(
                    choices=[('and', 'И'), ('or', 'ИЛИ')],
                    default='and',
                    help_text='Для первой строки не используется.',
                    max_length=8,
                    verbose_name='Связка с предыдущим',
                )),
                ('field', models.CharField(
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
                    ],
                    default='damage_type_count',
                    max_length=32,
                    verbose_name='Поле',
                )),
                ('damage_type', models.CharField(blank=True, default='', max_length=64, verbose_name='Код повреждения (кэш)')),
                ('operator', models.CharField(
                    choices=[
                        ('eq', '='),
                        ('ne', '≠'),
                        ('gt', '>'),
                        ('gte', '≥'),
                        ('lt', '<'),
                        ('lte', '≤'),
                        ('absent', 'нет (0 / ложь)'),
                        ('present', 'есть (>0 / истина)'),
                    ],
                    default='gte',
                    max_length=16,
                    verbose_name='Оператор',
                )),
                ('value', models.CharField(
                    blank=True,
                    default='',
                    help_text='Число или текст. Для «нет/есть» можно оставить пустым.',
                    max_length=64,
                    verbose_name='Значение',
                )),
                ('is_active', models.BooleanField(default=True, verbose_name='Активно')),
                ('damage_type_ref', models.ForeignKey(
                    blank=True,
                    help_text='Нужен для поля «Кол-во по типу повреждения».',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='rule_conditions',
                    to='estimation_engine.damagetype',
                    verbose_name='Тип повреждения',
                )),
                ('rule', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='conditions',
                    to='estimation_engine.estimationrule',
                    verbose_name='Правило',
                )),
            ],
            options={
                'verbose_name': 'Условие правила',
                'verbose_name_plural': 'Условия правил',
                'db_table': 'ee_estimation_rule_condition',
                'ordering': ['sort_order', 'id'],
            },
        ),
    ]
