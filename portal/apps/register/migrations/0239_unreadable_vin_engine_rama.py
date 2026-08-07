# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0238_reginteractivocenkareception_body_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='regestimationssettings',
            name='unreadable_vin_kf',
            field=models.FloatField(
                blank=True,
                default=0.0,
                null=True,
                verbose_name='Коэффициент нечитаемого VIN, %',
            ),
        ),
        migrations.AddField(
            model_name='regestimationssettings',
            name='unreadable_engine_num_kf',
            field=models.FloatField(
                blank=True,
                default=0.0,
                null=True,
                verbose_name='Коэффициент нечитаемого № ДВС, %',
            ),
        ),
        migrations.AddField(
            model_name='regestimationssettings',
            name='unreadable_rama_kf',
            field=models.FloatField(
                blank=True,
                default=0.0,
                null=True,
                verbose_name='Коэффициент нечитаемого № рамы, %',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenkavnesh',
            name='unreadable_vin_int',
            field=models.IntegerField(
                blank=True,
                default=10,
                null=True,
                verbose_name='Не читаемый VIN номер',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenkavnesh',
            name='unreadable_engine_num_int',
            field=models.IntegerField(
                blank=True,
                default=10,
                null=True,
                verbose_name='Не читаемый № ДВС',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenkavnesh',
            name='unreadable_rama_int',
            field=models.IntegerField(
                blank=True,
                default=10,
                null=True,
                verbose_name='Не читаемый № рамы',
            ),
        ),
        migrations.AddField(
            model_name='regcontroldiagnosticvnesh',
            name='unreadable_vin_int',
            field=models.IntegerField(
                blank=True,
                default=10,
                null=True,
                verbose_name='Не читаемый VIN номер',
            ),
        ),
        migrations.AddField(
            model_name='regcontroldiagnosticvnesh',
            name='unreadable_engine_num_int',
            field=models.IntegerField(
                blank=True,
                default=10,
                null=True,
                verbose_name='Не читаемый № ДВС',
            ),
        ),
        migrations.AddField(
            model_name='regcontroldiagnosticvnesh',
            name='unreadable_rama_int',
            field=models.IntegerField(
                blank=True,
                default=10,
                null=True,
                verbose_name='Не читаемый № рамы',
            ),
        ),
    ]
