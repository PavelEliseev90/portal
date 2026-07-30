from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0226_reginteractivocenka_avtoteka_last_run_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='regestimationssettings',
            name='iznos_with_ss',
            field=models.BooleanField(
                default=False,
                help_text='Коррекция повышенного износа применяется после вычета затрат на слесарный участок.',
                verbose_name='Повышенный износ с учётом слесарного ремонта',
            ),
        ),
    ]
