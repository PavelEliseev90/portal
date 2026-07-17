from django.db import migrations, models


def migrate_body_type_strings(apps, schema_editor):
    EstimationRule = apps.get_model('estimation_engine', 'EstimationRule')
    RefTypeBody = apps.get_model('refs', 'RefTypeBody')
    for rule in EstimationRule.objects.exclude(body_type='').exclude(body_type__isnull=True):
        raw = (rule.body_type or '').strip()
        if not raw:
            continue
        parts = [p.strip() for p in raw.replace(';', ',').split(',') if p.strip()]
        found = []
        for part in parts:
            bt = RefTypeBody.objects.filter(name__iexact=part).first()
            if bt is None:
                bt = RefTypeBody.objects.filter(name_autohub__iexact=part).first()
            if bt is not None:
                found.append(bt)
        if found:
            rule.body_types.set(found)
            rule.body_type = ', '.join(bt.name for bt in found)[:512]
            rule.save(update_fields=['body_type'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('refs', '0141_auction_express_source_soglasovanie'),
        ('estimation_engine', '0009_rule_conditions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='estimationrule',
            name='body_type',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Кэш названий из body_types; пусто = любой. Не редактировать вручную.',
                max_length=512,
                verbose_name='Типы кузова (кэш)',
            ),
        ),
        migrations.AddField(
            model_name='estimationrule',
            name='body_types',
            field=models.ManyToManyField(
                blank=True,
                help_text='Можно выбрать несколько. Пусто = любой тип кузова.',
                related_name='estimation_rules',
                to='refs.reftypebody',
                verbose_name='Типы кузова',
            ),
        ),
        migrations.RunPython(migrate_body_type_strings, noop_reverse),
    ]
