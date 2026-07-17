# Merge parallel leaves:
# - 0008_alter_preparationworkpackage_options_and_more (from 0007)
# - 0010_rule_body_types_m2m (via 0008_rule_windshield → 0009 → 0010)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('estimation_engine', '0008_alter_preparationworkpackage_options_and_more'),
        ('estimation_engine', '0010_rule_body_types_m2m'),
    ]

    operations = []
