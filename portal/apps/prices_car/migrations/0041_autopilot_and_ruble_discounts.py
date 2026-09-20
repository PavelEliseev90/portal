# Generated manually for Autopilot, Ruble discounts, and Consignment days triggers

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0040_command_center_plans_and_discounts'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pricecarkmdiscount',
            name='discount_percent',
            field=models.FloatField(
                default=0.0,
                help_text='Процент, на который изменяется минимальный Км (кумулятивная маржа)',
                verbose_name='Процент изменения мин. Км',
            ),
        ),
        migrations.AddField(
            model_name='pricecarkmdiscount',
            name='discount_rub',
            field=models.IntegerField(
                blank=True,
                default=0,
                help_text='Фиксированная сумма скидки к целевому КМ в рублях (напр. 50 000, 100 000). Можно комбинировать с процентом.',
                null=True,
                verbose_name='Скидка к Км (в рублях)',
            ),
        ),
        migrations.AddField(
            model_name='pricecarkmdiscount',
            name='days_consignment_left_lte',
            field=models.IntegerField(
                blank=True,
                default=None,
                help_text='Применять дисконт только если до платной консигнации осталось не более X дней (напр. 15, 10, 0).',
                null=True,
                verbose_name='Дней бесплатной консигнации осталось (<=)',
            ),
        ),
        migrations.AddField(
            model_name='pricecarkmdiscount',
            name='is_autopilot',
            field=models.BooleanField(
                default=False,
                help_text='Создано автоматически интеллектуальным помощником Центра управления',
                verbose_name='Создано автопилотом',
            ),
        ),
        migrations.AddField(
            model_name='dcmonthlyplan',
            name='is_autopilot',
            field=models.BooleanField(
                default=False,
                help_text='Автоматически активировать и синхронизировать рекомендованные правила дисконта при отставании от темпа или рисках консигнации',
                verbose_name='Автопилот дисконтов',
            ),
        ),
    ]
