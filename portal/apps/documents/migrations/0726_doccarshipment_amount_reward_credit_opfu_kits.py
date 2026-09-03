# Generated manually for DocCarShipment reward/kits amounts

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0725_alter_doсrecomendation_kod_recomendation'),
    ]

    operations = [
        migrations.AddField(
            model_name='doccarshipment',
            name='amount_reward_credit',
            field=models.FloatField(blank=True, default=0.0, verbose_name='Сумма вознаграждения кредит'),
        ),
        migrations.AddField(
            model_name='doccarshipment',
            name='amount_reward_opfu',
            field=models.FloatField(blank=True, default=0.0, verbose_name='Сумма вознаграждения ОПФУ'),
        ),
        migrations.AddField(
            model_name='doccarshipment',
            name='amount_kits',
            field=models.FloatField(blank=True, default=0.0, verbose_name='Сумма продажи комплектов'),
        ),
    ]
