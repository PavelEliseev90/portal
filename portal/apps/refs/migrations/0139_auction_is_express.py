from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('refs', '0138_refib_alfa'),
    ]

    operations = [
        migrations.AddField(
            model_name='auction',
            name='is_express',
            field=models.BooleanField(blank=True, default=False, verbose_name='Экспресс-лот'),
        ),
    ]
