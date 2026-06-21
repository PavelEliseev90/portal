from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0219_regcontroldiagnosticvnesh_windshield_camera_int_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='regestimationssettings',
            name='diagnostic_extra_by_price_group',
            field=models.JSONField(
                blank=True,
                default=dict,
                null=True,
                verbose_name='Диагностика по доп. ценовым группам (JSON)',
            ),
        ),
    ]
