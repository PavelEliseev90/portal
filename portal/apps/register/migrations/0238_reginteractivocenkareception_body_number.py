# Generated manually for RegInteractivOcenkaReception.body_number

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0237_regestimationssettings_mcu_kf'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='body_number',
            field=models.CharField(
                blank=True,
                default='',
                max_length=64,
                verbose_name='Номер кузова',
            ),
        ),
    ]
