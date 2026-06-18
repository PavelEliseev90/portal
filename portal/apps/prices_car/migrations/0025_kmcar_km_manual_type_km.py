from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0024_carcalculations_soglasovanie_rejected'),
    ]

    operations = [
        migrations.AddField(
            model_name='kmcar',
            name='km_manual',
            field=models.IntegerField(
                blank=True,
                default=0,
                null=True,
                verbose_name='КМ ручной (min_km)',
            ),
        ),
        migrations.AddField(
            model_name='kmcar',
            name='type_km',
            field=models.SmallIntegerField(
                blank=True,
                default=0,
                null=True,
                verbose_name='Тип итогового КМ',
            ),
        ),
    ]
