from django.db import models


class Exchange1CErrorLog(models.Model):
    """Ошибки загрузки элементов при обмене с 1С (/api/exchange/)."""

    date_create = models.DateTimeField('Дата', auto_now_add=True, db_index=True)
    exchange_type = models.CharField(
        'Тип (имя массива)',
        max_length=64,
        db_index=True,
        help_text='Staffs, Customers, Worksheets и т.д.',
    )
    data = models.TextField(
        'Данные элемента',
        help_text='JSON элемента массива из пакета 1С',
    )
    error_description = models.TextField('Описание ошибки')

    def __str__(self):
        return f'{self.exchange_type} / {self.date_create:%d.%m.%Y %H:%M}'

    class Meta:
        db_table = 'exchange1CErrorLog'
        verbose_name = 'Ошибка обмена с 1С'
        verbose_name_plural = 'Ошибки обмена с 1С'
        ordering = ['-date_create']
        indexes = [
            models.Index(fields=['-date_create', 'exchange_type']),
        ]
