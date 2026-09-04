from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.safestring import mark_safe
from refs.models import RefStore, RefUnit

class Profiles(models.Model):
    user                    = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    birth_date              = models.DateField(null=True, blank=True)
    email                   = models.EmailField(max_length=254, blank=True)
    phone                   = models.CharField("Телефон", max_length=512, default='', blank= True)
    image                   = models.ImageField(upload_to='logo_user/', max_length=100, verbose_name="Аватар", blank=True, null=True)
    view_checklist          = models.BooleanField("Чек лист - только просмотр", default = True)
    edit_sms_opros          = models.BooleanField("Редактирование смс опросов", default = False)
    
    eco_name                = models.CharField("Наименование в чате и согласовании", max_length=512, default='', blank= True, null=True)
    eco                     = models.BooleanField("ЕЦО аналитик", default = False)
    eco_visible             = models.BooleanField("ЕЦО просмотр", default = False)
    eco_page_price_info     = models.BooleanField("ЕЦО просмотр страницы ценообразование", default = False)
    eco_page_price_auto     = models.BooleanField("ЕЦО просмотр страницы ценообразование автоматическая", default = False)
    eco_toast               = models.BooleanField("Всплывающиесообщения", default = False)
    eco_chat_important      = models.BooleanField("Важные сообщения в чатах ЕЦО", default=False)
    eco_price_increase      = models.BooleanField(
        "Отработка запросов повышения цены",
        default=False,
        help_text='Может отмечать «отработано» по запросам повышения в интерактивной оценке',
    )
    
    korsavto_settings       = models.BooleanField("Доступ к настройкам корсавто", default = False)

    korsavto_settings_dc    = models.BooleanField("Доступ к настройкам корсавто директора дц", default = False)
    korsavto_stores         = models.ManyToManyField(RefStore, verbose_name='Стоянки автомобилей доступны', blank=True)
    available_units         = models.ManyToManyField(
        RefUnit,
        related_name='profiles_with_access',
        verbose_name='Доступные подразделения',
        blank=True,
    )
    korsavto_city           = models.CharField("Наименование города", max_length=512, default='', blank= True, null=True) 
    korsavto_auction        = models.BooleanField("Сотрудник аукциона", default = False)

    user_sb                 = models.BooleanField("Сотрудник службы безопасности", default = False)
    
    price_car_new           = models.BooleanField("Ценообразование новых", default = False)
    price_car_new_director  = models.BooleanField("Ценообразование новых директор", default = False)
    
    price_car_new_all       = models.BooleanField("Ценообразование новых всех ДЦ", default = False)
    price_car_bu            = models.BooleanField("Ценообразование бу", default = False)
    price_car_new_settings  = models.BooleanField("Ценообразование новых настройки", default = False)
    price_car_bu_settings   = models.BooleanField("Ценообразование бу настройки", default = False)
    estimation_settings     = models.BooleanField("Настройки интерактивных оценок", default = False)
    estimation_report       = models.BooleanField("Отчеты по интерактивным оценкам", default = False)
    eco_report              = models.BooleanField("Отчеты по аналитикам", default = False)
    
    # Один вход с одного устройства: разрешённый session_key (обновляется при логине)
    current_session_key     = models.CharField(
        "Разрешённый ключ сессии (один вход)",
        max_length=40, null=True, blank=True, db_index=True
    )
    telegram_chat_id = models.CharField(
        'Telegram chat ID',
        max_length=64,
        blank=True,
        default='',
        help_text='Личный chat_id. Задаётся только в админке или '
                  'на странице редактирования профиля. '
                  'Узнать: @userinfobot → Id.',
    )
    telegram_notify_pending = models.BooleanField(
        'Telegram: требуется согласование',
        default=True,
        help_text='Карточки КП, ожидающие согласования директором / УК.',
    )
    telegram_notify_auto_approved = models.BooleanField(
        'Telegram: автоматически согласованные',
        default=True,
        help_text='Оповещения, когда КП согласовано автоматически по правилам.',
    )
    telegram_notify_results = models.BooleanField(
        'Telegram: результаты согласования',
        default=True,
        help_text='Согласовано / отклонено / отправлено в УК.',
    )

    def image_img(self):
        if self.image:
            return mark_safe('<div style=" width:240px; height:120px;text-align:center;" ><img style="max-width:100%;max-height: 100%;" src="{0}"/></div>'.format(self.image.url))
        else: 
            return mark_safe('<div style=" width:240px; height:120px;text-align:center;" ><img style="max-width:100%;max-height: 100%;" src="/static/media/no_image.png"/></div>')
    image_img.short_description = 'Аватар'
    image_img.allow_tags = True

    def image_logo(self):
        if self.image:
            return mark_safe('{0}'.format(self.image.url))
        else: 
            return mark_safe('/static/media/no_image.png')
    image_logo.short_description = 'Аватар'
    image_logo.allow_tags = True

    def __str__(self):
        return str(self.user)
    
    def save(self, *args, **kwargs):

        if not self.eco:
            self.eco_name = self.user.last_name + ' ' + self.user.first_name

        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'profiles'
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"


class Profiles_save_search(models.Model):
    user                    = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    name                    = models.CharField("Наименование", max_length=512, default='', blank= True)
    model                   = models.CharField("Модель", max_length=512, default='', blank= True)
    search                  = models.CharField("Поисковая строка", max_length=512, default='', blank= True)

    def __str__(self):
        return str(self.user) + " " + self.name

    
    
    class Meta:
        db_table = 'profiles_save_search'
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"


@receiver(post_save, sender=User)
def create_user_profiles(sender, instance, created, **kwargs):
    if created:
        try:
            if instance.profiles == None:
            	Profiles.objects.create(user=instance)
        except:
            s = 13

@receiver(post_save, sender=User)
def save_user_profiles(sender, instance, **kwargs):
    try:
        if len(instance.profiles.phone) < 5:
            instance.profiles.phone = instance.phone
        instance.profiles.save()
    except:
        s = 12
        #Profiles.objects.create(user=instance)
    try:
        if Profiles.objects.filter(user = instance).count() == 0:
            Profiles.objects.create(user=instance)
    except:
        s = 13