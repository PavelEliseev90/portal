# Generated for DocCarShipment cumulative_margin

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0732_alter_doсrecomendation_kod_recomendation'),
    ]

    operations = [
        migrations.AddField(
            model_name='doccarshipment',
            name='cumulative_margin',
            field=models.FloatField(blank=True, null=True, verbose_name='Кумулятивная маржа'),
        ),
    ]
