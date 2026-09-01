# Generated manually for RegInteractivOcenkaReception.registration_owner_fl

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0252_reception_staff'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='registration_owner_fl',
            field=models.BooleanField(
                blank=True,
                null=True,
                verbose_name='Регистрация собственником ФЛ',
            ),
        ),
    ]
