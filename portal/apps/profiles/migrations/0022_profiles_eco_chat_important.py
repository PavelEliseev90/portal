from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0021_profiles_price_car_new_director'),
    ]

    operations = [
        migrations.AddField(
            model_name='profiles',
            name='eco_chat_important',
            field=models.BooleanField(
                default=False,
                verbose_name='Важные сообщения в чатах ЕЦО',
            ),
        ),
    ]
