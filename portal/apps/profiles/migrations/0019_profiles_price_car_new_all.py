from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0018_profiles_available_units'),
    ]

    operations = [
        migrations.AddField(
            model_name='profiles',
            name='price_car_new_all',
            field=models.BooleanField(
                default=False,
                verbose_name='Ценообразование новых всех ДЦ',
            ),
        ),
    ]
