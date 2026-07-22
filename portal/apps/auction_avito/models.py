"""
Модели данных аукциона Авито (B2B-лоты / offers API).

Иерархия:
  AvitoBidderAccount — аккаунт дилера на площадке (bidderId + dealerId)
  AvitoLot — лот (lotId), общий для всех дилеров
  AvitoLotOffer — предложение дилеру (lotOfferId), элемент массива offers[]
  дочерние сущности лота и оффера — см. ниже
"""
from django.conf import settings
from django.db import models


# ---------------------------------------------------------------------------
# Справочники / аккаунт
# ---------------------------------------------------------------------------

class AvitoBidderAccount(models.Model):
    """Привязка подразделения к аккаунту на аукционе Авито."""
    bidder_id = models.PositiveIntegerField('bidderId (Авито)', unique=True)
    dealer_id = models.PositiveIntegerField('dealerId (Авито)')
    unit = models.ForeignKey(
        'refs.RefUnit',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Подразделение',
    )
    is_active = models.BooleanField('Активен', default=True)
    comment = models.CharField('Комментарий', max_length=500, blank=True, default='')

    class Meta:
        db_table = 'avitoBidderAccount'
        verbose_name = 'Аккаунт аукциона Авито'
        verbose_name_plural = 'Аккаунты аукциона Авито'

    def __str__(self):
        return f'bidder {self.bidder_id} / dealer {self.dealer_id}'


class AvitoVenue(models.Model):
    """Площадка продавца на аукционе Авито (dealerId + место)."""

    dealer_id = models.PositiveIntegerField('dealerId', unique=True, db_index=True)
    name = models.CharField('Наименование', max_length=500, blank=True, default='')
    city = models.ForeignKey(
        'refs.RefCity',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Город',
        related_name='avito_venues',
    )
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        db_table = 'avitoVenue'
        verbose_name = 'Площадка Авито'
        verbose_name_plural = 'Площадки Авито'
        ordering = ['city__name', 'name', 'dealer_id']

    @property
    def city_name(self) -> str:
        return self.city.name if self.city_id else ''

    def __str__(self):
        parts = [p for p in (self.name, self.city_name) if p]
        label = ', '.join(parts) if parts else f'Площадка {self.dealer_id}'
        return f'{label} (dealer {self.dealer_id})'

    @property
    def display_label(self):
        parts = []
        if self.name:
            parts.append(self.name)
        if self.city_name:
            parts.append(self.city_name)
        base = ' · '.join(parts) if parts else f'Площадка {self.dealer_id}'
        return f'{base} (ID {self.dealer_id})'


# ---------------------------------------------------------------------------
# Лот (lot)
# ---------------------------------------------------------------------------

