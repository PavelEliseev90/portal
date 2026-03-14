# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('register', '0196_alter_regcontroldiagnosticfile_file_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='regcontroldiagnosticsalon',
            name='seat_zones_json',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Оценка зон сидений (JSON)'),
        ),
    ]
