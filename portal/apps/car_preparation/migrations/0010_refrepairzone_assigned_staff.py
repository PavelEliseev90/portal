from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('car_preparation', '0009_carpreparationcomment_carpreparationcommentfile_and_more'),
        ('refs', '0124_refcarsorganizationfiles_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='refrepairzone',
            name='assigned_staff',
            field=models.ManyToManyField(
                blank=True,
                help_text='Кто видит заказ-наряды этой ремзоны на своём рабочем столе',
                related_name='repair_zones',
                to='refs.refstaff',
                verbose_name='Сотрудники зоны',
            ),
        ),
    ]
