"""Отчёт по согласованию коммерческих предложений (только для УК)."""
from datetime import date
from calendar import monthrange
from urllib.parse import urlencode

from django.db.models import OuterRef, Subquery, Q, Sum
from django.urls import reverse
from django.utils import timezone

from avtosalon.deal_calc_approval import (
    AUTO_APPROVE_COMMENT,
    AUTO_APPROVE_USER_ID,
    LEGACY_AUTO_APPROVE_COMMENT,
    LEGACY_AUTO_APPROVE_COMMENT_RULE_MIN,
    user_has_deal_calc_uk_access,
)
from documents.models import DocCarShipment
from prices_car.calculations_table import get_soglasovanie_status_display
from prices_car.models import CarCalculations


def _auto_approved_q():
    """Условие ORM для автоматического согласования КП."""
    return Q(
        soglasovanie_status=CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED,
    ) & (
        Q(director_approve_user_id=AUTO_APPROVE_USER_ID)
        | Q(director_approve_comment__in=[
            AUTO_APPROVE_COMMENT,
            LEGACY_AUTO_APPROVE_COMMENT,
            LEGACY_AUTO_APPROVE_COMMENT_RULE_MIN,
        ])
        | Q(director_approve_comment__startswith='Автоматическое согласование')
    )


def is_auto_approved_calc(calc) -> bool:
    """Проверка объекта КП на признак автоматического согласования."""
    if getattr(calc, 'soglasovanie_status', None) != CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED:
        return False
    if getattr(calc, 'director_approve_user_id', None) == AUTO_APPROVE_USER_ID:
        return True
    comment = (getattr(calc, 'director_approve_comment', '') or '').strip()
    if comment in (
        AUTO_APPROVE_COMMENT,
        LEGACY_AUTO_APPROVE_COMMENT,
        LEGACY_AUTO_APPROVE_COMMENT_RULE_MIN,
    ) or comment.startswith('Автоматическое согласование'):
        return True
    return False


def _current_month_bounds():
    today = timezone.now().date()
    return today.replace(day=1), today.replace(day=monthrange(today.year, today.month)[1])


def _parse_date(raw):
    raw = (raw or '').strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _parse_int_id_list(values):
    ids = []
    for raw in values or []:
        try:
            val = int(raw)
        except (TypeError, ValueError):
            continue
        if val and val not in ids:
            ids.append(val)
    return ids


def approval_report_units_qs():
    """Подразделения с включённой автопереоценкой новых."""
    from refs.models import RefUnit

    return (
        RefUnit.objects
        .filter(
            auto_reprice_new=True,
            buauto=False,
            ib__active=True,
        )
        .select_related('city')
        .order_by('name')
    )


def _car_mark(car):
    if not car:
        return ''
    if car.mark:
        return car.mark
    mod = getattr(car, 'modification_autoru', None)
    model = getattr(mod, 'model', None) if mod else None
    mark = getattr(model, 'mark', None) if model else None
    return getattr(mark, 'name', '') or ''


def _car_model(car):
    if not car:
        return ''
    if car.model:
        return car.model
    mod = getattr(car, 'modification_autoru', None)
    model = getattr(mod, 'model', None) if mod else None
    return getattr(model, 'name', '') or ''


def _car_complectation(car):
    if not car:
        return ''
    comp = getattr(car, 'complectation_autoru', None)
    if comp and getattr(comp, 'name', None):
        return comp.name
    return ''


def _user_display_name(user) -> str:
    if not user:
        return ''
    profile = getattr(user, 'profiles', None)
    if profile and getattr(profile, 'eco_name', None):
        name = (profile.eco_name or '').strip()
        if name:
            return name
    full = (user.get_full_name() or '').strip()
    if full:
        return full
    return (user.username or '').strip() or str(user.pk)


