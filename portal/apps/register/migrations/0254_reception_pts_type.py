# Generated manually for RegInteractivOcenkaReception PTS type fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0253_reception_registration_owner_fl'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='pts_electronic',
            field=models.BooleanField(
                blank=True,
                null=True,
                verbose_name='Электронный ПТС (ЭПТС)',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='pts_series',
            field=models.CharField(
                blank=True,
                default='',
                max_length=32,
                verbose_name='Серия ПТС',
            ),
        ),
    ]
