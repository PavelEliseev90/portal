# Generated manually for disposition saved filters

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('asp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reportsavedfilter',
            name='report_key',
            field=models.CharField(
                choices=[
                    ('margin', 'Кумулятивная маржа'),
                    ('stock', 'Остатки'),
                    ('accepted', 'Принятые'),
                    ('disposition', 'Диспозиция'),
                ],
                db_index=True,
                max_length=32,
                verbose_name='Ключ отчёта',
            ),
        ),
    ]
