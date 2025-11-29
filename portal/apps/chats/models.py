from django.db import models
from django.conf import settings
from datetime import datetime


class ChatSuccesDate(models.Model):
    date        = models.DateTimeField('Дата', default=datetime.now, blank=False)
    class Meta:
        db_table = 'chatSuccesDate'
        verbose_name = "Дата обновления аналитики чата"
        verbose_name_plural = "Даты обновления аналитики чата"


class Chat(models.Model):
    name    = models.CharField('Наименование', max_length=200)
    slug    = models.SlugField(max_length=512, null=True, blank=True)
    user    = models.ForeignKey(settings.AUTH_USER_MODEL,
                             null=True,
                             on_delete=models.SET_NULL,
                             verbose_name="Пользователь")
    
    rlk_id  = models.IntegerField('ИД рлк', default=0, null=True, blank=True)
    
    def __str__(self):
        return self.name

    def get_last_messages(self):
        messages = list(ChatMessage.objects.filter(chat = self).order_by('-date'))        
        messages.reverse()
        return messages
        
    def last_message(self):
        messages = ChatMessage.objects.filter(chat = self).order_by('-date')[:1]
        if len(messages) > 0:
            return '' + messages[0].date.strftime('%d/%m/%y, %H:%M') + ' - ' + messages[0].content[:100] + '...'
        return 'Пока нет сообщений'

    def save(self, *args, **kwargs):
        try:
            if self.rlk_id == 0 or self.rlk_id == None:
                self.rlk_id = int(self.name)
        except:
            s =1
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['slug'])
        ]
        db_table = 'chat'
        verbose_name = "Чат"
        verbose_name_plural = "Чаты"



class ChatMessage(models.Model):
    chat        = models.ForeignKey(Chat, null=True, on_delete=models.CASCADE, verbose_name='Чат')  
    date        = models.DateTimeField('Дата', default=datetime.now, blank=False)
    content     = models.TextField('Текст')
    img_base64  = models.TextField('Картинка', null=True, blank=True)
    slug        = models.SlugField(max_length=512, null=True, blank=True)
    user        = models.ForeignKey(settings.AUTH_USER_MODEL,
                             null=True,
                             on_delete=models.CASCADE,
                             verbose_name="Пользователь")
    
    def content_html(self):
        return self.content.replace('\n', '<br>')

    def __str__(self):
        return "{} - {} / {}".format(self.chat, self.user, self.content[:25])

    def save(self, *args, **kwargs):
        try:
            if self.slug == None:
                self.slug = str(self.chat.slug) + '_' + self.date.strftime('%Y%m%d%H%m%S')
        except:
            s =1
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['chat'])
        ]
        db_table = 'chatMessage'
        verbose_name = "Сообщение чата"
        verbose_name_plural = "Сообщения чата"