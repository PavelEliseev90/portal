# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0730_merge_doccarshipment_kod_recomendation'),
    ]

    operations = [
        migrations.AddField(
            model_name='doclo',
            name='kolesa2_reception',
            field=models.BooleanField(
                default=False,
                help_text='Признак, что по листу оценки принят второй комплект колёс',
                verbose_name='Приёмка второго комплекта колёс',
            ),
        ),
    ]
