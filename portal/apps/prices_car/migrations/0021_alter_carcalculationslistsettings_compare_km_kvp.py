from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0020_carcalculationslistsettings_km_kvp'),
    ]

    operations = [
        migrations.AlterField(
            model_name='carcalculationslistsettings',
            name='compare_km_kvp',
            field=models.BooleanField(
                default=True,
                verbose_name='Сравнивать расчетный КМ с КВ',
            ),
        ),
    ]
