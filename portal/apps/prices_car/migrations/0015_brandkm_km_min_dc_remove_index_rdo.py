from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0014_alter_carcalculations_car'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='brandkm',
            name='km_index_rdo',
        ),
        migrations.AddField(
            model_name='brandkm',
            name='km_min_dc',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Минимальное значение кумулятивной маржи ДЦ',
                verbose_name='Минимальное значение кумулятивной маржи ДЦ',
            ),
        ),
    ]
