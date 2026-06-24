from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('refs', '0139_auction_is_express'),
        ('register', '0222_alter_reginteractivocenkaprice_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkasoglasovanie',
            name='auction_client_price',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Цена клиента (экспресс-аукцион)'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkasoglasovanie',
            name='auction_start_price',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Стартовая цена аукцион'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkasoglasovanie',
            name='express_auction',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='express_estimations',
                to='refs.auction',
                verbose_name='Экспресс-лот аукциона',
            ),
        ),
    ]
