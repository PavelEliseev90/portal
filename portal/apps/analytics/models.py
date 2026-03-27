from django.db import models


class TradeInFunnel(models.Model):
    
    rlk_uin      = models.CharField(max_length=255, blank=True)
    rlk_id      = models.PositiveIntegerField(primary_key=True, help_text='ID DocRLK')
    rlk_number  = models.CharField(max_length=255, blank=True)
    lo_number   = models.CharField(max_length=255, blank=True)
    
    footing_rlk_id          = models.PositiveIntegerField(null=True, blank=True, help_text='footing_ ID DocRLK')
    footing_rlk_uin         = models.CharField(max_length=255, blank=True, default="")
    footing_rlk_number      = models.CharField(max_length=255, blank=True, default="")

    estimation_id = models.PositiveIntegerField(null=True, blank=True, help_text='ID RegInteractivOcenka')
    
    unit_id     = models.PositiveIntegerField(null=True, blank=True, help_text='ID подразделения приема')
    unit_name   = models.CharField(max_length=255, blank=True)
    
    city_id     = models.PositiveIntegerField(null=True, blank=True, help_text='Город')
    city_name   = models.CharField(max_length=255, blank=True)
    
    brand     = models.CharField(max_length=255, blank=True)

    unit_source_id      = models.PositiveIntegerField(null=True, blank=True, help_text='ID подразделения источник')
    unit_source_name    = models.CharField(max_length=255, blank=True)

    source_bu   = models.BooleanField(default=False)

    staff_id    = models.PositiveIntegerField(null=True, blank=True)
    staff_name  = models.CharField(max_length=255, blank=True)
    
    analyst_remote_id       = models.PositiveIntegerField(null=True, blank=True)
    analyst_remote_name     = models.CharField(max_length=255, blank=True)
    
    analyst_before_id       = models.PositiveIntegerField(null=True, blank=True)
    analyst_before_name     = models.CharField(max_length=255, blank=True)
    
    analyst_after_id        = models.PositiveIntegerField(null=True, blank=True)
    analyst_after_name      = models.CharField(max_length=255, blank=True)

    type_reception_id   = models.PositiveIntegerField(null=True, blank=True)
    type_reception_name = models.CharField(max_length=255, blank=True)

    vin_trade_in        = models.CharField(max_length=64, blank=True)
    
    mark_id             = models.PositiveIntegerField(null=True, blank=True)
    mark_name           = models.CharField(max_length=255, blank=True)
    model_id            = models.PositiveIntegerField(null=True, blank=True)
    model_name          = models.CharField(max_length=255, blank=True)
    modification_id     = models.PositiveIntegerField(null=True, blank=True)
    modification_name   = models.CharField(max_length=255, blank=True)
    complectation_id    = models.PositiveIntegerField(null=True, blank=True)
    complectation_name  = models.CharField(max_length=255, blank=True)
    
    vin                 = models.CharField(max_length=64, blank=True)
    year                = models.IntegerField("Год выпуска",  default=0, null=True, blank=True) 
    run                 = models.IntegerField("Пробег",  default=0, null=True, blank=True)

    date_rlk                    = models.DateTimeField(null=True, blank=True)
    date_start_estimation       = models.DateTimeField(null=True, blank=True)
    date_remote_success         = models.DateTimeField(null=True, blank=True)
    date_before_success         = models.DateTimeField(null=True, blank=True)
    date_diagnostic_success     = models.DateTimeField(null=True, blank=True)
    date_after_success          = models.DateTimeField(null=True, blank=True)
    date_reception_success      = models.DateTimeField(null=True, blank=True)
    date_archive                = models.DateTimeField(null=True, blank=True)
    date_sale                   = models.DateTimeField(null=True, blank=True)
    
    hours_stock      = models.IntegerField('Дней на стоке', default=0, null=True, blank=True)
    hours_estimation = models.IntegerField('Дней оценки', default=0, null=True, blank=True)

    remote              = models.BooleanField(default=False)
    diagostica          = models.BooleanField(default=False)
    auction             = models.BooleanField(default=False)
    auction_auto        = models.BooleanField(default=False)
    
    owners              = models.IntegerField('Владельцев', default=0, null=True, blank=True)
    count_dtp           = models.IntegerField('Количество ДТП', default=0, null=True, blank=True)
    dtp_red             = models.BooleanField('Есть сильные повреждения при дтп', default = False, null=True, blank=True)
    iznos               = models.BooleanField(default=False)
    taxi                = models.BooleanField("Использование в такси", default = False, null=True, blank=True)
    carsharing          = models.BooleanField("Использование в каршеринге", default = False, null=True, blank=True)
    k_i                 = models.FloatField("Коэфицент износа", default=0.0, blank=True)
    autodex             = models.FloatField('Автотека сумма расчетов ремонтов', default=0.00, null=True, blank=True)

    price_reception_staff   = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_sale_staff        = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    price_remote        = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_before        = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_after         = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_sale          = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_auto_bcp      = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    price_auto_remote   = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_auto_before   = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_auto_after    = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    zna                 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    zna_custom          = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    zg_id               = models.PositiveIntegerField(null=True, blank=True)
    zg_name             = models.CharField(max_length=255, blank=True)


    archive_name    = models.CharField(max_length=1024, blank=True)
    archive_comment = models.CharField(max_length=5120, blank=True)

    cost_plan               = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    cost_plan_ss            = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    cost_plan_mcu           = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    cost_plan_preparation   = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    count_task = models.IntegerField('Задач', default=0, null=True, blank=True)
    
    stage = models.CharField(max_length=64, blank=True, help_text='Текущая стадия воронки')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    comparison_remote   = models.IntegerField('Разница с авторасчетом дистанционно', default=0, null=True, blank=True)
    comparison_before   = models.IntegerField('Разница с авторасчетом до кд', default=0, null=True, blank=True)
    comparison_after    = models.IntegerField('Разница с авторасчетом после кд', default=0, null=True, blank=True)

    comparison_remote_type   = models.IntegerField('Разница с авторасчетом дистанционно', default=0, null=True, blank=True)
    comparison_before_type   = models.IntegerField('Разница с авторасчетом до кд', default=0, null=True, blank=True)
    comparison_after_type    = models.IntegerField('Разница с авторасчетом после кд', default=0, null=True, blank=True)

    class Meta:
        verbose_name = 'Воронки Trade-In'
        verbose_name_plural = 'Воронки Trade-In'
        indexes = [
            models.Index(fields=['rlk_id']),
            models.Index(fields=['estimation_id']),
            models.Index(fields=['date_rlk']),
            models.Index(fields=['date_start_estimation']),
            models.Index(fields=['date_after_success']),
            models.Index(fields=['unit_id']),
            models.Index(fields=['staff_id']),
            models.Index(fields=['stage']),
        ]

    def __str__(self):
        return f'TradeInFunnel #{self.rlk_id}'



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

    tasks_total = models.IntegerField(null=True, blank=True)
    tasks_closed = models.IntegerField(null=True, blank=True)

    has_soglasovanie = models.BooleanField(default=False)
    has_diagnostics = models.BooleanField(default=False)
    accepted = models.BooleanField(default=False)

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
        ('remote', 'Дистанционная'), 
    )

    estimation_id = models.PositiveIntegerField(help_text='ID RegInteractivOcenka')
    rlk_id = models.PositiveIntegerField(null=True, blank=True, help_text='ID DocRLK')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

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

    comparison = models.IntegerField(null=True, blank=True)

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
            models.Index(fields=['comparison']),
        ]

    def __str__(self):
        return f'EcoAnalystSnapshot #{self.estimation_id} ({self.role})'


