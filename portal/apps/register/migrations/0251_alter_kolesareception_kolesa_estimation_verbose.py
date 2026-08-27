# Generated manually: fix verbose_name for kolesa_estimation

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0250_kolesareception_route_sheet_and_events'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reginteractivocenkakolesareception',
            name='kolesa_estimation',
            field=models.IntegerField(
                default=10,
                verbose_name='Признак второго комплекта колёс',
            ),
        ),
    ]
