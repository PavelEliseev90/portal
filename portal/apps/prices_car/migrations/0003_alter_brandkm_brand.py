# BrandKM.brand: FK from AutoruMark to PriceCarBrand

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0002_pricecarbrand'),
    ]

    operations = [
        migrations.AlterField(
            model_name='brandkm',
            name='brand',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='km_values',
                to='prices_car.pricecarbrand',
                verbose_name='Бренд',
            ),
        ),
    ]