class AppraiserPerformanceSnapshot(models.Model):
    """Витрина по работе оценщиков (staff / DocRLK)."""

    estimation_id = models.PositiveIntegerField(primary_key=True, help_text='ID RegInteractivOcenka')
    rlk_id = models.PositiveIntegerField(null=True, blank=True, help_text='ID DocRLK')

    worksheet_created_at = models.DateTimeField(null=True, blank=True)
    start_estimation = models.DateTimeField(null=True, blank=True)
    end_estimation = models.DateTimeField(null=True, blank=True)

    unit_id = models.PositiveIntegerField(null=True, blank=True)
    unit_name = models.CharField(max_length=255, blank=True)
    unit_source = models.CharField(max_length=32, blank=True)

    staff_id = models.PositiveIntegerField(null=True, blank=True)
    staff_name = models.CharField(max_length=255, blank=True)

    source_type = models.CharField(max_length=255, blank=True)
    status_id = models.PositiveIntegerField(null=True, blank=True)
    status_name = models.CharField(max_length=255, blank=True)

    has_soglasovanie = models.BooleanField(default=False)
    has_diagnostics = models.BooleanField(default=False)
    accepted = models.BooleanField(default=False)

    price_offer = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_agreed = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_reception = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_sale = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    price_auto_selected = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    diff_vs_auto = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    cost_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    duration_estimation_sec = models.IntegerField(null=True, blank=True)
    duration_to_accept_sec = models.IntegerField(null=True, blank=True)
    duration_to_sale_sec = models.IntegerField(null=True, blank=True)
    days_in_stock = models.IntegerField(null=True, blank=True)

    tasks_total = models.IntegerField(null=True, blank=True)
    tasks_closed = models.IntegerField(null=True, blank=True)

    extra_payload = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Витрина оценщиков'
        verbose_name_plural = 'Витрина оценщиков'
        indexes = [
            models.Index(fields=['worksheet_created_at']),
            models.Index(fields=['unit_id']),
            models.Index(fields=['staff_id']),
            models.Index(fields=['status_id']),
        ]

    def __str__(self):
        return f'AppraiserPerformanceSnapshot #{self.estimation_id}'


