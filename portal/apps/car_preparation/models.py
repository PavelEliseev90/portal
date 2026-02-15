"""
Модели для автоматизации и мобильности работы отдела подготовки автомобилей
"""
from django.db import models
from django.conf import settings
from datetime import datetime, timedelta
from refs.models import RefUnit, RefStaff, RefCarsOrganization, RefStatusCarsOrganization
from changelog.mixins import ChangeloggableMixin
from django.db.models.signals import post_delete, post_save
from changelog.signals import journal_save_handler, journal_delete_handler


# ===========================================
# СПРАВОЧНИКИ
# ===========================================

class RefCarPreparationStage(models.Model):
    """Этап подготовки автомобиля"""
    name = models.CharField("Наименование этапа", max_length=250, default='')
    code = models.CharField("Код", max_length=50, default='', unique=False)
    sort_order = models.IntegerField("Порядок сортировки", default=0)
    description = models.TextField("Описание", max_length=2000, blank=True, default='')
    is_active = models.BooleanField("Активен", default=True)
    required = models.BooleanField("Обязательный этап", default=True)
    estimated_time = models.IntegerField("Оценка времени в минутах", default=0, blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'refCarPreparationStage'
        verbose_name = "Этап подготовки"
        verbose_name_plural = "Этапы подготовки"
        ordering = ['sort_order']


class RefCarPreparationWork(models.Model):
    """Виды работ по подготовке автомобиля"""
    stage = models.ForeignKey(RefCarPreparationStage, null=True, on_delete=models.SET_NULL, 
                             verbose_name="Этап подготовки", related_name='works')
    name = models.CharField("Наименование работы", max_length=512, default='')
    code = models.CharField("Код", max_length=50, null=True, blank=True, default=None)
    description = models.TextField("Описание работы", max_length=2000, blank=True, default='')
    sort_order = models.IntegerField("Порядок сортировки", default=0)
    is_active = models.BooleanField("Активна", default=True)
    default_required = models.BooleanField("Обязательна по умолчанию", default=False)
    estimated_time = models.IntegerField("Оценка времени в минутах", default=0, blank=True)
    
    def __str__(self):
        if self.stage:
            return f"{self.stage.name} - {self.name}"
        return self.name
    
    class Meta:
        db_table = 'refCarPreparationWork'
        verbose_name = "Работа по подготовке"
        verbose_name_plural = "Работы по подготовке"
        ordering = ['stage__sort_order', 'sort_order']


class RefCarPreparationStatus(models.Model):
    """Статусы подготовки автомобиля"""
    name = models.CharField("Наименование", max_length=250, default='')
    code = models.CharField("Код", max_length=50, default='', unique=True)
    color = models.CharField("Цвет (HEX)", max_length=7, default='#000000', 
                            help_text="Цвет для отображения в интерфейсе")
    is_final = models.BooleanField("Финальный статус", default=False, 
                                   help_text="Подготовка завершена")
    can_edit = models.BooleanField("Можно редактировать", default=True,
                                  help_text="Можно редактировать после установки статуса")
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'refCarPreparationStatus'
        verbose_name = "Статус подготовки"
        verbose_name_plural = "Статусы подготовки"


# ===========================================
# ОСНОВНЫЕ МОДЕЛИ
# ===========================================

class CarPreparation(ChangeloggableMixin, models.Model):
    """Подготовка автомобиля"""
    car = models.ForeignKey(RefCarsOrganization, on_delete=models.PROTECT, 
                           verbose_name="Автомобиль", related_name='preparations')
    unit = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL, 
                            verbose_name="Подразделение")
    
    # Статусы и этапы
    status = models.ForeignKey(RefCarPreparationStatus, null=True, on_delete=models.SET_NULL,
                              verbose_name="Статус подготовки")
    current_stage = models.ForeignKey(RefCarPreparationStage, null=True, on_delete=models.SET_NULL,
                                      verbose_name="Текущий этап")
    
    # Даты
    date_start = models.DateTimeField('Дата начала подготовки', null=True, blank=True)
    date_planned_end = models.DateTimeField('Планируемая дата окончания', null=True, blank=True)
    date_end = models.DateTimeField('Дата окончания подготовки', null=True, blank=True)
    date_created = models.DateTimeField('Дата создания', default=datetime.now)
    date_updated = models.DateTimeField('Дата обновления', auto_now=True)
    
    # Ответственные
    responsible = models.ForeignKey(RefStaff, null=True, on_delete=models.SET_NULL,
                                   verbose_name="Ответственный", related_name='preparations_responsible')
    inspector = models.ForeignKey(RefStaff, null=True, on_delete=models.SET_NULL, blank=True,
                                 verbose_name="Инспектор качества", 
                                 related_name='preparations_inspected')
    
    # Комментарии и описание
    comment_initial = models.TextField("Комментарий при создании", max_length=5000, blank=True, default='')
    comment_final = models.TextField("Комментарий при завершении", max_length=5000, blank=True, default='')
    quality_notes = models.TextField("Заметки по качеству", max_length=5000, blank=True, default='')
    
    # Мобильность
    qr_code = models.CharField("QR код", max_length=100, blank=True, default='')
    mobile_created = models.BooleanField("Создано с мобильного", default=False)
    mobile_last_sync = models.DateTimeField('Последняя синхронизация с мобильного', null=True, blank=True)
    
    # Прогресс
    progress_percent = models.IntegerField("Прогресс выполнения (%)", default=0)
    
    # Планирование
    scheduled_start = models.DateTimeField('Планируемое время начала подготовки', null=True, blank=True)
    scheduled_end = models.DateTimeField('Планируемое время окончания подготовки', null=True, blank=True)
    
    def calculate_progress(self):
        """Расчет процента выполнения"""
        total_works = self.work_items.filter(work__is_active=True).count()
        if total_works == 0:
            return 0
        completed_works = self.work_items.filter(
            work__is_active=True, 
            status='completed'
        ).count()
        return int((completed_works / total_works) * 100)
    
    def get_total_time(self):
        """Общее время на подготовку"""
        return self.work_items.aggregate(
            total=models.Sum('actual_time')
        )['total'] or 0
    
    def get_total_cost(self):
        """Общая стоимость подготовки"""
        return self.work_items.aggregate(
            total=models.Sum('cost')
        )['total'] or 0
    
    def is_overdue(self):
        """Проверка просрочки"""
        if self.date_planned_end and not self.date_end:
            return datetime.now() > self.date_planned_end
        return False
    
    def __str__(self):
        return f"Подготовка {self.car} - {self.status}"
    
    class Meta:
        db_table = 'carPreparation'
        verbose_name = "Подготовка автомобиля"
        verbose_name_plural = "Подготовки автомобилей"
        indexes = [
            models.Index(fields=['car']),
            models.Index(fields=['status']),
            models.Index(fields=['date_start']),
            models.Index(fields=['qr_code']),
        ]
        ordering = ['-date_created']


