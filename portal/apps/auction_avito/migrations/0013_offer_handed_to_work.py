# Generated manually for monitor «Выигранные» / передан в работу

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auction_avito', '0012_merge_manual_max_and_autobid_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='avitolotoffer',
            name='handed_to_work_at',
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text='Когда выигранный лот отметили как переданный в работу (убирается из монитора «Выигранные»).',
                null=True,
                verbose_name='Передан в работу',
            ),
        ),
        migrations.AddField(
            model_name='avitolotoffer',
            name='handed_to_work_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='avito_handed_to_work_offers',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Перенёс в работу',
            ),
        ),
    ]
