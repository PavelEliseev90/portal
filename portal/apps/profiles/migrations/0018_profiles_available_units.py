from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0017_profiles_eco_report_profiles_estimation_report_and_more'),
        ('refs', '0135_refstatusavailability_refstatusransom_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='profiles',
            name='available_units',
            field=models.ManyToManyField(
                blank=True,
                related_name='profiles_with_access',
                to='refs.refunit',
                verbose_name='Доступные подразделения',
            ),
        ),
    ]
