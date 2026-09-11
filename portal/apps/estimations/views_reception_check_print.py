# -*- coding: utf-8 -*-
"""Печать «Лист проверки автомобиля» (бланк приёма) — по макету test.pdf."""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render

# Секции бланка: (заголовок, [(№, текст), ...], show_nrd)
# show_nrd — колонки Норма / Ремонт / Диагностика
APPRAISER_ITEMS = [
    ('1', 'Сервисная книжка с информацией обо всех пройденных ТО'),
    ('2', 'Ключи зажигания (комплект), проверка работоспособности ДУ и мех. частей (все ключи и замки)'),
    ('3', 'Инструкция пользователя'),
    ('4', 'Запасное колесо/докатка. Минимально допустимая остаточная высота протектора 3 мм'),
    ('5', 'Штатные инструменты (домкрат, баллонный ключ), наличие ключа от «секретных» болтов'),
    ('6', 'Аварийный треугольник, аптечка, огнетушитель'),
    ('7', 'Наличие пультов ДУ, наушников, навигационных DVD (если применимо)'),
    ('8', 'Наличие меток и пультов от дополнительно установленных противоугонных систем'),
]

TEST_DRIVE_ITEMS = [
    ('9.1', 'Разгонная динамика, посторонние шумы, вибрации при движении'),
    ('9.2', 'Плавность включения передач (МКПП/АКПП, проверка CVT во всех режимах), все передачи'),
    ('9.3', 'Увод от прямолинейного движения'),
    ('9.4', 'Работа измерительных приборов и указателей (исправность, корректность показаний)'),
]

SERVICE_UNDERHOOD = [
    ('9', 'Шланги и патрубки тормозной системы — визуальная проверка (трещины, подтекания), уровень жидкости'),
    ('10', 'Шланги и патрубки топливной системы — визуальная проверка (трещины, подтекания)'),
    ('11', 'Шланги и патрубки системы охлаждения — визуальная проверка (трещины, подтекания), уровень жидкости'),
    ('12', 'Система ГУР/АВС — визуальная проверка (подтекания), уровень жидкости'),
    ('13', 'Проверка и, при необходимости, восстановление уровня остальных эксплуатационных жидкостей'),
    ('14', 'Работа замков, петель, упоров капота'),
    ('15', 'Чистота моторного отсека'),
]

SERVICE_LIFT = [
    ('16', 'Двигатель, осмотр картера на предмет отсутствия деформаций и следов течи рабочих жидкостей *'),
    ('17', 'Осмотр КПП на предмет отсутствия деформаций, трещин, следов течи масла *'),
    ('18', 'Состояние и износ шкивов КВ и навесного оборудования, приводных ремней'),
    ('19', 'Состояние и износ тормозных дисков и колодок (мин. износ по техрегламенту + 2 мм)'),
    ('20', 'Степень и равномерность износа покрышек, повреждения, мин. высота протектора — 3 мм'),
    ('21', 'Оценка состояния и работоспособности исполнительных механизмов стояночного тормоза'),
    ('22', 'Осмотр тормозных магистралей на предмет коррозии, деформаций и следов течи'),
    ('23', 'Состояние системы выпуска ОГ, катализаторов, защитных экранов'),
    ('24', 'Состояние деталей подвески передней'),
    ('25', 'Состояние деталей подвески задней'),
    ('26', 'Состояние амортизаторов, пыльников и защитных чехлов'),
    ('27', 'Состояние подшипников, муфт, соединений рулевого управления, прямое положение руля'),
    ('28', 'Состояние рулевой рейки, наличие люфтов, посторонних стуков, следов течи масла'),
    ('29', 'Оценка состояния опор ДВС и трансмиссии'),
    ('30', 'Оценка состояния подшипников колес'),
    ('31', 'Оценка состояния полного привода (при наличии)'),
]

