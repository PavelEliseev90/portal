from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('refs', '0136_refgroupprice_metadata_unitpricegroupsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='auction',
            name='is_express',
            field=models.BooleanField(blank=True, default=False, verbose_name='Экспресс-лот'),
        ),
    ]