class AvitoLot(models.Model):
    """Лот аукциона — стабильная сущность по lotId."""

    lot_id = models.BigIntegerField('lotId', unique=True, db_index=True)
    venue = models.ForeignKey(
        AvitoVenue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lots',
        verbose_name='Площадка',
    )
    description = models.TextField('Описание объявления', blank=True, default='')
    seller_place_name = models.CharField('Место продавца', max_length=500, blank=True, default='')

    min_price = models.PositiveIntegerField('minPrice', null=True, blank=True)
    min_available_bid = models.PositiveIntegerField('minAvailableBid', null=True, blank=True)
    max_available_bid = models.PositiveIntegerField('maxAvailableBid', null=True, blank=True)
    max_bid = models.PositiveIntegerField('maxBid', null=True, blank=True)

    bid_l1 = models.PositiveIntegerField('bidGroupV2.l1', null=True, blank=True)
    bid_l2 = models.PositiveIntegerField('bidGroupV2.l2', null=True, blank=True)

    imv_low = models.PositiveIntegerField('imvMarketRange.low', null=True, blank=True)
    imv_median = models.PositiveIntegerField('imvMarketRange.median', null=True, blank=True)
    imv_high = models.PositiveIntegerField('imvMarketRange.high', null=True, blank=True)

    created_at = models.DateTimeField('createdAt (лот)', null=True, blank=True)
    updated_at = models.DateTimeField('updatedAt (лот)', null=True, blank=True)
    finish_at = models.DateTimeField('finishAt', null=True, blank=True, db_index=True)
    origin_finish_at = models.DateTimeField('originFinishAt', null=True, blank=True)
    expires_at = models.DateTimeField('expiresAt', null=True, blank=True)

    trade_in_considers = models.BooleanField('tradeIn.considersTradeIn', null=True, blank=True)
    trade_in_looking_for_used = models.BooleanField('tradeIn.lookingForUsedCar', null=True, blank=True)
    trade_in_comment = models.TextField('tradeIn.comment', blank=True, null=True)

    # Сырой фрагмент lot из API (без offers-уровня)
    raw_lot_json = models.JSONField('JSON лота (сырой)', default=dict, blank=True)
    synced_at = models.DateTimeField('Последняя синхронизация', auto_now=True)

    class Meta:
        db_table = 'avitoLot'
        verbose_name = 'Лот Авито'
        verbose_name_plural = 'Лоты Авито'
        ordering = ['-finish_at', '-lot_id']

    def __str__(self):
        return f'Лот {self.lot_id}'

    def _raw(self, key, default=None):
        return (self.raw_lot_json or {}).get(key, default)

    @property
    def display_min_available_bid(self):
        return self.min_available_bid if self.min_available_bid is not None else self._raw('minAvailableBid')

    @property
    def display_max_available_bid(self):
        return self.max_available_bid if self.max_available_bid is not None else self._raw('maxAvailableBid')

    @property
    def display_min_price(self):
        return self.min_price if self.min_price is not None else self._raw('minPrice')

    @property
    def display_max_bid(self):
        return self.max_bid if self.max_bid is not None else self._raw('maxBid')

    @property
    def has_trade_in(self):
        if self.trade_in_considers or self.trade_in_looking_for_used:
            return True
        if (self.trade_in_comment or '').strip():
            return True
        trade = self._raw('tradeIn') or {}
        return bool(
            trade.get('considersTradeIn')
            or trade.get('lookingForUsedCar')
            or (trade.get('comment') or '').strip()
        )


class AvitoLotVehicle(models.Model):
    """Характеристики из lot.vehicle (каталог Авито, человекочитаемые поля)."""
    lot = models.OneToOneField(
        AvitoLot,
        on_delete=models.CASCADE,
        related_name='vehicle_avito',
        verbose_name='Лот',
    )

    brand_id = models.BigIntegerField('brand.id', null=True, blank=True)
    brand_name = models.CharField('Марка', max_length=200, blank=True, default='')
    model_id = models.BigIntegerField('model.id', null=True, blank=True)
    model_name = models.CharField('Модель', max_length=200, blank=True, default='')
    generation_id = models.BigIntegerField('generation.id', null=True, blank=True)
    generation_name = models.CharField('Поколение', max_length=300, blank=True, default='')
    modification_id = models.BigIntegerField('modification.id', null=True, blank=True)
    modification_name = models.CharField('Модификация', max_length=300, blank=True, default='')
    configuration_id = models.BigIntegerField('configuration.id', null=True, blank=True)
    configuration_name = models.CharField('Комплектация', max_length=200, blank=True, default='')

    year = models.PositiveSmallIntegerField('Год', null=True, blank=True)
    mileage = models.PositiveIntegerField('Пробег', null=True, blank=True)
    body_type_id = models.BigIntegerField(null=True, blank=True)
    body_type_name = models.CharField('Кузов', max_length=100, blank=True, default='')
    engine_type_id = models.BigIntegerField(null=True, blank=True)
    engine_type_name = models.CharField('Двигатель', max_length=100, blank=True, default='')
    transmission_id = models.BigIntegerField(null=True, blank=True)
    transmission_name = models.CharField('КПП', max_length=100, blank=True, default='')
    drive_id = models.BigIntegerField(null=True, blank=True)
    drive_name = models.CharField('Привод', max_length=100, blank=True, default='')
    color_id = models.BigIntegerField(null=True, blank=True)
    color_name = models.CharField('Цвет', max_length=100, blank=True, default='')
    condition_id = models.BigIntegerField(null=True, blank=True)
    condition_name = models.CharField('Состояние', max_length=100, blank=True, default='')
    owners_count_id = models.BigIntegerField(null=True, blank=True)
    owners_count_name = models.CharField('Владельцы', max_length=50, blank=True, default='')
    doors_count = models.PositiveSmallIntegerField('Двери', null=True, blank=True)
    wheel_name = models.CharField('Руль', max_length=50, blank=True, default='')
    vehicle_type_name = models.CharField('Тип ТС', max_length=100, blank=True, default='')
    registration_in_russia = models.CharField('Учёт в РФ', max_length=100, blank=True, default='')
    registration_number = models.CharField('Госномер', max_length=20, blank=True, default='')

    class Meta:
        db_table = 'avitoLotVehicle'
        verbose_name = 'Авто (каталог Авито)'
        verbose_name_plural = 'Авто (каталог Авито)'


