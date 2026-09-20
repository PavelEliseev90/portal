# Generated manually for DcMonthlyPlan money targets (plan_km_rub and plan_revenue_rub)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0041_autopilot_and_ruble_discounts'),
    ]

    operations = [
        migrations.AddField(
            model_name='dcmonthlyplan',
            name='plan_km_rub',
            field=models.BigIntegerField(
                default=0,
                help_text='Целевой кумулятивный маржинальный доход ДЦ на месяц в рублях',
                verbose_name='План по КМ (марже), ₽',
            ),
        ),
        migrations.AddField(
            model_name='dcmonthlyplan',
            name='plan_revenue_rub',
            field=models.BigIntegerField(
                blank=True,
                default=0,
                help_text='Целевой оборот (выручка) ДЦ на месяц в рублях',
                null=True,
                verbose_name='План по выручке, ₽',
            ),
        ),
    ]
