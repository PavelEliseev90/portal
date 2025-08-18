from django.db import models
from datetime import datetime
from ckeditor_uploader.fields import RichTextUploadingField
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils.text import slugify


def transliterate(name):
   slovar = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e',
      'ж':'zh','з':'z','и':'i','й':'i','к':'k','л':'l','м':'m','н':'n',
      'о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h',
      'ц':'c','ч':'cz','ш':'sh','щ':'scz','ъ':'','ы':'y','ь':'','э':'e',
      'ю':'u','я':'ja', 'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Ё':'E',
      'Ж':'ZH','З':'Z','И':'I','Й':'I','К':'K','Л':'L','М':'M','Н':'N',
      'О':'O','П':'P','Р':'R','С':'S','Т':'T','У':'U','Ф':'F','Х':'H',
      'Ц':'C','Ч':'CZ','Ш':'SH','Щ':'SCH','Ъ':'','Ы':'y','Ь':'','Э':'E',
      'Ю':'U','Я':'YA',',':'','?':'',' ':'_','~':'','!':'','@':'','#':'',
      '$':'','%':'','^':'','&':'','*':'','(':'',')':'','-':'','=':'','+':'',
      ':':'',';':'','<':'','>':'','\'':'','"':'','\\':'','/':'','№':'',
      '[':'',']':'','{':'','}':'','ґ':'','ї':'', 'є':'','Ґ':'g','Ї':'i',
      'Є':'e', '—':''}
        
   # Циклически заменяем все буквы в строке
   for key in slovar:
      name = name.replace(key, slovar[key])
   return name


class TaskTag(models.Model):
    name    = models.CharField("Наименование", max_length=220)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'manualsTag'
        verbose_name = "Тэг"
        verbose_name_plural = "Тэги"


class Task(models.Model):
    author          = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    title           = models.CharField(max_length=220)
    text            = RichTextUploadingField()
    dateCreate      = models.DateTimeField("Дата создания", default=datetime.now, blank=False)
    dateUpdate      = models.DateTimeField("Дата обновления", default=datetime.now, blank=False)
    dateClose       = models.DateTimeField("Дата выполнения", null=True, blank=True)
    canceled        = models.BooleanField("Отменена", default=False)
    slug            = models.SlugField(max_length=250, unique=True)
    commentClose    = RichTextUploadingField()
    tags            = models.ManyToManyField(TaskTag, blank=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('task', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        self.dateUpdate = datetime.now()   
        if not self.slug:
            title = transliterate(self.title)
            self.slug = slugify(title)
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'task'
        verbose_name = "Задача "
        verbose_name_plural = "Задачи"