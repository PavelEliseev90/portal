# Generated manually for RegInteractivOcenkaReception.agreement_number_op

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0244_reception_amount_vzaimozachet'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='agreement_number_op',
            field=models.CharField(
                blank=True,
                default='',
                max_length=250,
                verbose_name='Номер соглашения ОП',
            ),
        ),
    ]
