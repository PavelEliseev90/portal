# Generated manually for RegInteractivOcenkaReception.amount_vzaimozachet

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0243_reginteractivocenkaalarm'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='amount_vzaimozachet',
            field=models.IntegerField(
                blank=True,
                default=0,
                null=True,
                verbose_name='Сумма взаимозачета',
            ),
        ),
    ]
