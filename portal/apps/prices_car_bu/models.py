from django.db import models
from documents.models import DocCarAgreement



class IndicatorKVP(models.Model):
    name        = models.CharField("Наименование", max_length=150, default='', null=True, blank=True) 
    bu_wheels   = models.BooleanField("БУ резина", default = False, null=True, blank=True)
    osago       = models.BooleanField("ОСАГО", default = False, null=True, blank=True)
    kasko       = models.BooleanField("КАСКО", default = False, null=True, blank=True)
    credit      = models.BooleanField("Кредит", default = False, null=True, blank=True)
    gap         = models.BooleanField("ГАП", default = False, null=True, blank=True)
    life        = models.BooleanField("Жизнь", default = False, null=True, blank=True)

    class Meta:
        db_table = 'indicatorKVP'
        verbose_name = 'Показатель КВП'
        verbose_name_plural = 'Показатели КВП'
        ordering = ['name']

    def __str__(self):
        return "{}".format(self.name)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class CalculatedCumulativeData(models.Model):
    agreement       = models.ForeignKey(DocCarAgreement, null=True, on_delete=models.SET_NULL, verbose_name='Соглашение')
    indicatorKVP    = models.ForeignKey(IndicatorKVP, null=True, on_delete=models.SET_NULL, verbose_name='Показатель')
    amount          = models.FloatField('Сумма', help_text='Расчетная сумма по показателю')
    author          = models.CharField("Автор", max_length=512, default='', null=True, blank=True)
    comment         = models.CharField("Комментарий", max_length=512, default='', null=True, blank=True)
    send            = models.BooleanField('Отпраавлено в базу', default=False) 

    class Meta:
        db_table = 'calculatedCumulativeData'
        verbose_name = 'Расчетные данные кумулятива'
        verbose_name_plural = 'Расчетные данные кумулятива'
        ordering = ['agreement__dataTime']

    def __str__(self):
        return "{} {} / {}".format(self.agreement, self.indicatorKVP, self.amount)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


# class CheckingCumulativeData(models.Model):
    
#     agreement       = models.ForeignKey(DocCarAgreement, null=True, on_delete=models.SET_NULL, verbose_name='Соглашение')
    
#     amount          = models.FloatField('Сумма', help_text='Расчетная сумма по показателю')
#     author          = models.CharField("Автор", max_length=512, default='', null=True, blank=True)
#     comment         = models.CharField("Комментарий", max_length=512, default='', null=True, blank=True)

#     class Meta:
#         db_table = 'checkingCumulativeData'
#         verbose_name = 'Проверка ценовых правил соглашений'
#         verbose_name_plural = 'Проверки ценовых правил соглашений'
#         ordering = ['agreement__dataTime']

#     def __str__(self):
#         return "{} {} / {}".format(self.agreement, self.amount)

#     def save(self, *args, **kwargs):
#         super().save(*args, **kwargs)