class CarPreparationWorkItem(ChangeloggableMixin, models.Model):
    """Пункт работы по подготовке"""
    STATUS_CHOICES = [
        ('pending', 'Ожидает выполнения'),
        ('in_progress', 'В работе'),
        ('completed', 'Выполнено'),
        ('rejected', 'Отклонено'),
        ('skipped', 'Пропущено'),
    ]
    
    QUALITY_CHOICES = [
        ('excellent', 'Отлично'),
        ('good', 'Хорошо'),
        ('satisfactory', 'Удовлетворительно'),
        ('poor', 'Плохо'),
    ]
    
    preparation = models.ForeignKey(CarPreparation, on_delete=models.CASCADE,
                                   verbose_name="Подготовка", related_name='work_items')
    work = models.ForeignKey(RefCarPreparationWork, on_delete=models.PROTECT,
                            verbose_name="Вид работы")
    
    # Статус и качество
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='pending')
    quality = models.CharField("Качество выполнения", max_length=20, choices=QUALITY_CHOICES, 
                              blank=True, null=True)
    
    # Подтверждение работы для планирования
    is_confirmed = models.BooleanField("Подтверждена для выполнения", default=True,
                                      help_text="Если отключено, работа не будет включена в планирование")
    confirmed_by = models.ForeignKey(RefStaff, null=True, blank=True, on_delete=models.SET_NULL,
                                     verbose_name="Подтвердил", related_name='confirmed_preparation_works')
    confirmed_at = models.DateTimeField('Дата подтверждения', null=True, blank=True)
    confirmation_comment = models.CharField("Комментарий подтверждения", max_length=1000, blank=True, default='')
    
    # Время
    planned_time = models.IntegerField("Планируемое время (мин)", default=0, blank=True)
    actual_time = models.IntegerField("Фактическое время (мин)", default=0, blank=True)
    date_start = models.DateTimeField('Дата начала', null=True, blank=True)
    date_end = models.DateTimeField('Дата окончания', null=True, blank=True)
    
    # Стоимость
    cost = models.DecimalField("Стоимость", max_digits=10, decimal_places=2, default=0.00, blank=True)
    
    # Ответственный
    performer = models.ForeignKey(RefStaff, null=True, on_delete=models.SET_NULL, blank=True,
                                 verbose_name="Исполнитель", related_name='preparation_works')
    
    # Комментарии
    comment = models.TextField("Комментарий", max_length=2000, blank=True, default='')
    rejection_reason = models.TextField("Причина отклонения", max_length=1000, blank=True, default='')
    
    # Фотофиксация
    has_photos = models.BooleanField("Есть фотографии", default=False)
    
    # Мобильность
    mobile_updated = models.BooleanField("Обновлено с мобильного", default=False)
    mobile_updated_at = models.DateTimeField('Дата обновления с мобильного', null=True, blank=True)
    
    def __str__(self):
        return f"{self.preparation.car} - {self.work.name}"
    
    class Meta:
        db_table = 'carPreparationWorkItem'
        verbose_name = "Работа по подготовке"
        verbose_name_plural = "Работы по подготовке"
        indexes = [
            models.Index(fields=['preparation']),
            models.Index(fields=['status']),
            models.Index(fields=['work']),
        ]
        ordering = ['work__stage__sort_order', 'work__sort_order']


class CarPreparationPhoto(models.Model):
    """Фотографии этапов подготовки"""
    work_item = models.ForeignKey(CarPreparationWorkItem, on_delete=models.CASCADE,
                                verbose_name="Работа", related_name='photos')
    preparation = models.ForeignKey(CarPreparation, on_delete=models.CASCADE,
                                   verbose_name="Подготовка", related_name='photos')
    
    photo = models.ImageField(upload_to='car_preparation/%Y/%m/%d/', 
                             verbose_name="Фотография", max_length=255)
    photo_thumbnail = models.ImageField(upload_to='car_preparation/thumbs/%Y/%m/%d/', 
                                      verbose_name="Миниатюра", max_length=255, blank=True, null=True)
    
    description = models.CharField("Описание", max_length=500, blank=True, default='')
    date_created = models.DateTimeField('Дата создания', default=datetime.now)
    
    # Метаданные
    latitude = models.FloatField("Широта", null=True, blank=True)
    longitude = models.FloatField("Долгота", null=True, blank=True)
    device_info = models.CharField("Информация об устройстве", max_length=200, blank=True, default='')
    
    # Автор
    created_by = models.ForeignKey(RefStaff, null=True, on_delete=models.SET_NULL,
                                  verbose_name="Автор фотографии")
    
    def __str__(self):
        return f"Фото {self.work_item.work.name} - {self.date_created}"
    
    class Meta:
        db_table = 'carPreparationPhoto'
        verbose_name = "Фотография подготовки"
        verbose_name_plural = "Фотографии подготовки"
        ordering = ['-date_created']


