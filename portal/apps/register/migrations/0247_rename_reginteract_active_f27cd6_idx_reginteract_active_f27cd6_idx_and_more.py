# Index stays as regInteractiv_active_due_idx from 0243 (0244_rename is a no-op).
# Only align PK with DEFAULT_AUTO_FIELD = BigAutoField.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0246_merge_reception_and_alarm_index'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reginteractivocenkaalarm',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