SERVICE_EQUIPMENT = [
    ('32', 'Проверка работоспособности электрических стеклоподъемников (передних и задних, режим auto)'),
    ('33', 'Проверка работы механизма люка (посторонние звуки, подклинивание, неполное открытие/закрытие)'),
    ('34', 'Проверка работы ремней безопасности, «детских замков», регулировки рулевой колонки'),
    ('35', 'Проверка работоспособности механизмов регулировки кресел, включая функцию памяти'),
    ('36', 'Проверка работы систем подогрева, вентиляции кресел, функции массажа и пневморегулировок'),
    ('37', 'Оценка работоспособности механизмов складывания сидений'),
    ('38', 'Проверка работы бортового компьютера, корректность выставленного времени'),
    ('39', 'Проверка работоспособности внешнего головного и заднего освещения'),
    ('40', 'Проверка работы стеклоомывателей и стеклоочистителей, включая задний (где применимо)'),
    ('41', 'Работа мультимедийной системы, CD/DVD, наушников и пультов, камеры заднего вида'),
    ('42', 'Работа штатного холодильника (где применимо)'),
    ('43', 'Работа системы Keyless-Go (где применимо)'),
    ('44', 'Работа вспомогательных систем (доводчики дверей, крышки багажника, круиз-контроль)'),
    ('45', 'Оценка работоспособности механизмов регулировки, складывания и подогрева зеркал'),
    ('46', 'Проверка работы внутреннего освещения (плафоны, козырьки, перчаточный ящик и т.д.)'),
    ('47', 'Проверка эффективности работы кондиционера, регулировки воздушных потоков'),
    ('48', 'Работа парковочного радара, включая функцию парковочного ассистента (если применимо)'),
    ('49', 'Проверка работоспособности предпускового отопителя (Webasto) (если применимо)'),
    ('50', 'Проверка регулировки света фар (если применимо)'),
]

SERVICE_DIAG = [
    ('51', 'Работа ДВС, КПП и катализаторов ОГ'),
    ('52', 'Работа ABS и ESP'),
    ('53', 'Работа SRS (AirBag)'),
    ('54', 'Работа системы климат-контроля'),
    ('55', 'Количество зарегистрированных ключей'),
    ('56', 'Проверка работоспособности контрольных ламп на панели приборов'),
    ('57', 'Легкость запуска двигателя'),
    ('58', 'Работа двигателя на холостом ходу'),
    ('59', 'Работа сцепления, шумы, вибрации (если применимо)'),
    ('60', 'Индикатор Check Engine'),
]


def _txt(*parts) -> str:
    return ' '.join(str(p).strip() for p in parts if p not in (None, '')).strip()


def _staff_name(obj) -> str:
    if obj is None:
        return ''
    name = getattr(obj, 'name', None)
    if name:
        return str(name).strip()
    return str(obj).strip()


