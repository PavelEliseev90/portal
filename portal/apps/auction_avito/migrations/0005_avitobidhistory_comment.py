from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auction_avito', '0004_avitovenue_city_refcity'),
    ]

    operations = [
        migrations.AddField(
            model_name='avitobidhistory',
            name='comment',
            field=models.TextField(blank=True, default='', verbose_name='Комментарий'),
        ),
    ]
