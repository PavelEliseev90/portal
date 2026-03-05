# Generated manually for PageViewLog

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('changelog', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PageViewLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(blank=True, db_index=True, max_length=40, verbose_name='Ключ сессии (анонимы)')),
                ('path', models.CharField(db_index=True, max_length=500, verbose_name='Путь (без query)')),
                ('path_full', models.CharField(blank=True, max_length=1024, verbose_name='Полный путь с параметрами')),
                ('method', models.CharField(default='GET', max_length=10)),
                ('status_code', models.SmallIntegerField(blank=True, null=True, verbose_name='HTTP код ответа')),
                ('ip', models.GenericIPAddressField(blank=True, null=True)),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Дата/время')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pageview_logs', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Лог просмотра страницы',
                'verbose_name_plural': 'Логи просмотров страниц',
                'db_table': 'pageview_log',
                'ordering': ('-created',),
            },
        ),
    ]
