# Generated manually

from django.db import migrations, models
from django.db.models import Q


def mark_vtd_reception_types(apps, schema_editor):
    RefType = apps.get_model('refs', 'RefTypeReceptionCarsOrganization')
    qs = RefType.objects.filter(
        Q(name__icontains='б/у на б/у')
        | Q(name__icontains='бу на бу')
        | Q(name__icontains='б.у. на б.у')
        | Q(name__icontains='б.у на б.у')
        | Q(name__icontains='bu на bu')
        | Q(name__icontains='trade-in б/у')
        | Q(name__icontains='trade in б/у')
        | Q(name__icontains='трейд-ин б/у')
        | Q(name__icontains='трейд ин б/у')
    )
    qs.update(is_vtd=True)


def unmark_vtd_reception_types(apps, schema_editor):
    RefType = apps.get_model('refs', 'RefTypeReceptionCarsOrganization')
    RefType.objects.filter(is_vtd=True).update(is_vtd=False)


class Migration(migrations.Migration):

    dependencies = [
        ('refs', '0145_refunit_alfa_auto_transition_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='reftypereceptioncarsorganization',
            name='is_vtd',
            field=models.BooleanField(
                default=False,
                help_text='Трейд-ин б/у на б/у. Используется в отчёте кумулятивной маржи.',
                verbose_name='ВТД',
            ),
        ),
        migrations.RunPython(mark_vtd_reception_types, unmark_vtd_reception_types),
    ]
