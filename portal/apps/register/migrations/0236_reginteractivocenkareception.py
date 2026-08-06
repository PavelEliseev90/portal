# Generated manually for RegInteractivOcenkaReception

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('register', '0235_price_increase_processed'),
        ('refs', '0144_pricegroupstagedays'),
    ]

    operations = [
        migrations.CreateModel(
            name='RegInteractivOcenkaReception',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('sent_to_1c_at', models.DateTimeField(blank=True, null=True, verbose_name='Отправлено в 1С')),
                ('sent_to_1c_status', models.CharField(blank=True, default='', max_length=250, verbose_name='Статус отправки в 1С')),
                ('customer_family', models.CharField(blank=True, default='', max_length=250, verbose_name='Фамилия')),
                ('customer_name', models.CharField(blank=True, default='', max_length=250, verbose_name='Имя')),
                ('customer_patronymic', models.CharField(blank=True, default='', max_length=250, verbose_name='Отчество')),
                ('customer_phone', models.CharField(blank=True, default='', max_length=250, verbose_name='Телефон')),
                ('vin', models.CharField(blank=True, default='', max_length=32, verbose_name='VIN')),
                ('vin2', models.CharField(blank=True, default='', max_length=32, verbose_name='VIN 2')),
                ('mark', models.CharField(blank=True, default='', max_length=250, verbose_name='Марка')),
                ('model', models.CharField(blank=True, default='', max_length=250, verbose_name='Модель')),
                ('year', models.IntegerField(blank=True, default=0, null=True, verbose_name='Год выпуска')),
                ('mileage', models.IntegerField(blank=True, default=0, null=True, verbose_name='Пробег')),
                ('pts_mark_model', models.CharField(blank=True, default='', max_length=250, verbose_name='Марка, модель по ПТС')),
                ('plate_number', models.CharField(blank=True, default='', max_length=32, verbose_name='Госномер')),
                ('count_owners', models.IntegerField(blank=True, default=0, null=True, verbose_name='Количество владельцев')),
                ('count_keys', models.IntegerField(blank=True, default=0, null=True, verbose_name='Количество ключей')),
                ('chassis_number', models.CharField(blank=True, default='', max_length=64, verbose_name='Номер шасси / рамы')),
                ('pts_number', models.CharField(blank=True, default='', max_length=250, verbose_name='Номер ПТС')),
                ('pts_date', models.DateField(blank=True, null=True, verbose_name='Дата выдачи ПТС')),
                ('pts_org_address', models.CharField(blank=True, default='', max_length=512, verbose_name='Адрес организации ПТС')),
                ('sts_number', models.CharField(blank=True, default='', max_length=250, verbose_name='СТС номер')),
                ('sts_date', models.DateField(blank=True, null=True, verbose_name='СТС дата')),
                ('pts_original', models.BooleanField(default=False, verbose_name='ПТС оригинал')),
                ('pts_org_issuer', models.CharField(blank=True, default='', max_length=512, verbose_name='Организация, выдавшая ПТС')),
                ('salon_color', models.CharField(blank=True, default='', max_length=150, verbose_name='Цвет салона')),
                ('body_color', models.CharField(blank=True, default='', max_length=150, verbose_name='Цвет кузова')),
                ('engine_number', models.CharField(blank=True, default='', max_length=64, verbose_name='Номер двигателя')),
                ('mass', models.IntegerField(blank=True, default=0, null=True, verbose_name='Масса')),
                ('max_mass', models.IntegerField(blank=True, default=0, null=True, verbose_name='Макс. масса')),
                ('eco_class', models.CharField(blank=True, default='', max_length=64, verbose_name='Экокласс')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='eco_receptions_created', to=settings.AUTH_USER_MODEL, verbose_name='Кто создал')),
                ('filial', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='refs.reffilial', verbose_name='Филиал')),
                ('interactiv_rlk', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='page_reception', to='register.reginteractivocenkarlk', verbose_name='Интерактивная оценка (РЛК)')),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='refs.reforganization', verbose_name='Организация')),
                ('store', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='refs.refstore', verbose_name='Склад поступления')),
                ('type_reception', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='refs.reftypereceptioncarsorganization', verbose_name='Тип приёма автомобиля')),
                ('unit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='refs.refunit', verbose_name='Подразделение')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='eco_receptions_updated', to=settings.AUTH_USER_MODEL, verbose_name='Кто обновил')),
            ],
            options={
                'verbose_name': 'Приём автомобиля (интерактивная оценка)',
                'verbose_name_plural': 'Приёмы автомобилей (интерактивная оценка)',
                'db_table': 'regInteractivOcenkaReception',
                'ordering': ['-created_at'],
            },
        ),
    ]
