# Generated manually

import django.db.models.deletion
from django.db import migrations, models


def migrate_venue_city_to_refcity(apps, schema_editor):
    AvitoVenue = apps.get_model('auction_avito', 'AvitoVenue')
    RefCity = apps.get_model('refs', 'RefCity')
    for venue in AvitoVenue.objects.all().iterator():
        old_name = (getattr(venue, 'city', None) or '').strip()
        if not old_name:
            continue
        ref_city = RefCity.objects.filter(name__iexact=old_name).first()
        if ref_city:
            venue.ref_city_id = ref_city.pk
            venue.save(update_fields=['ref_city_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('refs', '0132_refcarsorganizationaction'),
        ('auction_avito', '0003_avitovenue_avitolot_venue'),
    ]

    operations = [
        migrations.AddField(
            model_name='avitovenue',
            name='ref_city',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='avito_venues',
                to='refs.refcity',
                verbose_name='Город',
            ),
        ),
        migrations.RunPython(migrate_venue_city_to_refcity, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='avitovenue',
            name='city',
        ),
        migrations.RenameField(
            model_name='avitovenue',
            old_name='ref_city',
            new_name='city',
        ),
        migrations.AlterModelOptions(
            name='avitovenue',
            options={
                'ordering': ['city__name', 'name', 'dealer_id'],
                'verbose_name': 'Площадка Авито',
                'verbose_name_plural': 'Площадки Авито',
            },
        ),
    ]
