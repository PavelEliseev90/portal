from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0023_carcalculations_km_raschet'),
    ]

    operations = [
        migrations.AlterField(
            model_name='carcalculations',
            name='soglasovanie_status',
            field=models.CharField(
                blank=True,
                choices=[
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
