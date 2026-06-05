import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('documents', '0649_alter_doсrecomendation_kod_recomendation'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientJourneyLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='Токен доступа')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активна')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создана')),
                ('last_opened_at', models.DateTimeField(blank=True, null=True, verbose_name='Последний вход')),
                ('opens_count', models.PositiveIntegerField(default=0, verbose_name='Открытий')),
                ('rlk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='journey_links', to='documents.docrlk', verbose_name='Рабочий лист')),
            ],
            options={
                'verbose_name': 'Ссылка клиента',
                'verbose_name_plural': 'Ссылки клиентов',
                'db_table': 'clientJourneyLink',
                'ordering': ['-created_at'],
            },
        ),
    ]
