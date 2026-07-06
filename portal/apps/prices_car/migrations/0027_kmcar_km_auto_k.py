from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0026_carcalculations_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='kmcar',
            name='km_auto_k',
            field=models.IntegerField(
                blank=True,
                default=0,
                null=True,
                verbose_name='КМ АвтоК (target cum)',
            ),
        ),
    ]
