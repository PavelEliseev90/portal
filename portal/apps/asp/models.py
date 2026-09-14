# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models


class ReportSavedFilter(models.Model):
    """Сохранённый набор фильтров отчёта ОП АСП (JSON params)."""

    REPORT_KEY_CHOICES = (
        ('margin', 'Кумулятивная маржа'),
        ('stock', 'Остатки'),
        ('accepted', 'Принятые'),
        ('disposition', 'Диспозиция'),
        ('docs_agreement', 'Соглашения о покупке'),
        ('docs_shipment', 'Отгрузки автомобилей'),
        ('docs_rlk', 'Рабочие листы ОП'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='asp_saved_filters',
        verbose_name='Пользователь',
    )
    report_key = models.CharField(
        'Ключ отчёта',
        max_length=32,
        choices=REPORT_KEY_CHOICES,
        db_index=True,
    )
    name = models.CharField('Название', max_length=200)
    filter_data = models.JSONField(
        'Параметры фильтра',
        default=dict,
        blank=True,
        help_text='JSON с query-параметрами (unit, date_from, type_reception, …)',
    )
    is_shared = models.BooleanField(
        'Общий',
        default=False,
        help_text='Доступен всем пользователям (создание — staff/superuser)',
    )
    order = models.IntegerField('Порядок', default=0)
    date_created = models.DateTimeField('Создан', auto_now_add=True)
    date_updated = models.DateTimeField('Обновлён', auto_now=True)

    class Meta:
        db_table = 'asp_report_saved_filter'
        verbose_name = 'Сохранённый фильтр отчёта АСП'
        verbose_name_plural = 'Сохранённые фильтры отчётов АСП'
        ordering = ['order', 'name', 'id']
        unique_together = [['user', 'report_key', 'name']]
        indexes = [
            models.Index(fields=['report_key', 'user']),
            models.Index(fields=['report_key', 'is_shared']),
        ]

    def __str__(self):
        return '{} / {} ({})'.format(self.report_key, self.name, self.user_id)
