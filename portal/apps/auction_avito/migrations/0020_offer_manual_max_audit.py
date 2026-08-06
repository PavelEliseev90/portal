from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auction_avito', '0019_venue_unit_and_win_rlk'),
    ]

    operations = [
        migrations.AddField(
            model_name='avitolotoffer',
            name='manual_max_bid_set_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Потолок задан / сброшен',
            ),
        ),
        migrations.AddField(
            model_name='avitolotoffer',
            name='manual_max_bid_set_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='avito_manual_max_offers',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Потолок задал',
            ),
        ),
    ]