class AvitoLotAutohubVehicle(models.Model):
    """Технические ID из lot.autohubVehicle — для связи с Автохаб / порталом."""
    lot = models.OneToOneField(
        AvitoLot,
        on_delete=models.CASCADE,
        related_name='vehicle_autohub',
        verbose_name='Лот',
    )

    brand_id = models.PositiveIntegerField('brandID', null=True, blank=True)
    model_id = models.PositiveIntegerField('modelID', null=True, blank=True)
    generation_id = models.PositiveIntegerField('generationID', null=True, blank=True)
    modification_id = models.PositiveIntegerField('modificationID', null=True, blank=True)
    complectation_id = models.PositiveIntegerField('complectationID', null=True, blank=True)
    body_configuration_id = models.PositiveIntegerField('bodyConfigurationID', null=True, blank=True)

    year = models.PositiveSmallIntegerField(null=True, blank=True)
    km_distance = models.PositiveIntegerField('kmDistance', null=True, blank=True)
    owner_count = models.PositiveSmallIntegerField('ownerCount', null=True, blank=True)
    body_type = models.CharField('bodyType', max_length=50, blank=True, default='')
    body_door_count = models.PositiveSmallIntegerField('bodyDoorCount', null=True, blank=True)
    drive_type = models.CharField('driveType', max_length=30, blank=True, default='')
    engine_type = models.CharField('engineType', max_length=30, blank=True, default='')
    engine_volume = models.PositiveIntegerField('engineVolume', null=True, blank=True)
    engine_power = models.PositiveSmallIntegerField('enginePower', null=True, blank=True)
    gearbox_type = models.CharField('gearboxType', max_length=30, blank=True, default='')
    armored = models.BooleanField(default=False)
    equipment_ids = models.JSONField('equipment (ID)', default=list, blank=True)

    class Meta:
        db_table = 'avitoLotAutohubVehicle'
        verbose_name = 'Авто (Autohub ID)'
        verbose_name_plural = 'Авто (Autohub ID)'


class AvitoLotImage(models.Model):
    SOURCE_AVITO = 'avito'
    SOURCE_UPLOAD = 'upload'
    SOURCE_CHOICES = [
        (SOURCE_AVITO, 'Авито (URL)'),
        (SOURCE_UPLOAD, 'Загрузка в портал'),
    ]

    lot = models.ForeignKey(AvitoLot, on_delete=models.CASCADE, related_name='images')
    image_id = models.BigIntegerField('id фото')
    source = models.CharField(
        'Источник',
        max_length=10,
        choices=SOURCE_CHOICES,
        default=SOURCE_AVITO,
    )
    url = models.URLField('url', max_length=2048, blank=True, default='')
    url_preview = models.URLField('urlPreview', max_length=2048, blank=True, default='')
    file = models.ImageField(
        'Файл',
        upload_to='auction_avito/lots/%Y/%m/%d/',
        blank=True,
        null=True,
        max_length=500,
    )
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        db_table = 'avitoLotImage'
        verbose_name = 'Фото лота'
        verbose_name_plural = 'Фото лотов'
        ordering = ['sort_order', 'id']
        unique_together = [('lot', 'image_id')]

    @property
    def display_url(self):
        if self.file:
            return self.file.url
        return self.url_preview or self.url or ''


