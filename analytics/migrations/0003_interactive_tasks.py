from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0002_appraiserperformance_tradeinfunnel'),
    ]

    operations = [
        migrations.AddField(
            model_name='interactivepricingsnapshot',
            name='tasks_closed',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='interactivepricingsnapshot',
            name='tasks_total',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='interactivepricingsnapshot',
            name='accepted',
            field=models.BooleanField(default=False),
        ),
    ]

