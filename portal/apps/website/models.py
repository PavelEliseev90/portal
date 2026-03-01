from django.db import models
from django.conf import settings


class ImProduct(models.Model):
    """Кэш товаров стока интернет-магазина из 1C."""
    nomenclature_code = models.CharField('НоменклатураКод', max_length=100, unique=True, db_index=True)
    code = models.CharField('Код', max_length=100, blank=True)
    nomenclature = models.CharField('Номенклатура', max_length=500, blank=True)
    title = models.CharField('Наименование/Объявление', max_length=500, blank=True)
    profile = models.CharField('Профиль', max_length=100, blank=True)
    category = models.CharField('Категория', max_length=200, blank=True)
    category_avito = models.CharField('Категория Авито', max_length=200, blank=True)
    manufacturer = models.CharField('Производитель', max_length=200, blank=True)
    article = models.CharField('Артикул', max_length=100, blank=True)
    storage_cell = models.CharField('Ячейка хранения', max_length=100, blank=True)
    address = models.CharField('Адрес', max_length=500, blank=True)
    price_display = models.CharField('Цена (отображение)', max_length=50, blank=True)
    price_value = models.DecimalField('Цена (число)', max_digits=18, decimal_places=2, null=True, blank=True)
    quantity_balance = models.IntegerField('Остаток', default=0)
    photo_count = models.IntegerField('Количество фото', default=0)
    avito_id = models.CharField('AvitoId', max_length=50, blank=True)
    ad_status = models.CharField('AdStatus', max_length=50, blank=True)
    status_text = models.CharField('Статус', max_length=100, blank=True)
    date_begin = models.DateTimeField('DateBegin', null=True, blank=True)
    date_end = models.DateTimeField('DateEnd', null=True, blank=True)
    views_count = models.IntegerField('Просмотров', default=0)
    contacts_count = models.IntegerField('Контактов', default=0)
    favorites_count = models.IntegerField('Избранное', default=0)
    raw_json = models.JSONField('Сырой JSON', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    synced_at = models.DateTimeField('Последняя синхронизация', null=True, blank=True)

    class Meta:
        verbose_name = 'Товар IM сток'
        verbose_name_plural = 'Товары IM сток'
        indexes = [
            models.Index(fields=['status_text']),
            models.Index(fields=['photo_count']),
            models.Index(fields=['avito_id']),
            models.Index(fields=['synced_at']),
        ]

    def to_dict(self):
        """Преобразование в словарь для шаблона (совместимость с API)."""
        return {
            'Номенклатура': self.nomenclature or '',
            'Объявление': self.title or '',
            'Профиль': self.profile or '',
            'Код': self.code or '',
            'Наименование': self.nomenclature or '',
            'Категория': self.category or '',
            'КатегорияАвито': self.category_avito or '',
            'Производитель': self.manufacturer or '',
            'Артикул': self.article or '',
            'ЯчейкаХранения': self.storage_cell or '',
            'Address': self.address or '',
            'Price': self.price_display or str(self.price_value or 0),
            'AvitoId': self.avito_id or '',
            'Статус': self.status_text or '',
            'КоличествоОстаток': str(self.quantity_balance),
            'КоличествоФото': str(self.photo_count),
            'НоменклатураКод': self.nomenclature_code,
            'Просмотров': self.views_count,
            'Контактов': self.contacts_count,
            'Избранное': self.favorites_count,
        }


class ImSyncLog(models.Model):
    """Журнал синхронизации стока интернет-магазина."""
    SYNC_TYPES = [
        ('full_stok', 'Полная выгрузка стока'),
        ('product_update', 'Обновление товара'),
        ('photo_upload', 'Загрузка фото'),
    ]
    STATUSES = [
        ('success', 'Успешно'),
        ('partial', 'Частично'),
        ('error', 'Ошибка'),
    ]
    sync_type = models.CharField('Тип', max_length=50, choices=SYNC_TYPES, db_index=True)
    direction = models.CharField('Направление', max_length=20, default='in')  # in / out
    started_at = models.DateTimeField('Начало', auto_now_add=True)
    finished_at = models.DateTimeField('Окончание', null=True, blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUSES, default='success')
    request_url = models.CharField('URL запроса', max_length=1000, blank=True)
    response_code = models.IntegerField('Код ответа', null=True, blank=True)
    items_total = models.IntegerField('Всего записей', default=0)
    items_ok = models.IntegerField('Успешно', default=0)
    items_failed = models.IntegerField('Ошибок', default=0)
    error_message = models.TextField('Сообщение об ошибке', blank=True)
    details_json = models.JSONField('Детали', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Пользователь',
    )

    class Meta:
        verbose_name = 'Запись журнала синхронизации IM'
        verbose_name_plural = 'Журнал синхронизации IM'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['sync_type']),
            models.Index(fields=['-started_at']),
        ]
