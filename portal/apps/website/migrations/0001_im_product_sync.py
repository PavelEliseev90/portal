# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ImProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nomenclature_code', models.CharField(db_index=True, max_length=100, unique=True, verbose_name='НоменклатураКод')),
                ('code', models.CharField(blank=True, max_length=100, verbose_name='Код')),
                ('nomenclature', models.CharField(blank=True, max_length=500, verbose_name='Номенклатура')),
                ('title', models.CharField(blank=True, max_length=500, verbose_name='Наименование/Объявление')),
                ('profile', models.CharField(blank=True, max_length=100, verbose_name='Профиль')),
                ('category', models.CharField(blank=True, max_length=200, verbose_name='Категория')),
                ('category_avito', models.CharField(blank=True, max_length=200, verbose_name='Категория Авито')),
                ('manufacturer', models.CharField(blank=True, max_length=200, verbose_name='Производитель')),
                ('article', models.CharField(blank=True, max_length=100, verbose_name='Артикул')),
                ('storage_cell', models.CharField(blank=True, max_length=100, verbose_name='Ячейка хранения')),
                ('address', models.CharField(blank=True, max_length=500, verbose_name='Адрес')),
                ('price_display', models.CharField(blank=True, max_length=50, verbose_name='Цена (отображение)')),
                ('price_value', models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True, verbose_name='Цена (число)')),
                ('quantity_balance', models.IntegerField(default=0, verbose_name='Остаток')),
                ('photo_count', models.IntegerField(default=0, verbose_name='Количество фото')),
                ('avito_id', models.CharField(blank=True, max_length=50, verbose_name='AvitoId')),
                ('ad_status', models.CharField(blank=True, max_length=50, verbose_name='AdStatus')),
                ('status_text', models.CharField(blank=True, max_length=100, verbose_name='Статус')),
                ('date_begin', models.DateTimeField(blank=True, null=True, verbose_name='DateBegin')),
                ('date_end', models.DateTimeField(blank=True, null=True, verbose_name='DateEnd')),
                ('views_count', models.IntegerField(default=0, verbose_name='Просмотров')),
                ('contacts_count', models.IntegerField(default=0, verbose_name='Контактов')),
                ('favorites_count', models.IntegerField(default=0, verbose_name='Избранное')),
                ('raw_json', models.JSONField(blank=True, null=True, verbose_name='Сырой JSON')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('synced_at', models.DateTimeField(blank=True, null=True, verbose_name='Последняя синхронизация')),
            ],
            options={
                'verbose_name': 'Товар IM сток',
                'verbose_name_plural': 'Товары IM сток',
            },
        ),
        migrations.CreateModel(
            name='ImSyncLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sync_type', models.CharField(choices=[('full_stok', 'Полная выгрузка стока'), ('product_update', 'Обновление товара'), ('photo_upload', 'Загрузка фото')], db_index=True, max_length=50, verbose_name='Тип')),
                ('direction', models.CharField(default='in', max_length=20, verbose_name='Направление')),
                ('started_at', models.DateTimeField(auto_now_add=True, verbose_name='Начало')),
                ('finished_at', models.DateTimeField(blank=True, null=True, verbose_name='Окончание')),
                ('status', models.CharField(choices=[('success', 'Успешно'), ('partial', 'Частично'), ('error', 'Ошибка')], default='success', max_length=20, verbose_name='Статус')),
                ('request_url', models.CharField(blank=True, max_length=1000, verbose_name='URL запроса')),
                ('response_code', models.IntegerField(blank=True, null=True, verbose_name='Код ответа')),
                ('items_total', models.IntegerField(default=0, verbose_name='Всего записей')),
                ('items_ok', models.IntegerField(default=0, verbose_name='Успешно')),
                ('items_failed', models.IntegerField(default=0, verbose_name='Ошибок')),
                ('error_message', models.TextField(blank=True, verbose_name='Сообщение об ошибке')),
                ('details_json', models.JSONField(blank=True, null=True, verbose_name='Детали')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Запись журнала синхронизации IM',
                'verbose_name_plural': 'Журнал синхронизации IM',
                'ordering': ['-started_at'],
            },
        ),
        migrations.AddIndex(
            model_name='improduct',
            index=models.Index(fields=['status_text'], name='website_imp_status__b8f0c6_idx'),
        ),
        migrations.AddIndex(
            model_name='improduct',
            index=models.Index(fields=['photo_count'], name='website_imp_photo_c_b4d941_idx'),
        ),
        migrations.AddIndex(
            model_name='improduct',
            index=models.Index(fields=['avito_id'], name='website_imp_avito_i_3a9e32_idx'),
        ),
        migrations.AddIndex(
            model_name='improduct',
            index=models.Index(fields=['synced_at'], name='website_imp_synced__2c8d74_idx'),
        ),
        migrations.AddIndex(
            model_name='imsynclog',
            index=models.Index(fields=['sync_type'], name='website_ims_sync_ty_7e9a56_idx'),
        ),
        migrations.AddIndex(
            model_name='imsynclog',
            index=models.Index(fields=['-started_at'], name='website_ims_started_8f2c91_idx'),
        ),
    ]
