"""
Итоги завершённых лотов Maxposter (решение продавца).

Источник: страница лота / dealer/auction/{lotOfferId}/view или API оффера.
Тексты на UI Maxposter (наблюдаемые / эвристики):
- «Ждём решения продавца…» → waiting_seller (остаётся в очереди)
- выигрыш → won
- другой покупатель → lost
- «Продавец никого не выбрал» → no_selection (финал)
- «Лот не выкупили» → not_redeemed (финал)
- «Вы отказались от лота» → we_refused (финал)
- «Лот не взяли в работу…» / «Лот не обработан…» → not_taken (финал; как выигрыш: письмо + внимание в списке)
- «Продавец отменил аукцион» → canceled (финал)
"""
from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.html import escape

from auction_avito.services.offer_status import STATUS_NAMES, TERMINAL_OFFER_STATUSES

logger = logging.getLogger(__name__)

OUTCOME_WAITING = 'waiting_seller'
OUTCOME_WON = 'won'
OUTCOME_LOST = 'lost'
OUTCOME_NO_SELECTION = 'no_selection'
OUTCOME_NOT_REDEEMED = 'not_redeemed'
OUTCOME_WE_REFUSED = 'we_refused'
OUTCOME_NOT_TAKEN = 'not_taken'
OUTCOME_CANCELED = 'canceled'
OUTCOME_UNKNOWN = 'unknown'

OUTCOME_NAMES = {
    OUTCOME_WAITING: 'Ждём решения продавца',
    OUTCOME_WON: 'Выигран',
    OUTCOME_LOST: 'Проигран / выбрали другого',
    OUTCOME_NO_SELECTION: 'Продавец никого не выбрал',
    OUTCOME_NOT_REDEEMED: 'Лот не выкупили',
    OUTCOME_WE_REFUSED: 'Вы отказались от лота',
    OUTCOME_NOT_TAKEN: 'Лот не взяли в работу / не обработан',
    OUTCOME_CANCELED: 'Продавец отменил аукцион',
    OUTCOME_UNKNOWN: 'Итог неизвестен',
}

# Короткие подписи для бейджей в списке лотов.
OUTCOME_BADGE_LABELS = {
    OUTCOME_WAITING: 'Ждём продавца',
    OUTCOME_WON: 'Выигран',
    OUTCOME_LOST: 'Проигран',
    OUTCOME_NO_SELECTION: 'Никого не выбрали',
    OUTCOME_NOT_REDEEMED: 'Не выкупили',
    OUTCOME_WE_REFUSED: 'Отказались',
    OUTCOME_NOT_TAKEN: 'Не обработан',
    OUTCOME_CANCELED: 'Отменён',
    OUTCOME_UNKNOWN: 'Итог ?',
}

OUTCOME_FILTER_CHOICES = [
    (OUTCOME_WAITING, OUTCOME_NAMES[OUTCOME_WAITING]),
    (OUTCOME_WON, OUTCOME_NAMES[OUTCOME_WON]),
    (OUTCOME_LOST, OUTCOME_NAMES[OUTCOME_LOST]),
    (OUTCOME_NO_SELECTION, OUTCOME_NAMES[OUTCOME_NO_SELECTION]),
    (OUTCOME_NOT_REDEEMED, OUTCOME_NAMES[OUTCOME_NOT_REDEEMED]),
    (OUTCOME_WE_REFUSED, OUTCOME_NAMES[OUTCOME_WE_REFUSED]),
    (OUTCOME_NOT_TAKEN, OUTCOME_NAMES[OUTCOME_NOT_TAKEN]),
    (OUTCOME_CANCELED, OUTCOME_NAMES[OUTCOME_CANCELED]),
    (OUTCOME_UNKNOWN, OUTCOME_NAMES[OUTCOME_UNKNOWN]),
]


def offer_list_badge(offer) -> dict[str, str]:
    """
    Бейдж для карточки списка: приоритет у outcome_code, иначе status_code.
    Возвращает {code, label, css, important} — css = класс-модификатор aav-status-*.
    important=True для won / not_taken (выигрыш и «не обработан»).
    """
    if offer is None:
        return {'code': '', 'label': '—', 'css': 'muted', 'important': False}

    outcome = (getattr(offer, 'outcome_code', None) or '').strip()
    if outcome:
        return {
            'code': outcome,
            'label': OUTCOME_BADGE_LABELS.get(outcome) or OUTCOME_NAMES.get(outcome) or outcome,
            'css': outcome,
            'important': outcome in WIN_NOTIFY_OUTCOMES,
        }

    status = (getattr(offer, 'status_code', None) or '').strip()
    status_labels = {
        'inprogress': 'Активен',
        'finished': 'Завершён',
        'won': 'Выигран',
        'lost': 'Проигран',
        'ended': 'Завершён',
        'canceled': 'Отменён',
    }
    css = status if status in (
        'inprogress', 'finished', 'won', 'lost', 'canceled',
    ) else 'muted'
    if status == 'ended':
        css = 'finished'
    return {
        'code': status,
        'label': (
            getattr(offer, 'status_name', None)
            or status_labels.get(status)
            or status
            or '—'
        ),
        'css': css,
        'important': status == 'won',
    }


