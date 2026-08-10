# Generated manually for ECO estimation alarm

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('register', '0242_remove_vnesh_unreadable_checks'),
    ]

    operations = [
        migrations.CreateModel(
            name='RegInteractivOcenkaAlarm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active', models.BooleanField(db_index=True, default=True, verbose_name='Активен')),
                ('due_at', models.DateTimeField(db_index=True, verbose_name='Сработает')),
                ('set_at', models.DateTimeField(verbose_name='Поставлен')),
                ('dismissed_at', models.DateTimeField(blank=True, null=True, verbose_name='Снят')),
                ('dismissed_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='eco_estimation_alarms_dismissed',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Снял',
                )),
                ('interactiv_rlk', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='eco_alarm',
                    to='register.reginteractivocenkarlk',
                    verbose_name='Интерактивная оценка',
                )),
                ('set_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='eco_estimation_alarms_set',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Поставил',
                )),
            ],
            options={
                'verbose_name': 'Будильник ЕЦО',
                'verbose_name_plural': 'Будильники ЕЦО',
                'db_table': 'regInteractivOcenkaAlarm',
            },
        ),
        migrations.AddIndex(
            model_name='reginteractivocenkaalarm',
            index=models.Index(fields=['active', 'due_at'], name='regInteractiv_active_due_idx'),
        ),
    ]