class CarPreparationChecklist(ChangeloggableMixin, models.Model):
    """Чек-лист контроля качества подготовки"""
    preparation = models.OneToOneField(CarPreparation, on_delete=models.CASCADE,
                                      verbose_name="Подготовка", related_name='checklist')
    
    # Общие оценки
    overall_quality = models.IntegerField("Общая оценка качества (1-10)", default=0)
    cleanliness_score = models.IntegerField("Оценка чистоты (1-10)", default=0)
    completeness_score = models.IntegerField("Оценка комплектности (1-10)", default=0)
    defect_score = models.IntegerField("Оценка отсутствия дефектов (1-10)", default=0)
    
    # Проверки
    exterior_checked = models.BooleanField("Проверен экстерьер", default=False)
    interior_checked = models.BooleanField("Проверен интерьер", default=False)
    technical_checked = models.BooleanField("Проверена техника", default=False)
    documents_checked = models.BooleanField("Проверены документы", default=False)
    
    # Замечания
    defects_found = models.TextField("Обнаруженные дефекты", max_length=5000, blank=True, default='')
    recommendations = models.TextField("Рекомендации", max_length=5000, blank=True, default='')
    
    # Проверяющий
    checked_by = models.ForeignKey(RefStaff, null=True, on_delete=models.SET_NULL,
                                  verbose_name="Проверил", related_name='preparation_checklists')
    date_checked = models.DateTimeField('Дата проверки', null=True, blank=True)
    
    approved = models.BooleanField("Утверждено", default=False)
    approved_by = models.ForeignKey(RefStaff, null=True, blank=True, on_delete=models.SET_NULL,
                                   verbose_name="Утвердил", related_name='preparation_approvals')
    date_approved = models.DateTimeField('Дата утверждения', null=True, blank=True)
    
    def __str__(self):
        return f"Чек-лист {self.preparation}"
    
    class Meta:
        db_table = 'carPreparationChecklist'
        verbose_name = "Чек-лист подготовки"
        verbose_name_plural = "Чек-листы подготовки"


class CarPreparationTemplate(models.Model):
    """Шаблон подготовки автомобиля"""
    name = models.CharField("Наименование шаблона", max_length=250, default='')
    description = models.TextField("Описание", max_length=2000, blank=True, default='')
    
    # Условия применения
    unit = models.ForeignKey(RefUnit, null=True, blank=True, on_delete=models.SET_NULL,
                           verbose_name="Подразделение (если пусто - для всех)")
    car_type = models.CharField("Тип автомобиля", max_length=50, blank=True, default='',
                               help_text="new, used, trade-in")
    
    # Этапы и работы
    stages = models.ManyToManyField(RefCarPreparationStage, verbose_name="Этапы",
                                   related_name='templates')
    works = models.ManyToManyField(RefCarPreparationWork, through='CarPreparationTemplateWork',
                                  verbose_name="Работы")
    
    is_active = models.BooleanField("Активен", default=True)
    is_default = models.BooleanField("Шаблон по умолчанию", default=False)
    
    date_created = models.DateTimeField('Дата создания', default=datetime.now)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'carPreparationTemplate'
        verbose_name = "Шаблон подготовки"
        verbose_name_plural = "Шаблоны подготовки"


class CarPreparationTemplateWork(models.Model):
    """Работа в шаблоне подготовки"""
    template = models.ForeignKey(CarPreparationTemplate, on_delete=models.CASCADE)
    work = models.ForeignKey(RefCarPreparationWork, on_delete=models.CASCADE)
    
    is_required = models.BooleanField("Обязательна", default=True)
    planned_time = models.IntegerField("Планируемое время (мин)", default=0, blank=True)
    default_cost = models.DecimalField("Стоимость по умолчанию", max_digits=10, 
                                      decimal_places=2, default=0.00, blank=True)
    sort_order = models.IntegerField("Порядок", default=0)
    
    class Meta:
        db_table = 'carPreparationTemplateWork'
        verbose_name = "Работа в шаблоне"
        verbose_name_plural = "Работы в шаблонах"
        unique_together = ['template', 'work']
        ordering = ['sort_order']


class CarPreparationHistory(models.Model):
    """История изменений подготовки"""
    preparation = models.ForeignKey(CarPreparation, on_delete=models.CASCADE,
                                   verbose_name="Подготовка", related_name='history')
    
    action = models.CharField("Действие", max_length=100)
    field_name = models.CharField("Поле", max_length=100, blank=True)
    old_value = models.TextField("Старое значение", max_length=5000, blank=True)
    new_value = models.TextField("Новое значение", max_length=5000, blank=True)
    
    user = models.ForeignKey(RefStaff, null=True, on_delete=models.SET_NULL,
                            verbose_name="Пользователь")
    date = models.DateTimeField('Дата', default=datetime.now)
    
    comment = models.TextField("Комментарий", max_length=2000, blank=True, default='')
    
    class Meta:
        db_table = 'carPreparationHistory'
        verbose_name = "История подготовки"
        verbose_name_plural = "Истории подготовки"
        ordering = ['-date']


