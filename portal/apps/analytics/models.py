from django.conf import settings
from django.db import models


class InteractivePricingSnapshot(models.Model):
    """
    Денормализованная витрина для отчета по согласованию интерактивных оценок.
    Заполняется из RegInteractivOcenka и связанных моделей, чтобы избавить отчеты от тяжелых join-ов.
    """

    estimation_id = models.PositiveIntegerField(primary_key=True, help_text='ID записи RegInteractivOcenka')
    rlk_id = models.PositiveIntegerField(null=True, blank=True, help_text='ID рабочего листа DocRLK')

    start_estimation = models.DateTimeField()
    end_estimation = models.DateTimeField(null=True, blank=True)

    unit_id = models.PositiveIntegerField(null=True, blank=True)
    unit_name = models.CharField(max_length=255, blank=True)
    unit_source = models.CharField(
        max_length=32,
        blank=True,
        help_text='unit | unit_dc | page_documents__unit',
    )

    staff_id = models.PositiveIntegerField(null=True, blank=True)
    staff_name = models.CharField(max_length=255, blank=True)

    analyst_before_id = models.PositiveIntegerField(null=True, blank=True)
    analyst_before_name = models.CharField(max_length=255, blank=True)
    analyst_after_id = models.PositiveIntegerField(null=True, blank=True)
    analyst_after_name = models.CharField(max_length=255, blank=True)

    type_reception_id = models.PositiveIntegerField(null=True, blank=True)
    status_id = models.PositiveIntegerField(null=True, blank=True)
    status_name = models.CharField(max_length=255, blank=True)

    model_name = models.CharField(max_length=255, blank=True)
    vin = models.CharField(max_length=64, blank=True)

    price_auto_1 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_auto_2 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_auto_3 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_auto_selected = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    price_before_kd = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_after_kd = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    diff_before = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    diff_after = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    price_auto_bcp = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_bcp = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_reception = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_sale = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    cost_podgotovka = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    cost_ss = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    cost_mcu = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    cost_recovery = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    cost_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    has_soglasovanie = models.BooleanField(default=False)
    has_diagnostics = models.BooleanField(default=False)

    duration_estimation_sec = models.IntegerField(null=True, blank=True)
    duration_sogl_before_sec = models.IntegerField(null=True, blank=True)
    duration_diagnostics_sec = models.IntegerField(null=True, blank=True)
    duration_sogl_after_sec = models.IntegerField(null=True, blank=True)

    extra_payload = models.JSONField(blank=True, null=True, help_text='Дополнительные предрасчитанные данные')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Витрина интерактивных согласований'
        verbose_name_plural = 'Витрина интерактивных согласований'
        indexes = [
            models.Index(fields=['start_estimation']),
            models.Index(fields=['unit_id']),
            models.Index(fields=['staff_id']),
            models.Index(fields=['analyst_before_id']),
            models.Index(fields=['analyst_after_id']),
            models.Index(fields=['type_reception_id']),
            models.Index(fields=['status_id']),
        ]

    def __str__(self):
        return f'Snapshot #{self.estimation_id}'

