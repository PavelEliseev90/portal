# Generated manually: drop orphan unreadable fields from vnesh (moved to test_drive)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0241_testdrive_unreadable_checks'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reginteractivocenkavnesh',
            name='unreadable_vin_int',
        ),
        migrations.RemoveField(
            model_name='reginteractivocenkavnesh',
            name='unreadable_engine_num_int',
        ),
        migrations.RemoveField(
            model_name='reginteractivocenkavnesh',
            name='unreadable_rama_int',
        ),
        migrations.RemoveField(
            model_name='regcontroldiagnosticvnesh',
            name='unreadable_vin_int',
        ),
        migrations.RemoveField(
            model_name='regcontroldiagnosticvnesh',
            name='unreadable_engine_num_int',
        ),
        migrations.RemoveField(
            model_name='regcontroldiagnosticvnesh',
            name='unreadable_rama_int',
        ),
    ]
