from django.db import migrations, models


PHOTO_REQUIRED_CODES = {
    'dent_strong',
    'scratch_strong',
    'rust',
    'rust_through',
    'chip',
    'crack',
    'replaced',
    'replace_needed',
    'replace',
    'hole',
    'restore',
    'repaint',
    'reupholstery',
}


def seed_requires_photo(apps, schema_editor):
    DamageType = apps.get_model('estimation_engine', 'DamageType')
    for dt in DamageType.objects.all():
        need = dt.code in PHOTO_REQUIRED_CODES or (dt.severity or 1) >= 2
        if dt.requires_photo != need:
            dt.requires_photo = need
            dt.save(update_fields=['requires_photo'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('estimation_engine', '0006_damage_type_section_interior'),
    ]

    operations = [
        migrations.AddField(
            model_name='damagetype',
            name='requires_photo',
            field=models.BooleanField(
                default=False,
                help_text='В новом UI осмотра отметка без фото считается незавершённой.',
                verbose_name='Обязательное фото',
            ),
        ),
        migrations.RunPython(seed_requires_photo, noop_reverse),
    ]