class CarPreparationNotification(models.Model):
    """Уведомления по подготовке"""
    preparation = models.ForeignKey(CarPreparation, on_delete=models.CASCADE,
                                   verbose_name="Подготовка", related_name='notifications',
                                   null=True, blank=True)
    work_item = models.ForeignKey('CarPreparationWorkItem', on_delete=models.CASCADE,
                                 verbose_name="Работа", related_name='notifications',
                                 null=True, blank=True)
    work_schedule = models.ForeignKey('CarPreparationWorkSchedule', on_delete=models.CASCADE,
                                     verbose_name="Расписание работы", related_name='notifications',
                                     null=True, blank=True)
    
    TYPE_CHOICES = [
        ('created', 'Создана'),
        ('started', 'Начата'),
        ('stage_changed', 'Изменен этап'),
        ('work_completed', 'Работа выполнена'),
        ('work_overdue', 'Работа просрочена'),
        ('work_upcoming', 'Работа должна начаться'),
        ('preparation_overdue', 'Подготовка просрочена'),
        ('preparation_completed', 'Завершена'),
        ('quality_check', 'Требуется проверка качества'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('normal', 'Обычный'),
        ('high', 'Высокий'),
        ('urgent', 'Срочный'),
    ]
    
    notification_type = models.CharField("Тип уведомления", max_length=50, choices=TYPE_CHOICES)
    priority = models.CharField("Приоритет", max_length=20, choices=PRIORITY_CHOICES, default='normal')
    message = models.TextField("Сообщение", max_length=2000)
    
    recipient = models.ForeignKey(RefStaff, null=True, on_delete=models.SET_NULL,
                                 verbose_name="Получатель")
    
    sent = models.BooleanField("Отправлено", default=False)
    date_sent = models.DateTimeField('Дата отправки', null=True, blank=True)
    date_created = models.DateTimeField('Дата создания', default=datetime.now)
    
    # Канал отправки
    channel_email = models.BooleanField("Email", default=False)
    channel_push = models.BooleanField("Push", default=False)
    channel_sms = models.BooleanField("SMS", default=False)
    
    read = models.BooleanField("Прочитано", default=False)
    date_read = models.DateTimeField('Дата прочтения', null=True, blank=True)
    
    # Автоматически создано
    auto_created = models.BooleanField("Автоматически создано", default=False)
    
    # Дополнительные данные (JSON)
    metadata = models.TextField("Метаданные", max_length=5000, blank=True, default='',
                               help_text="JSON данные для дополнительной информации")
    
    def __str__(self):
        prep_info = f" - {self.preparation.car}" if self.preparation else ""
        work_info = f" / {self.work_item.work.name}" if self.work_item else ""
        return f"{self.get_notification_type_display()}{prep_info}{work_info} - {self.recipient}"
    
    class Meta:
        db_table = 'carPreparationNotification'
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        indexes = [
            models.Index(fields=['recipient', 'read']),
            models.Index(fields=['notification_type', 'priority']),
            models.Index(fields=['date_created']),
        ]
        ordering = ['-date_created']


# ===========================================
# ПЛАНИРОВАНИЕ И КАЛЕНДАРЬ
# ===========================================

class CarPreparationWorkSchedule(ChangeloggableMixin, models.Model):
    """Планирование выполнения работы"""
    work_item = models.OneToOneField(CarPreparationWorkItem, on_delete=models.CASCADE,
                                     verbose_name="Работа", related_name='schedule')
    
    # Временные рамки
    planned_start = models.DateTimeField('Планируемое время начала', null=True, blank=True)
    planned_end = models.DateTimeField('Планируемое время окончания', null=True, blank=True)
    
    # Исполнитель
    planned_performer = models.ForeignKey(RefStaff, null=True, on_delete=models.SET_NULL,
                                         verbose_name="Планируемый исполнитель",
                                         related_name='planned_preparation_works')
    
    # Приоритет
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('normal', 'Обычный'),
        ('high', 'Высокий'),
        ('urgent', 'Срочный'),
    ]
    priority = models.CharField("Приоритет", max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    # Блокировка времени (для других работ)
    blocks_time = models.BooleanField("Блокирует время исполнителя", default=True,
                                     help_text="Если включено, исполнитель не может выполнять другие работы в это время")
    
    # Комментарии планирования
    planning_comment = models.TextField("Комментарий планировщика", max_length=2000, blank=True, default='')
    
    # Автоматическое планирование
    auto_scheduled = models.BooleanField("Автоматически запланировано", default=False)
    
    # Статус планирования
    PLANNING_STATUS_CHOICES = [
        ('not_scheduled', 'Не запланировано'),
        ('scheduled', 'Запланировано'),
        ('in_progress', 'В работе'),
        ('completed', 'Выполнено'),
        ('delayed', 'Отложено'),
        ('cancelled', 'Отменено'),
    ]
    planning_status = models.CharField("Статус планирования", max_length=20, 
                                      choices=PLANNING_STATUS_CHOICES, default='not_scheduled')
    
    date_created = models.DateTimeField('Дата создания', default=datetime.now)
    date_updated = models.DateTimeField('Дата обновления', auto_now=True)
    
    def get_duration_minutes(self):
        """Получить продолжительность в минутах"""
        if self.planned_start and self.planned_end:
            delta = self.planned_end - self.planned_start
            return int(delta.total_seconds() / 60)
        return 0
    
    def is_overlapping(self, other_schedule):
        """Проверка пересечения с другим расписанием"""
        if not self.planned_start or not self.planned_end:
            return False
        if not other_schedule.planned_start or not other_schedule.planned_end:
            return False
        
        # Проверка, что исполнитель совпадает и время блокируется
        if (self.planned_performer == other_schedule.planned_performer and 
            self.blocks_time and other_schedule.blocks_time):
            return (self.planned_start < other_schedule.planned_end and 
                   self.planned_end > other_schedule.planned_start)
        return False
    
    def __str__(self):
        return f"Расписание {self.work_item.work.name} - {self.planned_start}"
    
    class Meta:
        db_table = 'carPreparationWorkSchedule'
        verbose_name = "Расписание работы"
        verbose_name_plural = "Расписания работ"
        indexes = [
            models.Index(fields=['planned_start', 'planned_end']),
            models.Index(fields=['planned_performer']),
            models.Index(fields=['planning_status']),
        ]


class CarPreparationCalendar(ChangeloggableMixin, models.Model):
    """Календарь выполнения подготовок"""
    unit = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL,
                            verbose_name="Подразделение", related_name='preparation_calendars')
    
    # Период календаря
    date = models.DateField('Дата', db_index=True)
    
    # Количество работ
    total_preparations = models.IntegerField("Всего подготовок", default=0)
    active_preparations = models.IntegerField("Активных подготовок", default=0)
    completed_preparations = models.IntegerField("Завершенных подготовок", default=0)
    
    # Загрузка исполнителей
    performers_count = models.IntegerField("Количество занятых исполнителей", default=0)
    total_work_hours = models.DecimalField("Всего часов работы", max_digits=5, decimal_places=2, default=0.00)
    available_capacity = models.DecimalField("Доступная мощность (часов)", max_digits=5, decimal_places=2, default=8.00)
    
    # Статистика
    on_time_count = models.IntegerField("Выполнено в срок", default=0)
    delayed_count = models.IntegerField("Просрочено", default=0)
    
    date_updated = models.DateTimeField('Дата обновления', auto_now=True)
    
    def get_utilization_percent(self):
        """Получить процент загрузки"""
        if self.available_capacity > 0:
            return min(100, int((self.total_work_hours / self.available_capacity) * 100))
        return 0
    
    def __str__(self):
        return f"Календарь {self.unit} - {self.date}"
    
    class Meta:
        db_table = 'carPreparationCalendar'
        verbose_name = "Календарь подготовки"
        verbose_name_plural = "Календари подготовки"
        unique_together = ['unit', 'date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['unit', 'date']),
        ]
        ordering = ['date']