class AvitoLotEquipment(models.Model):
    """lot.equipment[] — группы опций с values."""
    lot = models.ForeignKey(AvitoLot, on_delete=models.CASCADE, related_name='equipment')
    name = models.CharField('Группа', max_length=300)
    values = models.JSONField('Значения', default=list)

    class Meta:
        db_table = 'avitoLotEquipment'
        verbose_name = 'Комплектация (текст)'
        verbose_name_plural = 'Комплектация (текст)'


class AvitoAutotekaReport(models.Model):
    lot = models.OneToOneField(
        AvitoLot,
        on_delete=models.CASCADE,
        related_name='autoteka',
        verbose_name='Лот',
    )
    state_status = models.CharField(
        'state.status',
        max_length=30,
        blank=True,
        default='',
        help_text='success | incomplete | …',
    )

    class Meta:
        db_table = 'avitoAutotekaReport'
        verbose_name = 'Отчёт Автотеки'
        verbose_name_plural = 'Отчёты Автотеки'


class AvitoAutotekaEvent(models.Model):
    report = models.ForeignKey(
        AvitoAutotekaReport,
        on_delete=models.CASCADE,
        related_name='events',
    )
    event_type = models.CharField('type', max_length=50, db_index=True)
    status = models.CharField('status', max_length=20, blank=True, default='')
    description = models.CharField('description', max_length=500, blank=True, default='')

    class Meta:
        db_table = 'avitoAutotekaEvent'
        verbose_name = 'Событие Автотеки'
        verbose_name_plural = 'События Автотеки'
        ordering = ['id']


class AvitoLotBadge(models.Model):
    """Бейджи на уровне лота (lot.badges)."""
    lot = models.ForeignKey(AvitoLot, on_delete=models.CASCADE, related_name='badges')
    avito_badge_id = models.BigIntegerField('id')
    badge_type = models.CharField('badgeType', max_length=50, db_index=True)
    title = models.CharField('title', max_length=300, blank=True, default='')
    description = models.TextField(blank=True, default='')
    priority = models.SmallIntegerField(default=0)
    style = models.CharField(
        'style',
        max_length=30,
        blank=True,
        default='',
        help_text='round | classic | пусто для lot.badges',
    )

    class Meta:
        db_table = 'avitoLotBadge'
        verbose_name = 'Бейдж лота'
        verbose_name_plural = 'Бейджи лота'


# ---------------------------------------------------------------------------
# Оффер дилера (offer)
# ---------------------------------------------------------------------------

