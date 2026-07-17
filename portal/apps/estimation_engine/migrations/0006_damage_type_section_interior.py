from django.db import migrations, models


def seed_sections_and_interior(apps, schema_editor):
    DamageType = apps.get_model('estimation_engine', 'DamageType')

    exterior = {
        'dent': ('Вмятина', 'вмятина', 1, 10),
        'dent_strong': ('Вмятина сильная', 'вмятина сильная', 2, 20),
        'scratch': ('Царапина', 'царапина', 1, 30),
        'scratch_strong': ('Царапина сильная', 'царапина сильная', 2, 40),
        'rust': ('Ржавчина', 'ржавчина', 2, 50),
        'rust_through': ('Ржавчина сквозная', 'ржавчина сквозная', 3, 60),
        'chip': ('Скол', 'скол', 1, 80),
        'crack': ('Трещина', 'трещина', 2, 90),
        'replaced': ('Заменён', 'заменен', 3, 100),
        'replace_needed': ('Заменить', 'заменить', 3, 110),
    }
    for code, (name, legacy, severity, order) in exterior.items():
        DamageType.objects.update_or_create(
            code=code,
            defaults={
                'name': name,
                'legacy_label': legacy,
                'severity': severity,
                'sort_order': order,
                'section': 'exterior',
                'is_active': True,
            },
        )

    # старый код replace → replaced (не удаляем, помечаем exterior)
    DamageType.objects.filter(code='replace').update(section='exterior', legacy_label='заменен')
    DamageType.objects.filter(code='paint').update(section='exterior')

    interior = [
        ('restore', 'Восстановление формы', 'восстановление', 2, 10),
        ('hole', 'Дырка', 'дырка', 3, 20),
        ('reupholstery', 'Перешив', 'перешив', 2, 30),
        ('repaint', 'Перекрас', 'перекрас', 2, 40),
    ]
    for code, name, legacy, severity, order in interior:
        DamageType.objects.update_or_create(
            code=code,
            defaults={
                'name': name,
                'legacy_label': legacy,
                'severity': severity,
                'sort_order': order,
                'section': 'interior',
                'is_active': True,
            },
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('estimation_engine', '0005_scheme_elements_damage_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='damagetype',
            name='section',
            field=models.CharField(
                choices=[
                    ('exterior', 'Кузов / внешний'),
                    ('interior', 'Салон / внутренний'),
                    ('common', 'Общий'),
                ],
                db_index=True,
                default='exterior',
                max_length=32,
                verbose_name='Раздел',
            ),
        ),
        migrations.RunPython(seed_sections_and_interior, noop_reverse),
    ]