class CarPreparationResource(models.Model):
    """Ресурсы для планирования (исполнители, оборудование)"""
    RESOURCE_TYPE_CHOICES = [
        ('performer', 'Исполнитель'),
        ('equipment', 'Оборудование'),
        ('workplace', 'Рабочее место'),
    ]
    
    resource_type = models.CharField("Тип ресурса", max_length=20, choices=RESOURCE_TYPE_CHOICES)
    
    # Если исполнитель
    performer = models.ForeignKey(RefStaff, null=True, blank=True, on_delete=models.CASCADE,
                                 verbose_name="Исполнитель", related_name='preparation_resources')
    
    # Если оборудование или рабочее место
    name = models.CharField("Наименование", max_length=250, blank=True, default='')
    code = models.CharField("Код", max_length=50, blank=True, default='')
    
    unit = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL,
                           verbose_name="Подразделение")
    
    # Доступность
    is_active = models.BooleanField("Активен", default=True)
    max_concurrent_works = models.IntegerField("Максимум одновременных работ", default=1,
                                              help_text="Сколько работ может выполнять одновременно")
    
    # Рабочие часы (если нужно)
    work_start_time = models.TimeField("Время начала работы", default='09:00', null=True, blank=True)
    work_end_time = models.TimeField("Время окончания работы", default='18:00', null=True, blank=True)
    
    # Дни недели работы (битовая маска: 1=Пн, 2=Вт, ..., 64=Вс)
    work_days = models.IntegerField("Рабочие дни", default=62, 
                                   help_text="Сумма: 1=Пн, 2=Вт, 4=Ср, 8=Чт, 16=Пт, 32=Сб, 64=Вс (62 = Пн-Пт)")
    
    def is_available_at(self, datetime_check):
        """Проверка доступности ресурса в указанное время"""
        if not self.is_active:
            return False
        
        # Проверка дня недели
        day_of_week = datetime_check.weekday()  # 0=Пн, 6=Вс
        day_bit = 1 << day_of_week
        if not (self.work_days & day_bit):
            return False
        
        # Проверка времени работы
        if self.work_start_time and self.work_end_time:
            time_check = datetime_check.time()
            if not (self.work_start_time <= time_check <= self.work_end_time):
                return False
        
        # Проверка загрузки
        if datetime_check:
            concurrent_works = CarPreparationWorkSchedule.objects.filter(
                planned_performer=self.performer if self.resource_type == 'performer' else None,
                planned_start__lte=datetime_check,
                planned_end__gte=datetime_check,
                planning_status__in=['scheduled', 'in_progress']
            ).count()
            
            if concurrent_works >= self.max_concurrent_works:
                return False
        
        return True
    
    def __str__(self):
        if self.resource_type == 'performer' and self.performer:
            return f"{self.performer.name}"
        return f"{self.get_resource_type_display()} - {self.name or self.code}"
    
    class Meta:
        db_table = 'carPreparationResource'
        verbose_name = "Ресурс планирования"
        verbose_name_plural = "Ресурсы планирования"
        indexes = [
            models.Index(fields=['resource_type']),
            models.Index(fields=['unit']),
        ]