class AvitoLotOffer(models.Model):
    """
    Предложение дилеру — элемент offers[].
    Уникально по lotOfferId; привязано к лоту и аккаунту.
    """
    lot_offer_id = models.BigIntegerField('lotOfferId', unique=True, db_index=True)
    lot = models.ForeignKey(AvitoLot, on_delete=models.CASCADE, related_name='offers')
    account = models.ForeignKey(
        AvitoBidderAccount,
        on_delete=models.PROTECT,
        related_name='offers',
        verbose_name='Аккаунт',
    )

    status_code = models.CharField('status.status', max_length=30, db_index=True, blank=True, default='')
    status_name = models.CharField('status.name', max_length=100, blank=True, default='')

    bid = models.PositiveIntegerField('Текущая ставка', null=True, blank=True)
    bid_made_at = models.DateTimeField('bidMadeAt', null=True, blank=True)
    min_bid_step = models.PositiveIntegerField('minBidStep', null=True, blank=True)

    sale_cost = models.PositiveIntegerField('saleCost', null=True, blank=True)
    presale_preparation_cost = models.PositiveIntegerField(
        'presalePreparationCost', null=True, blank=True,
    )
    gm1_money = models.IntegerField('gm1Money', null=True, blank=True)
    gm1_percent = models.DecimalField('gm1Percent', max_digits=5, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField('createdAt', null=True, blank=True)
    updated_at = models.DateTimeField('updatedAt', null=True, blank=True, db_index=True)

    hidden_by_user_ids = models.JSONField(
        'hiddenBy',
        default=list,
        blank=True,
        help_text='Список id пользователей Авито, скрывших лот',
    )

    is_buyout_on_site_available = models.BooleanField(
        'isBuyoutOnSiteAvailable', default=False,
    )
    is_inspection_on_site_available = models.BooleanField(
        'isInspectionOnSiteAvailable', default=False,
    )

    bid_made_by_avito_user_id = models.PositiveIntegerField(null=True, blank=True)
    bid_made_by_email = models.EmailField(blank=True, default='')
    bid_made_by_first_name = models.CharField(max_length=100, blank=True, default='')
    bid_made_by_last_name = models.CharField(max_length=100, blank=True, default='')
    bid_made_by_middle_name = models.CharField(max_length=100, blank=True, default='')
    bid_made_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='avito_lot_bids',
        verbose_name='Ставку сделал (портал)',
    )

    # Связь с карточкой склада после выкупа
    car = models.ForeignKey(
        'refs.RefCarsOrganization',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='avito_lot_offers',
        verbose_name='Автомобиль на складе',
    )

    # Итог после завершения аукциона (решение продавца на Maxposter)
    outcome_code = models.CharField(
        'Код итога',
        max_length=40,
        blank=True,
        default='',
        db_index=True,
        help_text='waiting_seller | won | lost | no_selection | canceled | unknown',
    )
    outcome_title = models.CharField(
        'Заголовок итога',
        max_length=300,
        blank=True,
        default='',
        help_text='Как на Maxposter: «Аукцион завершен» и т.п.',
    )
    outcome_detail = models.TextField(
        'Подробности итога',
        blank=True,
        default='',
        help_text='Напр. «Ждём решения продавца…»',
    )
    outcome_raw = models.TextField(
        'Сырой текст/JSON итога',
        blank=True,
        default='',
    )
    outcome_synced_at = models.DateTimeField(
        'Итог синхронизирован',
        null=True,
        blank=True,
        db_index=True,
    )
    win_email_sent_at = models.DateTimeField(
        'Письмо о победе отправлено',
        null=True,
        blank=True,
    )

    raw_offer_json = models.JSONField('JSON оффера (сырой)', default=dict, blank=True)

    class Meta:
        db_table = 'avitoLotOffer'
        verbose_name = 'Оффер дилера'
        verbose_name_plural = 'Офферы дилеров'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['status_code', 'account']),
            models.Index(fields=['lot', 'account']),
            models.Index(fields=['outcome_code', 'outcome_synced_at']),
        ]

    def __str__(self):
        return f'Оффер {self.lot_offer_id} / лот {self.lot.lot_id}'

    @property
    def display_min_bid_step(self):
        if self.min_bid_step is not None:
            return self.min_bid_step
        return (self.raw_offer_json or {}).get('minBidStep')


class AvitoOfferBadge(models.Model):
    """Бейджи уровня оффера (badges + badgesByStyle на offer)."""
    offer = models.ForeignKey(AvitoLotOffer, on_delete=models.CASCADE, related_name='badges')
    avito_badge_id = models.BigIntegerField('id')
    badge_type = models.CharField('badgeType', max_length=50, db_index=True)
    title = models.CharField(max_length=300, blank=True, default='')
    description = models.TextField(blank=True, default='')
    priority = models.SmallIntegerField(default=0)
    style = models.CharField(max_length=30, blank=True, default='')

    class Meta:
        db_table = 'avitoOfferBadge'
        verbose_name = 'Бейдж оффера'
        verbose_name_plural = 'Бейджи оффера'


