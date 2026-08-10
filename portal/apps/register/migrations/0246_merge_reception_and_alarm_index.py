# Merge parallel leaves: alarm index rename + reception fields

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0244_rename_reginteractiv_active_due_idx_reginteract_active_f27cd6_idx_and_more'),
        ('register', '0245_reception_agreement_number_op'),
    ]

    operations = []
