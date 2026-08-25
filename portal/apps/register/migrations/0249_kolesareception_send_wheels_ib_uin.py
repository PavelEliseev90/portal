from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0248_kolesareception_send_wheels_ib_meta'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkakolesareception',
            name='send_wheels_ib_uin',
            field=models.CharField(
                blank=True,
                default='',
                max_length=100,
                verbose_name='УИН документа приёмки в базе БУ колёс',
            ),
        ),
    ]
