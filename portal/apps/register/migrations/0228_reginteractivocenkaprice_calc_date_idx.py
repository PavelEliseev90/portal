# Generated manually for price recalc history report speedup

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0227_regestimationssettings_iznos_with_ss'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='reginteractivocenkaprice',
            index=models.Index(fields=['price_calculation', 'date'], name='regInteract_price_c_autohub_idx'),
        ),
    ]
