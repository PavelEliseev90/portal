from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_manual_uk_approvals(apps, schema_editor):
    CarCalculations = apps.get_model('prices_car', 'CarCalculations')
    CarCalculationUkApproval = apps.get_model(
        'prices_car', 'CarCalculationUkApproval',
    )

    calculations = CarCalculations.objects.filter(
        soglasovanie_status='uk_approved',
        rlk_id__isnull=False,
        car_id__isnull=False,
        kvp__gt=0,
    ).iterator()
    for calc in calculations:
        approval, _ = CarCalculationUkApproval.objects.get_or_create(
            calculation_id=calc.pk,
            defaults={
                'rlk_id': calc.rlk_id,
                'car_id': calc.car_id,
                'approved_kvp': int(calc.kvp or 0),
                'approved_by_id': calc.uk_approve_user_id,
                'approved_at': (
                    calc.uk_approve_date
                    or calc.date_success
                    or calc.date
                ),
                'comment': calc.uk_approve_comment or '',
            },
        )
        CarCalculations.objects.filter(pk=calc.pk).update(
            uk_approval_basis='manual',
            uk_approval_threshold_kvp=int(calc.kvp or 0),
            uk_approval_reference_id=approval.pk,
        )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('prices_car', '0030_carcalculations_soglasovanie_awaiting_1c'),
    ]

    operations = [
        migrations.CreateModel(
            name='CarCalculationUkApproval',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'approved_kvp',
                    models.PositiveIntegerField(verbose_name='Согласованный КВП'),
                ),
                (
                    'approved_at',
                    models.DateTimeField(verbose_name='Дата ручного согласования УК'),
                ),
                (
                    'comment',
                    models.CharField(
                        blank=True,
                        default='',
                        max_length=2048,
                        verbose_name='Комментарий УК',
                    ),
                ),
                (
                    'created_at',
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name='Дата фиксации',
                    ),
                ),
                (
                    'approved_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='manual_car_calculation_uk_approvals',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Согласовал УК',
                    ),
                ),
                (
                    'calculation',
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='manual_uk_approval_snapshot',
                        to='prices_car.carcalculations',
                        verbose_name='Исходное коммерческое предложение',
                    ),
                ),
                (
                    'car',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='calculation_uk_approvals',
                        to='refs.refcarsorganization',
                        verbose_name='Автомобиль',
                    ),
                ),
                (
                    'rlk',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='car_calculation_uk_approvals',
                        to='documents.docrlk',
                        verbose_name='Рабочий лист',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Ручное согласование КВП управляющей компанией',
                'verbose_name_plural': 'Ручные согласования КВП управляющей компанией',
                'db_table': 'carCalculationUkApproval',
                'ordering': ['approved_kvp', '-approved_at', 'pk'],
            },
        ),
        migrations.AddIndex(
            model_name='carcalculationukapproval',
            index=models.Index(
                fields=['rlk', 'car', 'approved_kvp'],
                name='calc_uk_rlk_car_kvp_idx',
            ),
        ),
        migrations.AddField(
            model_name='carcalculations',
            name='uk_approval_basis',
            field=models.CharField(
                blank=True,
                choices=[
                    ('manual', 'Ручное согласование УК'),
                    ('prior_threshold', 'Ранее согласованный минимальный КВП УК'),
                ],
                default='',
                max_length=32,
                verbose_name='Основание согласования УК',
            ),
        ),
        migrations.AddField(
            model_name='carcalculations',
            name='uk_approval_reference',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='derived_calculations',
                to='prices_car.carcalculationukapproval',
                verbose_name='Основание из истории согласований УК',
            ),
        ),
        migrations.AddField(
            model_name='carcalculations',
            name='uk_approval_threshold_kvp',
            field=models.IntegerField(
                blank=True,
                null=True,
                verbose_name='Применённый минимальный КВП УК',
            ),
        ),
        migrations.RunPython(
            backfill_manual_uk_approvals,
            migrations.RunPython.noop,
        ),
    ]
