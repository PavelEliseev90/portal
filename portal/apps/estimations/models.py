from django.db import models


class EstimationBriefFactor(models.Model):
    """Вес пункта шкалы состояния авто для сводки клиенту."""

    key = models.CharField('Код', max_length=64, unique=True)
    label = models.CharField('Название', max_length=200)
    group = models.CharField('Группа', max_length=64, blank=True, default='')
    weight = models.FloatField(
        'Вес',
        default=0,
        help_text='Плюс повышает оценку (к 5★), минус понижает. База шкалы 3.5.',
    )
    objection = models.CharField('Возражение клиента', max_length=300, blank=True, default='')
    answer = models.TextField('Ответ / аргументация', blank=True, default='')
    sort = models.IntegerField('Порядок', default=0)
    active = models.BooleanField('Участвует в шкале', default=True)

    class Meta:
        db_table = 'estimationBriefFactor'
        verbose_name = 'Сводка клиенту: фактор шкалы'
        verbose_name_plural = 'Сводка клиенту: факторы шкалы'
        ordering = ['sort', 'id']

    def __str__(self):
        sign = '+' if self.weight >= 0 else ''
        return '{} ({}{})'.format(self.label, sign, self.weight)
