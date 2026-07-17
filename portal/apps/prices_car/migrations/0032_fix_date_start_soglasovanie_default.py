from django.db import migrations, models


def clear_bogus_date_start_soglasovanie(apps, schema_editor):
    """
    date_start_soglasovanie раньше имел default=now, поэтому при создании КП
    дата всегда заполнялась. Логика submit/prepare воспринимала это как
    «уже отправлено директору» и пропускала чат/email/смену статуса.

    Обнуляем дату у КП, которые ещё не в реальной очереди директора:
    awaiting_1c, либо pending без директора и без писем по этому КП.
    """
    CarCalculations = apps.get_model('prices_car', 'CarCalculations')
    EmailPushCar = apps.get_model('prices_car', 'EmailPushCar')

    calc_ids_with_email = set(
        EmailPushCar.objects.exclude(calc_id=None).values_list('calc_id', flat=True)
    )

    CarCalculations.objects.filter(
        soglasovanie_status='awaiting_1c',
    ).update(date_start_soglasovanie=None)

    pending_qs = CarCalculations.objects.filter(
        soglasovanie_status='pending',
        director_approve_user_id__isnull=True,
    )
    if calc_ids_with_email:
        pending_qs = pending_qs.exclude(pk__in=calc_ids_with_email)
    pending_qs.update(date_start_soglasovanie=None)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0031_carcalculationukapproval'),
    ]

    operations = [
        migrations.AlterField(
            model_name='carcalculations',
            name='date_start_soglasovanie',
            field=models.DateTimeField(
                blank=True,
                default=None,
                help_text='Заполняется при подтверждении отправки на согласование из 1С.',
                null=True,
                verbose_name='Дата начала согласования',
            ),
        ),
        migrations.RunPython(clear_bogus_date_start_soglasovanie, noop_reverse),
    ]
