# Generated manually for Autohub ZG analytics performance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0233_price_increase_request'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='regestimationrefcarsorganizations',
            index=models.Index(fields=['date'], name='regestimati_date_autohub_idx'),
        ),
    ]