# Финальные исходы — повторный опрос не нужен.
FINAL_OUTCOMES = frozenset({
    OUTCOME_WON,
    OUTCOME_LOST,
    OUTCOME_NO_SELECTION,
    OUTCOME_NOT_REDEEMED,
    OUTCOME_WE_REFUSED,
    OUTCOME_NOT_TAKEN,
    OUTCOME_CANCELED,
})

# Итоги, при которых шлём win-письмо разово и считаем «требует внимания» как выигрыш.
WIN_NOTIFY_OUTCOMES = frozenset({
    OUTCOME_WON,
    OUTCOME_NOT_TAKEN,
})

# Маппинг сырого status.status с ленты Maxposter → portal status_code.
MAXPOSTER_STATUS_MAP = {
    'ended': 'finished',
    'finished': 'finished',
    'canceled': 'canceled',
    'cancelled': 'canceled',
    'won': 'won',
    'lost': 'lost',
    'inprogress': 'inprogress',
}

_WON_RE = re.compile(
    r'вас\s+выбрали|вы\s+выиграл|выбран[аы]?\s+ваш[аеи]\s|'
    r'поздравляем|'
    r'лот\s+ваш|вы\s+победил|продавец\s+выбрал\s+вас|winner|you\s+won',
    re.I,
)
# Шаблонные тексты Maxposter («уведомление о том, что продавец… выбрал предложение…»)
# не являются фактом победы — вырезаем из haystack до классификации.
_OUTCOME_NOISE_RE = re.compile(
    r'уведомление\s+о\s+том[^.|]{0,200}дилерского\s+центра[^.|]{0,80}'
    r'|уведомление\s+о\s+том[^.|]{0,200}среди\s+прочих',
    re.I,
)
_NO_SELECTION_RE = re.compile(
    r'продавец\s+никого\s+не\s+выбрал|никого\s+не\s+выбрал|'
    r'не\s+выбрал\s+никого|никто\s+не\s+выбран',
    re.I,
)
_NOT_REDEEMED_RE = re.compile(
    r'не\s*выкупил',
    re.I,
)
_WE_REFUSED_RE = re.compile(
    r'отказал\w*\s+от\s+лота',
    re.I,
)
_NOT_TAKEN_RE = re.compile(
    r'не\s*взял\w*\s*в\s*работ|'
    r'не\s*обработан|'
    r'лот\s+не\s+обработан|'
    r'доступен\w*\s+другим\s+дилер|'
    r'лот\s+не\s+взял',
    re.I,
)
_LOST_RE = re.compile(
    r'выбрал[аи]?\s+друго|выбран\s+друг|другого\s+покупател|другой\s+участник|проиграл|'
    r'лот\s+достался|продавец\s+выбрал\s+друг|you\s+lost|another\s+bidder',
    re.I,
)
# Не использовать голое «решения продавца» — ловит «Пожелания продавца».
_WAIT_RE = re.compile(
    r'(?:ждём|ждем)\s+решения(?:\s+продавца)?|'
    r'ожида(?:ем|ние)\s+решени|'
    r'обычно\s+на\s+это\s+уходит\s+день',
    re.I,
)
_CANCEL_RE = re.compile(
    r'отменил\w*\s+аукцион|аукцион\s+отмен|'
    r'продавец\s+отмен|'
    r'отмен[её]н|canceled|cancelled|снят\s+с\s+аукциона',
    re.I,
)
_FINISHED_TITLE_RE = re.compile(r'аукцион\s+заверш', re.I)

# Запасной матч без пробелов/пунктуации (ломаные пробелы в DOM Maxposter).
_COMPACT_FINALS = (
    (OUTCOME_NOT_REDEEMED, ('невыкупил',)),
    (OUTCOME_WE_REFUSED, ('отказалисьотлота', 'отказалсяотлота')),
    (OUTCOME_NOT_TAKEN, ('невзяливработ', 'необработан', 'доступендругимдилер')),
    (OUTCOME_NO_SELECTION, ('никогоневыбрал', 'продавецникогоневыбрал')),
    (OUTCOME_CANCELED, (
        'продавецотменилаукцион',
        'отменилаукцион',
        'отменилаукцион',
        'аукционотмен',
        'продавецотменил',
    )),
)

# Самый надёжный слой: обычные подстроки (после lower + norm spaces).
# Порядок важен — более специфичные фразы раньше.
_FINAL_SUBSTRING_RULES = (
    (OUTCOME_NOT_REDEEMED, (
        'лот не выкупил',
        'не выкупил',
    )),
    (OUTCOME_WE_REFUSED, (
        'отказались от лота',
        'отказался от лота',
        'вы отказались от лота',
    )),
    (OUTCOME_NOT_TAKEN, (
        'не взяли в работу',
        'не взял в работу',
        'не взяла в работу',
        'лот не обработан',
        'не обработан',
        'доступен другим дилер',
    )),
    (OUTCOME_NO_SELECTION, (
        'никого не выбрал',
        'продавец никого не выбрал',
    )),
    (OUTCOME_CANCELED, (
        'продавец отменил аукцион',
        'отменил аукцион',
        'отменила аукцион',
        'аукцион отменён',
        'аукцион отменен',
        'аукцион отмен',
    )),
    (OUTCOME_LOST, (
        'выбрали другого покупател',
        'выбрал другого покупател',
        'другого покупател',
        'выбрали другого',
    )),
)