class TradeInFunnelSnapshot(models.Model):
    """Витрина для воронки Trade-In (рабочий лист / оценка / продажа)."""

    rlk_id = models.PositiveIntegerField(primary_key=True, help_text='ID DocRLK')
    worksheet_number = models.CharField(max_length=255, blank=True)

    unit_id = models.PositiveIntegerField(null=True, blank=True)
    unit_name = models.CharField(max_length=255, blank=True)
    unit_source = models.CharField(max_length=32, blank=True)

    staff_id = models.PositiveIntegerField(null=True, blank=True)
    staff_name = models.CharField(max_length=255, blank=True)
    analyst_before_id = models.PositiveIntegerField(null=True, blank=True)
    analyst_after_id = models.PositiveIntegerField(null=True, blank=True)

    source_type = models.CharField(max_length=255, blank=True)
    type_reception_id = models.PositiveIntegerField(null=True, blank=True)

    date_work_order = models.DateTimeField(null=True, blank=True)
    date_evaluation = models.DateTimeField(null=True, blank=True)
    date_diagnostic = models.DateTimeField(null=True, blank=True)
    date_acceptance = models.DateTimeField(null=True, blank=True)
    date_sale = models.DateTimeField(null=True, blank=True)
    date_market = models.DateTimeField(null=True, blank=True)

    price_offer = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_agreed_before = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_agreed_after = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_reception = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_sale = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_market = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    cost_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    duration_to_evaluation_sec = models.IntegerField(null=True, blank=True)
    duration_to_diagnostic_sec = models.IntegerField(null=True, blank=True)
    duration_to_acceptance_sec = models.IntegerField(null=True, blank=True)
    duration_to_sale_sec = models.IntegerField(null=True, blank=True)

    accepted = models.BooleanField(default=False)
    sold = models.BooleanField(default=False)
    went_to_market = models.BooleanField(default=False)

    stage = models.CharField(max_length=64, blank=True, help_text='Текущая стадия воронки')

    extra_payload = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Витрина воронки Trade-In'
        verbose_name_plural = 'Витрина воронки Trade-In'
        indexes = [
            models.Index(fields=['date_work_order']),
            models.Index(fields=['unit_id']),
            models.Index(fields=['staff_id']),
            models.Index(fields=['stage']),
        ]

    def __str__(self):
        return f'TradeInFunnelSnapshot #{self.rlk_id}'