# ===========================================
# МАТЕРИАЛЫ И УЧЕТ
# ===========================================

class RefPreparationMaterial(models.Model):
    """Справочник материалов для подготовки"""
    name = models.CharField("Наименование", max_length=250, default='')
    code = models.CharField("Код", max_length=64, default='', blank=True)
    uom = models.CharField("Ед.изм", max_length=32, default='шт')
    is_active = models.BooleanField("Активен", default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'refPreparationMaterial'
        verbose_name = "Материал подготовки"
        verbose_name_plural = "Материалы подготовки"
        indexes = [models.Index(fields=['code']), models.Index(fields=['name'])]


class PreparationMaterialStock(models.Model):
    """Остатки материалов по подразделениям"""
    unit = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL, verbose_name='Подразделение')
    material = models.ForeignKey(RefPreparationMaterial, on_delete=models.PROTECT, verbose_name='Материал')
    qty_on_hand = models.DecimalField("Остаток", max_digits=14, decimal_places=3, default=0)
    min_qty = models.DecimalField("Мин. остаток", max_digits=14, decimal_places=3, default=0)
    max_qty = models.DecimalField("Макс. остаток", max_digits=14, decimal_places=3, default=0)
    date_updated = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        db_table = 'prepMaterialStock'
        unique_together = ('unit', 'material')
        verbose_name = "Остаток материала"
        verbose_name_plural = "Остатки материалов"
        indexes = [models.Index(fields=['unit', 'material'])]


class PreparationMaterialMovement(models.Model):
    """Движение материалов (приход/расход/корректировка)"""
    MOVEMENT_TYPES = [
        ('receipt', 'Приход'),
        ('consume', 'Расход'),
        ('adjust', 'Корректировка'),
    ]
    date = models.DateTimeField('Дата', default=datetime.now)
    unit = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL, verbose_name='Подразделение')
    material = models.ForeignKey(RefPreparationMaterial, on_delete=models.PROTECT, verbose_name='Материал')
    qty = models.DecimalField("Количество", max_digits=14, decimal_places=3, default=0)
    movement_type = models.CharField("Тип движения", max_length=16, choices=MOVEMENT_TYPES, default='receipt')
    work_item = models.ForeignKey(CarPreparationWorkItem, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Работа')
    comment = models.CharField("Комментарий", max_length=1000, blank=True, default='')
    user = models.ForeignKey(RefStaff, null=True, on_delete=models.SET_NULL, verbose_name='Пользователь')
    
    class Meta:
        db_table = 'prepMaterialMovement'
        verbose_name = "Движение материала"
        verbose_name_plural = "Движения материалов"
        ordering = ['-date']
        indexes = [models.Index(fields=['date']), models.Index(fields=['unit', 'material'])]


class PlannedMaterialConsumption(models.Model):
    """Планируемый расход материалов под работу"""
    work_item = models.ForeignKey(CarPreparationWorkItem, on_delete=models.CASCADE, related_name='planned_materials', verbose_name='Работа')
    material = models.ForeignKey(RefPreparationMaterial, on_delete=models.PROTECT, verbose_name='Материал')
    qty_planned = models.DecimalField("Планируемое количество", max_digits=14, decimal_places=3, default=0)
    qty_reserved = models.DecimalField("Зарезервировано", max_digits=14, decimal_places=3, default=0)
    reserved = models.BooleanField("Резерв создан", default=False)
    date_created = models.DateTimeField('Дата создания', default=datetime.now)
    
    class Meta:
        db_table = 'prepMaterialPlanned'
        verbose_name = "Планируемый расход материала"
        verbose_name_plural = "Планируемые расходы материалов"
        indexes = [models.Index(fields=['work_item']), models.Index(fields=['material'])]

# Сигналы для журналирования изменений
post_save.connect(journal_save_handler, sender=CarPreparation)
post_delete.connect(journal_delete_handler, sender=CarPreparation)
post_save.connect(journal_save_handler, sender=CarPreparationWorkItem)
post_delete.connect(journal_delete_handler, sender=CarPreparationWorkItem)
post_save.connect(journal_save_handler, sender=CarPreparationChecklist)
post_delete.connect(journal_delete_handler, sender=CarPreparationChecklist)
post_save.connect(journal_save_handler, sender=CarPreparationWorkSchedule)
post_delete.connect(journal_delete_handler, sender=CarPreparationWorkSchedule)


# Сигналы для уведомлений
def create_work_notifications(sender, instance, created, **kwargs):
    """Создание уведомлений при изменении работы"""
    from .notifications import create_work_started_notification, create_work_completed_notification
    
    if not created:
        # Проверяем изменение статуса
        if instance.pk:
            try:
                old_instance = CarPreparationWorkItem.objects.get(pk=instance.pk)
                # Если работа началась
                if old_instance.status != 'in_progress' and instance.status == 'in_progress':
                    create_work_started_notification(instance, instance.performer)
                # Если работа завершена
                if old_instance.status != 'completed' and instance.status == 'completed':
                    create_work_completed_notification(instance)
            except CarPreparationWorkItem.DoesNotExist:
                pass

# Отключаем автоматическое создание, чтобы не было дублирования
# post_save.connect(create_work_notifications, sender=CarPreparationWorkItem)


# ===========================================
# СИСТЕМА ЗАКАЗ-НАРЯДОВ
# ===========================================

class RefRepairZone(models.Model):
    """Ремонтные зоны (где выполняются работы)"""
    name = models.CharField("Наименование зоны", max_length=250, default='')
    code = models.CharField("Код", max_length=50, default='', unique=True)
    description = models.TextField("Описание", max_length=2000, blank=True, default='')
    unit = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL,
                            verbose_name="Подразделение")
    is_active = models.BooleanField("Активна", default=True)
    sort_order = models.IntegerField("Порядок сортировки", default=0)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'refRepairZone'
        verbose_name = "Ремонтная зона"
        verbose_name_plural = "Ремонтные зоны"
        ordering = ['sort_order', 'name']