def normalize_maxposter_status(status_code: str | None) -> str:
    code = (status_code or '').strip()
    return MAXPOSTER_STATUS_MAP.get(code, code)


def _norm_spaces(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '').strip())


def _compact_text(text: str) -> str:
    return re.sub(r'[^\wа-яё]+', '', (text or '').lower(), flags=re.I)


def _match_compact_final(haystack: str) -> str | None:
    compact = _compact_text(haystack)
    if not compact:
        return None
    for code, needles in _COMPACT_FINALS:
        if any(n in compact for n in needles):
            return code
    return None


def _match_substring_final(haystack: str) -> str | None:
    low = (haystack or '').lower()
    if not low:
        return None
    for code, needles in _FINAL_SUBSTRING_RULES:
        if any(n in low for n in needles):
            return code
    return None


def _finished_outcome(code: str, title: str, detail: str, *, status: str = 'finished') -> dict[str, str]:
    if code == OUTCOME_WON:
        st = 'won'
    elif code == OUTCOME_LOST:
        st = 'lost'
    else:
        st = status or 'finished'
    return {
        'outcome_code': code,
        'outcome_title': title or ('Аукцион отменён' if code == OUTCOME_CANCELED else 'Аукцион завершен'),
        'outcome_detail': detail or OUTCOME_NAMES.get(code, ''),
        'status_code': st,
    }


def _strip_outcome_noise(text: str) -> str:
    """Убирает шаблонные уведомления Maxposter, дающие ложный won."""
    if not text:
        return ''
    return _norm_spaces(_OUTCOME_NOISE_RE.sub(' ', text))


def _our_bid_behind_max(offer) -> bool:
    """True, если на лоте maxBid строго выше нашей ставки — мы не лидеры."""
    if offer is None:
        return False
    our = getattr(offer, 'bid', None)
    lot = getattr(offer, 'lot', None)
    if our in (None, '') or lot is None:
        return False
    max_bid = getattr(lot, 'max_bid', None)
    if max_bid in (None, ''):
        try:
            max_bid = lot.display_max_bid
        except Exception:
            max_bid = None
    try:
        our_n = int(our)
        max_n = int(max_bid) if max_bid not in (None, '') else None
    except (TypeError, ValueError):
        return False
    if max_n is None or our_n <= 0:
        return False
    return max_n > our_n


