"""Сроки этапов УС по ценовым группам (глобальная матрица + история снимков).

Логика как в RefCarsOrganization.refresh_data:
  days < days_1 → этап pk=4 (тест)
  days < days_2 → этап pk=2 (РДО)
  days < days_3 → этап pk=3 (коррекция)
  иначе         → этап pk=1 (ТХТ)
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.db import models, transaction


# Порядок этапов по дням на складе (как в legacy refresh_data).
STAGE_PK_ORDER = (4, 2, 3, 1)

# Значения по умолчанию из прежнего hardcode refresh_data (пороги «days < N»).
DEFAULT_STAGE_DAYS_BY_CODE = {
    '200': (3, 14, 24),
    '400': (4, 25, 34),
    '700': (5, 30, 39),
    '1200': (5, 36, 49),
    '2000': (7, 41, 54),
    '3000': (10, 45, 59),
    '5000': (12, 55, 69),
    '5001': (12, 55, 69),
}


class PriceGroupStageDaysSnapshot(models.Model):
    """Один снимок матрицы «ЦГ → пороги дней этапов». Каждое сохранение — новая запись."""
    created_at = models.DateTimeField('Дата', auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='price_group_stage_days_snapshots',
        verbose_name='Кто сохранил',
    )
    comment = models.CharField('Комментарий', max_length=255, blank=True, default='')

    class Meta:
        db_table = 'priceGroupStageDaysSnapshot'
        verbose_name = 'Снимок сроков этапов УС по ЦГ'
        verbose_name_plural = 'Снимки сроков этапов УС по ЦГ'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return 'Снимок #{} ({})'.format(
            self.pk,
            self.created_at.strftime('%d.%m.%Y %H:%M') if self.created_at else '—',
        )


class PriceGroupStageDaysLine(models.Model):
    """Строка снимка: пороги дней для одной ценовой группы."""
    snapshot = models.ForeignKey(
        PriceGroupStageDaysSnapshot,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name='Снимок',
    )
    price_group = models.ForeignKey(
        'RefGroupPrice',
        on_delete=models.PROTECT,
        related_name='stage_days_lines',
        verbose_name='Ценовая группа',
    )
    days_1 = models.PositiveIntegerField(
        'Дней до 2-го этапа (порог 1)',
        default=0,
        help_text='days < days_1 → этап 1 в цепочке (обычно «тест»)',
    )
    days_2 = models.PositiveIntegerField(
        'Дней до 3-го этапа (порог 2)',
        default=0,
        help_text='days < days_2 → этап 2 (обычно РДО)',
    )
    days_3 = models.PositiveIntegerField(
        'Дней до 4-го этапа (порог 3)',
        default=0,
        help_text='days < days_3 → этап 3 (обычно коррекция); иначе финальный этап',
    )

    class Meta:
        db_table = 'priceGroupStageDaysLine'
        verbose_name = 'Строка сроков этапов по ЦГ'
        verbose_name_plural = 'Строки сроков этапов по ЦГ'
        ordering = ['price_group__sort_order', 'price_group__code', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['snapshot', 'price_group'],
                name='uniq_stage_days_line_snapshot_group',
            ),
        ]

    def __str__(self):
        return '{}: <{}/{}/{}'.format(
            self.price_group_id, self.days_1, self.days_2, self.days_3,
        )

    def as_thresholds(self) -> Tuple[int, int, int]:
        return (int(self.days_1 or 0), int(self.days_2 or 0), int(self.days_3 or 0))


def get_latest_snapshot() -> Optional[PriceGroupStageDaysSnapshot]:
    return (
        PriceGroupStageDaysSnapshot.objects
        .prefetch_related('lines__price_group')
        .order_by('-created_at', '-id')
        .first()
    )


def get_latest_thresholds_by_code() -> Dict[str, Tuple[int, int, int]]:
    """code ЦГ → (days_1, days_2, days_3). Пусто → дефолты."""
    snap = get_latest_snapshot()
    if not snap:
        return dict(DEFAULT_STAGE_DAYS_BY_CODE)
    result = dict(DEFAULT_STAGE_DAYS_BY_CODE)
    for line in snap.lines.all():
        code = (line.price_group.code or '').strip()
        if code:
            result[code] = line.as_thresholds()
    return result


def resolve_stage_pk(days: int, price_group_code: str, thresholds_map: Optional[dict] = None) -> int:
    """Вернуть pk RefStagePrice по дням на складе и коду ЦГ."""
    mapping = thresholds_map if thresholds_map is not None else get_latest_thresholds_by_code()
    code = (price_group_code or '').strip()
    thresholds = mapping.get(code) or DEFAULT_STAGE_DAYS_BY_CODE.get(code) or (0, 0, 0)
    d1, d2, d3 = thresholds
    days = int(days or 0)
    if days < d1:
        return STAGE_PK_ORDER[0]
    if days < d2:
        return STAGE_PK_ORDER[1]
    if days < d3:
        return STAGE_PK_ORDER[2]
    return STAGE_PK_ORDER[3]


def days_until_next_stage(days: int, price_group_code: str, thresholds_map: Optional[dict] = None) -> int:
    """Сколько дней осталось до следующего порога (0 если уже на последнем)."""
    mapping = thresholds_map if thresholds_map is not None else get_latest_thresholds_by_code()
    code = (price_group_code or '').strip()
    thresholds = mapping.get(code) or DEFAULT_STAGE_DAYS_BY_CODE.get(code) or (0, 0, 0)
    d1, d2, d3 = thresholds
    days = int(days or 0)
    for bound in (d1, d2, d3):
        if days < bound:
            return max(0, bound - days)
    return 0


def get_rdo_days_to(price_group_code: str, thresholds_map: Optional[dict] = None) -> int:
    """
    Верхняя граница этапа РДО («по») для ЦГ = порог 2 (days_2).
    days < days_2 → этап РДО; значение days_2 — «по» для финансирования в формуле Авито.
    """
    from refs.price_groups import price_group_code as normalize_code

    code = normalize_code(price_group_code) or (price_group_code or '').strip().replace(' ', '')
    mapping = thresholds_map if thresholds_map is not None else get_latest_thresholds_by_code()
    thresholds = mapping.get(code) or DEFAULT_STAGE_DAYS_BY_CODE.get(code)
    if not thresholds:
        return 0
    return max(0, int(thresholds[1] or 0))


@transaction.atomic
def save_stage_days_snapshot(
    *,
    rows: List[dict],
    user=None,
    comment: str = '',
) -> PriceGroupStageDaysSnapshot:
    """
    rows: [{'price_group_id': int, 'days_1': int, 'days_2': int, 'days_3': int}, ...]
    """
    snap = PriceGroupStageDaysSnapshot.objects.create(
        created_by=user if getattr(user, 'is_authenticated', False) else None,
        comment=(comment or '')[:255],
    )
    lines = []
    for row in rows:
        pg_id = row.get('price_group_id')
        if not pg_id:
            continue
        lines.append(PriceGroupStageDaysLine(
            snapshot=snap,
            price_group_id=int(pg_id),
            days_1=max(0, int(row.get('days_1') or 0)),
            days_2=max(0, int(row.get('days_2') or 0)),
            days_3=max(0, int(row.get('days_3') or 0)),
        ))
    if lines:
        PriceGroupStageDaysLine.objects.bulk_create(lines)
    return snap


@transaction.atomic
def ensure_initial_snapshot(user=None) -> PriceGroupStageDaysSnapshot:
    """Создать первый снимок из DEFAULT_STAGE_DAYS_BY_CODE, если снимков ещё нет."""
    existing = get_latest_snapshot()
    if existing:
        return existing

    from refs.price_groups import get_active_price_groups

    rows = []
    for pg in get_active_price_groups():
        code = (pg.code or '').strip()
        d1, d2, d3 = DEFAULT_STAGE_DAYS_BY_CODE.get(code, (0, 0, 0))
        rows.append({
            'price_group_id': pg.pk,
            'days_1': d1,
            'days_2': d2,
            'days_3': d3,
        })
    return save_stage_days_snapshot(
        rows=rows,
        user=user,
        comment='Начальное заполнение из legacy refresh_data',
    )