class AvitoBidHistory(models.Model):
    """История ставок (накапливается при синхронизации, если bid изменился)."""
    offer = models.ForeignKey(AvitoLotOffer, on_delete=models.CASCADE, related_name='bid_history')
    bid = models.PositiveIntegerField()
    bid_made_at = models.DateTimeField(null=True, blank=True)
    bid_made_by_avito_user_id = models.PositiveIntegerField(null=True, blank=True)
    comment = models.TextField('Комментарий', blank=True, default='')
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'avitoBidHistory'
        verbose_name = 'История ставки'
        verbose_name_plural = 'История ставок'
        ordering = ['-recorded_at']


# ---------------------------------------------------------------------------
# Расчёты выкупа (история — несколько записей на один лот)
# ---------------------------------------------------------------------------

class AvitoLotCalculation(models.Model):
    """
    Один автоматический расчёт лота (POST /api/calculate_car/).
    История: у лота может быть много расчётов, актуальный — последний по calculated_at.
    """
    lot = models.ForeignKey(
        AvitoLot,
        on_delete=models.CASCADE,
        related_name='calculations',
        verbose_name='Лот',
    )
    offer = models.ForeignKey(
        AvitoLotOffer,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='calculations',
        verbose_name='Оффер',
    )
    unit = models.ForeignKey(
        'refs.RefUnit',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Подразделение (настройки расчёта)',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='avito_lot_calculations',
        verbose_name='Пользователь',
    )

    calculated_at = models.DateTimeField('Дата расчёта', auto_now_add=True, db_index=True)
    is_success = models.BooleanField('Успешно', default=True)
    error_message = models.TextField('Ошибка', blank=True, default='')

    min_price = models.PositiveIntegerField('minPrice (запрос)', null=True, blank=True)
    mileage = models.PositiveIntegerField('Пробег', null=True, blank=True)
    year = models.PositiveSmallIntegerField('Год', null=True, blank=True)

    estimation_price = models.IntegerField('Цена выкупа (итог)', null=True, blank=True)
    profit = models.IntegerField('Маржа (profit)', null=True, blank=True)
    zna = models.IntegerField('ЦНА / avgPriceWithCorrection', null=True, blank=True)
    avg_days_in_sale = models.PositiveSmallIntegerField('Ср. дни продажи', null=True, blank=True)
    price_group = models.CharField('Ценовая группа (zg)', max_length=30, blank=True, default='')
    kf = models.DecimalField('Коэф. токсичности (kf)', max_digits=8, decimal_places=2, null=True, blank=True)

    price_sale = models.IntegerField('Цена продажи (sale)', null=True, blank=True)
    price_sale_rdo = models.IntegerField('Цена продажи RDO', null=True, blank=True)
    price_sale_kor = models.IntegerField('Цена продажи Корс', null=True, blank=True)
    cna_expenses = models.IntegerField('cna_expenses', null=True, blank=True)
    zachita_ot_ubitka = models.IntegerField('Защита от убытка', null=True, blank=True)
    finance_price = models.IntegerField('Финансирование', null=True, blank=True)
    iznos_price = models.IntegerField('Коррекция износ', null=True, blank=True)
    discount_torg = models.IntegerField('Скидка торг', null=True, blank=True)

    auction_risk = models.BooleanField('Риск аукциона (такси/пробег/…)', default=False)
    auction_risk_note = models.CharField('Примечание по риску', max_length=500, blank=True, default='')

    price_steps = models.JSONField(
        'Шаги цены (list_info_price)',
        default=list,
        blank=True,
    )
    raw_request_json = models.JSONField('Запрос (фрагмент)', default=dict, blank=True)
    raw_answer_json = models.JSONField('Ответ расчёта', default=dict, blank=True)

    class Meta:
        db_table = 'avitoLotCalculation'
        verbose_name = 'Расчёт лота'
        verbose_name_plural = 'Расчёты лотов'
        ordering = ['-calculated_at']
        indexes = [
            models.Index(fields=['lot', '-calculated_at']),
        ]

    def __str__(self):
        return f'Расчёт {self.lot_id} · {self.calculated_at:%d.%m.%Y %H:%M}'


