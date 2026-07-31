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
    'admin_settings_switch': 'Смена настроек ценообразования (админ)',
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


def build_price_recalc_history_queryset(
    *,
    date_start=None,
    date_end=None,
    unit_id=None,
    calc_type='autohub',
    trigger='',
    car_query='',
):
    """Отфильтрованный queryset истории перерасчётов для отчёта (по умолчанию только autohub)."""
    from analytics.models import InteractivePricingSnapshot
    from register.models import RegInteractivOcenkaPrice

    qs = (
        RegInteractivOcenkaPrice.objects
        .filter(estimation_id__isnull=False)
        .order_by('-date', '-id')
    )

    calc_type = (calc_type or 'autohub').strip() or 'autohub'
    qs = qs.filter(price_calculation=calc_type)

    if date_start is not None:
        qs = qs.filter(date__gte=date_start)
    if date_end is not None:
        qs = qs.filter(date__lte=date_end)
    if trigger:
        qs = qs.filter(trigger=trigger)

    car_query = (car_query or '').strip()
    needs_snapshot = bool(unit_id) or bool(car_query)
    if needs_snapshot:
        snap = InteractivePricingSnapshot.objects.all()
        if unit_id:
            snap = snap.filter(unit_id=unit_id)
        if car_query:
            car_q = (
                Q(vin__icontains=car_query)
                | Q(model_name__icontains=car_query)
            )
            if car_query.isdigit():
                car_id = int(car_query)
                car_q |= Q(rlk_id=car_id) | Q(estimation_id=car_id)
            snap = snap.filter(car_q)
        qs = qs.filter(estimation_id__in=snap.values('estimation_id'))

    return qs


def _delta_fields(item, prev):
    if prev is None:
        return {
            'has_prev': False,
            'prev_estimation_price': None,
            'delta_estimation_price': None,
            'prev_cna_expenses': None,
            'delta_cna_expenses': None,
            'prev_amount_recovery': None,
            'delta_amount_recovery': None,
            'prev_price_auto_1': None,
            'delta_price_auto_1': None,
            'prev_price_auto_2': None,
            'delta_price_auto_2': None,
            'prev_price_auto_3': None,
            'delta_price_auto_3': None,
            'calc_type_changed': False,
            'prev_type_label': None,
        }

    prev_recovery = prev.amount_recovery or (
        (prev.amount_podgotovka or 0) + (prev.amount_ss or 0) + (prev.amount_mcu or 0)
    )
    curr_recovery = item.amount_recovery or (
        (item.amount_podgotovka or 0) + (item.amount_ss or 0) + (item.amount_mcu or 0)
    )
    return {
        'has_prev': True,
        'prev_estimation_price': prev.estimation_price or 0,
        'delta_estimation_price': (item.estimation_price or 0) - (prev.estimation_price or 0),
        'prev_cna_expenses': prev.cna_expenses or 0,
        'delta_cna_expenses': (item.cna_expenses or 0) - (prev.cna_expenses or 0),
        'prev_amount_recovery': prev_recovery,
        'delta_amount_recovery': curr_recovery - prev_recovery,
        'prev_price_auto_1': prev.price_auto_1 or 0,
        'delta_price_auto_1': (item.price_auto_1 or 0) - (prev.price_auto_1 or 0),
        'prev_price_auto_2': prev.price_auto_2 or 0,
        'delta_price_auto_2': (item.price_auto_2 or 0) - (prev.price_auto_2 or 0),
        'prev_price_auto_3': prev.price_auto_3 or 0,
        'delta_price_auto_3': (item.price_auto_3 or 0) - (prev.price_auto_3 or 0),
        'calc_type_changed': (prev.price_calculation or '') != (item.price_calculation or ''),
        'prev_type_label': PRICE_CALCULATION_LABELS.get(
            prev.price_calculation, prev.price_calculation or '—'
        ),
    }


