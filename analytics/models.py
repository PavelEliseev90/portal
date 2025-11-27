from django.db import models


class InteractivePricingSnapshot(models.Model):
    """Витрина для отчета по согласованию интерактивных оценок."""

    estimation_id = models.PositiveIntegerField(primary_key=True, help_text='ID RegInteractivOcenka')
    rlk_id = models.PositiveIntegerField(null=True, blank=True, help_text='ID DocRLK')

    start_estimation = models.DateTimeField()
    end_estimation = models.DateTimeField(null=True, blank=True)

    unit_id = models.PositiveIntegerField(null=True, blank=True)
    unit_name = models.CharField(max_length=255, blank=True)
    unit_source = models.CharField(max_length=32, blank=True)

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

    extra_payload = models.JSONField(blank=True, null=True)

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
        return f'InteractivePricingSnapshot #{self.estimation_id}'


class EcoAnalystSnapshot(models.Model):
    """Витрина по аналитикам ЕЦО в разрезе каждой оценки и роли (до/после диагностики)."""

    ROLE_CHOICES = (
        ('before', 'До диагностики'),
        ('after', 'После диагностики'),
    )

    estimation_id = models.PositiveIntegerField(help_text='ID RegInteractivOcenka')
    rlk_id = models.PositiveIntegerField(null=True, blank=True, help_text='ID DocRLK')
    role = models.CharField(max_length=8, choices=ROLE_CHOICES)

    start_estimation = models.DateTimeField()
    end_estimation = models.DateTimeField(null=True, blank=True)

    unit_id = models.PositiveIntegerField(null=True, blank=True)
    unit_name = models.CharField(max_length=255, blank=True)
    unit_source = models.CharField(max_length=32, blank=True)

    staff_id = models.PositiveIntegerField(null=True, blank=True)
    staff_name = models.CharField(max_length=255, blank=True)

    analyst_id = models.PositiveIntegerField(null=True, blank=True)
    analyst_name = models.CharField(max_length=255, blank=True)

    type_reception_id = models.PositiveIntegerField(null=True, blank=True)
    status_id = models.PositiveIntegerField(null=True, blank=True)
    status_name = models.CharField(max_length=255, blank=True)

    has_soglasovanie = models.BooleanField(default=False)
    has_diagnostics = models.BooleanField(default=False)
    accepted = models.BooleanField(default=False)

    price_auto_selected = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_before_kd = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_after_kd = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    diff_before = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    diff_after = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    price_reception = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_sale = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    cost_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    duration_estimation_sec = models.IntegerField(null=True, blank=True)
    duration_sogl_before_sec = models.IntegerField(null=True, blank=True)
    duration_diagnostics_sec = models.IntegerField(null=True, blank=True)
    duration_sogl_after_sec = models.IntegerField(null=True, blank=True)

    tasks_total = models.IntegerField(null=True, blank=True)
    tasks_closed = models.IntegerField(null=True, blank=True)

    extra_payload = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Витрина аналитиков ЕЦО'
        verbose_name_plural = 'Витрина аналитиков ЕЦО'
        unique_together = ('estimation_id', 'role')
        indexes = [
            models.Index(fields=['start_estimation']),
            models.Index(fields=['unit_id']),
            models.Index(fields=['analyst_id']),
            models.Index(fields=['role']),
            models.Index(fields=['status_id']),
            models.Index(fields=['type_reception_id']),
        ]

    def __str__(self):
        return f'EcoAnalystSnapshot #{self.estimation_id} ({self.role})'

