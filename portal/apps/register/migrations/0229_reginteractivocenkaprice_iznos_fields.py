# Generated manually for iznos fields in price recalc history

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0228_reginteractivocenkaprice_calc_date_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='iznos',
            field=models.BooleanField(blank=True, default=False, null=True, verbose_name='Повышенный износ'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='taxi',
            field=models.BooleanField(blank=True, default=False, null=True, verbose_name='Использование в такси'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='k_i',
            field=models.FloatField(blank=True, default=0.0, null=True, verbose_name='Коэффициент износа'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='iznos_price',
            field=models.FloatField(blank=True, default=0.0, null=True, verbose_name='Сумма коррекции повышенного износа'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='iznos_data',
            field=models.FloatField(blank=True, default=0.0, null=True, verbose_name='Сумма износа до учёта СС'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='iznos_with_ss',
            field=models.BooleanField(blank=True, default=False, null=True, verbose_name='Износ с учётом слесарки'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkaprice',
            name='iznos_ss_compensation',
            field=models.FloatField(
                blank=True,
                default=0.0,
                help_text='Сколько вернули к цене из-за влияния СС на износ',
                null=True,
                verbose_name='Компенсация износа слесаркой',
            ),
        ),
    ]
