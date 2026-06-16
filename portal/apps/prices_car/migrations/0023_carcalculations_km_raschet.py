from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0022_carcalculations_soglasovanie'),
    ]

    operations = [
        migrations.AddField(
            model_name='carcalculations',
            name='km_raschet',
            field=models.IntegerField(
                blank=True,
                null=True,
                verbose_name='Расчетный КМ',
            ),
        ),
    ]
