# Generated manually for RegInteractivOcenkaReception.staff

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0251_alter_kolesareception_kolesa_estimation_verbose'),
        ('register', '0251_alter_reginteractivocenkakolesareceptionevent_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='staff',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='eco_receptions_staff',
                to='refs.refstaff',
                verbose_name='Оценщик',
            ),
        ),
    ]