class WorkOrderTemplate(models.Model):
    """Шаблон заказ-наряда (например, 'мойка перед выдачей')"""
    name = models.CharField("Наименование шаблона", max_length=250, default='')
    description = models.TextField("Описание", max_length=2000, blank=True, default='')
    code = models.CharField("Код", max_length=50, default='', unique=True)
    
    # Работы в шаблоне
    works = models.ManyToManyField(RefCarPreparationWork, through='WorkOrderTemplateWork',
                                  verbose_name="Работы")
    
    # Планируемое время заказ-наряда
    estimated_duration_minutes = models.IntegerField("Планируемая длительность (мин)", default=0)
    
    # Настройки
    is_active = models.BooleanField("Активен", default=True)
    is_default = models.BooleanField("Шаблон по умолчанию", default=False)
    unit = models.ForeignKey(RefUnit, null=True, blank=True, on_delete=models.SET_NULL,
                            verbose_name="Подразделение (если пусто - для всех)")
    
    date_created = models.DateTimeField('Дата создания', default=datetime.now)
    date_updated = models.DateTimeField('Дата обновления', auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'workOrderTemplate'
        verbose_name = "Шаблон заказ-наряда"
        verbose_name_plural = "Шаблоны заказ-нарядов"
        ordering = ['name']


class WorkOrderTemplateWork(models.Model):
    """Работа в шаблоне заказ-наряда"""
    template = models.ForeignKey(WorkOrderTemplate, on_delete=models.CASCADE)
    work = models.ForeignKey(RefCarPreparationWork, on_delete=models.CASCADE)
    
    is_required = models.BooleanField("Обязательна", default=True)
    estimated_time = models.IntegerField("Планируемое время (мин)", default=0, blank=True)
    sort_order = models.IntegerField("Порядок", default=0)
    
    class Meta:
        db_table = 'workOrderTemplateWork'
        verbose_name = "Работа в шаблоне заказ-наряда"
        verbose_name_plural = "Работы в шаблонах заказ-нарядов"
        unique_together = ['template', 'work']
        ordering = ['sort_order']


class WorkOrder(models.Model):
    """Заказ-наряд по автомобилю"""
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('scheduled', 'Запланирован'),
        ('in_progress', 'В работе'),
        ('completed', 'Выполнен'),
        ('cancelled', 'Отменен'),
    ]
    
    car = models.ForeignKey(RefCarsOrganization, on_delete=models.PROTECT,
                           verbose_name="Автомобиль", related_name='work_orders')
    preparation = models.ForeignKey(CarPreparation, null=True, blank=True, on_delete=models.SET_NULL,
                                   verbose_name="Подготовка", related_name='work_orders')
    template = models.ForeignKey(WorkOrderTemplate, null=True, blank=True, on_delete=models.SET_NULL,
                                verbose_name="Шаблон заказ-наряда")
    
    # Основная информация
    number = models.CharField("Номер заказ-наряда", max_length=50, default='', unique=True, blank=True)
    title = models.CharField("Название заказ-наряда", max_length=512, default='')
    description = models.TextField("Описание", max_length=2000, blank=True, default='')
    
    # Ремонтная зона
    repair_zone = models.ForeignKey(RefRepairZone, null=True, blank=True, on_delete=models.SET_NULL,
                                    verbose_name="Ремонтная зона")
    
    # Временные рамки
    planned_start = models.DateTimeField('Планируемое время начала', null=True, blank=True)
    planned_end = models.DateTimeField('Планируемое время окончания', null=True, blank=True)
    actual_start = models.DateTimeField('Фактическое время начала', null=True, blank=True)
    actual_end = models.DateTimeField('Фактическое время окончания', null=True, blank=True)
    
    # Статус
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Ответственные
    created_by = models.ForeignKey(RefStaff, null=True, on_delete=models.SET_NULL,
                                  verbose_name="Создал", related_name='created_work_orders')
    responsible = models.ForeignKey(RefStaff, null=True, blank=True, on_delete=models.SET_NULL,
                                   verbose_name="Ответственный", related_name='responsible_work_orders')
    
    # Даты
    date_created = models.DateTimeField('Дата создания', default=datetime.now)
    date_updated = models.DateTimeField('Дата обновления', auto_now=True)
    
    # Комментарии
    comment = models.TextField("Комментарий", max_length=5000, blank=True, default='')
    
    def get_duration_minutes(self):
        """Получить продолжительность в минутах"""
        if self.planned_start and self.planned_end:
            delta = self.planned_end - self.planned_start
            return int(delta.total_seconds() / 60)
        return 0
    
    def get_actual_duration_minutes(self):
        """Получить фактическую продолжительность в минутах"""
        if self.actual_start and self.actual_end:
            delta = self.actual_end - self.actual_start
            return int(delta.total_seconds() / 60)
        return 0
    
    def generate_number(self):
        """Генерация номера заказ-наряда"""
        if not self.number:
            from django.utils import timezone
            date_str = timezone.now().strftime('%Y%m%d')
            last_order = WorkOrder.objects.filter(number__startswith=date_str).order_by('-id').first()
            if last_order:
                try:
                    last_num = int(last_order.number[-4:])
                    new_num = last_num + 1
                except:
                    new_num = 1
            else:
                new_num = 1
            self.number = f"ЗН-{date_str}-{new_num:04d}"
        return self.number
    
    def save(self, *args, **kwargs):
        if not self.number:
            self.generate_number()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.number or 'Черновик'} - {self.car}"
    
    class Meta:
        db_table = 'workOrder'
        verbose_name = "Заказ-наряд"
        verbose_name_plural = "Заказ-наряды"
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['car', 'status']),
            models.Index(fields=['planned_start', 'planned_end']),
            models.Index(fields=['status']),
            models.Index(fields=['number']),
        ]


