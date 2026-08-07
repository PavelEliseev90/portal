# Generated manually for RegEstimationsSettings.mcu_kf

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0236_reginteractivocenkareception'),
    ]

    operations = [
        migrations.AddField(
            model_name='regestimationssettings',
            name='mcu_kf',
            field=models.FloatField(
                blank=True,
                default=1.0,
                help_text='Применяется ко всем работам кузовного участка. По умолчанию 1.',
                null=True,
                verbose_name='Коэффициент кузовного ремонта',
            ),
        ),
    ]
