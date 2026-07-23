from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('refs', '0142_reffilial_store'),
    ]

    operations = [
        migrations.AddField(
            model_name='refunit',
            name='auto_reprice_new',
            field=models.BooleanField(
                default=False,
                help_text='Участвует в отчётах и процессах по новым АМ с автопереоценкой.',
                verbose_name='Включена автоматическая переоценка новых',
            ),
        ),
    ]
