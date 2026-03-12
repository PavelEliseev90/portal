# Generated manually for control diagnostic test_drive

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0195_control_diagnostic'),
    ]

    operations = [
        migrations.CreateModel(
            name='RegControlDiagnosticTestDrive',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_estimation', models.DateTimeField(blank=True, null=True, verbose_name='Дата начала')),
                ('end_estimation', models.DateTimeField(blank=True, null=True, verbose_name='Дата окончания')),
                ('text_json', models.TextField(blank=True, null=True, verbose_name='Текст')),
                ('engine', models.IntegerField(blank=True, default=10, null=True, verbose_name='Двигатель')),
                ('system_og', models.IntegerField(blank=True, default=10, null=True, verbose_name='Система выпуска ОГ')),
                ('gear', models.IntegerField(blank=True, default=10, null=True, verbose_name='КПП')),
                ('suspension', models.IntegerField(blank=True, default=10, null=True, verbose_name='Подвеска')),
                ('airbag', models.IntegerField(blank=True, default=10, null=True, verbose_name='Подушка безопастности')),
                ('wheel', models.IntegerField(blank=True, default=10, null=True, verbose_name='Рулевое управление')),
                ('brake', models.IntegerField(blank=True, default=10, null=True, verbose_name='Тормозная система')),
                ('subframe', models.IntegerField(blank=True, default=10, null=True, verbose_name='Подрамник')),
                ('conditioner', models.IntegerField(blank=True, default=10, null=True, verbose_name='Кондиционер')),
                ('turbo', models.IntegerField(blank=True, default=10, null=True, verbose_name='Турбина')),
                ('drive', models.IntegerField(blank=True, default=10, null=True, verbose_name='Полный привод')),
                ('to', models.IntegerField(blank=True, default=10, null=True, verbose_name='ТО')),
                ('stapele_type', models.IntegerField(blank=True, null=True, verbose_name='Тип стапеля')),
                ('stapele_hours', models.IntegerField(blank=True, null=True, verbose_name='Часы стапеля')),
                ('stapele_cost', models.IntegerField(blank=True, null=True, verbose_name='Стоимость стапеля')),
                ('comment_engine', models.CharField(blank=True, default='', max_length=512, null=True, verbose_name='Комментарий двигатель')),
                ('comment_system_og', models.CharField(blank=True, default='', max_length=512, null=True, verbose_name='Комментарий система выпуска ОГ')),
                ('comment_gear', models.CharField(blank=True, default='', max_length=512, null=True, verbose_name='Комментарий коробка передач')),
                ('comment_suspension', models.CharField(blank=True, default='', max_length=512, null=True, verbose_name='Комментарий подвеска')),
                ('comment_airbag', models.CharField(blank=True, default='', max_length=512, null=True, verbose_name='Комментарий подушки безопастности')),
                ('airbag_issues', models.CharField(blank=True, default='', max_length=2048, null=True, verbose_name='Проблемы безопасности (JSON)')),
                ('airbag_driver_issue', models.BooleanField(blank=True, default=False, null=True, verbose_name='Проблема: Подушка водителя')),
                ('airbag_passenger_issue', models.BooleanField(blank=True, default=False, null=True, verbose_name='Проблема: Подушка пассажира + перешив торпеды')),
                ('airbag_side_issue', models.BooleanField(blank=True, default=False, null=True, verbose_name='Проблема: Боковые подушки')),
                ('airbag_knee_issue', models.BooleanField(blank=True, default=False, null=True, verbose_name='Проблема: Подушка коленная')),
                ('seat_belt_restore_issue', models.BooleanField(blank=True, default=False, null=True, verbose_name='Проблема: Восстановление ремней безопасности')),
                ('srs_block_issue', models.BooleanField(blank=True, default=False, null=True, verbose_name='Проблема: Блок SRS')),
                ('comment_wheel', models.CharField(blank=True, default='', max_length=512, null=True, verbose_name='Комментарий рулевого управления')),
                ('comment_brake', models.CharField(blank=True, default='', max_length=512, null=True, verbose_name='Комментарий тормозной системы')),
                ('comment_subframe', models.CharField(blank=True, default='', max_length=512, null=True, verbose_name='Комментарий подрамника')),
                ('hood_trunk_shock_absorber', models.IntegerField(blank=True, default=10, null=True, verbose_name='Амортизатор капота/багажника')),
                ('comment_hood_trunk_shock_absorber', models.CharField(blank=True, default='', max_length=512, null=True, verbose_name='Комментарий амортизатор капота/багажника')),
                ('comment_conditioner', models.CharField(blank=True, default='', max_length=512, null=True, verbose_name='Комментарий системы кондиционирования')),
                ('comment_turbo', models.CharField(blank=True, default='', max_length=512, null=True, verbose_name='Комментарий турбокомпрессора')),
                ('comment_drive', models.CharField(blank=True, default='', max_length=512, null=True, verbose_name='Комментарий полный привод')),
                ('pp_dinamyc', models.IntegerField(blank=True, default=10, null=True, verbose_name='Разгонная динамика, посторонние шумы, вибрации при движении')),
                ('pp_kpp', models.IntegerField(blank=True, default=10, null=True, verbose_name='Плавность включения передач')),
                ('pp_uvod', models.IntegerField(blank=True, default=10, null=True, verbose_name='Увод от прямолинейного движения')),
                ('pp_pribor', models.IntegerField(blank=True, default=10, null=True, verbose_name='Работа измерительных приборов и указателей')),
                ('no_test', models.BooleanField(blank=True, default=False, null=True, verbose_name='Тест драйв не производился')),
                ('comment', models.CharField(blank=True, default='', max_length=250, null=True, verbose_name='Комментарий тест - драйва')),
                ('control_diagnostic', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='page_test_drive_copy', to='register.regcontroldiagnostic', verbose_name='Контрольная диагностика')),
            ],
            options={
                'verbose_name': 'КД: тест-драйв',
                'verbose_name_plural': 'КД: тест-драйв',
                'db_table': 'regControlDiagnosticTestDrive',
            },
        ),
        migrations.CreateModel(
            name='RegControlDiagnosticReferenceSelection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category_code', models.CharField(db_index=True, max_length=50, verbose_name='Код категории')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('control_test_drive', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reference_selections', to='register.regcontroldiagnostictestdrive', verbose_name='КД тест-драйв')),
                ('reference_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='control_diagnostic_selections', to='register.diagnosticreferenceitem', verbose_name='Элемент справочника')),
            ],
            options={
                'verbose_name': 'КД: выбор элемента справочника',
                'verbose_name_plural': 'КД: выборы элементов справочника',
                'db_table': 'regControlDiagnosticReferenceSelection',
                'unique_together': {('control_test_drive', 'category_code', 'reference_item')},
            },
        ),
    ]
