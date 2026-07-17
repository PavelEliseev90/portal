# Generated manually to match parallel leaf on deploy hosts.
# Options drift: catalog package verbose names.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('estimation_engine', '0007_damage_type_requires_photo'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='preparationworkpackage',
            options={
                'ordering': ['sort_order', 'code'],
                'verbose_name': 'Пакет работ (каталог)',
                'verbose_name_plural': 'Пакеты работ (каталог)',
            },
        ),
    ]