def build_reception_check_sheet(*, estimation=None, rlk=None, page_reception=None, back_url=''):
    """Данные для печати листа проверки автомобиля."""
    if rlk is None and estimation is not None:
        rlk = estimation.rlk

    lo = None
    if rlk is not None:
        from documents.models import DocLO
        lo = (
            DocLO.objects
            .filter(rlk=rlk)
            .select_related('organization', 'staff')
            .order_by('-active', '-dataTime', '-id')
            .first()
        )

    if page_reception is None and rlk is not None:
        try:
            link = RegInteractivOcenkaRLK_from_rlk(rlk)
            if link is not None:
                page_reception = getattr(link, 'page_reception', None)
        except Exception:
            page_reception = None

    page_docs = None
    page_salon = None
    page_test = None
    if estimation is not None:
        page_docs = estimation.page_documents if estimation.page_documents_id else None
        page_salon = estimation.page_salon if estimation.page_salon_id else None
        page_test = estimation.page_test_drive if estimation.page_test_drive_id else None

    # --- header fields ---
    lo_nomer = ''
    if lo and lo.nomer:
        lo_nomer = lo.nomer
    else:
        try:
            from avtosalon.car_card_context import _sklad_nomer
            lo_nomer = _sklad_nomer(lo=lo, rlk=rlk) or ''
        except Exception:
            if rlk and rlk.nomer:
                lo_nomer = rlk.nomer

    inspect_date = None
    if page_reception and getattr(page_reception, 'actual_reception_at', None):
        inspect_date = page_reception.actual_reception_at
    elif page_reception and getattr(page_reception, 'created_at', None):
        inspect_date = page_reception.created_at
    elif lo and lo.dataTime:
        inspect_date = lo.dataTime
    elif estimation and estimation.end_estimation:
        inspect_date = estimation.end_estimation

    mark_model = ''
    if page_reception and (page_reception.mark or page_reception.model):
        mark_model = _txt(page_reception.mark, page_reception.model)
    elif estimation is not None:
        try:
            from estimations.views_kolesa_reception import _estimation_car_label
            mark_model = _estimation_car_label(estimation)
        except Exception:
            mark_model = ''

    color = ''
    if page_reception and (getattr(page_reception, 'body_color', None) or ''):
        color = (page_reception.body_color or '').strip()
    if not color and page_reception and (getattr(page_reception, 'salon_color', None) or ''):
        color = (page_reception.salon_color or '').strip()
    if not color and page_docs and (page_docs.pts_color or '').strip():
        color = page_docs.pts_color.strip()
    if not color and estimation and getattr(estimation, 'color', None):
        color = (estimation.color or '').strip()

    year = ''
    if estimation and estimation.year:
        year = str(estimation.year)
    elif page_reception and page_reception.year:
        year = str(page_reception.year)

    vin = ''
    if estimation:
        vin = (estimation.vin or estimation.number_body or '').strip()
    if not vin and page_reception:
        vin = (getattr(page_reception, 'vin', None) or '').strip()

    engine_number = ''
    if page_reception and (page_reception.engine_number or '').strip():
        engine_number = page_reception.engine_number.strip()
    elif page_docs and (page_docs.engine_number or '').strip():
        engine_number = page_docs.engine_number.strip()

    engine_label = ''
    body_label = ''
    gear_label = ''
    if estimation and estimation.modification_autoru_id and estimation.modification_autoru:
        mod = estimation.modification_autoru
        if getattr(mod, 'typeEngine', None):
            engine_label = mod.typeEngine.name or ''
        if getattr(mod, 'typeBody', None):
            body_label = mod.typeBody.name or ''
        if getattr(mod, 'typeGear', None):
            gear_label = mod.typeGear.name or ''
        # модель ДВС из имени модификации, если есть
        if not engine_number and (mod.name or ''):
            pass

    mileage = ''
    mileage_val = None
    if page_reception and page_reception.mileage:
        mileage_val = page_reception.mileage
    elif page_salon and page_salon.run:
        mileage_val = page_salon.run
    elif lo and lo.run:
        mileage_val = lo.run
    if mileage_val:
        try:
            mileage = '{:,}'.format(int(mileage_val)).replace(',', ' ')
        except (TypeError, ValueError):
            mileage = str(mileage_val)

    count_owners = None
    if page_reception and page_reception.count_owners:
        count_owners = page_reception.count_owners
    elif page_docs and page_docs.count_owners:
        count_owners = page_docs.count_owners

    pts_series = ''
    pts_number = ''
    pts_original = None
    if page_reception:
        pts_series = (page_reception.pts_series or '').strip()
        pts_number = (page_reception.pts_number or '').strip()
        if page_reception.pts_original:
            pts_original = True
        elif page_reception.pts_electronic:
            pts_original = False
    if not pts_number and page_docs:
        pts_number = (page_docs.pts_number or '').strip()
        if pts_original is None and page_docs.pts_original:
            pts_original = True

    pts_full = _txt(pts_series, pts_number)

    appraiser = ''
    if page_reception and page_reception.staff_id and page_reception.staff:
        appraiser = _staff_name(page_reception.staff)
    elif estimation and estimation.staff_id and estimation.staff:
        appraiser = _staff_name(estimation.staff)
    elif lo and lo.staff_id and lo.staff:
        appraiser = _staff_name(lo.staff)

    test_drive_done = None
    test_drive_comment = ''
    if page_test is not None:
        if page_test.no_test:
            test_drive_done = False
        else:
            test_drive_done = True
            test_drive_comment = (page_test.comment or '').strip()

    return {
        'title': 'Лист проверки автомобиля',
        'back_url': back_url,
        'rlk': rlk,
        'estimation': estimation,
        'lo_nomer': lo_nomer,
        'inspect_date': inspect_date,
        'mark_model': mark_model or '—',
        'color': color,
        'engine_label': engine_label,
        'gear_label': gear_label,
        'year': year,
        'body_label': body_label,
        'vin': vin,
        'engine_number': engine_number,
        'mileage': mileage,
        'count_owners': count_owners,
        'pts_full': pts_full,
        'pts_original': pts_original,
        'appraiser': appraiser,
        'test_drive_done': test_drive_done,
        'test_drive_comment': test_drive_comment,
        'appraiser_items': APPRAISER_ITEMS,
        'test_drive_items': TEST_DRIVE_ITEMS,
        'service_underhood': SERVICE_UNDERHOOD,
        'service_lift': SERVICE_LIFT,
        'service_equipment': SERVICE_EQUIPMENT,
        'service_diag': SERVICE_DIAG,
    }


