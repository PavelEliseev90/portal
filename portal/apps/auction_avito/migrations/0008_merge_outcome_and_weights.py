# Merge: веса настроек + итоги лотов / win emails

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auction_avito', '0007_alter_avitoauctionsettings_weight_kor_and_more'),
        ('auction_avito', '0007_offer_outcome_and_win_emails'),
    ]

    operations = []
