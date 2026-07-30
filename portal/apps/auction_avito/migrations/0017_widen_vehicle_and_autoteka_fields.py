# Generated manually for varchar overflow fixes on outcome upsert

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auction_avito', '0016_auction_txt_coeffs_and_commission'),
    ]

    operations = [
        migrations.AlterField(
            model_name='avitolotvehicle',
            name='registration_number',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='Госномер'),
        ),
        migrations.AlterField(
            model_name='avitoautotekareport',
            name='state_status',
            field=models.CharField(
                blank=True,
                default='',
                help_text='success | incomplete | …',
                max_length=50,
                verbose_name='state.status',
            ),
        ),
        migrations.AlterField(
            model_name='avitoautotekaevent',
            name='event_type',
            field=models.CharField(db_index=True, max_length=100, verbose_name='type'),
        ),
        migrations.AlterField(
            model_name='avitoautotekaevent',
            name='status',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='status'),
        ),
        migrations.AlterField(
            model_name='avitoautotekaevent',
            name='description',
            field=models.TextField(blank=True, default='', verbose_name='description'),
        ),
    ]
