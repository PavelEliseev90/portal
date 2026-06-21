"""История перерасчётов ценообразования интерактивной оценки."""
import contextvars
import json
import logging

from django.db.models import Q
from django.utils import timezone

from refs.models import RefStaff

logger = logging.getLogger(__name__)

PRICE_CALCULATION_LABELS = {
    'kors': '1C / Kors',
    'autohub_k': 'Автохаб +К',
    'autohub': 'Автохаб',
    'avito': 'Авито / Автотека',
    'custom': 'Ручной расчёт',
    'manual_save': 'Сохранение цен',
}

TRIGGER_LABELS = {
    'price_before_kd': 'Согласование до КД',
    'price_after_kd': 'Согласование после КД',
    'price_remote': 'Дистанционная оценка',
    'save_auto_price': 'Сохранение автоматических цен',
    'save_custom_price': 'Сохранение согласованных цен',
    'refresh_autohub': 'Обновление ЦНА',
    'refresh_znak': 'Обновление ЦНА + К',
    'refresh_kors': 'Обновление 1С / Kors',
    'refresh_all': 'Обновление всех данных ценообразования',
    'refresh_data1c': 'Обновление в 1С',
}

_history_context = contextvars.ContextVar('interactive_price_history_context', default=None)
_history_recorded = contextvars.ContextVar('interactive_price_history_recorded', default=False)


class InteractivePriceHistoryContext:
    def __init__(self, user=None, trigger='', save_history=False):
        self.user = user
        self.trigger = trigger or ''
        self.save_history = bool(save_history)


class interactive_price_history_context:
    def __init__(self, user=None, trigger='', save_history=True):
        self._token = None
        self._context = InteractivePriceHistoryContext(
            user=user,
            trigger=trigger,
            save_history=save_history,
        )

    def __enter__(self):
        _history_recorded.set(False)
        self._token = _history_context.set(self._context)
        return self._context

    def __exit__(self, exc_type, exc, tb):
        if self._token is not None:
            _history_context.reset(self._token)
        return False


def get_interactive_price_history_context():
    return _history_context.get()


def was_interactive_price_history_recorded():
    return bool(_history_recorded.get())


def resolve_history_params(user=None, trigger='', save_history=None):
    ctx = get_interactive_price_history_context()
    if save_history is None:
        save_history = ctx.save_history if ctx else False
    if user is None and ctx:
        user = ctx.user
    if not trigger and ctx:
        trigger = ctx.trigger
    return user, trigger, bool(save_history)


def resolve_soglasovanie(interactiv_rlk=None, estimation=None, soglasovanie=None):
    if soglasovanie is not None:
        return soglasovanie
    if interactiv_rlk is not None:
        ps = getattr(interactiv_rlk, 'page_soglasovanie', None)
        if ps is not None:
            return ps
    if estimation is not None:
        ps = getattr(estimation, 'page_soglasovanie', None)
        if ps is not None:
            return ps
    return None


def ensure_page_soglasovanie(interactiv_rlk=None, estimation=None):
    """Создать или синхронизировать page_soglasovanie на RLK и оценке."""
    from register.models import RegInteractivOcenkaSoglasovanie

    soglasovanie = resolve_soglasovanie(interactiv_rlk=interactiv_rlk, estimation=estimation)
    if soglasovanie is None:
        soglasovanie = RegInteractivOcenkaSoglasovanie()
        soglasovanie.save()

    if interactiv_rlk is not None and getattr(interactiv_rlk, 'page_soglasovanie_id', None) != soglasovanie.pk:
        interactiv_rlk.page_soglasovanie = soglasovanie
        interactiv_rlk.save(update_fields=['page_soglasovanie'])
    if estimation is not None and getattr(estimation, 'page_soglasovanie_id', None) != soglasovanie.pk:
        estimation.page_soglasovanie = soglasovanie
        estimation.save(update_fields=['page_soglasovanie'])
    return soglasovanie


