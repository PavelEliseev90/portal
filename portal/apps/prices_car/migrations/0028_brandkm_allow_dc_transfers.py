from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0027_kmcar_km_auto_k'),
    ]

    operations = [
        migrations.AddField(
            model_name='brandkm',
            name='allow_dc_transfers',
            field=models.BooleanField(
                default=False,
                help_text='Если включено — при подборе альтернатив с более низким КМ учитываются автомобили всех ДЦ бренда',
                verbose_name='Могут быть перемещения между ДЦ',
            ),
        ),
    ]