def build_approval_report_queryset(request):
    """
    Последнее КП по рабочему листу (active=True).
    Только подразделения с auto_reprice_new=True.
    """
    date_start = _parse_date(request.GET.get('date_start'))
    date_end = _parse_date(request.GET.get('date_end'))
    if date_start is None and date_end is None:
        date_start, date_end = _current_month_bounds()

    vin = (request.GET.get('vin') or '').strip()
    unit_ids = _parse_int_id_list(
        request.GET.getlist('unit[]')
        + request.GET.getlist('unit_ids')
        + request.GET.getlist('unit_id')
        + request.GET.getlist('unit')
    )
    only_shipped = (request.GET.get('only_shipped') or '').strip() in ('1', 'true', 'yes', 'on')
    soglasovanie = (request.GET.get('soglasovanie') or '').strip()
    type_sale = (request.GET.get('type_sale') or '').strip()

    allowed_unit_ids = list(approval_report_units_qs().values_list('pk', flat=True))
    if unit_ids:
        allowed_set = set(allowed_unit_ids)
        unit_ids = [uid for uid in unit_ids if uid in allowed_set]

    shipment_qs = (
        DocCarShipment.objects
        .filter(rlk_id=OuterRef('rlk_id'), active=True)
        .order_by('-dataTime')
    )

    sale_kvp_sq = None
    try:
        from powerbi.models import CumulativeMarginUS

        sale_kvp_sq = (
            CumulativeMarginUS.objects
            .filter(VIN=OuterRef('car__vin'))
            .exclude(VIN='')
            .exclude(VIN__isnull=True)
            .order_by('-DataProdazhi', '-pk')
        )
    except Exception:
        sale_kvp_sq = None

    qs = (
        CarCalculations.objects
        .filter(active=True, rlk_id__isnull=False)
        .filter(unit_id__in=allowed_unit_ids or [-1])
        .select_related(
            'unit',
            'unit__city',
            'car',
            'car__type_sale',
            'car__modification_autoru',
            'car__modification_autoru__model',
            'car__modification_autoru__model__mark',
            'car__complectation_autoru',
            'rlk',
            'director_approve_user',
            'director_approve_user__profiles',
            'uk_approve_user',
            'uk_approve_user__profiles',
        )
        .annotate(
            shipment_pk=Subquery(shipment_qs.values('pk')[:1]),
            shipment_nomer=Subquery(shipment_qs.values('nomer')[:1]),
            shipment_type_sale=Subquery(shipment_qs.values('typeSale')[:1]),
            shipment_cumulative_margin=Subquery(shipment_qs.values('cumulative_margin')[:1]),
        )
    )
    if sale_kvp_sq is not None:
        qs = qs.annotate(sale_kvp=Subquery(sale_kvp_sq.values('KVP')[:1]))

    if date_start:
        qs = qs.filter(date__date__gte=date_start)
    if date_end:
        qs = qs.filter(date__date__lte=date_end)
    if vin:
        qs = qs.filter(car__vin__icontains=vin)
    if unit_ids:
        qs = qs.filter(unit_id__in=unit_ids)
    if only_shipped:
        qs = qs.filter(shipment_pk__isnull=False)
    if type_sale:
        if type_sale.isdigit():
            qs = qs.filter(car__type_sale_id=int(type_sale))
        else:
            qs = qs.filter(
                Q(car__type_sale__name__icontains=type_sale)
                | Q(shipment_type_sale__icontains=type_sale)
            )
    if soglasovanie:
        if soglasovanie == 'auto_approved':
            qs = qs.filter(_auto_approved_q())
        elif soglasovanie in ('director_approved', 'manual_director_approved'):
            qs = qs.filter(
                soglasovanie_status=CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED
            ).exclude(_auto_approved_q())
        elif soglasovanie == 'uk_approved':
            qs = qs.filter(soglasovanie_status=CarCalculations.SOGLASOVANIE_UK_APPROVED)
        elif soglasovanie == 'approved':
            qs = qs.filter(soglasovanie_status__in=[
                CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED,
                CarCalculations.SOGLASOVANIE_UK_APPROVED,
            ])
        elif soglasovanie == 'pending':
            qs = qs.filter(
                Q(soglasovanie_status__in=[
                    CarCalculations.SOGLASOVANIE_PENDING,
                    CarCalculations.SOGLASOVANIE_PENDING_UK,
                    CarCalculations.SOGLASOVANIE_AWAITING_1C,
                    '',
                ])
                | Q(soglasovanie_status__isnull=True)
            )
        elif soglasovanie == 'pending_uk':
            qs = qs.filter(soglasovanie_status=CarCalculations.SOGLASOVANIE_PENDING_UK)
        elif soglasovanie == 'rejected':
            qs = qs.filter(soglasovanie_status__in=[
                CarCalculations.SOGLASOVANIE_DIRECTOR_REJECTED,
                CarCalculations.SOGLASOVANIE_UK_REJECTED,
            ])
        else:
            qs = qs.filter(soglasovanie_status=soglasovanie)

    filtr = {
        'date_start': date_start.isoformat() if date_start else '',
        'date_end': date_end.isoformat() if date_end else '',
        'vin': vin,
        'filter_unit': unit_ids,
        'only_shipped': only_shipped,
        'soglasovanie': soglasovanie,
        'type_sale': type_sale,
    }
    from asp.report_table import resolve_order_by
    order_ui, orm_order = resolve_order_by('deal_calc_approval', request.GET.get('order_by'))
    filtr['order_by'] = order_ui
    return qs.order_by(*orm_order), filtr


