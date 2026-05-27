from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('refs', '0124_refcarsorganizationfiles_date'),
        ('avtosalon', '0023_rename_sms_auth_se_phone_n_a994ea_idx_sms_auth_se_phone_n_285a1d_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CarsOrganizationEquipment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_update', models.DateTimeField(auto_now=True, verbose_name='Дата изменения')),
                ('car', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='equipment_selections', to='refs.refcarsorganization', verbose_name='Автомобиль')),
                ('option', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='car_selections', to='avtosalon.avtohuboptions', verbose_name='Опция')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Опция автомобиля',
                'verbose_name_plural': 'Опции автомобилей',
                'db_table': 'carsOrganizationEquipment',
            },
        ),
        migrations.AddConstraint(
            model_name='carsorganizationequipment',
            constraint=models.UniqueConstraint(fields=('car', 'option'), name='cars_org_equipment_car_option_uniq'),
        ),
    ]
