# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('refs', '0125_refallowablediscountkm'),
    ]

    operations = [
        migrations.AddField(
            model_name='refcarsorganization',
            name='min_km',
            field=models.IntegerField(blank=True, null=True, verbose_name='Мин. КМ'),
        ),
    ]