class WorkOrderItem(models.Model):
    """Работа в заказ-наряде"""
    STATUS_CHOICES = [
        ('pending', 'Ожидает выполнения'),
        ('in_progress', 'В работе'),
        ('completed', 'Выполнена'),
        ('skipped', 'Пропущена'),
    ]
    
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE,
                                   verbose_name="Заказ-наряд", related_name='items')
    work = models.ForeignKey(RefCarPreparationWork, on_delete=models.PROTECT,
                            verbose_name="Вид работы")
    
    # Статус
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Временные рамки
    planned_start = models.DateTimeField('Планируемое время начала', null=True, blank=True)
    planned_end = models.DateTimeField('Планируемое время окончания', null=True, blank=True)
    actual_start = models.DateTimeField('Фактическое время начала', null=True, blank=True)
    actual_end = models.DateTimeField('Фактическое время окончания', null=True, blank=True)
    
    # Исполнитель
    performer = models.ForeignKey(RefStaff, null=True, blank=True, on_delete=models.SET_NULL,
                                 verbose_name="Исполнитель", related_name='work_order_items')
    
    # Комментарии
    comment = models.TextField("Комментарий", max_length=2000, blank=True, default='')
    
    # Порядок выполнения
    sort_order = models.IntegerField("Порядок", default=0)
    
    # Связь с работой подготовки (если есть)
    preparation_work_item = models.ForeignKey(CarPreparationWorkItem, null=True, blank=True,
                                              on_delete=models.SET_NULL,
                                              verbose_name="Работа подготовки",
                                              related_name='work_order_items')
    
    date_created = models.DateTimeField('Дата создания', default=datetime.now)
    date_updated = models.DateTimeField('Дата обновления', auto_now=True)
    
    def get_duration_minutes(self):
        """Получить планируемую продолжительность в минутах"""
        if self.planned_start and self.planned_end:
            delta = self.planned_end - self.planned_start
            return int(delta.total_seconds() / 60)
        return self.work.estimated_time if self.work else 0
    
    def get_actual_duration_minutes(self):
        """Получить фактическую продолжительность в минутах"""
        if self.actual_start and self.actual_end:
            delta = self.actual_end - self.actual_start
            return int(delta.total_seconds() / 60)
        return 0
    
    def __str__(self):
        return f"{self.work_order.number or 'Черновик'} - {self.work.name}"
    
    class Meta:
        db_table = 'workOrderItem'
        verbose_name = "Работа в заказ-наряде"
        verbose_name_plural = "Работы в заказ-нарядах"
        ordering = ['sort_order', 'id']
        indexes = [
            models.Index(fields=['work_order', 'status']),
            models.Index(fields=['performer', 'status']),
        ]


class WorkOrderItemPhoto(models.Model):
    """Фотографии работы в заказ-наряде"""
    work_order_item = models.ForeignKey(WorkOrderItem, on_delete=models.CASCADE,
                                       verbose_name="Работа", related_name='photos')
    photo = models.ImageField(upload_to='work_orders/%Y/%m/%d/',
                             verbose_name="Фотография", max_length=255)
    description = models.CharField("Описание", max_length=500, blank=True, default='')
    date_created = models.DateTimeField('Дата создания', default=datetime.now)
    created_by = models.ForeignKey(RefStaff, null=True, on_delete=models.SET_NULL,
                                  verbose_name="Автор фотографии")
    
    def __str__(self):
        return f"Фото {self.work_order_item.work.name} - {self.date_created}"
    
    class Meta:
        db_table = 'workOrderItemPhoto'
        verbose_name = "Фотография работы"
        verbose_name_plural = "Фотографии работ"
        ordering = ['-date_created']


class WorkOrderItemMaterial(models.Model):
    """Товары/материалы в работе заказ-наряда"""
    work_order_item = models.ForeignKey(WorkOrderItem, on_delete=models.CASCADE,
                                       verbose_name="Работа", related_name='materials')
    material = models.ForeignKey('RefPreparationMaterial', on_delete=models.PROTECT,
                                verbose_name="Материал/Товар")
    quantity = models.DecimalField("Количество", max_digits=14, decimal_places=3, default=1)
    unit_price = models.DecimalField("Цена за единицу", max_digits=14, decimal_places=2, default=0.00)
    total_price = models.DecimalField("Общая стоимость", max_digits=14, decimal_places=2, default=0.00)
    comment = models.CharField("Комментарий", max_length=500, blank=True, default='')
    date_created = models.DateTimeField('Дата создания', default=datetime.now)
    
    def save(self, *args, **kwargs):
        # Автоматический расчет общей стоимости
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.material.name} - {self.quantity} {self.material.uom}"
    
    class Meta:
        db_table = 'workOrderItemMaterial'
        verbose_name = "Материал в работе"
        verbose_name_plural = "Материалы в работах"
        ordering = ['-date_created']