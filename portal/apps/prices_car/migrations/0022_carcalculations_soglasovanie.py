from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('prices_car', '0021_alter_carcalculationslistsettings_compare_km_kvp'),
    ]

    operations = [
        migrations.AddField(
            model_name='carcalculations',
            name='soglasovanie_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('pending', 'Ожидает директора ДЦ'),
                    ('director_approved', 'Согласовано директором ДЦ'),
                    ('pending_uk', 'На согласовании УК'),
                    ('uk_approved', 'Согласовано УК'),
                ],
                default='pending',
                max_length=32,
                verbose_name='Статус согласования',
            ),
        ),
        migrations.AddField(
            model_name='carcalculations',
            name='director_approve_user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='calc_director_approvals',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Согласовал директор',
            ),
        ),
        migrations.AddField(
            model_name='carcalculations',
            name='director_approve_date',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Дата согласования директором',
            ),
        ),
        migrations.AddField(
            model_name='carcalculations',
            name='director_approve_comment',
            field=models.CharField(
                blank=True,
                default='',
                max_length=2048,
                null=True,
                verbose_name='Комментарий директора',
            ),
        ),
        migrations.AddField(
            model_name='carcalculations',
            name='uk_approve_user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='calc_uk_approvals',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Согласовал УК',
            ),
        ),
        migrations.AddField(
            model_name='carcalculations',
            name='uk_approve_date',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Дата согласования УК',
            ),
        ),
        migrations.AddField(
            model_name='carcalculations',
            name='uk_approve_comment',
            field=models.CharField(
                blank=True,
                default='',
                max_length=2048,
                null=True,
                verbose_name='Комментарий УК',
            ),
        ),
    ]
