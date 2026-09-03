# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0256_reception_customer_tax_bank'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='actual_reception_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Дата и время фактического приёма автомобиля',
                null=True,
                verbose_name='Фактическая дата приёма автомобиля',
            ),
        ),
    ]