def build_approval_report_querystring(filtr, *, page=None):
    params = []
    if filtr.get('date_start'):
        params.append(('date_start', filtr['date_start']))
    if filtr.get('date_end'):
        params.append(('date_end', filtr['date_end']))
    if filtr.get('vin'):
        params.append(('vin', filtr['vin']))
    for unit_id in filtr.get('filter_unit') or []:
        params.append(('unit_ids', str(unit_id)))
    if filtr.get('soglasovanie'):
        params.append(('soglasovanie', filtr['soglasovanie']))
    if filtr.get('only_shipped'):
        params.append(('only_shipped', '1'))
    if filtr.get('type_sale'):
        params.append(('type_sale', str(filtr['type_sale'])))
    if filtr.get('order_by'):
        params.append(('order_by', filtr['order_by']))
    if page:
        params.append(('page', str(page)))
    return urlencode(params)


class BrandKMResolver:
    """Быстрый резолвер BrandKM в памяти без N+1 запросов к БД."""

    def __init__(self):
        self._load_data()

    def _load_data(self):
        from prices_car.models import BrandKM, PriceCarBrand

        try:
            brands = list(
                PriceCarBrand.objects.prefetch_related('marks', 'models_included').all()
            )
        except Exception:
            brands = []

        self._brands_data = []
        for b in brands:
            self._brands_data.append({
                'pk': b.pk,
                'mark_ids': {m.pk for m in b.marks.all()},
                'model_ids': {m.pk for m in b.models_included.all()},
            })

        self._km_exact = {}
        self._brand_history = {}

        try:
            km_rows = list(
                BrandKM.objects
                .order_by('month')
                .values('brand_id', 'month', 'km', 'km_min_dc')
            )
        except Exception:
            km_rows = []

        for r in km_rows:
            bid = r['brand_id']
            m = r['month']
            self._km_exact[(bid, m)] = r
            if bid not in self._brand_history:
                self._brand_history[bid] = []
            self._brand_history[bid].append((m, r))

    def resolve_brand_id(self, car):
        if not car:
            return None
        mod = getattr(car, 'modification_autoru', None)
        if not mod:
            return None
        model = getattr(mod, 'model', None)
        if not model:
            return None
        mark_id = getattr(model, 'mark_id', None)
        model_id = getattr(model, 'pk', None)
        if not mark_id:
            return None

        explicit_match = None
        generic_match = None
        for b in self._brands_data:
            if mark_id in b['mark_ids']:
                if b['model_ids']:
                    if model_id in b['model_ids']:
                        explicit_match = b['pk']
                else:
                    generic_match = b['pk']

        return explicit_match or generic_match

    def get_brand_km_for_calc(self, calc):
        if not calc or not calc.car:
            return None
        brand_id = self.resolve_brand_id(calc.car)
        if not brand_id:
            return None

        calc_date = getattr(calc, 'date', None)
        if calc_date:
            target_month = date(calc_date.year, calc_date.month, 1)
        else:
            target_month = timezone.now().date().replace(day=1)

        # 1. Exact match
        exact = self._km_exact.get((brand_id, target_month))
        if exact:
            return exact

        # 2. Latest month <= target_month
        history = self._brand_history.get(brand_id) or []
        past = [r for m, r in history if m <= target_month]
        if past:
            return past[-1]

        # 3. Any latest available
        if history:
            return history[-1][1]

        return None


def is_yellow_car_at_date(car, calc_date=None):
    """
    Признак «жёлтого» автомобиля на момент КП:
    заполнена дата рапорта (date_report) и установлена не позже даты КП.
    """
    if not car:
        return False, ''
    dt_report = getattr(car, 'date_report', None)
    if not dt_report or getattr(dt_report, 'year', 0) <= 2000:
        return False, ''

    date_report_str = dt_report.strftime('%d.%m.%Y') if hasattr(dt_report, 'strftime') else str(dt_report)

    if calc_date:
        try:
            r_date = dt_report.date() if hasattr(dt_report, 'date') else dt_report
            c_date = calc_date.date() if hasattr(calc_date, 'date') else calc_date
            if r_date <= c_date:
                return True, date_report_str
            return False, date_report_str
        except Exception:
            return True, date_report_str

    return True, date_report_str


