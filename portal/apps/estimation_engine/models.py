"""
Изолированные справочники конструктора оценки и подготовки.

Не участвуют в текущем расчёте интерактивной оценки.
Не содержат URL, сигналов и автоматического заполнения.

Стык с car_preparation:
оценка строит EstimationPlanSnapshot → явный handoff создаёт
CarPreparation + work_items (is_confirmed=False) без ЗН и расписания.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from car_preparation.models import (
    CarPreparation,
    CarPreparationWorkItem,
    RefCarPreparationWork,
    RefPreparationMaterial,
    RefRepairZone,
)
from documents.models import DocRLK
from refs.models import AutoruMark, AutoruModel, RefCarsOrganization, RefTypeBody, RefUnit
from register.models import RegInteractivOcenka, RegPodgotovkaWork


class TimeStampedModel(models.Model):
    """Общие служебные поля справочников."""

    created_at = models.DateTimeField('Создано', default=timezone.now, editable=False)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        abstract = True


class LegacyWorkMapping(TimeStampedModel):
    """
    Однозначное соответствие legacy-работы расчёта новой работе подготовки.

    Заполняется вручную. Не изменяет RegPodgotovkaWork и не влияет на расчёт.
    """

    REVIEW_STATUS_DRAFT = 'draft'
    REVIEW_STATUS_REVIEWED = 'reviewed'
    REVIEW_STATUS_CONFIRMED = 'confirmed'
    REVIEW_STATUS_REJECTED = 'rejected'
    REVIEW_STATUS_CHOICES = (
        (REVIEW_STATUS_DRAFT, 'Черновик'),
        (REVIEW_STATUS_REVIEWED, 'Проверено'),
        (REVIEW_STATUS_CONFIRMED, 'Подтверждено'),
        (REVIEW_STATUS_REJECTED, 'Отклонено'),
    )

    legacy_work = models.OneToOneField(
        RegPodgotovkaWork,
        on_delete=models.PROTECT,
        related_name='estimation_engine_mapping',
        verbose_name='Legacy-работа (RegPodgotovkaWork)',
    )
    target_work = models.ForeignKey(
        RefCarPreparationWork,
        on_delete=models.PROTECT,
        related_name='legacy_mappings',
        verbose_name='Целевая работа (RefCarPreparationWork)',
    )
    review_status = models.CharField(
        'Статус проверки',
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default=REVIEW_STATUS_DRAFT,
        db_index=True,
    )
    comment = models.TextField('Комментарий', blank=True, default='')
    is_active = models.BooleanField('Активно', default=True, db_index=True)

    class Meta:
        db_table = 'ee_legacy_work_mapping'
        verbose_name = 'Соответствие legacy-работы'
        verbose_name_plural = 'Соответствия legacy-работ'
        ordering = ['legacy_work_id']
        indexes = [
            models.Index(fields=['is_active', 'review_status']),
            models.Index(fields=['target_work', 'is_active']),
        ]

    def __str__(self):
        return f'{self.legacy_work_id} → {self.target_work_id}'


class PreparationMaterialProfile(TimeStampedModel):
    """
    Расширение существующего справочника материалов.

    Складской учёт остаётся в car_preparation; здесь только каталожные свойства.
    """

    CATEGORY_PAINT = 'paint'
    CATEGORY_PRIMER = 'primer'
    CATEGORY_CLEARCOAT = 'clearcoat'
    CATEGORY_ADHESIVE = 'adhesive'
    CATEGORY_ABRASIVE = 'abrasive'
    CATEGORY_CHEMICAL = 'chemical'
    CATEGORY_OTHER = 'other'
    CATEGORY_CHOICES = (
        (CATEGORY_PAINT, 'Краска'),
        (CATEGORY_PRIMER, 'Грунт'),
        (CATEGORY_CLEARCOAT, 'Лак'),
        (CATEGORY_ADHESIVE, 'Клей'),
        (CATEGORY_ABRASIVE, 'Абразив'),
        (CATEGORY_CHEMICAL, 'Химия'),
        (CATEGORY_OTHER, 'Прочее'),
    )

    material = models.OneToOneField(
        RefPreparationMaterial,
        on_delete=models.PROTECT,
        related_name='estimation_profile',
        verbose_name='Материал подготовки',
    )
    code = models.CharField('Код профиля', max_length=64, unique=True)
    category = models.CharField(
        'Категория',
        max_length=32,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_OTHER,
        db_index=True,
    )
    manufacturer = models.CharField('Производитель', max_length=250, blank=True, default='')
    article = models.CharField('Артикул', max_length=128, blank=True, default='', db_index=True)
    process_loss_percent = models.DecimalField(
        'Технологические потери, %',
        max_digits=6,
        decimal_places=2,
        default=0,
    )
    properties = models.JSONField('Свойства', default=dict, blank=True)
    notes = models.TextField('Примечание', blank=True, default='')
    is_active = models.BooleanField('Активен', default=True, db_index=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        db_table = 'ee_preparation_material_profile'
        verbose_name = 'Профиль материала подготовки'
        verbose_name_plural = 'Профили материалов подготовки'
        ordering = ['sort_order', 'code']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['manufacturer', 'article']),
        ]

    def __str__(self):
        return f'{self.code} / {self.material}'

    def clean(self):
        if self.process_loss_percent is not None and self.process_loss_percent < 0:
            raise ValidationError({'process_loss_percent': 'Потери не могут быть отрицательными.'})


class PreparationPart(TimeStampedModel):
    """Справочник деталей (PART): стекло, крыло, фара и т.п."""

    KIND_ORIGINAL = 'original'
    KIND_ANALOG = 'analog'
    KIND_CHOICES = (
        (KIND_ORIGINAL, 'Оригинал'),
        (KIND_ANALOG, 'Аналог'),
    )

    code = models.CharField('Код', max_length=64, unique=True)
    name = models.CharField('Наименование', max_length=512)
    category = models.CharField('Категория', max_length=128, blank=True, default='', db_index=True)
    oem_number = models.CharField('OEM / артикул', max_length=128, blank=True, default='', db_index=True)
    manufacturer = models.CharField('Производитель', max_length=250, blank=True, default='')
    kind = models.CharField(
        'Тип детали',
        max_length=16,
        choices=KIND_CHOICES,
        default=KIND_ORIGINAL,
        db_index=True,
    )
    characteristics = models.JSONField('Характеристики', default=dict, blank=True)
    description = models.TextField('Описание', blank=True, default='')
    is_active = models.BooleanField('Активна', default=True, db_index=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        db_table = 'ee_preparation_part'
        verbose_name = 'Деталь подготовки'
        verbose_name_plural = 'Детали подготовки'
        ordering = ['sort_order', 'code']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['oem_number', 'manufacturer']),
        ]

    def __str__(self):
        return f'{self.code} / {self.name}'


class PreparationPartCompatibility(TimeStampedModel):
    """Совместимость детали с типом кузова / маркой / моделью."""

    part = models.ForeignKey(
        PreparationPart,
        on_delete=models.CASCADE,
        related_name='compatibilities',
        verbose_name='Деталь',
    )
    type_body = models.ForeignKey(
        RefTypeBody,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='estimation_part_compatibilities',
        verbose_name='Тип кузова',
    )
    mark = models.ForeignKey(
        AutoruMark,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='estimation_part_compatibilities',
        verbose_name='Марка',
    )
    model = models.ForeignKey(
        AutoruModel,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='estimation_part_compatibilities',
        verbose_name='Модель',
    )
    year_from = models.PositiveSmallIntegerField('Год от', null=True, blank=True)
    year_to = models.PositiveSmallIntegerField('Год до', null=True, blank=True)
    notes = models.CharField('Примечание', max_length=512, blank=True, default='')
    is_active = models.BooleanField('Активно', default=True, db_index=True)

    class Meta:
        db_table = 'ee_preparation_part_compatibility'
        verbose_name = 'Совместимость детали'
        verbose_name_plural = 'Совместимости деталей'
        ordering = ['part_id', 'id']
        indexes = [
            models.Index(fields=['part', 'is_active']),
            models.Index(fields=['type_body', 'mark', 'model']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['part', 'type_body', 'mark', 'model', 'year_from', 'year_to'],
                name='ee_part_compat_unique_scope',
            ),
        ]

    def __str__(self):
        return f'{self.part_id}: body={self.type_body_id} mark={self.mark_id} model={self.model_id}'

    def clean(self):
        if self.year_from and self.year_to and self.year_from > self.year_to:
            raise ValidationError({'year_to': 'Год «до» не может быть меньше года «от».'})
        if not any([self.type_body_id, self.mark_id, self.model_id]):
            raise ValidationError('Укажите хотя бы тип кузова, марку или модель.')


class PreparationService(TimeStampedModel):
    """Каталог подрядных услуг."""

    code = models.CharField('Код', max_length=64, unique=True)
    name = models.CharField('Наименование', max_length=512)
    category = models.CharField('Категория', max_length=128, blank=True, default='', db_index=True)
    description = models.TextField('Описание', blank=True, default='')
    is_active = models.BooleanField('Активна', default=True, db_index=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        db_table = 'ee_preparation_service'
        verbose_name = 'Подрядная услуга'
        verbose_name_plural = 'Подрядные услуги'
        ordering = ['sort_order', 'code']
        indexes = [
            models.Index(fields=['category', 'is_active']),
        ]

    def __str__(self):
        return f'{self.code} / {self.name}'


class PreparationServiceProvider(TimeStampedModel):
    """Исполнитель / подрядчик услуг подготовки."""

    code = models.CharField('Код', max_length=64, unique=True)
    name = models.CharField('Наименование', max_length=512)
    legal_name = models.CharField('Юридическое наименование', max_length=512, blank=True, default='')
    inn = models.CharField('ИНН', max_length=20, blank=True, default='', db_index=True)
    contract_number = models.CharField('Номер договора', max_length=128, blank=True, default='')
    contract_valid_from = models.DateField('Договор действует с', null=True, blank=True)
    contract_valid_to = models.DateField('Договор действует по', null=True, blank=True)
    contacts = models.CharField('Контакты', max_length=512, blank=True, default='')
    notes = models.TextField('Примечание', blank=True, default='')
    is_active = models.BooleanField('Активен', default=True, db_index=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        db_table = 'ee_preparation_service_provider'
        verbose_name = 'Исполнитель подрядных услуг'
        verbose_name_plural = 'Исполнители подрядных услуг'
        ordering = ['sort_order', 'code']
        indexes = [
            models.Index(fields=['is_active', 'name']),
            models.Index(fields=['contract_valid_from', 'contract_valid_to']),
        ]

    def __str__(self):
        return f'{self.code} / {self.name}'

    def clean(self):
        if (
            self.contract_valid_from
            and self.contract_valid_to
            and self.contract_valid_from > self.contract_valid_to
        ):
            raise ValidationError(
                {'contract_valid_to': 'Дата окончания договора не может быть раньше даты начала.'},
            )


class PreparationServiceOffering(TimeStampedModel):
    """
    Предложение исполнителя по услуге.

    Цены намеренно не хранятся — они войдут в версионные прайсы следующего этапа.
    """

    service = models.ForeignKey(
        PreparationService,
        on_delete=models.PROTECT,
        related_name='offerings',
        verbose_name='Услуга',
    )
    provider = models.ForeignKey(
        PreparationServiceProvider,
        on_delete=models.PROTECT,
        related_name='offerings',
        verbose_name='Исполнитель',
    )
    code = models.CharField('Код предложения', max_length=64, unique=True)
    sla_hours = models.PositiveIntegerField('SLA, часов', null=True, blank=True)
    includes_works = models.BooleanField('Включает работы', default=True)
    includes_materials = models.BooleanField('Включает материалы', default=False)
    includes_parts = models.BooleanField('Включает детали', default=False)
    package_description = models.TextField('Состав пакета', blank=True, default='')
    valid_from = models.DateField('Действует с', null=True, blank=True)
    valid_to = models.DateField('Действует по', null=True, blank=True)
    is_active = models.BooleanField('Активно', default=True, db_index=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        db_table = 'ee_preparation_service_offering'
        verbose_name = 'Предложение подрядной услуги'
        verbose_name_plural = 'Предложения подрядных услуг'
        ordering = ['sort_order', 'code']
        indexes = [
            models.Index(fields=['service', 'is_active']),
            models.Index(fields=['provider', 'is_active']),
            models.Index(fields=['valid_from', 'valid_to']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['service', 'provider'],
                name='ee_service_offering_unique_pair',
            ),
        ]

    def __str__(self):
        return f'{self.code}: {self.service_id} / {self.provider_id}'

    def clean(self):
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValidationError({'valid_to': 'Дата окончания не может быть раньше даты начала.'})


# ---------------------------------------------------------------------------
# Пакет работ (единица согласования и передачи в подготовку)
# ---------------------------------------------------------------------------


class PreparationWorkPackage(TimeStampedModel):
    """
    Пакет работ / техкарта.

    Пример: «Покраска крыла без ремонта».
    Согласовывается целиком; внутри — работы, материалы, детали, услуги.
    """

    SECTION_EXTERIOR = 'exterior'
    SECTION_INTERIOR = 'interior'
    SECTION_DIAGNOSTIC = 'diagnostic'
    SECTION_COMMON = 'common'
    SECTION_CHOICES = (
        (SECTION_EXTERIOR, 'Внешний осмотр'),
        (SECTION_INTERIOR, 'Внутренний осмотр'),
        (SECTION_DIAGNOSTIC, 'Диагностика'),
        (SECTION_COMMON, 'Общий'),
    )

    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_ARCHIVED = 'archived'
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Черновик'),
        (STATUS_PUBLISHED, 'Опубликован'),
        (STATUS_ARCHIVED, 'Архив'),
    )

    ROUTE_IN_HOUSE = 'in_house'
    ROUTE_CONTRACTOR = 'contractor'
    ROUTE_MANUAL = 'manual'
    ROUTE_CHOICES = (
        (ROUTE_IN_HOUSE, 'Свой цех / ремзона'),
        (ROUTE_CONTRACTOR, 'Подрядчик'),
        (ROUTE_MANUAL, 'Ручной выбор'),
    )

    code = models.CharField('Код', max_length=64, unique=True)
    name = models.CharField('Наименование', max_length=512)
    section = models.CharField(
        'Раздел осмотра',
        max_length=32,
        choices=SECTION_CHOICES,
        default=SECTION_COMMON,
        db_index=True,
    )
    status = models.CharField(
        'Статус',
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    description = models.TextField('Описание', blank=True, default='')
    route_type = models.CharField(
        'Маршрут по умолчанию',
        max_length=16,
        choices=ROUTE_CHOICES,
        default=ROUTE_IN_HOUSE,
        db_index=True,
    )
    default_repair_zone = models.ForeignKey(
        RefRepairZone,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='work_packages',
        verbose_name='Ремзона / цех по умолчанию',
    )
    default_service_offering = models.ForeignKey(
        'PreparationServiceOffering',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='default_for_packages',
        verbose_name='Подряд по умолчанию',
    )
    estimation_reduction_amount = models.DecimalField(
        'Сумма снижения оценки, ₽',
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text='На сколько снижается оценка автомобиля при применении этого пакета.',
    )
    is_active = models.BooleanField('Активен', default=True, db_index=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        db_table = 'ee_preparation_work_package'
        verbose_name = 'Пакет работ (каталог)'
        verbose_name_plural = 'Пакеты работ (каталог)'
        ordering = ['sort_order', 'code']
        indexes = [
            models.Index(fields=['section', 'status', 'is_active']),
            models.Index(fields=['route_type', 'is_active']),
        ]

    def __str__(self):
        return f'{self.code} / {self.name}'

    def clean(self):
        if self.route_type == self.ROUTE_IN_HOUSE and not self.default_repair_zone_id:
            # Не блокируем черновики жёстко — предупреждение через admin later;
            # для published требуем ремзону.
            if self.status == self.STATUS_PUBLISHED:
                raise ValidationError(
                    {'default_repair_zone': 'Для опубликованного пакета своего цеха укажите ремзону.'},
                )
        if self.route_type == self.ROUTE_CONTRACTOR and not self.default_service_offering_id:
            if self.status == self.STATUS_PUBLISHED:
                raise ValidationError(
                    {
                        'default_service_offering':
                        'Для опубликованного подрядного пакета укажите предложение подрядчика.',
                    },
                )


class PreparationWorkPackageLine(TimeStampedModel):
    """Строка состава пакета работ."""

    LINE_WORK = 'WORK'
    LINE_MATERIAL = 'MATERIAL'
    LINE_PART = 'PART'
    LINE_SERVICE = 'SERVICE'
    LINE_TYPE_CHOICES = (
        (LINE_WORK, 'Работа'),
        (LINE_MATERIAL, 'Материал'),
        (LINE_PART, 'Деталь'),
        (LINE_SERVICE, 'Подрядная услуга'),
    )

    SCOPE_DAMAGE = 'damage'
    SCOPE_ELEMENT = 'element'
    SCOPE_OPERATION = 'operation'
    SCOPE_VEHICLE = 'vehicle'
    SCOPE_CHOICES = (
        (SCOPE_DAMAGE, 'Повреждение'),
        (SCOPE_ELEMENT, 'Элемент'),
        (SCOPE_OPERATION, 'Операция'),
        (SCOPE_VEHICLE, 'Автомобиль'),
    )

    package = models.ForeignKey(
        PreparationWorkPackage,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name='Пакет работ',
    )
    line_type = models.CharField('Тип строки', max_length=16, choices=LINE_TYPE_CHOICES, db_index=True)
    work = models.ForeignKey(
        RefCarPreparationWork,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='work_package_lines',
        verbose_name='Работа',
    )
    material = models.ForeignKey(
        RefPreparationMaterial,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='work_package_lines',
        verbose_name='Материал',
    )
    part = models.ForeignKey(
        PreparationPart,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='work_package_lines',
        verbose_name='Деталь',
    )
    service = models.ForeignKey(
        PreparationService,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='work_package_lines',
        verbose_name='Услуга',
    )
    service_offering = models.ForeignKey(
        PreparationServiceOffering,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='work_package_lines',
        verbose_name='Предложение подрядчика',
    )
    quantity = models.DecimalField('Количество', max_digits=14, decimal_places=3, default=1)
    norm_hours = models.DecimalField('Нормочасы', max_digits=10, decimal_places=2, default=0)
    unit_cost = models.DecimalField(
        'Цена единицы (MVP)',
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text='Временная цена до версионных прайсов. Для WORK обычно 0 — считается через ставку н/ч правила.',
    )
    is_required = models.BooleanField('Обязательная', default=True)
    scope = models.CharField(
        'Область',
        max_length=16,
        choices=SCOPE_CHOICES,
        default=SCOPE_OPERATION,
    )
    coverage_key = models.CharField(
        'Ключ дедупликации',
        max_length=128,
        blank=True,
        default='',
        db_index=True,
        help_text='Одинаковый ключ объединяет строки при раскрытии пакетов.',
    )
    parent_coverage_key = models.CharField(
        'Ключ родительской работы',
        max_length=128,
        blank=True,
        default='',
        help_text='Для MATERIAL/PART: привязка к WORK-строке с таким coverage_key.',
    )
    condition_json = models.JSONField('Условие включения', default=dict, blank=True)
    notes = models.CharField('Примечание', max_length=512, blank=True, default='')
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Активна', default=True)

    class Meta:
        db_table = 'ee_preparation_work_package_line'
        verbose_name = 'Строка пакета работ'
        verbose_name_plural = 'Строки пакетов работ'
        ordering = ['package_id', 'sort_order', 'id']
        indexes = [
            models.Index(fields=['package', 'line_type', 'is_active']),
            models.Index(fields=['coverage_key']),
        ]

    def __str__(self):
        return f'{self.package_id}:{self.line_type}#{self.sort_order}'

    def clean(self):
        linked = {
            self.LINE_WORK: self.work_id,
            self.LINE_MATERIAL: self.material_id,
            self.LINE_PART: self.part_id,
            self.LINE_SERVICE: self.service_id or self.service_offering_id,
        }
        if self.line_type and not linked.get(self.line_type):
            raise ValidationError(
                f'Для типа {self.line_type} нужно указать соответствующую ссылку на справочник.',
            )
        if self.quantity is not None and self.quantity < 0:
            raise ValidationError({'quantity': 'Количество не может быть отрицательным.'})
        if self.norm_hours is not None and self.norm_hours < 0:
            raise ValidationError({'norm_hours': 'Нормочасы не могут быть отрицательными.'})


# ---------------------------------------------------------------------------
# Snapshot плана оценки и связь с подготовкой
# ---------------------------------------------------------------------------


class EstimationPlanSnapshot(TimeStampedModel):
    """
    Согласованный (или черновой) план работ оценки.

    Независим от legacy RegEstimationPodgotovka/SS/MCU.
    Передача в CarPreparation выполняется только явным вызовом сервиса.
    Единица согласования — пакет (EstimationPlanPackage), строки — детализация.
    """

    STATUS_DRAFT = 'draft'
    STATUS_APPROVED = 'approved'
    STATUS_TRANSFERRED = 'transferred'
    STATUS_SUPERSEDED = 'superseded'
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Черновик'),
        (STATUS_APPROVED, 'Согласован'),
        (STATUS_TRANSFERRED, 'Передан в подготовку'),
        (STATUS_SUPERSEDED, 'Заменён новой ревизией'),
    )

    estimation = models.ForeignKey(
        RegInteractivOcenka,
        on_delete=models.PROTECT,
        related_name='estimation_engine_plan_snapshots',
        verbose_name='Оценка',
    )
    rlk = models.ForeignKey(
        DocRLK,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='estimation_engine_plan_snapshots',
        verbose_name='Рабочий лист',
    )
    car = models.ForeignKey(
        RefCarsOrganization,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='estimation_engine_plan_snapshots',
        verbose_name='Автомобиль склада',
    )
    unit = models.ForeignKey(
        RefUnit,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='estimation_engine_plan_snapshots',
        verbose_name='Подразделение',
    )
    vin = models.CharField('VIN', max_length=32, blank=True, default='', db_index=True)
    revision = models.PositiveIntegerField('Ревизия', default=1)
    status = models.CharField(
        'Статус',
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    source = models.CharField(
        'Источник',
        max_length=64,
        blank=True,
        default='manual',
        help_text='manual / engine / import — не влияет на legacy-расчёт',
    )
    total_norm_hours = models.DecimalField('Итого нормочасов', max_digits=12, decimal_places=2, default=0)
    total_cost = models.DecimalField('Итого стоимость', max_digits=14, decimal_places=2, default=0)
    approved_at = models.DateTimeField('Согласовано', null=True, blank=True)
    transferred_at = models.DateTimeField('Передано в подготовку', null=True, blank=True)
    preparation = models.ForeignKey(
        CarPreparation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='estimation_engine_plan_snapshots',
        verbose_name='Документ подготовки',
    )
    notes = models.TextField('Примечание', blank=True, default='')
    meta = models.JSONField('Метаданные', default=dict, blank=True)

    class Meta:
        db_table = 'ee_estimation_plan_snapshot'
        verbose_name = 'Снимок плана оценки'
        verbose_name_plural = 'Снимки планов оценки'
        ordering = ['-created_at', '-revision']
        indexes = [
            models.Index(fields=['estimation', 'status']),
            models.Index(fields=['vin', 'status']),
            models.Index(fields=['preparation']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['estimation', 'revision'],
                name='ee_plan_snapshot_unique_revision',
            ),
        ]

    def __str__(self):
        return f'Plan #{self.pk} est={self.estimation_id} rev={self.revision} ({self.status})'


class EstimationPlanPackage(TimeStampedModel):
    """
    Согласованный пакет в снимке плана.

    Именно эту сущность видят при согласовании: «Покраска крыла без ремонта — 6190 ₽».
    """

    snapshot = models.ForeignKey(
        EstimationPlanSnapshot,
        on_delete=models.CASCADE,
        related_name='packages',
        verbose_name='Снимок плана',
    )
    work_package = models.ForeignKey(
        PreparationWorkPackage,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='plan_packages',
        verbose_name='Пакет работ (каталог)',
    )
    code = models.CharField('Код (снимок)', max_length=64, blank=True, default='')
    name = models.CharField('Наименование (снимок)', max_length=512)
    section = models.CharField('Раздел', max_length=32, blank=True, default='')
    route_type = models.CharField(
        'Маршрут',
        max_length=16,
        choices=PreparationWorkPackage.ROUTE_CHOICES,
        default=PreparationWorkPackage.ROUTE_IN_HOUSE,
    )
    repair_zone = models.ForeignKey(
        RefRepairZone,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='estimation_plan_packages',
        verbose_name='Ремзона',
    )
    service_offering = models.ForeignKey(
        PreparationServiceOffering,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='estimation_plan_packages',
        verbose_name='Подряд',
    )
    total_norm_hours = models.DecimalField('Нормочасы пакета', max_digits=12, decimal_places=2, default=0)
    total_cost = models.DecimalField('Стоимость пакета', max_digits=14, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    preparation_package = models.ForeignKey(
        'car_preparation.CarPreparationPackage',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='estimation_plan_packages',
        verbose_name='Пакет в подготовке',
    )
    meta = models.JSONField('Метаданные', default=dict, blank=True)

    class Meta:
        db_table = 'ee_estimation_plan_package'
        verbose_name = 'Пакет в плане оценки'
        verbose_name_plural = 'Пакеты в плане оценки'
        ordering = ['snapshot_id', 'sort_order', 'id']
        indexes = [
            models.Index(fields=['snapshot', 'sort_order']),
            models.Index(fields=['work_package']),
        ]

    def __str__(self):
        return f'{self.snapshot_id}: {self.name}'


class EstimationPlanLine(TimeStampedModel):
    """Детализация пакета в снимке. После передачи может ссылаться на work_item."""

    LINE_WORK = PreparationWorkPackageLine.LINE_WORK
    LINE_MATERIAL = PreparationWorkPackageLine.LINE_MATERIAL
    LINE_PART = PreparationWorkPackageLine.LINE_PART
    LINE_SERVICE = PreparationWorkPackageLine.LINE_SERVICE
    LINE_TYPE_CHOICES = PreparationWorkPackageLine.LINE_TYPE_CHOICES

    SECTION_PODGOTOVKA = 'podgotovka'
    SECTION_SS = 'ss'
    SECTION_MCU = 'mcu'
    SECTION_OTHER = 'other'
    SECTION_CHOICES = (
        (SECTION_PODGOTOVKA, 'Подготовка'),
        (SECTION_SS, 'Слесарный ремонт'),
        (SECTION_MCU, 'Кузовной ремонт'),
        (SECTION_OTHER, 'Прочее'),
    )

    snapshot = models.ForeignKey(
        EstimationPlanSnapshot,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name='Снимок плана',
    )
    plan_package = models.ForeignKey(
        EstimationPlanPackage,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name='Пакет плана',
    )
    line_type = models.CharField('Тип строки', max_length=16, choices=LINE_TYPE_CHOICES, db_index=True)
    section = models.CharField(
        'Секция',
        max_length=16,
        choices=SECTION_CHOICES,
        default=SECTION_OTHER,
        db_index=True,
    )
    name = models.CharField('Наименование (снимок)', max_length=512)
    work = models.ForeignKey(
        RefCarPreparationWork,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='estimation_plan_lines',
        verbose_name='Работа',
    )
    material = models.ForeignKey(
        RefPreparationMaterial,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='estimation_plan_lines',
        verbose_name='Материал',
    )
    part = models.ForeignKey(
        PreparationPart,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='estimation_plan_lines',
        verbose_name='Деталь',
    )
    service = models.ForeignKey(
        PreparationService,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='estimation_plan_lines',
        verbose_name='Услуга',
    )
    service_offering = models.ForeignKey(
        PreparationServiceOffering,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='estimation_plan_lines',
        verbose_name='Предложение подрядчика',
    )
    quantity = models.DecimalField('Количество', max_digits=14, decimal_places=3, default=1)
    norm_hours = models.DecimalField('Нормочасы', max_digits=10, decimal_places=2, default=0)
    planned_minutes = models.PositiveIntegerField('Плановые минуты', default=0)
    cost = models.DecimalField('Стоимость', max_digits=14, decimal_places=2, default=0)
    coverage_key = models.CharField('Ключ дедупликации', max_length=128, blank=True, default='', db_index=True)
    parent_coverage_key = models.CharField('Ключ родительской работы', max_length=128, blank=True, default='')
    source_package_line = models.ForeignKey(
        PreparationWorkPackageLine,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='plan_lines',
        verbose_name='Строка пакета-источника',
    )
    preparation_work_item = models.ForeignKey(
        CarPreparationWorkItem,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='estimation_plan_lines',
        verbose_name='Строка подготовки',
    )
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    meta = models.JSONField('Метаданные', default=dict, blank=True)

    class Meta:
        db_table = 'ee_estimation_plan_line'
        verbose_name = 'Строка плана оценки'
        verbose_name_plural = 'Строки планов оценки'
        ordering = ['snapshot_id', 'sort_order', 'id']
        indexes = [
            models.Index(fields=['snapshot', 'line_type']),
            models.Index(fields=['plan_package', 'line_type']),
            models.Index(fields=['coverage_key']),
            models.Index(fields=['preparation_work_item']),
        ]

    def __str__(self):
        return f'{self.snapshot_id}:{self.line_type} {self.name}'

    def clean(self):
        if self.line_type == self.LINE_WORK and not self.work_id:
            raise ValidationError({'work': 'Для WORK нужна ссылка на RefCarPreparationWork.'})
        if self.line_type == self.LINE_MATERIAL and not self.material_id:
            raise ValidationError({'material': 'Для MATERIAL нужна ссылка на материал.'})
        if self.line_type == self.LINE_PART and not self.part_id:
            raise ValidationError({'part': 'Для PART нужна ссылка на деталь.'})
        if self.line_type == self.LINE_SERVICE and not (self.service_id or self.service_offering_id):
            raise ValidationError('Для SERVICE укажите услугу или предложение подрядчика.')


class EstimationPreparationTransfer(TimeStampedModel):
    """Журнал явной передачи снимка плана в документ подготовки."""

    STATUS_SUCCESS = 'success'
    STATUS_PARTIAL = 'partial'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = (
        (STATUS_SUCCESS, 'Успешно'),
        (STATUS_PARTIAL, 'Частично'),
        (STATUS_FAILED, 'Ошибка'),
    )

    snapshot = models.ForeignKey(
        EstimationPlanSnapshot,
        on_delete=models.CASCADE,
        related_name='transfers',
        verbose_name='Снимок плана',
    )
    preparation = models.ForeignKey(
        CarPreparation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='estimation_engine_transfers',
        verbose_name='Подготовка',
    )
    status = models.CharField('Статус', max_length=16, choices=STATUS_CHOICES, db_index=True)
    created_packages = models.PositiveIntegerField('Создано пакетов', default=0)
    created_work_items = models.PositiveIntegerField('Создано работ', default=0)
    updated_work_items = models.PositiveIntegerField('Обновлено работ', default=0)
    created_materials = models.PositiveIntegerField('Создано материалов', default=0)
    skipped_lines = models.PositiveIntegerField('Пропущено строк', default=0)
    error_message = models.TextField('Ошибка', blank=True, default='')
    details = models.JSONField('Детали', default=dict, blank=True)

    class Meta:
        db_table = 'ee_estimation_preparation_transfer'
        verbose_name = 'Передача плана в подготовку'
        verbose_name_plural = 'Передачи планов в подготовку'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['snapshot', 'status']),
            models.Index(fields=['preparation']),
        ]

    def __str__(self):
        return f'Transfer #{self.pk} snapshot={self.snapshot_id} ({self.status})'


# ---------------------------------------------------------------------------
# Справочники элементов схемы и типов повреждений
# ---------------------------------------------------------------------------


class SchemeElement(TimeStampedModel):
    """
    Канонический элемент осмотра (крыло, бампер, дверь…).

    Полигоны RegInfoBody привязываются через SchemeElementPolygon.
    В правилах выбирается этот справочник, а не свободный текст.
    """

    SECTION_CHOICES = PreparationWorkPackage.SECTION_CHOICES

    code = models.CharField('Код', max_length=64, unique=True)
    name = models.CharField('Наименование', max_length=256)
    section = models.CharField(
        'Раздел',
        max_length=32,
        choices=SECTION_CHOICES,
        default=PreparationWorkPackage.SECTION_EXTERIOR,
        db_index=True,
    )
    description = models.CharField('Описание', max_length=512, blank=True, default='')
    is_active = models.BooleanField('Активен', default=True, db_index=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        db_table = 'ee_scheme_element'
        verbose_name = 'Элемент схемы'
        verbose_name_plural = 'Элементы схемы'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f'{self.code} / {self.name}'


class SchemeElementPolygon(TimeStampedModel):
    """Связка канонического элемента с полигоном RegInfoBody."""

    element = models.ForeignKey(
        SchemeElement,
        on_delete=models.CASCADE,
        related_name='polygons',
        verbose_name='Элемент',
    )
    info_body = models.ForeignKey(
        'register.RegInfoBody',
        on_delete=models.CASCADE,
        related_name='scheme_element_links',
        verbose_name='Полигон (RegInfoBody)',
    )
    is_active = models.BooleanField('Активна', default=True)

    class Meta:
        db_table = 'ee_scheme_element_polygon'
        verbose_name = 'Полигон элемента'
        verbose_name_plural = 'Полигоны элементов'
        constraints = [
            models.UniqueConstraint(
                fields=['element', 'info_body'],
                name='ee_element_polygon_unique',
            ),
        ]

    def __str__(self):
        return f'{self.element_id} ↔ {self.info_body_id}'


class DamageType(TimeStampedModel):
    """
    Тип повреждения: вмятина, царапина, ржавчина и т.д.

    code — стабильный ключ для правил; name — подпись в UI.
    """

    SECTION_EXTERIOR = PreparationWorkPackage.SECTION_EXTERIOR
    SECTION_INTERIOR = PreparationWorkPackage.SECTION_INTERIOR
    SECTION_COMMON = PreparationWorkPackage.SECTION_COMMON
    SECTION_CHOICES = (
        (SECTION_EXTERIOR, 'Кузов / внешний'),
        (SECTION_INTERIOR, 'Салон / внутренний'),
        (SECTION_COMMON, 'Общий'),
    )

    code = models.CharField('Код', max_length=64, unique=True)
    name = models.CharField('Наименование', max_length=128)
    section = models.CharField(
        'Раздел',
        max_length=32,
        choices=SECTION_CHOICES,
        default=SECTION_EXTERIOR,
        db_index=True,
    )
    legacy_label = models.CharField(
        'Метка в legacy-оценке',
        max_length=128,
        blank=True,
        default='',
        help_text='Как называется в текущем UI осмотра, например «вмятина сильная».',
    )
    severity = models.PositiveSmallIntegerField(
        'Тяжесть',
        default=1,
        help_text='1 — лёгкая, выше — тяжелее',
    )
    requires_photo = models.BooleanField(
        'Обязательное фото',
        default=False,
        help_text='В новом UI осмотра отметка без фото считается незавершённой.',
    )
    is_active = models.BooleanField('Активен', default=True, db_index=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        db_table = 'ee_damage_type'
        verbose_name = 'Тип повреждения'
        verbose_name_plural = 'Типы повреждений'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f'{self.code} / {self.name}'


# ---------------------------------------------------------------------------
# Правила подбора пакетов (MVP) + preview
# ---------------------------------------------------------------------------


class EstimationRule(TimeStampedModel):
    """
    Правило: факты осмотра → пакет(ы) работ.

    Базовые поля (раздел, элемент, …) всегда связываются через И.
    Дополнительно — цепочка EstimationRuleCondition с И/ИЛИ между строками.
    Сумма в preview = н/ч × ставка + unit_cost строк, либо fixed_cost на связи.
    """

    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_ARCHIVED = 'archived'
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Черновик'),
        (STATUS_PUBLISHED, 'Опубликовано'),
        (STATUS_ARCHIVED, 'Архив'),
    )

    SECTION_ANY = ''
    SECTION_CHOICES = (
        (SECTION_ANY, 'Любой раздел'),
    ) + PreparationWorkPackage.SECTION_CHOICES

    code = models.CharField('Код', max_length=64, unique=True)
    name = models.CharField('Наименование', max_length=512)
    description = models.TextField('Описание', blank=True, default='')
    status = models.CharField(
        'Статус',
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    priority = models.PositiveIntegerField(
        'Приоритет',
        default=100,
        help_text='Больше = важнее. При конфликте exclusive_group побеждает больший приоритет.',
    )
    exclusive_group = models.CharField(
        'Группа взаимоисключения',
        max_length=64,
        blank=True,
        default='',
        db_index=True,
        help_text='В одной группе срабатывает только одно правило (с макс. приоритетом).',
    )

    section = models.CharField(
        'Раздел осмотра',
        max_length=32,
        blank=True,
        default='',
        choices=SECTION_CHOICES,
    )
    element = models.ForeignKey(
        SchemeElement,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='rules',
        verbose_name='Элемент схемы',
    )
    element_code = models.CharField(
        'Код элемента (кэш)',
        max_length=64,
        blank=True,
        default='',
        help_text='Заполняется из справочника; можно оставить пустым = любой элемент.',
    )
    damage_type_ref = models.ForeignKey(
        DamageType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='rules',
        verbose_name='Тип повреждения',
    )
    damage_type = models.CharField(
        'Код повреждения (кэш)',
        max_length=64,
        blank=True,
        default='',
        help_text='Заполняется из справочника.',
    )
    min_damage_count = models.PositiveIntegerField(
        'Мин. кол-во повреждений (всего)',
        default=0,
        help_text='0 = не проверять общий счётчик. Для счётчиков по типам используйте доп. условия.',
    )
    body_type = models.CharField(
        'Типы кузова (кэш)',
        max_length=512,
        blank=True,
        default='',
        help_text='Кэш названий из body_types; пусто = любой. Не редактировать вручную.',
    )
    body_types = models.ManyToManyField(
        'refs.RefTypeBody',
        blank=True,
        related_name='estimation_rules',
        verbose_name='Типы кузова',
        help_text='Можно выбрать несколько. Пусто = любой тип кузова.',
    )
    price_group = models.CharField(
        'Ценовая группа',
        max_length=32,
        blank=True,
        default='',
        help_text='Например: 2000, 4000',
    )
    paint_type = models.CharField('Тип краски', max_length=64, blank=True, default='')
    under_instrument = models.BooleanField(
        'Только «под прибор»',
        default=False,
        help_text='Если включено — правило срабатывает только при факте under_instrument=true.',
    )

    # Опции комплектации (лобовое и т.п.): пусто = не проверять, yes/no = строгое совпадение.
    FLAG_ANY = ''
    FLAG_YES = 'yes'
    FLAG_NO = 'no'
    FLAG_CHOICES = (
        (FLAG_ANY, 'Любое'),
        (FLAG_YES, 'Да'),
        (FLAG_NO, 'Нет'),
    )
    windshield_heat = models.CharField(
        'Подогрев лобового',
        max_length=8,
        blank=True,
        default=FLAG_ANY,
        choices=FLAG_CHOICES,
        help_text='Условие по комплектации. Для 4 вариантов стекла задайте yes/no '
                  'и одну exclusive_group (например windshield).',
    )
    windshield_projection = models.CharField(
        'Проекция на лобовое',
        max_length=8,
        blank=True,
        default=FLAG_ANY,
        choices=FLAG_CHOICES,
        help_text='HUD / проекция. Пусто = не учитывать в условии.',
    )

    # Химчистка / вариант салона — коды как в page_salon.cleaning_int / type_salon_int.
    CLEANING_ANY = ''
    CLEANING_NONE = '0'
    CLEANING_HARD = '1'
    CLEANING_MEDIUM = '2'
    CLEANING_LIGHT = '3'
    CLEANING_CHOICES = (
        (CLEANING_ANY, 'Любая'),
        (CLEANING_NONE, 'Не требуется'),
        (CLEANING_LIGHT, 'Лёгкая'),
        (CLEANING_MEDIUM, 'Средняя'),
        (CLEANING_HARD, 'Сложная'),
    )
    SALON_ANY = ''
    SALON_FABRIC = '0'
    SALON_LEATHER = '1'
    SALON_TYPE_CHOICES = (
        (SALON_ANY, 'Любой'),
        (SALON_FABRIC, 'Ткань'),
        (SALON_LEATHER, 'Кожа'),
    )
    cleaning_level = models.CharField(
        'Степень химчистки',
        max_length=8,
        blank=True,
        default=CLEANING_ANY,
        choices=CLEANING_CHOICES,
        help_text='Как cleaning_int в осмотре салона. Пусто = не учитывать.',
    )
    salon_type = models.CharField(
        'Вариант салона',
        max_length=8,
        blank=True,
        default=SALON_ANY,
        choices=SALON_TYPE_CHOICES,
        help_text='Как type_salon_int: 0 — ткань, 1 — кожа. Пусто = не учитывать.',
    )

    # Диагностика — коды как в page_test_drive (engine/gear/…).
    DIAG_SYSTEM_ANY = ''
    DIAG_SYSTEM_ENGINE = 'engine'
    DIAG_SYSTEM_SYSTEM_OG = 'system_og'
    DIAG_SYSTEM_GEAR = 'gear'
    DIAG_SYSTEM_SUSPENSION = 'suspension'
    DIAG_SYSTEM_CONDITIONER = 'conditioner'
    DIAG_SYSTEM_CHOICES = (
        (DIAG_SYSTEM_ANY, 'Любая система'),
        (DIAG_SYSTEM_ENGINE, 'Двигатель'),
        (DIAG_SYSTEM_SYSTEM_OG, 'Система выпуска ОГ'),
        (DIAG_SYSTEM_GEAR, 'КПП'),
        (DIAG_SYSTEM_SUSPENSION, 'Подвеска'),
        (DIAG_SYSTEM_CONDITIONER, 'Кондиционер'),
    )
    DIAG_STATUS_ANY = ''
    DIAG_STATUS_BROKEN = '0'
    DIAG_STATUS_OK = '1'
    DIAG_STATUS_REMARKS = '2'
    DIAG_STATUS_CHOICES = (
        (DIAG_STATUS_ANY, 'Любой статус'),
        (DIAG_STATUS_OK, 'Исправен'),
        (DIAG_STATUS_BROKEN, 'Не исправен'),
        (DIAG_STATUS_REMARKS, 'Есть замечания'),
    )
    diagnostic_system = models.CharField(
        'Система диагностики',
        max_length=32,
        blank=True,
        default=DIAG_SYSTEM_ANY,
        choices=DIAG_SYSTEM_CHOICES,
        help_text='Узел из тест-драйва / диагностики. Пусто = не учитывать.',
    )
    diagnostic_status = models.CharField(
        'Статус диагностики',
        max_length=8,
        blank=True,
        default=DIAG_STATUS_ANY,
        choices=DIAG_STATUS_CHOICES,
        help_text='0 — не исправен, 1 — исправен, 2 — есть замечания. '
                  'Имеет смысл вместе с системой.',
    )

    hour_rate = models.DecimalField(
        'Ставка н/ч, ₽',
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Для строк WORK в preview: нормочасы × ставка.',
    )
    packages = models.ManyToManyField(
        PreparationWorkPackage,
        through='EstimationRulePackage',
        related_name='rules',
        verbose_name='Пакеты работ',
        blank=True,
    )
    is_active = models.BooleanField('Активно', default=True, db_index=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        db_table = 'ee_estimation_rule'
        verbose_name = 'Правило подбора пакетов'
        verbose_name_plural = 'Правила подбора пакетов'
        ordering = ['-priority', 'code']
        indexes = [
            models.Index(fields=['status', 'is_active', 'priority']),
            models.Index(fields=['exclusive_group', 'priority']),
            models.Index(fields=['section', 'element_code', 'damage_type']),
        ]

    def __str__(self):
        return f'{self.code} / {self.name}'

    def sync_condition_codes(self):
        """Кэш кодов для движка match."""
        if self.element_id:
            self.element_code = self.element.code
        if self.damage_type_ref_id:
            self.damage_type = self.damage_type_ref.code

    def sync_body_type_cache(self):
        """Кэш названий выбранных типов кузова (после M2M save)."""
        if not self.pk:
            return
        names = list(self.body_types.order_by('name').values_list('name', flat=True))
        cache = ', '.join(names)[:512]
        if self.body_type != cache:
            type(self).objects.filter(pk=self.pk).update(body_type=cache)
            self.body_type = cache

    def clean(self):
        if self.hour_rate is not None and self.hour_rate < 0:
            raise ValidationError({'hour_rate': 'Ставка не может быть отрицательной.'})
        if self.min_damage_count is not None and self.min_damage_count < 0:
            raise ValidationError({'min_damage_count': 'Не может быть отрицательным.'})

    def save(self, *args, **kwargs):
        self.sync_condition_codes()
        super().save(*args, **kwargs)


class EstimationRuleCondition(TimeStampedModel):
    """
    Строка условия правила.

    Первая строка — без join; у следующих join_op связывает с результатом слева
    (левоассоциативно: A И B ИЛИ C = (A И B) ИЛИ C).
    """

    JOIN_AND = 'and'
    JOIN_OR = 'or'
    JOIN_CHOICES = (
        (JOIN_AND, 'И'),
        (JOIN_OR, 'ИЛИ'),
    )

    FIELD_DAMAGE_TYPE_COUNT = 'damage_type_count'
    FIELD_DAMAGE_COUNT = 'damage_count'
    FIELD_ELEMENT = 'element_code'
    FIELD_SECTION = 'section'
    FIELD_PRICE_GROUP = 'price_group'
    FIELD_BODY_TYPE = 'body_type'
    FIELD_PAINT_TYPE = 'paint_type'
    FIELD_UNDER_INSTRUMENT = 'under_instrument'
    FIELD_WINDSHIELD_HEAT = 'windshield_heat'
    FIELD_WINDSHIELD_PROJECTION = 'windshield_projection'
    FIELD_CLEANING_LEVEL = 'cleaning_level'
    FIELD_SALON_TYPE = 'salon_type'
    FIELD_DIAGNOSTIC_SYSTEM = 'diagnostic_system'
    FIELD_DIAGNOSTIC_STATUS = 'diagnostic_status'
    FIELD_CHOICES = (
        (FIELD_DAMAGE_TYPE_COUNT, 'Кол-во по типу повреждения'),
        (FIELD_DAMAGE_COUNT, 'Кол-во повреждений (всего)'),
        (FIELD_ELEMENT, 'Код элемента'),
        (FIELD_SECTION, 'Раздел'),
        (FIELD_PRICE_GROUP, 'Ценовая группа'),
        (FIELD_BODY_TYPE, 'Тип кузова'),
        (FIELD_PAINT_TYPE, 'Тип краски'),
        (FIELD_UNDER_INSTRUMENT, 'Под прибор'),
        (FIELD_WINDSHIELD_HEAT, 'Подогрев лобового'),
        (FIELD_WINDSHIELD_PROJECTION, 'Проекция на лобовое'),
        (FIELD_CLEANING_LEVEL, 'Степень химчистки'),
        (FIELD_SALON_TYPE, 'Вариант салона'),
        (FIELD_DIAGNOSTIC_SYSTEM, 'Система диагностики'),
        (FIELD_DIAGNOSTIC_STATUS, 'Статус диагностики'),
    )

    OP_EQ = 'eq'
    OP_NE = 'ne'
    OP_GT = 'gt'
    OP_GTE = 'gte'
    OP_LT = 'lt'
    OP_LTE = 'lte'
    OP_ABSENT = 'absent'
    OP_PRESENT = 'present'
    OPERATOR_CHOICES = (
        (OP_EQ, '='),
        (OP_NE, '≠'),
        (OP_GT, '>'),
        (OP_GTE, '≥'),
        (OP_LT, '<'),
        (OP_LTE, '≤'),
        (OP_ABSENT, 'нет (0 / ложь)'),
        (OP_PRESENT, 'есть (>0 / истина)'),
    )

    rule = models.ForeignKey(
        EstimationRule,
        on_delete=models.CASCADE,
        related_name='conditions',
        verbose_name='Правило',
    )
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    join_op = models.CharField(
        'Связка с предыдущим',
        max_length=8,
        choices=JOIN_CHOICES,
        default=JOIN_AND,
        help_text='Для первой строки не используется.',
    )
    field = models.CharField(
        'Поле',
        max_length=32,
        choices=FIELD_CHOICES,
        default=FIELD_DAMAGE_TYPE_COUNT,
    )
    damage_type_ref = models.ForeignKey(
        DamageType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='rule_conditions',
        verbose_name='Тип повреждения',
        help_text='Нужен для поля «Кол-во по типу повреждения».',
    )
    damage_type = models.CharField(
        'Код повреждения (кэш)',
        max_length=64,
        blank=True,
        default='',
    )
    operator = models.CharField(
        'Оператор',
        max_length=16,
        choices=OPERATOR_CHOICES,
        default=OP_GTE,
    )
    value = models.CharField(
        'Значение',
        max_length=64,
        blank=True,
        default='',
        help_text='Число или текст. Для «нет/есть» можно оставить пустым.',
    )
    is_active = models.BooleanField('Активно', default=True)

    class Meta:
        db_table = 'ee_estimation_rule_condition'
        verbose_name = 'Условие правила'
        verbose_name_plural = 'Условия правил'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.rule_id}: {self.field} {self.operator} {self.value}'

    def sync_codes(self):
        if self.damage_type_ref_id:
            self.damage_type = self.damage_type_ref.code

    def clean(self):
        if self.field == self.FIELD_DAMAGE_TYPE_COUNT and not (
            self.damage_type_ref_id or self.damage_type
        ):
            raise ValidationError({
                'damage_type_ref': 'Укажите тип повреждения для счётчика.',
            })
        if self.operator in (self.OP_GT, self.OP_GTE, self.OP_LT, self.OP_LTE, self.OP_EQ, self.OP_NE):
            if self.field in (
                self.FIELD_DAMAGE_TYPE_COUNT,
                self.FIELD_DAMAGE_COUNT,
            ) and str(self.value or '').strip() == '':
                raise ValidationError({'value': 'Укажите число для сравнения.'})

    def save(self, *args, **kwargs):
        self.sync_codes()
        super().save(*args, **kwargs)


class EstimationRulePackage(TimeStampedModel):
    """Связь правила с пакетом работ."""

    rule = models.ForeignKey(
        EstimationRule,
        on_delete=models.CASCADE,
        related_name='rule_packages',
        verbose_name='Правило',
    )
    package = models.ForeignKey(
        PreparationWorkPackage,
        on_delete=models.PROTECT,
        related_name='rule_links',
        verbose_name='Пакет работ',
    )
    fixed_cost = models.DecimalField(
        'Фикс. стоимость пакета, ₽',
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Если задано — в preview берётся эта сумма вместо построчного расчёта.',
    )
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Активна', default=True)

    class Meta:
        db_table = 'ee_estimation_rule_package'
        verbose_name = 'Пакет в правиле'
        verbose_name_plural = 'Пакеты в правилах'
        ordering = ['sort_order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['rule', 'package'],
                name='ee_rule_package_unique',
            ),
        ]

    def __str__(self):
        return f'{self.rule_id} → {self.package_id}'

    def clean(self):
        if self.fixed_cost is not None and self.fixed_cost < 0:
            raise ValidationError({'fixed_cost': 'Стоимость не может быть отрицательной.'})
