# Generated manually for PriceCarAlgorithmSettings and PriceCarBrand.analysis_period_days

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0043_dccommandcentershowcase'),
    ]

    operations = [
        migrations.CreateModel(
            name='PriceCarAlgorithmSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('analysis_period_days', models.PositiveIntegerField(default=60, help_text='Глубина выборки розничных продаж аналогов (в днях) для алгоритма АвтоК', verbose_name='Период анализа статистики продаж по умолчанию (дней)')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
            ],
            options={
                'verbose_name': 'Настройки алгоритма ценообразования',
                'verbose_name_plural': 'Настройки алгоритма ценообразования',
                'db_table': 'prices_car_algorithm_settings',
            },
        ),
        migrations.AddField(
            model_name='pricecarbrand',
            name='analysis_period_days',
            field=models.PositiveIntegerField(blank=True, help_text='Глубина выборки сделок аналогов для АвтоК в днях (если не задано — берётся общее значение)', null=True, verbose_name='Период анализа статистики продаж (дней)'),
        ),
    ]