def RegInteractivOcenkaRLK_from_rlk(rlk):
    from register.models import RegInteractivOcenkaRLK
    try:
        return (
            RegInteractivOcenkaRLK.objects
            .select_related('page_reception', 'page_reception__staff', 'estimation')
            .get(rlk=rlk)
        )
    except RegInteractivOcenkaRLK.DoesNotExist:
        return None


@login_required
def estimation_reception_check_sheet_print(request, rlk_id):
    """Печать листа проверки автомобиля со вкладки приёма."""
    from documents.models import DocRLK
    from register.models import RegInteractivOcenka, RegInteractivOcenkaRLK

    rlk = get_object_or_404(DocRLK.objects.select_related('unit'), pk=rlk_id)

    estimation = None
    page_reception = None
    try:
        link = RegInteractivOcenkaRLK.objects.select_related(
            'estimation',
            'estimation__modification_autoru',
            'estimation__modification_autoru__typeEngine',
            'estimation__modification_autoru__typeBody',
            'estimation__modification_autoru__typeGear',
            'estimation__modification_autoru__model',
            'estimation__modification_autoru__model__mark',
            'estimation__staff',
            'estimation__page_documents',
            'estimation__page_salon',
            'estimation__page_test_drive',
            'page_reception',
            'page_reception__staff',
        ).get(rlk=rlk)
        estimation = link.estimation
        page_reception = getattr(link, 'page_reception', None)
    except RegInteractivOcenkaRLK.DoesNotExist:
        try:
            estimation = (
                RegInteractivOcenka.objects
                .select_related(
                    'modification_autoru',
                    'modification_autoru__typeEngine',
                    'modification_autoru__typeBody',
                    'modification_autoru__typeGear',
                    'modification_autoru__model',
                    'modification_autoru__model__mark',
                    'staff',
                    'page_documents',
                    'page_salon',
                    'page_test_drive',
                )
                .get(rlk=rlk)
            )
        except RegInteractivOcenka.DoesNotExist:
            raise Http404('Интерактивная оценка для рабочего листа не найдена')

    sheet = build_reception_check_sheet(
        estimation=estimation,
        rlk=rlk,
        page_reception=page_reception,
        back_url='/eco/{}/?page=24'.format(rlk.pk),
    )
    return render(request, 'estimations/reception_check_sheet_print.html', {'params': sheet})