def serialize_approval_report_row(calc, brand_resolver=None, details_map=None):
    car = calc.car
    unit = calc.unit
    city = getattr(unit, 'city', None) if unit else None
    shipped = bool(getattr(calc, 'shipment_pk', None))
    shipment_cm = getattr(calc, 'shipment_cumulative_margin', None)
    sale_kvp = getattr(calc, 'sale_kvp', None)
    if shipped and shipment_cm is not None:
        sale_profit = shipment_cm
    elif sale_kvp is not None:
        sale_profit = sale_kvp
    elif shipped:
        sale_profit = calc.kvp
    else:
        sale_profit = None

    diff_kp = None
    if calc.kvp is not None and sale_profit is not None:
        try:
            diff_kp = round(float(calc.kvp) - float(sale_profit), 2)
        except (ValueError, TypeError):
            diff_kp = None

    diff_formula = None
    if calc.km_raschet is not None and sale_profit is not None:
        try:
            diff_formula = round(float(calc.km_raschet) - float(sale_profit), 2)
        except (ValueError, TypeError):
            diff_formula = None

    is_auto = is_auto_approved_calc(calc)
    if is_auto:
        soglasovanie_label = 'Согласовано автоматически'
        director_approver = 'Автоматически'
    else:
        soglasovanie_label = get_soglasovanie_status_display(calc)
        director_approver = _user_display_name(calc.director_approve_user) or '—'

    brand_km_data = brand_resolver.get_brand_km_for_calc(calc) if brand_resolver else None
    brand_km_month = brand_km_data.get('km') if brand_km_data else None
    brand_km_min_dc = brand_km_data.get('km_min_dc') if brand_km_data else None
    is_yellow, date_report_str = is_yellow_car_at_date(car, calc.date)

    type_sale_name = getattr(calc, 'shipment_type_sale', None) or (calc.car.type_sale.name if calc.car and getattr(calc.car, 'type_sale', None) else '') or '—'

    row = {
        'pk': calc.pk,
        'id': calc.pk,
        'url': reverse('avtosalon:deal_calculation_doc', kwargs={'id': calc.pk}),
        'unit_name': unit.name if unit else '—',
        'city_name': city.name if city else '—',
        'unit_label': (
            '{} ({})'.format(unit.name, city.name)
            if unit and city
            else (unit.name if unit else '—')
        ),
        'mark': _car_mark(car) or '—',
        'model': _car_model(car) or '—',
        'complectation': _car_complectation(car) or '—',
        'year': car.year if car and car.year else '—',
        'vin': car.vin if car and car.vin else '—',
        'type_sale': type_sale_name,
        'is_yellow': is_yellow,
        'date_report_str': date_report_str,
        'brand_km_month': brand_km_month,
        'brand_km_min_dc': brand_km_min_dc,
        'rlk_nomer': calc.rlk.nomer if calc.rlk else '—',
        'number': calc.number or '—',
        'date': calc.date,
        'date_str': calc.date.strftime('%d.%m.%Y %H:%M') if calc.date else '',
        'kvp': calc.kvp,
        'km_raschet': calc.km_raschet,
        'km_formula': calc.km_raschet,
        'is_auto_approved': is_auto,
        'soglasovanie_status': calc.soglasovanie_status or '',
        'soglasovanie_label': soglasovanie_label,
        'director_approver': director_approver,
        'uk_approver': _user_display_name(calc.uk_approve_user) or '—',
        'shipped': shipped,
        'shipment_nomer': getattr(calc, 'shipment_nomer', None) or '',
        'sale_profit': sale_profit,
        'diff_kp': diff_kp,
        'diff_formula': diff_formula,
        # Поля коммерческого предложения
        'calc_discount': calc.discount,
        'calc_custom_opfu': calc.custom_opfu,
        'calc_custom_tradein': calc.custom_tradein,
        'calc_custom_wheels': calc.custom_wheels,
        'calc_custom_grz': calc.custom_grz,
        'calc_custom_work': calc.custom_work,
        'calc_custom_product': calc.custom_product,
    }

    # Детали коммерческого предложения (CarCalculationsDetail)
    calc_details = None
    if details_map is not None:
        calc_details = details_map.get(calc.pk)
    if calc_details:
        for d in calc_details:
            dt_id = getattr(d, 'detail_type_id', None)
            if dt_id:
                row[f'detail_{dt_id}'] = {
                    'vp': d.vp,
                    'amount': d.amount,
                    'success': d.success,
                    'pocazatel': d.pocazatel,
                    'amount_k': d.amount_k,
                }
    return row


