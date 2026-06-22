from django.db import migrations, models


def set_latest_active_per_rlk(apps, schema_editor):
    CarCalculations = apps.get_model('prices_car', 'CarCalculations')
    rlk_ids = (
        CarCalculations.objects
        .exclude(rlk_id=None)
        .values_list('rlk_id', flat=True)
        .distinct()
    )
    prefix = 'Неактивно: есть другое активное коммерческое предложение'
    for rlk_id in rlk_ids:
        calcs = list(
            CarCalculations.objects.filter(rlk_id=rlk_id).order_by('-date', '-pk')
        )
        if not calcs:
            continue
        active = calcs[0]
        number = (active.number or '').strip() or '—'
        inactive_reason = '{} №{}.'.format(prefix, number)
        CarCalculations.objects.filter(rlk_id=rlk_id).exclude(pk=active.pk).update(
            active=False,
            inactive_reason=inactive_reason,
        )
        CarCalculations.objects.filter(pk=active.pk).update(active=True, inactive_reason='')


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0025_kmcar_km_manual_type_km'),
    ]

    operations = [
        migrations.AddField(
            model_name='carcalculations',
            name='active',
            field=models.BooleanField(db_index=True, default=True, verbose_name='Активное КП по рабочему листу'),
        ),
        migrations.AddField(
            model_name='carcalculations',
            name='inactive_reason',
            field=models.CharField(blank=True, default='', max_length=512, verbose_name='Причина неактивности'),
        ),
        migrations.RunPython(set_latest_active_per_rlk, migrations.RunPython.noop),
    ]
