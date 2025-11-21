from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from ckeditor_uploader.fields import RichTextUploadingField
from django.urls import reverse


class TaskStatus(models.Model):
    """Модель статусов задач"""
    name = models.CharField("Наименование", max_length=100, unique=True)
    code = models.CharField("Код", max_length=50, unique=True, db_index=True)
    color = models.CharField("Цвет", max_length=20, default="#6c757d", help_text="HEX цвет для отображения")
    order = models.IntegerField("Порядок сортировки", default=0)
    is_closed = models.BooleanField("Завершающий статус", default=False, 
                                    help_text="Задачи с этим статусом считаются закрытыми")
    is_active = models.BooleanField("Активный", default=True)

    class Meta:
        db_table = 'helpdesk_task_status'
        verbose_name = "Статус задачи"
        verbose_name_plural = "Статусы задач"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Priority(models.Model):
    """Модель приоритетов задач"""
    name = models.CharField("Наименование", max_length=50, unique=True)
    code = models.CharField("Код", max_length=20, unique=True)
    level = models.IntegerField("Уровень приоритета", default=0, 
                               help_text="Чем выше число, тем выше приоритет")
    color = models.CharField("Цвет", max_length=20, default="#6c757d")

    class Meta:
        db_table = 'helpdesk_priority'
        verbose_name = "Приоритет"
        verbose_name_plural = "Приоритеты"
        ordering = ['-level']

    def __str__(self):
        return self.name


class ProjectTag(models.Model):
    """Модель тегов проектов"""
    name = models.CharField("Наименование проекта", max_length=200, unique=True)
    code = models.CharField("Код проекта", max_length=100, unique=True, db_index=True)
    description = models.TextField("Описание", blank=True, null=True)
    color = models.CharField("Цвет", max_length=20, default="#007bff", 
                            help_text="HEX цвет для отображения")
    is_active = models.BooleanField("Активный", default=True)
    order = models.IntegerField("Порядок сортировки", default=0)
    date_created = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        db_table = 'helpdesk_project_tag'
        verbose_name = "Тег проекта"
        verbose_name_plural = "Теги проектов"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class HelpDeskTask(models.Model):
    """Модель задач helpdesk"""
    # Основная информация
    title = models.CharField("Тема", max_length=500)
    description = RichTextUploadingField("Описание", blank=True, null=True)
    
    # Автор и исполнитель
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name='authored_tasks',
                               verbose_name="Автор", null=False)
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='assigned_tasks',
                                verbose_name="Исполнитель", null=True, blank=True)
    
    # Статус и приоритет
    status = models.ForeignKey(TaskStatus, on_delete=models.PROTECT, related_name='tasks',
                              verbose_name="Статус", null=True)
    priority = models.ForeignKey(Priority, on_delete=models.SET_NULL, related_name='tasks',
                                verbose_name="Приоритет", null=True, blank=True)
    
    # Временные рамки
    date_created = models.DateTimeField("Дата создания", auto_now_add=True)
    date_updated = models.DateTimeField("Дата обновления", auto_now=True)
    date_start = models.DateTimeField("Дата начала выполнения", null=True, blank=True)
    date_deadline = models.DateTimeField("Срок выполнения", null=True, blank=True)
    date_closed = models.DateTimeField("Дата закрытия", null=True, blank=True)
    
    # Дополнительная информация
    estimated_time = models.DurationField("Планируемое время выполнения", null=True, blank=True,
                                         help_text="В формате ЧЧ:ММ:СС")
    actual_time = models.DurationField("Фактическое время выполнения", null=True, blank=True)
    
    # Метаданные
    is_deleted = models.BooleanField("Удалена", default=False)
    observers = models.ManyToManyField(User, related_name='observed_tasks', 
                                      verbose_name="Наблюдатели", blank=True)
    
    # Проекты (теги проектов)
    projects = models.ManyToManyField('ProjectTag', related_name='tasks',
                                     verbose_name="Проекты", blank=True,
                                     help_text="Проекты, к которым относится задача")
    
    # Метки для фильтрации и категоризации (дополнительные теги)
    tags = models.CharField("Дополнительные теги", max_length=500, blank=True, null=True,
                           help_text="Через запятую")
    
    class Meta:
        db_table = 'helpdesk_task'
        verbose_name = "Задача HelpDesk"
        verbose_name_plural = "Задачи HelpDesk"
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['status', 'date_created']),
            models.Index(fields=['assignee', 'status']),
            models.Index(fields=['author', 'date_created']),
            models.Index(fields=['date_deadline']),
        ]

    def __str__(self):
        return f"#{self.id} - {self.title}"

    def get_absolute_url(self):
        return reverse('helpdesk:task_detail', kwargs={'pk': self.pk})

    def close_task(self):
        """Закрытие задачи"""
        if self.status and self.status.is_closed:
            self.date_closed = timezone.now()
            self.save()

    def is_overdue(self):
        """Проверка просрочки задачи"""
        if self.date_deadline and self.status and not self.status.is_closed:
            return timezone.now() > self.date_deadline
        return False

    def days_left(self):
        """Количество дней до дедлайна"""
        if self.date_deadline:
            delta = self.date_deadline.date() - timezone.now().date()
            return delta.days
        return None


