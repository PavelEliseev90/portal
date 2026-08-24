# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('refs', '0144_pricegroupstagedays'),
    ]

    operations = [
        migrations.AddField(
            model_name='refunit',
            name='alfa_auto_transition_date',
            field=models.DateField(
                blank=True,
                help_text='Если заполнена — подразделение нельзя выбирать в оценке портала и нельзя начинать оценку с рабочего листа.',
                null=True,
                verbose_name='Дата перехода на Альфа-Авто',
            ),
        ),
    ]