def build_approval_report_excel(rows, visible_columns=None):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = 'Согласование КП'

    header_fill = PatternFill(start_color='002A5A', end_color='002A5A', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')

    if visible_columns:
        headers = [c['label_export'] for c in visible_columns]
        ws.append(headers)
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        from asp.report_table import cell_export_value
        for row in rows:
            row_vals = []
            for col in visible_columns:
                val = cell_export_value('deal_calc_approval', row, col['key'])
                row_vals.append(val if val is not None else '')
            ws.append(row_vals)
    else:
        headers = [
            'Подразделение',
            'Город',
            'Марка',
            'Модель',
            'Комплектация',
            'Год',
            'VIN',
            'Тип продажи',
            'Жёлтый АМ',
            'КМ на месяц',
            'КП',
            'Формула',
            'Статус согласования',
            'Автосогласование',
            'Согласовал директор',
            'Согласовал УК',
            'Доходность уехала',
            'Разница с КП',
            'Разница с формулой',
            'Номер РЛ',
            'Номер КП',
            'Номер отгрузки',
            'Дата КП',
            'Ссылка КП',
        ]
        ws.append(headers)
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        for row in rows:
            ws.append([
                row['unit_name'],
                row['city_name'],
                row['mark'],
                row['model'],
                row['complectation'],
                row['year'],
                row['vin'],
                row.get('type_sale', '—'),
                'Да' if row.get('is_yellow') else 'Нет',
                row.get('brand_km_month') if row.get('brand_km_month') is not None else '',
                row['kvp'] if row['kvp'] is not None else '',
                row['km_formula'] if row['km_formula'] is not None else '',
                row['soglasovanie_label'],
                'Да' if row.get('is_auto_approved') else 'Нет',
                row['director_approver'] if row['director_approver'] != '—' else '',
                row['uk_approver'] if row['uk_approver'] != '—' else '',
                row['sale_profit'] if row['sale_profit'] is not None else '',
                row.get('diff_kp') if row.get('diff_kp') is not None else '',
                row.get('diff_formula') if row.get('diff_formula') is not None else '',
                row['rlk_nomer'],
                row['number'],
                row['shipment_nomer'] or '',
                row['date_str'],
                row['url'],
            ])

    for col in range(1, len(headers) + 1):
        letter = get_column_letter(col)
        max_length = 0
        for cell in ws[letter]:
            try:
                if cell.value is not None and len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception:
                pass
        ws.column_dimensions[letter].width = min(max_length + 2, 40)

    return wb


def compute_approval_report_metrics(qs):
    """Агрегированные KPI-показатели для карточек отчёта."""
    auto_q = _auto_approved_q()
    auto_count = qs.filter(auto_q).count()
    manual_approved = qs.filter(
        Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_UK_APPROVED)
        | (Q(soglasovanie_status=CarCalculations.SOGLASOVANIE_DIRECTOR_APPROVED) & ~auto_q)
    ).count()
    pending = qs.filter(
        Q(soglasovanie_status__in=[
            CarCalculations.SOGLASOVANIE_PENDING,
            CarCalculations.SOGLASOVANIE_PENDING_UK,
            CarCalculations.SOGLASOVANIE_AWAITING_1C,
            '',
        ]) | Q(soglasovanie_status__isnull=True)
    ).count()
    rejected = qs.filter(
        soglasovanie_status__in=[
            CarCalculations.SOGLASOVANIE_DIRECTOR_REJECTED,
            CarCalculations.SOGLASOVANIE_UK_REJECTED,
        ]
    ).count()
    shipped = qs.filter(shipment_pk__isnull=False).count()
    total_kvp = qs.aggregate(s=Sum('kvp'))['s'] or 0
    return {
        'auto_approved': auto_count,
        'manual_approved': manual_approved,
        'pending': pending,
        'rejected': rejected,
        'shipped': shipped,
        'total_kvp': total_kvp,
    }


def build_approval_report_context(request):
    from refs.models import RefTypeSaleCarsOrganization

    qs, filtr = build_approval_report_queryset(request)
    units = approval_report_units_qs()
    type_sales = RefTypeSaleCarsOrganization.objects.all().order_by('name')
    metrics = compute_approval_report_metrics(qs)
    return {
        'filtr': filtr,
        'units': units,
        'type_sales': type_sales,
        'metrics': metrics,
        'queryset': qs,
        'querystring': build_approval_report_querystring(filtr),
        'desktop_url': reverse('prices_car:new_cars_director_desktop'),
        'report_url': reverse('prices_car:deal_calc_approval_report'),
        'export_url': reverse('prices_car:deal_calc_approval_report_export'),
        'is_uk': user_has_deal_calc_uk_access(request.user),
    }
