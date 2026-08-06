from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0022_profiles_eco_chat_important'),
    ]

    operations = [
        migrations.AddField(
            model_name='profiles',
            name='eco_price_increase',
            field=models.BooleanField(
                default=False,
                help_text='Может отмечать «отработано» по запросам повышения в интерактивной оценке',
                verbose_name='Отработка запросов повышения цены',
            ),
        ),
    ]
