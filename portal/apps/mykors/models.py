"""Состояние выгрузки в MyKors (только внутри приложения mykors)."""
from django.db import models
from django.utils import timezone


class MykorsCarSyncState(models.Model):
    """
    Локальный журнал последней выгрузки авто.
    Не трогает RefCarsOrganization — только читает car_id/vin.
    """
    car_id = models.IntegerField('ID авто на портале', db_index=True)
    vin = models.CharField('VIN', max_length=18, db_index=True)
    payload_hash = models.CharField('Hash payload', max_length=64, blank=True, default='')
    remote_id = models.IntegerField('ID в MyKors', null=True, blank=True)
    last_synced_at = models.DateTimeField('Последняя попытка', null=True, blank=True)
    last_ok = models.BooleanField('Успешно', default=False)
    last_http_status = models.IntegerField('HTTP status', null=True, blank=True)
    last_error = models.TextField('Ошибка', blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mykors_car_sync_state'
        verbose_name = 'Статус выгрузки авто в MyKors'
        verbose_name_plural = 'Статусы выгрузки авто в MyKors'
        indexes = [
            models.Index(fields=['last_ok', 'last_synced_at']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['car_id'], name='mykors_carsync_car_id_uniq'),
        ]

    def __str__(self):
        return f'{self.vin} car_id={self.car_id} ok={self.last_ok}'

    def mark_result(self, *, ok, status_code=None, remote_id=None, error='', payload_hash_value=''):
        self.last_ok = bool(ok)
        self.last_http_status = status_code
        self.last_error = (error or '')[:2000]
        self.last_synced_at = timezone.now()
        if payload_hash_value:
            self.payload_hash = payload_hash_value
        if remote_id is not None:
            self.remote_id = remote_id
        self.save(update_fields=[
            'last_ok',
            'last_http_status',
            'last_error',
            'last_synced_at',
            'payload_hash',
            'remote_id',
            'updated_at',
        ])
