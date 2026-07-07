from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0029_tradein_km_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='carcalculations',
            name='soglasovanie_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('awaiting_1c', 'Ожидает подтверждения из 1С'),
                    ('pending', 'Ожидает директора ДЦ'),
                    ('director_approved', 'Согласовано директором ДЦ'),
                    ('pending_uk', 'На согласовании УК'),
                    ('uk_approved', 'Согласовано УК'),
                    ('director_rejected', 'Отказ директора ДЦ'),
                    ('uk_rejected', 'Отказ УК'),
                ],
                default='pending',
                max_length=32,
                verbose_name='Статус согласования',
            ),
        ),
    ]
