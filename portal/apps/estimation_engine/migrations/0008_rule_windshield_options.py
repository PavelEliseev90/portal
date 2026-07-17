from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estimation_engine', '0007_damage_type_requires_photo'),
    ]

    operations = [
        migrations.AddField(
            model_name='estimationrule',
            name='windshield_heat',
            field=models.CharField(
                blank=True,
                choices=[('', 'Любое'), ('yes', 'Да'), ('no', 'Нет')],
                default='',
                help_text='Условие по комплектации. Для 4 вариантов стекла задайте yes/no '
                          'и одну exclusive_group (например windshield).',
                max_length=8,
                verbose_name='Подогрев лобового',
            ),
        ),
        migrations.AddField(
            model_name='estimationrule',
            name='windshield_projection',
            field=models.CharField(
                blank=True,
                choices=[('', 'Любое'), ('yes', 'Да'), ('no', 'Нет')],
                default='',
                help_text='HUD / проекция. Пусто = не учитывать в условии.',
                max_length=8,
                verbose_name='Проекция на лобовое',
            ),
        ),
    ]
