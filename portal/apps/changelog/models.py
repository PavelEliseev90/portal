from django.db import models
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.apps import apps


ACTION_CREATE = 'create'
ACTION_UPDATE = 'update'
ACTION_DELETE = 'delete'

class ChangeLog(models.Model):
  TYPE_ACTION_ON_MODEL = (
        (ACTION_CREATE, _('Создание')),
        (ACTION_UPDATE, _('Изменение')),
        (ACTION_DELETE, _('Удаление')),
    )
  changed           = models.DateTimeField(auto_now=True, verbose_name=u'Дата/время изменения')
  model             = models.CharField(max_length=255, verbose_name=u'Таблица', null=True)
  record_id         = models.IntegerField(verbose_name=u'ID записи', null=True)
  user              = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=u'Автор изменения', on_delete=models.CASCADE, null=True)
  action_on_model   = models.CharField(choices=TYPE_ACTION_ON_MODEL, max_length=50, verbose_name=u'Действие', null=True)
  data              = models.JSONField(verbose_name=u'Изменяемые данные модели', default=dict)
  ipaddress         = models.CharField(max_length=15, verbose_name=u'IP адресс', null=True)
  
  def get_change_human(self):
    if self.model.startswith('RegInteractivOcenka'):
      model = apps.get_model(app_label='register', model_name=self.model)
    else:
      model = apps.get_model(app_label='checklists', model_name=self.model)
    list_change = list()
    for change in self.data:
      name  = model._meta.get_field(change).verbose_name
      value = self.data.get(change)
      fields = {
        'name'  : name,
        'value' : value
      }
      list_change.append(fields)
   
    return list_change
  
  @classmethod
  def add(cls, instance, user, ipaddress, action_on_model, data, id=None):
      """Создание записи в журнале регистрации изменений"""
      log = ChangeLog.objects.get(id=id) if id else ChangeLog()
      log.model               = instance.__class__.__name__
      log.record_id           = instance.pk
      if user:
        log.user = user
      log.ipaddress           = ipaddress
      log.action_on_model     = action_on_model
      log.data                = data
      log.save()
      
      return log.pk

  def __str__(self):
    return f'{self.id}'

  class Meta:
    db_table = 'changeLog'
    ordering = ('changed', )
    verbose_name = _('Change log')
    verbose_name_plural = _('Change logs')
  
  

