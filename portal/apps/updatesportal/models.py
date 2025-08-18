from django.db import models
from datetime import datetime
from ckeditor_uploader.fields import RichTextUploadingField
from django.contrib.auth.models import User


class UpdatesportalTag(models.Model):
    name = models.CharField("Наименование", max_length=220)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'updatesportalTag'
        verbose_name = "Тэг обновления"
        verbose_name_plural = "Тэги обновлений портала"


class Updatesportal(models.Model):
    author      = models.ForeignKey(User, on_delete=models.CASCADE)
    title       = models.CharField(max_length=220)
    text        = RichTextUploadingField()
    tags        = models.ManyToManyField(UpdatesportalTag, blank=True)
    dateCreate  = models.DateTimeField("Дата создания", default=datetime.now, blank=False)
    dateUpdate  = models.DateTimeField("Дата обновления", default=datetime.now, blank=False)
    activated   = models.BooleanField("Активна", default=False)
    users       = models.ManyToManyField(User, related_name='user_confim', blank=True) 

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.dateUpdate = datetime.now()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'updatesportal'
        verbose_name = "Обновление"
        verbose_name_plural = "Обновления"