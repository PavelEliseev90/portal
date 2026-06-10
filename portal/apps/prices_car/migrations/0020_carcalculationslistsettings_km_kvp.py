from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0019_kmcar_km_auto_3'),
    ]

    operations = [
        migrations.AddField(
            model_name='carcalculationslistsettings',
            name='compare_km_kvp',
            field=models.BooleanField(default=False, verbose_name='Сравнивать расчетный КМ с КВ'),
        ),
        migrations.AddField(
            model_name='carcalculationslistsettings',
            name='highlight_km_below_kvp',
            field=models.BooleanField(
                default=True,
                verbose_name='Подсвечивать строки, где расчетный КМ ниже КВ',
            ),
        ),
    ]