class AvitoSyncLog(models.Model):
    """Журнал загрузок списка offers."""
    account = models.ForeignKey(
        AvitoBidderAccount,
        on_delete=models.CASCADE,
        related_name='sync_logs',
        null=True,
        blank=True,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    success = models.BooleanField(default=False)
    offers_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default='')
    response_hash = models.CharField(max_length=64, blank=True, default='')

    class Meta:
        db_table = 'avitoSyncLog'
        verbose_name = 'Синхронизация Авито'
        verbose_name_plural = 'Синхронизации Авито'
        ordering = ['-started_at']


class AvitoAuctionSettings(models.Model):
    """
    Единые настройки раздела «Аукцион Авито»:
    фильтры автоставок + веса этапов УС для рекомендаций выкупа.
    Хранится одна запись (pk=1).
    """

    auto_bid_enabled = models.BooleanField(
        'Автоставки включены',
        default=False,
        help_text='Глобальный выключатель. Парсер/воркер ставит только если включено.',
    )
    mileage_min = models.PositiveIntegerField(
        'Пробег от, км',
        null=True,
        blank=True,
        help_text='Пусто = без нижней границы.',
    )
    mileage_max = models.PositiveIntegerField(
        'Пробег до, км',
        null=True,
        blank=True,
        help_text='Пусто = без верхней границы.',
    )
    year_min = models.PositiveSmallIntegerField(
        'Год выпуска от',
        null=True,
        blank=True,
    )
    year_max = models.PositiveSmallIntegerField(
        'Год выпуска до',
        null=True,
        blank=True,
    )
    block_taxi = models.BooleanField(
        'Не ставить на такси (taxi)',
        default=True,
    )
    block_carsharing = models.BooleanField(
        'Не ставить на каршеринг (carsharing)',
        default=True,
    )
    block_mileage_twisted = models.BooleanField(
        'Не ставить при скрученном пробеге (mileageTwisted)',
        default=True,
    )
    bid_round_to = models.PositiveIntegerField(
        'Округление ставки вверх до',
        default=1000,
        help_text='maxBid + minBidStep округляется вверх до этого шага (обычно 1000).',
    )

    weight_test_price = models.DecimalField(
        'Вес этапа «Тест-прайс»',
        max_digits=6,
        decimal_places=3,
        default=1,
    )
    weight_rdo = models.DecimalField(
        'Вес этапа «РДО»',
        max_digits=6,
        decimal_places=3,
        default='0.55',
    )
    weight_kor = models.DecimalField(
        'Вес этапа «Коррекция»',
        max_digits=6,
        decimal_places=3,
        default='0.25',
    )
    weight_txt = models.DecimalField(
        'Вес этапа «ТХТ»',
        max_digits=6,
        decimal_places=3,
        default='0.05',
    )

    win_notify_emails = models.TextField(
        'Email при выигрыше лота',
        blank=True,
        default='',
        help_text='Адреса через запятую или с новой строки. Письмо уходит один раз при outcome=won.',
    )
    outcome_poll_enabled = models.BooleanField(
        'Опрашивать итоги завершённых лотов',
        default=True,
        help_text='Парсер забирает очередь лотов со ставкой и обновляет статус решения продавца.',
    )

    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        db_table = 'avitoAuctionSettings'
        verbose_name = 'Настройки аукциона Авито'
        verbose_name_plural = 'Настройки аукциона Авито'

    def __str__(self):
        return 'Настройки аукциона Авито'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.mileage_min is not None and self.mileage_max is not None:
            if self.mileage_min > self.mileage_max:
                raise ValidationError({'mileage_max': '«Пробег до» не может быть меньше «от».'})
        if self.year_min is not None and self.year_max is not None:
            if self.year_min > self.year_max:
                raise ValidationError({'year_max': '«Год до» не может быть меньше «от».'})
        if self.bid_round_to is not None and self.bid_round_to < 1:
            raise ValidationError({'bid_round_to': 'Шаг округления должен быть ≥ 1.'})
        for field in ('weight_test_price', 'weight_rdo', 'weight_kor', 'weight_txt'):
            val = getattr(self, field)
            if val is not None and val < 0:
                raise ValidationError({field: 'Вес не может быть отрицательным.'})
