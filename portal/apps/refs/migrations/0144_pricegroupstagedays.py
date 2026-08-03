# Generated manually for PriceGroupStageDaysSnapshot / Line

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_initial_snapshot(apps, schema_editor):
    Snapshot = apps.get_model('refs', 'PriceGroupStageDaysSnapshot')
    Line = apps.get_model('refs', 'PriceGroupStageDaysLine')
    RefGroupPrice = apps.get_model('refs', 'RefGroupPrice')

    if Snapshot.objects.exists():
        return

    defaults = {
        '200': (3, 14, 24),
        '400': (4, 25, 34),
        '700': (5, 30, 39),
        '1200': (5, 36, 49),
        '2000': (7, 41, 54),
        '3000': (10, 45, 59),
        '5000': (12, 55, 69),
        '5001': (12, 55, 69),
    }

    snap = Snapshot.objects.create(comment='Начальное заполнение из legacy refresh_data')
    groups = list(
        RefGroupPrice.objects.filter(is_active=True).exclude(code='').order_by('sort_order', 'code')
    )
    if not groups:
        groups = list(RefGroupPrice.objects.exclude(code='').order_by('sort_order', 'code'))

    for pg in groups:
        code = (pg.code or '').strip()
        d1, d2, d3 = defaults.get(code, (0, 0, 0))
        Line.objects.create(
            snapshot=snap,
            price_group=pg,
            days_1=d1,
            days_2=d2,
            days_3=d3,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('refs', '0143_refunit_auto_reprice_new'),
    ]

    operations = [
        migrations.CreateModel(
            name='PriceGroupStageDaysSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Дата')),
                ('comment', models.CharField(blank=True, default='', max_length=255, verbose_name='Комментарий')),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='price_group_stage_days_snapshots',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Кто сохранил',
                )),
            ],
            options={
                'verbose_name': 'Снимок сроков этапов УС по ЦГ',
                'verbose_name_plural': 'Снимки сроков этапов УС по ЦГ',
                'db_table': 'priceGroupStageDaysSnapshot',
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.CreateModel(
            name='PriceGroupStageDaysLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('days_1', models.PositiveIntegerField(
                    default=0,
                    help_text='days < days_1 → этап 1 в цепочке (обычно «тест»)',
                    verbose_name='Дней до 2-го этапа (порог 1)',
                )),
                ('days_2', models.PositiveIntegerField(
                    default=0,
                    help_text='days < days_2 → этап 2 (обычно РДО)',
                    verbose_name='Дней до 3-го этапа (порог 2)',
                )),
                ('days_3', models.PositiveIntegerField(
                    default=0,
                    help_text='days < days_3 → этап 3 (обычно коррекция); иначе финальный этап',
                    verbose_name='Дней до 4-го этапа (порог 3)',
                )),
                ('price_group', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='stage_days_lines',
                    to='refs.refgroupprice',
                    verbose_name='Ценовая группа',
                )),
                ('snapshot', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='lines',
                    to='refs.pricegroupstagedayssnapshot',
                    verbose_name='Снимок',
                )),
            ],
            options={
                'verbose_name': 'Строка сроков этапов по ЦГ',
                'verbose_name_plural': 'Строки сроков этапов по ЦГ',
                'db_table': 'priceGroupStageDaysLine',
                'ordering': ['price_group__sort_order', 'price_group__code', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='pricegroupstagedaysline',
            constraint=models.UniqueConstraint(
                fields=('snapshot', 'price_group'),
                name='uniq_stage_days_line_snapshot_group',
            ),
        ),
        migrations.RunPython(seed_initial_snapshot, noop_reverse),
    ]
