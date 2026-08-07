# Generated manually: unreadable checks on test_drive (not soglasovanie)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0240_soglasovanie_unreadable_checks'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenktestdrive',
            name='unreadable_vin_int',
            field=models.IntegerField(
                blank=True,
                default=10,
                null=True,
                verbose_name='Не читаемый VIN номер',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenktestdrive',
            name='unreadable_engine_num_int',
            field=models.IntegerField(
                blank=True,
                default=10,
                null=True,
                verbose_name='Не читаемый № ДВС',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenktestdrive',
            name='unreadable_rama_int',
            field=models.IntegerField(
                blank=True,
                default=10,
                null=True,
                verbose_name='Не читаемый № рамы',
            ),
        ),
        migrations.AddField(
            model_name='regcontroldiagnostictestdrive',
            name='unreadable_vin_int',
            field=models.IntegerField(
                blank=True,
                default=10,
                null=True,
                verbose_name='Не читаемый VIN номер',
            ),
        ),
        migrations.AddField(
            model_name='regcontroldiagnostictestdrive',
            name='unreadable_engine_num_int',
            field=models.IntegerField(
                blank=True,
                default=10,
                null=True,
                verbose_name='Не читаемый № ДВС',
            ),
        ),
        migrations.AddField(
            model_name='regcontroldiagnostictestdrive',
            name='unreadable_rama_int',
            field=models.IntegerField(
                blank=True,
                default=10,
                null=True,
                verbose_name='Не читаемый № рамы',
            ),
        ),
        migrations.RemoveField(
            model_name='reginteractivocenkasoglasovanie',
            name='unreadable_vin_int',
        ),
        migrations.RemoveField(
            model_name='reginteractivocenkasoglasovanie',
            name='unreadable_engine_num_int',
        ),
        migrations.RemoveField(
            model_name='reginteractivocenkasoglasovanie',
            name='unreadable_rama_int',
        ),
    ]
