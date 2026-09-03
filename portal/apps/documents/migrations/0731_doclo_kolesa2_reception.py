# Generated manually
# На копии D:\kors_group\portal уже есть:
#   0730_merge_20260903_1521
#   0731_alter_doсrecomendation_kod_recomendation
# Нельзя зависеть от несуществующего 0730_merge_doccarshipment_kod_recomendation.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0730_merge_20260903_1521'),
        ('documents', '0731_alter_doсrecomendation_kod_recomendation'),
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
