from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prices_car', '0028_brandkm_allow_dc_transfers'),
    ]

    operations = [
        migrations.AddField(
            model_name='carcalculationstypedetail',
            name='is_trade_in',
            field=models.BooleanField(
                default=False,
                help_text='Если включено — применение этого показателя в КП влияет на выбор расчётного КМ (АвтоК с trade-in)',
                verbose_name='Показатель трейд-ин',
            ),
        ),
        migrations.AddField(
            model_name='kmcar',
            name='km_auto_k_tradein',
            field=models.IntegerField(
                blank=True,
                default=0,
                null=True,
                verbose_name='КМ АвтоК с trade-in',
            ),
        ),
        migrations.AlterField(
            model_name='kmcar',
            name='km_auto_k',
            field=models.IntegerField(
                blank=True,
                default=0,
                null=True,
                verbose_name='КМ АвтоК без trade-in',
            ),
        ),
    ]