def classify_outcome_text(
    *,
    title: str = '',
    detail: str = '',
    blob: str = '',
    status_code: str = '',
) -> dict[str, str]:
    """
    Классифицирует итог по текстам со страницы/API.
    Возвращает outcome_code, outcome_title, outcome_detail, status_code.

    «Ждём решения продавца» приоритетнее шаблонных фраз про «выбрали» в blob.
    Won — только по title/detail или явному status=won (не по blob в одиночку).
    """
    title = _norm_spaces(title)
    detail = _norm_spaces(detail)
    blob = _norm_spaces(blob)
    primary = _strip_outcome_noise(_norm_spaces(f'{title}\n{detail}'))
    haystack = _strip_outcome_noise(_norm_spaces(f'{title}\n{detail}\n{blob}'))
    raw_status = normalize_maxposter_status(status_code)

    # 1) Прямые финальные фразы — сначала title/detail.
    phrase_code = (
        _match_substring_final(primary)
        or _match_compact_final(primary)
        or _match_substring_final(haystack)
        or _match_compact_final(haystack)
    )
    if phrase_code == OUTCOME_LOST:
        return {
            'outcome_code': OUTCOME_LOST,
            'outcome_title': title or 'Аукцион завершен',
            'outcome_detail': detail or OUTCOME_NAMES[OUTCOME_LOST],
            'status_code': OUTCOME_LOST,
        }
    if phrase_code in FINAL_OUTCOMES:
        return _finished_outcome(
            phrase_code,
            title or ('Аукцион отменён' if phrase_code == OUTCOME_CANCELED else 'Аукцион завершен'),
            detail or OUTCOME_NAMES.get(phrase_code, ''),
        )

    # 2) Regex-слой финалов (кроме won).
    if _NOT_REDEEMED_RE.search(haystack):
        return _finished_outcome(OUTCOME_NOT_REDEEMED, title, detail or OUTCOME_NAMES[OUTCOME_NOT_REDEEMED])
    if _WE_REFUSED_RE.search(haystack):
        return _finished_outcome(OUTCOME_WE_REFUSED, title, detail or OUTCOME_NAMES[OUTCOME_WE_REFUSED])
    if _NOT_TAKEN_RE.search(haystack):
        return _finished_outcome(OUTCOME_NOT_TAKEN, title, detail or OUTCOME_NAMES[OUTCOME_NOT_TAKEN])
    if raw_status == OUTCOME_NO_SELECTION or _NO_SELECTION_RE.search(haystack):
        return _finished_outcome(OUTCOME_NO_SELECTION, title, detail or OUTCOME_NAMES[OUTCOME_NO_SELECTION])
    if raw_status == OUTCOME_CANCELED or _CANCEL_RE.search(haystack):
        return _finished_outcome(
            OUTCOME_CANCELED,
            title or 'Аукцион отменён',
            detail or OUTCOME_NAMES[OUTCOME_CANCELED],
        )

    # 3) Ожидание решения — ДО won по слабым совпадениям в blob.
    strong_won_primary = bool(_WON_RE.search(primary))
    strong_lost_primary = bool(_LOST_RE.search(primary))
    wait_in_primary = bool(_WAIT_RE.search(primary) or raw_status == OUTCOME_WAITING)
    wait_anywhere = wait_in_primary or bool(_WAIT_RE.search(haystack))

    if wait_anywhere and not strong_won_primary and not strong_lost_primary:
        return {
            'outcome_code': OUTCOME_WAITING,
            'outcome_title': title or 'Аукцион завершен',
            'outcome_detail': detail or OUTCOME_NAMES[OUTCOME_WAITING],
            'status_code': 'finished',
        }

    # 4) Won — только явный status или фраза в title/detail (не blob).
    if raw_status == OUTCOME_WON or strong_won_primary:
        return {
            'outcome_code': OUTCOME_WON,
            'outcome_title': title or 'Аукцион завершен',
            'outcome_detail': detail or OUTCOME_NAMES[OUTCOME_WON],
            'status_code': OUTCOME_WON,
        }
    if raw_status == OUTCOME_LOST or strong_lost_primary or _LOST_RE.search(haystack):
        return {
            'outcome_code': OUTCOME_LOST,
            'outcome_title': title or 'Аукцион завершен',
            'outcome_detail': detail or OUTCOME_NAMES[OUTCOME_LOST],
            'status_code': OUTCOME_LOST,
        }
    if (
        _FINISHED_TITLE_RE.search(haystack)
        and not phrase_code
        and not strong_won_primary
        and not strong_lost_primary
        and not _NO_SELECTION_RE.search(haystack)
        and not _NOT_REDEEMED_RE.search(haystack)
        and not _WE_REFUSED_RE.search(haystack)
        and not _NOT_TAKEN_RE.search(haystack)
        and not _CANCEL_RE.search(haystack)
    ):
        return {
            'outcome_code': OUTCOME_WAITING,
            'outcome_title': title or 'Аукцион завершен',
            'outcome_detail': detail or OUTCOME_NAMES[OUTCOME_WAITING],
            'status_code': 'finished',
        }
    if raw_status in ('finished', 'ended') or _FINISHED_TITLE_RE.search(haystack):
        return {
            'outcome_code': OUTCOME_WAITING if not detail else OUTCOME_UNKNOWN,
            'outcome_title': title or 'Аукцион завершен',
            'outcome_detail': detail or OUTCOME_NAMES[OUTCOME_WAITING],
            'status_code': 'finished',
        }
    return {
        'outcome_code': OUTCOME_UNKNOWN if haystack else '',
        'outcome_title': title,
        'outcome_detail': detail or haystack[:500],
        'status_code': raw_status or 'finished',
    }


