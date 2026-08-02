# Generated manually: speedup price recalc history by estimation

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0230_merge_20260802_iznos_and_no_auto_status'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='reginteractivocenkaprice',
            index=models.Index(
                fields=['price_calculation', 'estimation', 'date', 'id'],
                name='regInteract_pc_est_date_idx',
            ),
        ),
    ]
