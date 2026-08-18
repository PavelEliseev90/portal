from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0247_rename_reginteract_active_f27cd6_idx_reginteract_active_f27cd6_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkakolesareception',
            name='send_wheels_ib_date',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Дата документа приёмки в базе БУ колёс',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenkakolesareception',
            name='send_wheels_ib_number',
            field=models.CharField(
                blank=True,
                default='',
                max_length=64,
                verbose_name='Номер документа приёмки в базе БУ колёс',
            ),
        ),
    ]