def parse_win_notify_emails(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = re.split(r'[\s,;]+', str(raw))
    seen = set()
    out = []
    for p in parts:
        email = p.strip().lower()
        if not email or '@' not in email or email in seen:
            continue
        seen.add(email)
        out.append(email)
    return out


def offers_needing_outcome_poll(
    *,
    limit: int = 30,
    lookback_days: int = 21,
    recheck_hours: int = 6,
    dealer_id=None,
) -> QuerySet:
    """
    Офферы со ставкой по завершённым (или «зависшим») лотам, где итог ещё не финальный.

    waiting_seller («Ждём решения продавца») всегда остаётся в очереди —
    при следующем опросе состояние проверяется снова, пока продавец не выберет итог.

    Важно: лот мог уйти с активной ленты Maxposter без обновления status/finish_at
    на портале — такие офферы со ставкой тоже включаем (иначе «сделали ставку,
    а в итоги не попадает»).
    """
    from django.db.models import Case, IntegerField, Value, When

    from auction_avito.models import AvitoLotOffer

    now = timezone.now()
    since = now - timedelta(days=max(1, int(lookback_days)))
    # recheck_hours оставлен для совместимости API; waiting_seller без паузы.
    _ = recheck_hours

    terminal_statuses = list(TERMINAL_OFFER_STATUSES) + ['ended', 'canceled', 'finished']

    # «Завершён для опроса итога»
    finished_like = (
        Q(lot__finish_at__lte=now)
        | Q(lot__origin_finish_at__lte=now)
        | Q(status_code__in=terminal_statuses)
        # Нет дат финиша — лот часто уже снят с ленты, finish_at так и не обновили
        | Q(lot__finish_at__isnull=True, lot__origin_finish_at__isnull=True)
    )

    # Окно давности: по finish / ставке / последней синхронизации итога / updated
    in_lookback = (
        Q(lot__finish_at__gte=since)
        | Q(lot__origin_finish_at__gte=since)
        | Q(bid_made_at__gte=since)
        | Q(outcome_synced_at__gte=since)
        | Q(updated_at__gte=since)
    )

    qs = (
        AvitoLotOffer.objects
        .select_related('lot', 'account', 'lot__vehicle_avito', 'lot__venue')
        .filter(bid__gt=0)
        .filter(finished_like)
        .filter(in_lookback)
        .exclude(outcome_code__in=list(FINAL_OUTCOMES))
        .filter(
            Q(outcome_synced_at__isnull=True)
            | Q(outcome_code='')
            | Q(outcome_code=OUTCOME_UNKNOWN)
            | Q(outcome_code=OUTCOME_WAITING)
        )
    )

    if dealer_id not in (None, ''):
        try:
            qs = qs.filter(account__dealer_id=int(dealer_id))
        except (TypeError, ValueError):
            pass

    # Сначала никогда не опрашивали, потом давно не синкали waiting_seller
    qs = qs.annotate(
        _sync_priority=Case(
            When(outcome_synced_at__isnull=True, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        ),
    ).order_by('_sync_priority', 'outcome_synced_at', 'lot__finish_at', 'id')

    return qs[:max(1, min(int(limit or 30), 100))]


def backfill_outcome_lot_chats(*, lookback_days: int = 21, limit: int = 80) -> dict[str, int]:
    """
    Досылает короткий статус в чат лота по недавним офферам с известным итогом.
    Нужен, когда итог уже сохранён (в т.ч. финал ушёл из очереди опроса),
    а сообщение в чат раньше не ушло. Дубликаты отсекаются внутри notify_*.
    """
    from auction_avito.chat_utils import notify_auction_won, notify_lot_outcome
    from auction_avito.models import AvitoLotOffer

    since = timezone.now() - timedelta(days=max(1, int(lookback_days)))
    qs = (
        AvitoLotOffer.objects
        .select_related('lot')
        .filter(bid__gt=0, lot__isnull=False)
        .exclude(outcome_code='')
        .exclude(outcome_code=OUTCOME_UNKNOWN)
        .filter(
            Q(outcome_synced_at__gte=since)
            | Q(outcome_synced_at__isnull=True, lot__finish_at__gte=since)
        )
        .order_by('-outcome_synced_at', '-id')[:max(1, min(int(limit or 80), 200))]
    )
    sent = 0
    skipped = 0
    errors = 0
    for offer in qs:
        code = (offer.outcome_code or '').strip()
        if not code:
            skipped += 1
            continue
        try:
            if code == OUTCOME_WON:
                msg = notify_auction_won(offer)
            else:
                msg = notify_lot_outcome(offer)
            if msg is not None:
                sent += 1
            else:
                skipped += 1
        except Exception as exc:
            errors += 1
            logger.warning(
                'avito outcome chat backfill failed lotOfferId=%s: %s',
                offer.lot_offer_id,
                exc,
            )
    result = {'sent': sent, 'skipped': skipped, 'errors': errors, 'checked': sent + skipped + errors}
    if sent or errors:
        logger.info('avito outcome chat backfill: %s', result)
    return result


def serialize_outcome_queue_item(offer) -> dict[str, Any]:
    lot = offer.lot
    vehicle = getattr(lot, 'vehicle_avito', None)
    brand = getattr(vehicle, 'brand_name', '') or ''
    model = getattr(vehicle, 'model_name', '') or ''
    year = getattr(vehicle, 'year', None)
    return {
        'lotOfferId': offer.lot_offer_id,
        'lotId': lot.lot_id if lot else None,
        'lotPk': lot.pk if lot else None,
        'dealerId': getattr(offer.account, 'dealer_id', None),
        'bid': offer.bid,
        'statusCode': offer.status_code,
        'outcomeCode': offer.outcome_code or '',
        'outcomeTitle': offer.outcome_title or '',
        'outcomeDetail': offer.outcome_detail or '',
        'outcomeSyncedAt': offer.outcome_synced_at.isoformat() if offer.outcome_synced_at else '',
        'finishAt': lot.finish_at.isoformat() if lot and lot.finish_at else '',
        'maxposterUrl': (
            f'https://app.maxposter.ru/dealer/auction/{offer.lot_offer_id}/view'
            if offer.lot_offer_id else ''
        ),
        'car': ' '.join(str(x) for x in (brand, model, year) if x).strip(),
        'viewUrl': f'/auction_avito/lots/{lot.pk}/' if lot else '',
    }


def _last_calc(lot):
    if lot is None:
        return None
    return lot.calculations.filter(is_success=True).order_by('-calculated_at').first()


def _portal_lot_url(lot) -> str:
    if lot is None:
        return ''
    base = getattr(settings, 'SITE_URL', '') or getattr(settings, 'PORTAL_BASE_URL', '') or ''
    path = f'/auction_avito/lots/{lot.pk}/'
    if base:
        return base.rstrip('/') + path
    return path


def _offer_venue_label(offer) -> str:
    """Площадка аукциона (AvitoVenue или sellerPlaceName + dealerId)."""
    lot = getattr(offer, 'lot', None)
    if lot is None:
        return '—'
    venue = getattr(lot, 'venue', None)
    if venue is not None:
        return venue.display_label
    account = getattr(offer, 'account', None)
    dealer_id = getattr(account, 'dealer_id', None) if account else None
    name = (lot.seller_place_name or '').strip()
    city = ''
    if name and ',' in name:
        city_part, _, rest = name.partition(',')
        if rest.strip():
            city = city_part.strip()
            name = rest.strip()
    label_parts = [p for p in (name, city) if p]
    label = ' · '.join(label_parts) if label_parts else '—'
    if dealer_id:
        label = f'{label} (ID {dealer_id})' if label != '—' else f'ID {dealer_id}'
    return label or '—'


def _html_link(url: str, text: str | None = None) -> str:
    if not url:
        return '—'
    href = escape(url)
    label = escape(text or url)
    return f'<a href="{href}" style="color:#2563eb;text-decoration:underline">{label}</a>'


def _email_table_rows(rows: list[tuple]) -> str:
    parts = []
    for row in rows:
        key = row[0]
        value = row[1]
        is_html = row[2] if len(row) > 2 else False
        if is_html:
            cell = str(value)
        else:
            cell = escape(str(value)).replace('\n', '<br>')
        parts.append(
            f'<tr><td style="padding:6px 10px;color:#64748b;vertical-align:top">'
            f'{escape(str(key))}</td>'
            f'<td style="padding:6px 10px;color:#0f172a">{cell}</td></tr>'
        )
    return ''.join(parts)


def _maxposter_url(offer) -> str:
    if not offer or not offer.lot_offer_id:
        return ''
    return f'https://app.maxposter.ru/dealer/auction/{offer.lot_offer_id}/view'


def build_win_email_html(offer) -> tuple[str, str]:
    """subject, html для письма о победе."""
    lot = offer.lot
    vehicle = getattr(lot, 'vehicle_avito', None) if lot else None
    brand = getattr(vehicle, 'brand_name', '') or ''
    model = getattr(vehicle, 'model_name', '') or ''
    year = getattr(vehicle, 'year', '') or ''
    car = ' '.join(str(x) for x in (brand, model, year) if x).strip() or f'лот {getattr(lot, "lot_id", "—")}'
    calc = _last_calc(lot)
    buyout = getattr(calc, 'estimation_price', None) if calc else None
    profit = getattr(calc, 'profit', None) if calc else None
    zna = getattr(calc, 'zna', None) if calc else None

    def money(v):
        if v in (None, ''):
            return '—'
        try:
            return f'{int(round(float(v))):,}'.replace(',', ' ') + ' ₽'
        except (TypeError, ValueError):
            return str(v)

    subject = f'Аукцион Авито: выигран лот {getattr(lot, "lot_id", "—")} — {car}'
    headline = 'Мы выиграли лот на аукционе Авито'
    if (offer.outcome_code or '').strip() == OUTCOME_NOT_TAKEN:
        subject = (
            f'Аукцион Авито: лот не обработан {getattr(lot, "lot_id", "—")} — {car}'
        )
        headline = 'Лот не обработан / не взяли в работу — требуется внимание'

    rows = [
        ('Площадка', _offer_venue_label(offer)),
        ('Автомобиль', car),
        ('Лот', getattr(lot, 'lot_id', '—')),
        ('lotOfferId', offer.lot_offer_id),
        ('Наша ставка', money(offer.bid)),
        ('Выкуп (расчёт)', money(buyout)),
        ('Прибыль (расчёт)', money(profit)),
        ('ЦНА (расчёт)', money(zna)),
        ('Итог Maxposter', f'{offer.outcome_title or ""}\n{offer.outcome_detail or ""}'.strip()),
        ('Maxposter', _html_link(_maxposter_url(offer), 'Открыть лот в Maxposter'), True),
        ('Портал', _html_link(_portal_lot_url(lot), 'Открыть лот на портале'), True),
    ]
    body_rows = _email_table_rows(rows)
    html = (
        '<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#0f172a">'
        f'<h2 style="color:#166534;margin:0 0 12px">{escape(headline)}</h2>'
        f'<p style="margin:0 0 16px">{escape(car)}</p>'
        f'<table style="border-collapse:collapse;width:100%;max-width:640px">{body_rows}</table>'
        '</div>'
    )
    return subject, html


def resolve_win_notify_emails(offer) -> list[str]:
    """Сначала email площадки (account), иначе общий fallback из настроек."""
    from auction_avito.models import AvitoAuctionSettings

    account = getattr(offer, 'account', None)
    platform_raw = (getattr(account, 'win_notify_emails', None) or '').strip()
    if platform_raw:
        emails = parse_win_notify_emails(platform_raw)
        if emails:
            return emails
    return parse_win_notify_emails(AvitoAuctionSettings.get_solo().win_notify_emails)


def send_win_email(offer, *, emails: list[str] | None = None) -> dict[str, Any]:
    from django.core.mail import EmailMultiAlternatives
    from auction_avito.models import AvitoLotOffer

    if emails is None:
        emails = resolve_win_notify_emails(offer)
    if not emails:
        return {'sent': False, 'reason': 'no recipients'}

    offer = (
        AvitoLotOffer.objects.select_related(
            'lot',
            'lot__venue',
            'lot__venue__city',
            'account',
        )
        .get(pk=offer.pk)
    )

    subject, html = build_win_email_html(offer)
    from_email = getattr(settings, 'EMAIL_HOST_USER_INFO', None) or settings.EMAIL_HOST_USER
    msg = EmailMultiAlternatives(subject, html, from_email, emails)
    msg.attach_alternative(html, 'text/html')
    msg.send(fail_silently=False)
    return {'sent': True, 'to': emails, 'subject': subject}


def apply_offer_outcome(
    offer,
    *,
    title: str = '',
    detail: str = '',
    blob: str = '',
    status_code: str = '',
    outcome_code: str = '',
    raw: str = '',
    send_email: bool = True,
    notify_chat: bool = True,
) -> dict[str, Any]:
    """
    Сохраняет итог на оффере, при необходимости меняет status_code,
    шлёт письмо и чат при первом переходе в won / not_taken,
    пишет короткий статус в чат лота (с защитой от дублей).
    """
    from auction_avito.chat_utils import notify_auction_won, notify_lot_outcome

    prev_outcome = (offer.outcome_code or '').strip()
    prev_status = (offer.status_code or '').strip()

    # Всегда классифицируем по текстам со страницы — так финальные фразы
    # («Лот не выкупили» и т.п.) не залипают как waiting_seller.
    classified = classify_outcome_text(
        title=title,
        detail=detail,
        blob=blob,
        status_code=status_code,
    )

    # Пустая выгрузка с Maxposter (UI/сессия) — не затираем известный итог на unknown/? .
    extract_empty = not (
        (title or '').strip() or (detail or '').strip() or (blob or '').strip() or (status_code or '').strip()
    )
    if extract_empty:
        logger.warning(
            'avito outcome: empty extract lotOfferId=%s — keep prev=%s',
            getattr(offer, 'lot_offer_id', None),
            prev_outcome or '-',
        )
        classified = {
            'outcome_code': prev_outcome or '',
            'outcome_title': (offer.outcome_title or '') if prev_outcome else '',
            'outcome_detail': (offer.outcome_detail or '') if prev_outcome else '',
            'status_code': prev_status or offer.status_code or 'finished',
        }
    elif (classified.get('outcome_code') or '').strip() in ('', OUTCOME_UNKNOWN) and prev_outcome:
        # Слабая классификация при наличии прежнего waiting/финала — не откатываем в ?.
        if prev_outcome == OUTCOME_WAITING or prev_outcome in FINAL_OUTCOMES:
            classified = {
                'outcome_code': prev_outcome,
                'outcome_title': _norm_spaces(title) or offer.outcome_title or OUTCOME_NAMES.get(prev_outcome, ''),
                'outcome_detail': _norm_spaces(detail) or offer.outcome_detail or OUTCOME_NAMES.get(prev_outcome, ''),
                'status_code': (
                    prev_outcome if prev_outcome in ('won', 'lost')
                    else (prev_status or 'finished')
                ),
            }
    # Явный код от клиента — только если по тексту итог пустой/неясный,
    # либо клиент прислал более «сильный» финал.
    if outcome_code:
        text_code = (classified.get('outcome_code') or '').strip()
        if (
            outcome_code in FINAL_OUTCOMES
            and text_code in ('', OUTCOME_UNKNOWN, OUTCOME_WAITING)
        ) or text_code in ('', OUTCOME_UNKNOWN):
            classified = {
                'outcome_code': outcome_code,
                'outcome_title': _norm_spaces(title) or OUTCOME_NAMES.get(outcome_code, ''),
                'outcome_detail': _norm_spaces(detail) or OUTCOME_NAMES.get(outcome_code, ''),
                'status_code': (
                    outcome_code if outcome_code in ('won', 'lost')
                    else normalize_maxposter_status(status_code) or 'finished'
                ),
            }
            if outcome_code in (
                OUTCOME_CANCELED, OUTCOME_NO_SELECTION,
                OUTCOME_NOT_REDEEMED, OUTCOME_WE_REFUSED, OUTCOME_NOT_TAKEN,
            ):
                classified['status_code'] = 'finished'

    # Защита от ложного won: наша ставка ниже maxBid лота → победы быть не может.
    if (classified.get('outcome_code') or '').strip() == OUTCOME_WON and _our_bid_behind_max(offer):
        logger.warning(
            'avito outcome: reject won lotOfferId=%s ourBid=%s maxBid=%s (not leading)',
            getattr(offer, 'lot_offer_id', None),
            getattr(offer, 'bid', None),
            getattr(getattr(offer, 'lot', None), 'max_bid', None),
        )
        wait_hint = _WAIT_RE.search(_norm_spaces(f'{title}\n{detail}\n{blob}'))
        classified = {
            'outcome_code': OUTCOME_WAITING if wait_hint else OUTCOME_UNKNOWN,
            'outcome_title': _norm_spaces(title) or 'Аукцион завершен',
            'outcome_detail': (
                _norm_spaces(detail)
                or (
                    OUTCOME_NAMES[OUTCOME_WAITING] if wait_hint
                    else 'Итог уточняется (наша ставка ниже maxBid)'
                )
            ),
            'status_code': 'finished',
        }

    now = timezone.now()
    offer.outcome_code = classified['outcome_code'] or offer.outcome_code
    offer.outcome_title = classified['outcome_title'] or offer.outcome_title
    offer.outcome_detail = classified['outcome_detail'] or offer.outcome_detail
    if raw:
        offer.outcome_raw = raw[:20000]
    elif blob or title or detail:
        offer.outcome_raw = _norm_spaces(f'{title}\n{detail}\n{blob}')[:20000]
    offer.outcome_synced_at = now

    new_status = classified.get('status_code') or offer.status_code
    new_status = normalize_maxposter_status(new_status)
    if new_status in ('won', 'lost', 'finished', 'inprogress', 'canceled'):
        offer.status_code = new_status if new_status != 'canceled' else 'finished'
        offer.status_name = STATUS_NAMES.get(
            offer.status_code,
            classified.get('outcome_title') or offer.status_name or offer.status_code,
        )
        if offer.outcome_code == OUTCOME_WON:
            offer.status_code = 'won'
            offer.status_name = STATUS_NAMES['won']
        elif offer.outcome_code == OUTCOME_LOST:
            offer.status_code = 'lost'
            offer.status_name = STATUS_NAMES['lost']
        elif offer.outcome_code in (
            OUTCOME_NO_SELECTION, OUTCOME_CANCELED, OUTCOME_WAITING,
            OUTCOME_NOT_REDEEMED, OUTCOME_WE_REFUSED, OUTCOME_NOT_TAKEN,
            OUTCOME_UNKNOWN,
        ):
            offer.status_code = 'finished'
            offer.status_name = STATUS_NAMES['finished']
            if offer.outcome_code in FINAL_OUTCOMES and not offer.outcome_detail:
                offer.outcome_detail = OUTCOME_NAMES.get(offer.outcome_code, '')

    update_fields = [
        'outcome_code', 'outcome_title', 'outcome_detail', 'outcome_raw',
        'outcome_synced_at', 'status_code', 'status_name',
    ]

    email_result = {'sent': False, 'reason': 'skipped'}
    chat_result = {'sent': False, 'reason': 'skipped'}
    became_won = (
        offer.outcome_code == OUTCOME_WON
        and prev_outcome != OUTCOME_WON
    )
    became_win_notify = (
        offer.outcome_code in WIN_NOTIFY_OUTCOMES
        and prev_outcome not in WIN_NOTIFY_OUTCOMES
    )
    new_code = (offer.outcome_code or '').strip()

    # В чат лота — короткий статус при любом известном итоге.
    # Дубликаты отсекает notify_* (в т.ч. waiting_seller → waiting_seller,
    # если сообщения ещё не было — отправим).
    # won / not_taken — win-письмо разово + чат.
    if notify_chat and became_win_notify:
        try:
            if offer.outcome_code == OUTCOME_WON:
                sent = notify_auction_won(offer)
                chat_kind = 'won'
            else:
                sent = notify_lot_outcome(offer, prev_outcome=prev_outcome)
                chat_kind = 'not_taken' if offer.outcome_code == OUTCOME_NOT_TAKEN else 'outcome'
            chat_result = {
                'sent': sent is not None,
                'kind': chat_kind,
                'reason': None if sent is not None else 'duplicate',
            }
        except Exception as exc:
            chat_result = {'sent': False, 'reason': f'chat error: {exc}'}
        if send_email and offer.win_email_sent_at is None:
            try:
                email_result = send_win_email(offer)
                if email_result.get('sent'):
                    offer.win_email_sent_at = now
                    update_fields.append('win_email_sent_at')
            except Exception as exc:
                email_result = {'sent': False, 'reason': str(exc)}
    elif notify_chat and new_code and new_code != OUTCOME_UNKNOWN:
        try:
            sent = notify_lot_outcome(offer, prev_outcome=prev_outcome)
            chat_result = {
                'sent': sent is not None,
                'kind': 'outcome',
                'code': new_code,
                'reason': None if sent is not None else 'duplicate',
            }
        except Exception as exc:
            chat_result = {'sent': False, 'reason': f'chat error: {exc}'}
            logger.warning('avito outcome chat failed lotOfferId=%s: %s', offer.lot_offer_id, exc)

    offer.save(update_fields=update_fields)
    result = {
        'ok': True,
        'lotOfferId': offer.lot_offer_id,
        'lotId': offer.lot.lot_id if offer.lot_id else None,
        'prevOutcome': prev_outcome,
        'prevStatus': prev_status,
        'outcomeCode': offer.outcome_code,
        'outcomeTitle': offer.outcome_title,
        'outcomeDetail': offer.outcome_detail,
        'statusCode': offer.status_code,
        'statusName': offer.status_name,
        'becameWon': became_won,
        'becameWinNotify': became_win_notify,
        'email': email_result,
        'chat': chat_result,
        'outcomeSyncedAt': now.isoformat(),
    }
    logger.info(
        'avito outcome: lotOfferId=%s lotId=%s %s/%s → %s/%s title=%r detail=%r '
        'becameWon=%s becameWinNotify=%s chat=%s',
        offer.lot_offer_id,
        offer.lot.lot_id if offer.lot_id else None,
        prev_outcome or '-',
        prev_status or '-',
        offer.outcome_code,
        offer.status_code,
        offer.outcome_title,
        offer.outcome_detail,
        became_won,
        became_win_notify,
        chat_result,
    )
    return result