def _car_meta_from_item(item):
    estimation = item.estimation
    rlk = getattr(estimation, 'rlk', None) if estimation else None
    unit = None
    if rlk is not None:
        unit = rlk.unit_dc or rlk.unit

    mark = ''
    model = ''
    if estimation is not None:
        mark = estimation.mark_name or ''
        model = estimation.model_name or ''
        if (not mark or not model) and estimation.modification_id:
            try:
                mod = estimation.modification
                if mod and getattr(mod, 'model', None):
                    if not model:
                        model = mod.model.name or ''
                    if not mark and getattr(mod.model, 'mark', None):
                        mark = mod.model.mark.name or ''
            except Exception:
                pass

    vin = getattr(estimation, 'vin', '') or ''
    car_label = ' '.join(x for x in (mark, model) if x).strip()
    if vin:
        car_label = f'{car_label} · {vin}'.strip(' ·') if car_label else vin

    return {
        'estimation_id': item.estimation_id,
        'rlk_id': getattr(rlk, 'id', None) if rlk else None,
        'vin': vin,
        'car_label': car_label or '—',
        'unit_name': getattr(unit, 'name', None) or '—',
        'unit_id': getattr(unit, 'id', None),
        'settings_id': (
            getattr(item.page_soglasovanie, 'settings_id', None)
            if item.page_soglasovanie_id else None
        ),
    }


def _recovery_amount(item):
    return item.amount_recovery or (
        (item.amount_podgotovka or 0) + (item.amount_ss or 0) + (item.amount_mcu or 0)
    )


def _history_values(item):
    return {
        'date': item.date,
        'estimation_price': item.estimation_price or 0,
        'cna_expenses': item.cna_expenses or 0,
        'zna': item.zna or 0,
        'kf': item.kf or '',
        'zg': item.zg or '',
        'price_auto_1': item.price_auto_1 or 0,
        'price_auto_2': item.price_auto_2 or 0,
        'price_auto_3': item.price_auto_3 or 0,
        'price_before_kd': item.price_before_kd or 0,
        'price_after_kd': item.price_after_kd or 0,
        'amount_podgotovka': item.amount_podgotovka or 0,
        'amount_ss': item.amount_ss or 0,
        'amount_mcu': item.amount_mcu or 0,
        'amount_recovery': _recovery_amount(item),
    }


def enrich_price_recalc_history_rows(items):
    """
    Строки журнала: лёгкая Δ к предыдущему autohub-перерасчёту той же оценки.
    """
    from collections import defaultdict

    from register.models import RegInteractivOcenkaPrice

    items = list(items)
    est_ids = {item.estimation_id for item in items if item.estimation_id}
    prev_map = {}
    if est_ids:
        history_by_est = defaultdict(list)
        for hist in (
            RegInteractivOcenkaPrice.objects
            .filter(estimation_id__in=est_ids, price_calculation='autohub')
            .order_by('estimation_id', 'date', 'id')
            .only(
                'id', 'estimation_id', 'date', 'price_calculation',
                'estimation_price', 'cna_expenses', 'amount_recovery',
                'amount_podgotovka', 'amount_ss', 'amount_mcu',
                'price_auto_1', 'price_auto_2', 'price_auto_3',
                'zna', 'kf',
            )
        ):
            history_by_est[hist.estimation_id].append(hist)
        for hist_list in history_by_est.values():
            for idx, hist in enumerate(hist_list):
                if idx > 0:
                    prev_map[hist.pk] = hist_list[idx - 1]

    rows = []
    for item in items:
        row = _build_history_row(item)
        row.update(_car_meta_from_item(item))
        row.update(_delta_fields(item, prev_map.get(item.pk)))
        rows.append(row)

    return rows


