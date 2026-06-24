from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0223_express_auction_fields'),
        ('refs', '0140_alter_refib_alfa'),
    ]

    operations = [
        migrations.AddField(
            model_name='auction',
            name='express_source_soglasovanie',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='express_lots',
                to='register.reginteractivocenkasoglasovanie',
                verbose_name='Источник: согласование ЕЦО',
            ),
        ),
    ]