def _resolve_staff(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    return RefStaff.objects.filter(domain_login=user.username).first()


def _json_safe_price_result(price_result):
    if not price_result:
        return {}
    data = dict(price_result)
    data.pop('estimation_settings', None)
    try:
        return json.loads(json.dumps(data, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        return {'estimation_price': data.get('estimation_price', 0)}


def _snapshot_soglasovanie_fields(soglasovanie):
    if soglasovanie is None:
        return {}
    return {
        'price_auto_1': soglasovanie.price_auto_1 or 0,
        'price_auto_2': soglasovanie.price_auto_2 or 0,
        'price_auto_3': soglasovanie.price_auto_3 or 0,
        'price_auto_bcp_1': soglasovanie.price_auto_bcp_1 or 0,
        'price_auto_bcp_2': soglasovanie.price_auto_bcp_2 or 0,
        'price_auto_bcp_3': soglasovanie.price_auto_bcp_3 or 0,
        'price_zna_1': soglasovanie.price_zna_1 or 0,
        'price_zna_2': soglasovanie.price_zna_2 or 0,
        'price_zna_3': soglasovanie.price_zna_3 or 0,
        'price_before_kd': soglasovanie.price_before_kd or 0,
        'price_after_kd': soglasovanie.price_after_kd or 0,
        'price_bcp': soglasovanie.price_bcp or 0,
        'discount_torg': soglasovanie.discount_torg or 0,
        'finance_price': soglasovanie.finance_price or 0,
        'zachita_ot_ubitka': soglasovanie.zachita_ot_ubitka or 0,
    }


def _resolve_recovery_amounts(safe_result=None, soglasovanie=None):
    """Затраты на восстановление: подготовка, слесарка, кузовной, итого."""
    safe_result = safe_result or {}

    podgotovka = safe_result.get('amount_podgotovka')
    ss = safe_result.get('amount_ss')
    mcu = safe_result.get('amount_mcu')

    if soglasovanie is not None:
        if not podgotovka:
            podgotovka = soglasovanie.amount_podgotovka or 0
        if not ss:
            ss = soglasovanie.amount_ss or 0
        if not mcu:
            mcu = soglasovanie.amount_mcu or 0

    podgotovka = podgotovka or 0
    ss = ss or 0
    mcu = mcu or 0

    total = safe_result.get('amount_sum') or safe_result.get('amount_recovery')
    if soglasovanie is not None and not total:
        total = soglasovanie.amount_recovery or 0
    if not total:
        total = podgotovka + ss + mcu

    return {
        'amount_podgotovka': podgotovka,
        'amount_ss': ss,
        'amount_mcu': mcu,
        'amount_recovery': total,
    }


def _build_history_row(item):
    author_name = ''
    if item.author_id:
        author_name = item.author.get_full_name() or item.author.username
    elif item.user_id:
        author_name = item.user.name
    return {
        'id': item.pk,
        'date': item.date,
        'type_calculation': item.price_calculation,
        'type_label': PRICE_CALCULATION_LABELS.get(item.price_calculation, item.price_calculation or '—'),
        'trigger': item.trigger,
        'trigger_label': TRIGGER_LABELS.get(item.trigger, item.trigger or '—'),
        'author_name': author_name or '—',
        'is_success': item.is_success,
        'error_message': item.error_message or '',
        'estimation_price': item.estimation_price or 0,
        'estimation_price_do_kd': item.estimation_price_do_kd or 0,
        'cna_expenses': item.cna_expenses or 0,
        'zna': item.zna or 0,
        'zg': item.zg or '',
        'kf': item.kf or '',
        'price_auto_1': item.price_auto_1 or 0,
        'price_auto_2': item.price_auto_2 or 0,
        'price_auto_3': item.price_auto_3 or 0,
        'price_auto_bcp_1': item.price_auto_bcp_1 or 0,
        'price_auto_bcp_2': item.price_auto_bcp_2 or 0,
        'price_auto_bcp_3': item.price_auto_bcp_3 or 0,
        'price_zna_1': item.price_zna_1 or 0,
        'price_zna_2': item.price_zna_2 or 0,
        'price_zna_3': item.price_zna_3 or 0,
        'price_before_kd': item.price_before_kd or 0,
        'price_after_kd': item.price_after_kd or 0,
        'amount_podgotovka': item.amount_podgotovka or 0,
        'amount_ss': item.amount_ss or 0,
        'amount_mcu': item.amount_mcu or 0,
        'amount_recovery': item.amount_recovery or (
            (item.amount_podgotovka or 0) + (item.amount_ss or 0) + (item.amount_mcu or 0)
        ),
        'comment': item.comment or '',
    }


def record_interactive_price_recalculation(
    estimation,
    soglasovanie,
    type_calculation,
    price_result,
    user=None,
    trigger='',
    save_history=None,
    is_success=True,
    error_message='',
    interactiv_rlk=None,
):
    from register.models import RegInteractivOcenkaPrice

    user, trigger, save_history = resolve_history_params(user, trigger, save_history)
    if not save_history:
        return None
    soglasovanie = resolve_soglasovanie(interactiv_rlk=interactiv_rlk, estimation=estimation, soglasovanie=soglasovanie)
    if soglasovanie is None:
        soglasovanie = ensure_page_soglasovanie(interactiv_rlk=interactiv_rlk, estimation=estimation)
    if soglasovanie is None:
        return None

    try:
        soglasovanie.refresh_from_db()
        safe_result = _json_safe_price_result(price_result)
        snapshot = _snapshot_soglasovanie_fields(soglasovanie)
        for key in ('discount_torg', 'finance_price', 'zachita_ot_ubitka'):
            snapshot.pop(key, None)
        recovery = _resolve_recovery_amounts(safe_result, soglasovanie)

        record = RegInteractivOcenkaPrice(
            date=timezone.now(),
            price_calculation=type_calculation or '',
            trigger=trigger or type_calculation or '',
            page_soglasovanie=soglasovanie,
            estimation=estimation,
            author=user if user and getattr(user, 'is_authenticated', False) else None,
            user=_resolve_staff(user),
            is_success=is_success,
            error_message=error_message or '',
            estimation_price=(safe_result.get('estimation_price') if safe_result else 0) or 0,
            estimation_price_do_kd=(safe_result.get('estimation_price_do_kd') if safe_result else 0) or 0,
            zna=(safe_result.get('zna') if safe_result else 0) or 0,
            zg=str(safe_result.get('zg') or '') if safe_result else '',
            kf=str(safe_result.get('kf') or '') if safe_result else '',
            cna_expenses=(safe_result.get('cna_expenses') if safe_result else 0) or 0,
            amount_podgotovka=recovery['amount_podgotovka'],
            amount_ss=recovery['amount_ss'],
            amount_mcu=recovery['amount_mcu'],
            amount_recovery=recovery['amount_recovery'],
            discount_torg=(safe_result.get('discount_torg') if safe_result else None) or getattr(soglasovanie, 'discount_torg', 0) or 0,
            finance_price=(safe_result.get('finance_price') if safe_result else None) or getattr(soglasovanie, 'finance_price', 0) or 0,
            zachita_ot_ubitka=(safe_result.get('zachita_ot_ubitka') if safe_result else None) or getattr(soglasovanie, 'zachita_ot_ubitka', 0) or 0,
            raw_calculation_json=safe_result,
            **snapshot,
        )
        record.text_json = json.dumps(safe_result, ensure_ascii=False, default=str)
        record.save()
        _history_recorded.set(True)
        return record
    except Exception:
        logger.exception('Не удалось записать историю перерасчёта цен (estimation=%s, trigger=%s)', getattr(estimation, 'pk', estimation), trigger)
        return None


def record_interactive_price_save_snapshot(
    estimation,
    interactiv_rlk=None,
    soglasovanie=None,
    user=None,
    trigger='',
    type_calculation='manual_save',
    force=False,
):
    """Записать снимок согласованных цен после POST-сохранения."""
    user, trigger, save_history = resolve_history_params(user, trigger, save_history=True)
    if not save_history:
        return None
    if not force and was_interactive_price_history_recorded():
        return None

    soglasovanie = ensure_page_soglasovanie(interactiv_rlk=interactiv_rlk, estimation=estimation)
    if soglasovanie is None:
        soglasovanie = resolve_soglasovanie(interactiv_rlk=interactiv_rlk, estimation=estimation, soglasovanie=soglasovanie)
    if soglasovanie is None:
        return None

    soglasovanie.refresh_from_db()
    recovery = _resolve_recovery_amounts(soglasovanie=soglasovanie)
    price_result = {
        'estimation_price': soglasovanie.price_after_kd or soglasovanie.price_before_kd or 0,
        'estimation_price_do_kd': soglasovanie.price_before_kd or 0,
        'cna_expenses': soglasovanie.price_bcp or soglasovanie.price_auto_bcp_2 or soglasovanie.price_auto_bcp_3 or 0,
        'amount_podgotovka': recovery['amount_podgotovka'],
        'amount_ss': recovery['amount_ss'],
        'amount_mcu': recovery['amount_mcu'],
        'amount_recovery': recovery['amount_recovery'],
        'amount_sum': recovery['amount_recovery'],
        'discount_torg': soglasovanie.discount_torg or 0,
        'finance_price': soglasovanie.finance_price or 0,
        'zachita_ot_ubitka': soglasovanie.zachita_ot_ubitka or 0,
        'zna': soglasovanie.price_zna_2 or soglasovanie.price_zna_3 or soglasovanie.price_zna_1 or 0,
    }
    if trigger == 'price_remote' and estimation is not None and getattr(estimation, 'page_remote', None) is not None:
        page_remote = estimation.page_remote
        price_result['estimation_price_do_kd'] = page_remote.price_eco or price_result['estimation_price_do_kd']
        price_result['estimation_price'] = page_remote.price_eco or price_result['estimation_price']
        price_result['cna_expenses'] = page_remote.price_auto_bcp or price_result['cna_expenses']
        price_result['zna'] = page_remote.price_zna or price_result['zna']

    return record_interactive_price_recalculation(
        estimation=estimation,
        soglasovanie=soglasovanie,
        type_calculation=type_calculation,
        price_result=price_result,
        user=user,
        trigger=trigger,
        save_history=True,
        interactiv_rlk=interactiv_rlk,
    )


def record_interactive_price_refresh(
    interactiv_rlk,
    estimation,
    user,
    refresh_kind,
    price_calculation_fn,
    body_info=None,
    salon_info=None,
):
    """Записать историю перерасчёта после обновления данных ценообразования (GET refresh_data)."""
    trigger_map = {
        'autohub': 'refresh_autohub',
        'znak': 'refresh_znak',
        'kors': 'refresh_kors',
        'all': 'refresh_all',
        'data1c': 'refresh_data1c',
    }
    trigger = trigger_map.get(refresh_kind, 'refresh_{}'.format(refresh_kind))

    calc_types = []
    if refresh_kind in ('autohub', 'all'):
        calc_types.extend(['autohub', 'avito'])
    if refresh_kind in ('znak', 'all'):
        calc_types.append('autohub_k')
    if refresh_kind in ('kors', 'all'):
        calc_types.append('kors')
    if refresh_kind == 'all':
        calc_types.append('custom')
    if refresh_kind == 'data1c':
        calc_types.extend(['kors', 'autohub_k', 'autohub', 'avito', 'custom'])

    calc_types = list(dict.fromkeys(calc_types))
    ensure_page_soglasovanie(interactiv_rlk=interactiv_rlk, estimation=estimation)

    with interactive_price_history_context(user=user, trigger=trigger, save_history=True):
        for calc_type in calc_types:
            price_calculation_fn(
                interactiv_rlk,
                estimation,
                type_calculation=calc_type,
                user=user,
                trigger=trigger,
                save_history=True,
                body_info=body_info,
                salon_info=salon_info,
                persist=False,
            )

    return record_interactive_price_save_snapshot(
        estimation=estimation,
        interactiv_rlk=interactiv_rlk,
        user=user,
        trigger=trigger,
        force=True,
    )


def get_price_recalc_history_for_estimation(estimation, interactiv_rlk=None, limit=50):
    from register.models import RegInteractivOcenkaPrice

    if estimation is None:
        return []

    filters = Q(estimation=estimation)
    soglasovanie = resolve_soglasovanie(interactiv_rlk=interactiv_rlk, estimation=estimation)
    if soglasovanie is not None:
        filters |= Q(page_soglasovanie=soglasovanie)

    qs = (
        RegInteractivOcenkaPrice.objects
        .filter(filters)
        .select_related('author', 'user', 'page_soglasovanie')
        .order_by('-date', '-id')[:limit]
    )
    return [_build_history_row(item) for item in qs]
