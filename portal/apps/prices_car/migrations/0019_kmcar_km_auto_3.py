from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0018_kmcar'),
    ]

    operations = [
        migrations.AddField(
            model_name='kmcar',
            name='km_auto_3',
            field=models.IntegerField(
                blank=True,
                default=0,
                null=True,
                verbose_name='КМ автомобиля спец. условие',
            ),
        ),
    ]