def build_autohub_first_last_page(
    *,
    date_start=None,
    date_end=None,
    unit_id=None,
    car_query='',
    trigger='',
    only_changed=False,
    page=1,
    per_page=50,
):
    """
    Быстрый отчёт «было → стало» только для autohub:
    1) агрегация estimation_id в SQL
    2) детали первого/последнего — только для текущей страницы
    3) метаданные авто — из InteractivePricingSnapshot
    """
    from collections import defaultdict

    from analytics.models import InteractivePricingSnapshot
    from django.core.paginator import Paginator
    from django.db.models import Count, Max, Min
    from register.models import RegInteractivOcenkaPrice

    filtered = build_price_recalc_history_queryset(
        date_start=date_start,
        date_end=date_end,
        unit_id=unit_id,
        calc_type='autohub',
        trigger=trigger,
        car_query=car_query,
    )

    total_recalcs = filtered.count()

    agg_qs = (
        filtered
        .order_by()
        .values('estimation_id')
        .annotate(
            recalc_count=Count('id'),
            first_date=Min('date'),
            last_date=Max('date'),
        )
        .order_by('-last_date')
    )

    if only_changed:
        # Дешёвый прокси: есть минимум 2 пересчёта для сравнения
        agg_qs = agg_qs.filter(recalc_count__gte=2)

    paginator = Paginator(agg_qs, per_page)
    page_obj = paginator.get_page(page)
    page_rows = list(page_obj.object_list)
    est_ids = [row['estimation_id'] for row in page_rows if row.get('estimation_id')]

    history_by_est = defaultdict(list)
    if est_ids:
        hist_qs = (
            RegInteractivOcenkaPrice.objects
            .filter(
                estimation_id__in=est_ids,
                price_calculation='autohub',
            )
            .only(
                'id', 'estimation_id', 'date', 'trigger',
                'estimation_price', 'cna_expenses', 'zna', 'kf', 'zg',
                'price_auto_1', 'price_auto_2', 'price_auto_3',
                'price_before_kd', 'price_after_kd',
                'amount_podgotovka', 'amount_ss', 'amount_mcu', 'amount_recovery',
            )
            .order_by('estimation_id', 'date', 'id')
        )
        if date_start is not None:
            hist_qs = hist_qs.filter(date__gte=date_start)
        if date_end is not None:
            hist_qs = hist_qs.filter(date__lte=date_end)
        if trigger:
            hist_qs = hist_qs.filter(trigger=trigger)
        for hist in hist_qs:
            history_by_est[hist.estimation_id].append(hist)

    snaps = {
        s.estimation_id: s
        for s in InteractivePricingSnapshot.objects.filter(estimation_id__in=est_ids)
    } if est_ids else {}

    compare_data = []
    changed_count = 0
    cars_with_pair = 0

    for agg in page_rows:
        est_id = agg['estimation_id']
        hist_list = history_by_est.get(est_id) or []
        if not hist_list:
            continue
        first = hist_list[0]
        last = hist_list[-1]
        has_pair = len(hist_list) >= 2 and first.pk != last.pk
        first_vals = _history_values(first)
        last_vals = _history_values(last)

        delta_price = (last_vals['estimation_price'] - first_vals['estimation_price']) if has_pair else None

        if has_pair:
            cars_with_pair += 1
            if delta_price:
                changed_count += 1

        snap = snaps.get(est_id)
        extra = getattr(snap, 'extra_payload', None) or {} if snap else {}
        compare_data.append({
            'estimation_id': est_id,
            'rlk_id': getattr(snap, 'rlk_id', None),
            'start_estimation': getattr(snap, 'start_estimation', None) or first_vals['date'],
            'unit_name': getattr(snap, 'unit_name', None) or '—',
            'unit_source': getattr(snap, 'unit_source', None) or '—',
            'status_name': getattr(snap, 'status_name', None) or '—',
            'model': getattr(snap, 'model_name', None) or '—',
            'vin': getattr(snap, 'vin', None) or '',
            'staff_name': getattr(snap, 'staff_name', None) or '—',
            'analyst_before_name': getattr(snap, 'analyst_before_name', None) or '—',
            'analyst_after_name': getattr(snap, 'analyst_after_name', None) or '—',
            'price_reception': getattr(snap, 'price_reception', None) or 0,
            'price_auto_auction': bool(extra.get('price_auto_auction')),
            'recalc_count': agg['recalc_count'],
            'has_pair': has_pair,
            'first_date': first_vals['date'],
            'last_date': last_vals['date'],
            'first': first_vals,
            'last': last_vals,
            'delta_estimation_price': delta_price,
            'delta_zna': (last_vals['zna'] - first_vals['zna']) if has_pair else None,
            'delta_price_auto_2': (last_vals['price_auto_2'] - first_vals['price_auto_2']) if has_pair else None,
            'delta_price_before_kd': (last_vals['price_before_kd'] - first_vals['price_before_kd']) if has_pair else None,
            'delta_price_after_kd': (last_vals['price_after_kd'] - first_vals['price_after_kd']) if has_pair else None,
            'delta_amount_recovery': (last_vals['amount_recovery'] - first_vals['amount_recovery']) if has_pair else None,
            'delta_cna_expenses': (last_vals['cna_expenses'] - first_vals['cna_expenses']) if has_pair else None,
            'kf_changed': has_pair and (first_vals['kf'] or '') != (last_vals['kf'] or ''),
        })

    return {
        'compare_data': compare_data,
        'page_obj': page_obj,
        'paginator': paginator,
        'total_count': paginator.count,
        'total_recalcs': total_recalcs,
        'changed_count': changed_count,
        'cars_with_pair': cars_with_pair,
    }
