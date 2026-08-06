from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('register', '0234_regestimationrefcarsorganizations_date_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkapriceincreaserequest',
            name='processed_at',
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                null=True,
                verbose_name='Отработано',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenkapriceincreaserequest',
            name='processed_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='eco_price_increase_processed',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Кто отработал',
            ),
        ),
    ]
