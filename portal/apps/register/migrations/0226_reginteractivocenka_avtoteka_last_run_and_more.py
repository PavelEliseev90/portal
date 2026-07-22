from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0225_alter_reginteractivocenka_v'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenka',
            name='avtoteka_last_run',
            field=models.IntegerField(
                blank=True,
                default=0,
                verbose_name='Последний зафиксированный пробег в Автотеке',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenka',
            name='avtoteka_warning_run',
            field=models.IntegerField(
                blank=True,
                default=0,
                verbose_name='Возможная рассчитанная скрутка',
            ),
        ),
    ]