class TaskComment(models.Model):
    """Модель комментариев к задачам"""
    task = models.ForeignKey(HelpDeskTask, on_delete=models.CASCADE, related_name='comments',
                            verbose_name="Задача")
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name='task_comments',
                              verbose_name="Автор")
    text = RichTextUploadingField("Текст комментария")
    date_created = models.DateTimeField("Дата создания", auto_now_add=True)
    date_updated = models.DateTimeField("Дата обновления", auto_now=True)
    is_internal = models.BooleanField("Внутренний комментарий", default=False,
                                     help_text="Виден только исполнителям")
    is_deleted = models.BooleanField("Удален", default=False)

    class Meta:
        db_table = 'helpdesk_task_comment'
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ['-date_created']

    def __str__(self):
        return f"Комментарий #{self.id} к задаче #{self.task.id}"


class TaskAttachment(models.Model):
    """Модель вложений к задачам"""
    task = models.ForeignKey(HelpDeskTask, on_delete=models.CASCADE, related_name='attachments',
                            verbose_name="Задача")
    comment = models.ForeignKey(TaskComment, on_delete=models.CASCADE, related_name='attachments',
                               verbose_name="Комментарий", null=True, blank=True)
    file = models.FileField("Файл", upload_to='helpdesk/attachments/%Y/%m/%d/')
    original_filename = models.CharField("Оригинальное имя файла", max_length=500)
    file_size = models.BigIntegerField("Размер файла (байт)", default=0)
    mime_type = models.CharField("MIME тип", max_length=100, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='task_attachments',
                                   verbose_name="Загрузил")
    date_uploaded = models.DateTimeField("Дата загрузки", auto_now_add=True)
    description = models.CharField("Описание", max_length=500, blank=True)

    class Meta:
        db_table = 'helpdesk_task_attachment'
        verbose_name = "Вложение"
        verbose_name_plural = "Вложения"
        ordering = ['-date_uploaded']

    def __str__(self):
        return f"{self.original_filename} (задача #{self.task.id})"


class TaskHistory(models.Model):
    """Модель истории изменений задач"""
    task = models.ForeignKey(HelpDeskTask, on_delete=models.CASCADE, related_name='history',
                            verbose_name="Задача")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                            verbose_name="Пользователь")
    action = models.CharField("Действие", max_length=100)
    field_name = models.CharField("Поле", max_length=100, blank=True)
    old_value = models.TextField("Старое значение", blank=True, null=True)
    new_value = models.TextField("Новое значение", blank=True, null=True)
    date_created = models.DateTimeField("Дата изменения", auto_now_add=True)
    comment = models.TextField("Комментарий", blank=True)

    class Meta:
        db_table = 'helpdesk_task_history'
        verbose_name = "История изменения"
        verbose_name_plural = "История изменений"
        ordering = ['-date_created']

    def __str__(self):
        return f"{self.action} - задача #{self.task.id}"
