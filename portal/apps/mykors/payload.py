"""Сборка payload машины для MyKors ingest."""
import hashlib
import json

from mykors import conf


INGEST_FIELDS = (
    'vin',
    'vin2',
    'name',
    'mark',
    'model',
    'modification',
    'year',
    'color',
    'is_new',
    'run',
    'price',
    'plate_number',
    'organization',
    'unit',
    'store',
    'modification_autoru',
    'complectation_autoru',
    'photos',
)


def _clean_str(value, max_len=None):
    if value is None:
        return ''
    text = str(value).strip()
    if max_len and len(text) > max_len:
        return text[:max_len]
    return text


def _clean_int(value):
    if value in (None, ''):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _fk_id(obj):
    if obj is None:
        return None
    pk = getattr(obj, 'pk', None)
    if pk:
        return int(pk)
    return None


def organization_to_ingest(org) -> dict:
    if org is None or not org.pk:
        return {}
    return {
        'id': int(org.pk),
        'name': _clean_str(org.name, 250),
        'full_name': _clean_str(getattr(org, 'full_name', ''), 250),
        'phone': _clean_str(getattr(org, 'phone', ''), 512),
        'email': _clean_str(getattr(org, 'email', ''), 200),
        'inn': _clean_str(getattr(org, 'inn', ''), 20),
        'kpp': _clean_str(getattr(org, 'kpp', ''), 20),
        'actual_adress': _clean_str(getattr(org, 'actual_adress', ''), 200),
        'adress': _clean_str(getattr(org, 'adress', ''), 200),
        'active_eco': bool(getattr(org, 'active_eco', False)),
    }


def unit_to_ingest(unit) -> dict:
    if unit is None or not unit.pk:
        return {}
    city = getattr(unit, 'city', None)
    uin = _clean_str(getattr(unit, 'uin', ''), 200) or f"unit_{unit.pk}"
    name = _clean_str(unit.name, 200) or f"Подразделение {unit.pk}"
    return {
        'id': int(unit.pk),
        'uin': uin,
        'name': name,
        'name_dop': _clean_str(getattr(unit, 'name_dop', ''), 200),
        'adress': _clean_str(getattr(unit, 'adress', ''), 512),
        'phone': _clean_str(getattr(unit, 'phone', ''), 512),
        'email': _clean_str(getattr(unit, 'email', ''), 512),
        'latitude': float(getattr(unit, 'latitude', 0) or 0),
        'longitude': float(getattr(unit, 'longitude', 0) or 0),
        'buauto': bool(getattr(unit, 'buauto', False)),
        'active_eco': bool(getattr(unit, 'active_eco', False)),
        'city': _fk_id(city),
        'city_name': _clean_str(city.name, 200) if city else '',
    }


def store_to_ingest(store) -> dict:
    if store is None or not store.pk:
        return {}
    city = getattr(store, 'city', None)
    unit = getattr(store, 'unit', None)
    uin = _clean_str(getattr(store, 'uin', ''), 200) or f"store_{store.pk}"
    name = _clean_str(store.name, 200) or f"Стоянка {store.pk}"
    return {
        'id': int(store.pk),
        'uin': uin,
        'name': name,
        'name_dop': _clean_str(getattr(store, 'name_dop', ''), 200),
        'adress': _clean_str(getattr(store, 'adress', ''), 512),
        'phone': _clean_str(getattr(store, 'phone', ''), 512),
        'email': _clean_str(getattr(store, 'email', ''), 512),
        'latitude': float(getattr(store, 'latitude', 0) or 0),
        'longitude': float(getattr(store, 'longitude', 0) or 0),
        'active_eco': bool(getattr(store, 'active_eco', False)),
        'unit': _fk_id(unit),
        'city': _fk_id(city),
        'city_name': _clean_str(city.name, 200) if city else '',
    }


def autoru_mark_to_ingest(mark) -> dict:
    if mark is None or not mark.pk:
        return {}
    return {
        'id': int(mark.pk),
        'name': _clean_str(mark.name, 200),
        'nameEn': _clean_str(getattr(mark, 'nameEn', ''), 200),
        'idSite': _clean_int(getattr(mark, 'idSite', 0)),
        'avtosalon': bool(getattr(mark, 'avtosalon', False)),
    }


def autoru_model_to_ingest(model) -> dict:
    if model is None or not model.pk:
        return {}
    mark = getattr(model, 'mark', None)
    data = {
        'id': int(model.pk),
        'name': _clean_str(model.name, 200),
        'nameEn': _clean_str(getattr(model, 'nameEn', ''), 200),
        'nameHuman': _clean_str(getattr(model, 'nameHuman', ''), 200),
        'idSite': _clean_int(getattr(model, 'idSite', 0)),
        'idSiteGeneration': _clean_int(getattr(model, 'idSiteGeneration', 0)),
        'mark': _fk_id(mark),
    }
    mark_data = autoru_mark_to_ingest(mark)
    if mark_data:
        data['mark_data'] = mark_data
    return data


def autoru_modification_to_ingest(mod) -> dict:
    if mod is None or not mod.pk:
        return {}
    model = getattr(mod, 'model', None)
    type_body = getattr(mod, 'typeBody', None)
    type_engine = getattr(mod, 'typeEngine', None)
    type_gear = getattr(mod, 'typeGear', None)
    data = {
        'id': int(mod.pk),
        'name': _clean_str(mod.name, 200),
        'nameEn': _clean_str(getattr(mod, 'nameEn', ''), 200),
        'idSite': _clean_int(getattr(mod, 'idSite', 0)),
        'idSiteGeneration': _clean_int(getattr(mod, 'idSiteGeneration', 0)),
        'idSiteKonf': _clean_int(getattr(mod, 'idSiteKonf', 0)),
        'idSiteTech': _clean_int(getattr(mod, 'idSiteTech', 0)),
        'engineVolume': float(getattr(mod, 'engineVolume', 0) or 0),
        'enginePower': float(getattr(mod, 'enginePower', 0) or 0),
        'ProductionStartYear': _clean_int(getattr(mod, 'ProductionStartYear', 0)),
        'ProductionEndYear': _clean_int(getattr(mod, 'ProductionEndYear', 0)),
        'typeBody': _fk_id(type_body),
        'typeBody_name': _clean_str(type_body.name, 200) if type_body else '',
        'typeEngine': _fk_id(type_engine),
        'typeEngine_name': _clean_str(type_engine.name, 200) if type_engine else '',
        'typeGear': _fk_id(type_gear),
        'typeGear_name': _clean_str(type_gear.name, 200) if type_gear else '',
        'model': _fk_id(model),
    }
    model_data = autoru_model_to_ingest(model)
    if model_data:
        data['model_data'] = model_data
    return data


def autoru_complectation_to_ingest(compl) -> dict:
    if compl is None or not compl.pk:
        return {}
    modification = getattr(compl, 'modification', None)
    return {
        'id': int(compl.pk),
        'name': _clean_str(compl.name, 200),
        'idSite': _clean_int(getattr(compl, 'idSite', 0)),
        'modification': _fk_id(modification),
    }


def _absolutize_url(url: str) -> str:
    """Относительный /media/... → абсолютный HTTPS URL на портале."""
    text = _clean_str(url, 1024)
    if not text:
        return ''
    if text.startswith('http://'):
        text = 'https://' + text[7:]
    if text.startswith('https://'):
        return text
    if not text.startswith('/'):
        text = '/' + text
    base = conf.portal_public_base_url() or 'https://ah.kors-group.com'
    if base.startswith('http://'):
        base = 'https://' + base[7:]
    return base + text


def _photo_file_url(photo, attr_name: str) -> str:
    field = getattr(photo, attr_name, None)
    if field:
        try:
            return _absolutize_url(field.url)
        except Exception:
            pass
    return ''


def photo_to_ingest(photo) -> dict:
    """Ссылка на фото — URL файла на портале (ImageField), не CharField url."""
    url = _photo_file_url(photo, 'file')
    url_mini = _photo_file_url(photo, 'file_mini') or url
    if not url:
        return {}
    return {
        'id': int(photo.pk) if photo.pk else None,
        'url': url,
        'url_mini': url_mini,
        'main': bool(getattr(photo, 'main', False)),
        'name': _clean_str(getattr(photo, 'name', ''), 512),
    }


def car_photos_to_ingest(car, photos=None) -> list:
    """
    Ссылки на фото автомобиля.
    photos — уже загруженный queryset/list (чтобы не бить БД в цикле).
    """
    if photos is None:
        from refs.models import RefCarsOrganizationFiles
        photos = (
            RefCarsOrganizationFiles.objects
            .filter(сars_organization_id=car.pk)
            .order_by('-main', 'id')
        )
    limit = conf.photos_limit()
    result = []
    for photo in photos:
        item = photo_to_ingest(photo)
        if not item:
            continue
        result.append(item)
        if limit and len(result) >= limit:
            break
    return result


def car_to_ingest_payload(car) -> dict:
    """
    RefCarsOrganization → JSON ingest.
    organization / unit / store / Auto.ru — ID с портала (та же схема БД).
    Вложенные *_data — чтобы MyKors мог создать справочники на пустой базе.
    """
    vin = _clean_str(getattr(car, 'vin', ''), 18)
    payload = {
        'vin': vin,
        'vin2': _clean_str(getattr(car, 'vin2', ''), 18),
        'name': _clean_str(getattr(car, 'name', ''), 512),
        'mark': _clean_str(getattr(car, 'mark', ''), 512),
        'model': _clean_str(getattr(car, 'model', ''), 512),
        'modification': _clean_str(getattr(car, 'modification', ''), 512),
        'year': _clean_int(getattr(car, 'year', 0)),
        'color': _clean_str(getattr(car, 'color', ''), 512),
        'is_new': bool(getattr(car, 'is_new', False)),
        'run': _clean_int(getattr(car, 'run', 0)),
        'price': _clean_int(getattr(car, 'price', 0)),
        'plate_number': _clean_str(getattr(car, 'plate_number', ''), 30),
    }

    org = getattr(car, 'organization', None)
    unit = getattr(car, 'unit', None)
    store = getattr(car, 'store', None)

    org_id = _fk_id(org) or getattr(car, 'organization_id', None)
    unit_id = _fk_id(unit) or getattr(car, 'unit_id', None)
    store_id = _fk_id(store) or getattr(car, 'store_id', None)

    if org_id:
        payload['organization'] = int(org_id)
        org_data = organization_to_ingest(org)
        if org_data:
            payload['organization_data'] = org_data
    if unit_id:
        payload['unit'] = int(unit_id)
        unit_data = unit_to_ingest(unit)
        if unit_data:
            payload['unit_data'] = unit_data
    if store_id:
        payload['store'] = int(store_id)
        store_data = store_to_ingest(store)
        if store_data:
            payload['store_data'] = store_data

    modification = getattr(car, 'modification_autoru', None)
    complectation = getattr(car, 'complectation_autoru', None)
    mod_id = _fk_id(modification) or getattr(car, 'modification_autoru_id', None)
    compl_id = _fk_id(complectation) or getattr(car, 'complectation_autoru_id', None)

    if mod_id:
        payload['modification_autoru'] = int(mod_id)
        mod_data = autoru_modification_to_ingest(modification)
        if mod_data:
            payload['modification_autoru_data'] = mod_data

        model = getattr(modification, 'model', None) if modification else None
        mark = getattr(model, 'mark', None) if model else None
        if not payload['mark'] and mark is not None:
            payload['mark'] = _clean_str(getattr(mark, 'name', ''), 512)
        if not payload['model'] and model is not None:
            payload['model'] = _clean_str(getattr(model, 'name', ''), 512)
        if not payload['modification'] and modification is not None:
            payload['modification'] = _clean_str(modification.name, 512)

    if compl_id:
        payload['complectation_autoru'] = int(compl_id)
        compl_data = autoru_complectation_to_ingest(complectation)
        if compl_data:
            payload['complectation_autoru_data'] = compl_data

    photos = getattr(car, '_mykors_photos', None)
    payload['photos'] = car_photos_to_ingest(car, photos=photos)

    return payload


def _date_to_iso(value):
    """Дата/время Django → ISO 8601, пустое значение или пустая дата 1С (0001-01-01) → null в JSON."""
    if value is None:
        return None
    try:
        if hasattr(value, 'year') and value.year < 1970:
            return None
        return value.isoformat()
    except (AttributeError, ValueError):
        return None


def _image_field_url(instance, field_name: str) -> str:
    """Абсолютный URL ImageField без ошибки для пустого или битого файла."""
    field = getattr(instance, field_name, None)
    if not field:
        return ''
    try:
        return _absolutize_url(field.url)
    except (AttributeError, ValueError):
        return ''


def _clean_phone(value) -> str:
    r"""Очистка телефона до формата ^\+?\d{10,15}$ под валидатор MyKors."""
    import re
    text = _clean_str(value, 64)
    if not text:
        return ''
    digits = re.sub(r'\D', '', text)
    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    if 10 <= len(digits) <= 15:
        return ('+' if text.startswith('+') or (len(digits) == 11 and digits.startswith('7')) else '') + digits
    return ''


def user_to_ingest_payload(user) -> dict:
    """
    Django User + Profiles → JSON для MyKors.

    Пароль, is_superuser и current_session_key намеренно не передаются.
    portal_user_id является стабильным ключом для upsert на стороне MyKors.
    """
    payload = {
        'portal_user_id': int(user.pk),
        'username': _clean_str(getattr(user, 'username', ''), 150),
        'email': _clean_str(getattr(user, 'email', ''), 254),
        'first_name': _clean_str(getattr(user, 'first_name', ''), 150),
        'last_name': _clean_str(getattr(user, 'last_name', ''), 150),
        'is_active': bool(getattr(user, 'is_active', False)),
        'is_staff': bool(getattr(user, 'is_staff', False)),
        'date_joined': _date_to_iso(getattr(user, 'date_joined', None)),
    }

    profile = getattr(user, 'profiles', None)
    if profile is None:
        payload['profile'] = None
        return payload

    raw_image_url = _image_field_url(profile, 'image')
    image_url = ''
    if raw_image_url:
        from urllib.parse import urlparse
        parsed = urlparse(raw_image_url)
        # MyKors принимает аватар строго с хоста ah.kors-group.com и только по HTTPS
        image_url = f"https://ah.kors-group.com{parsed.path}"

    units = sorted(profile.available_units.all(), key=lambda item: item.pk)
    stores = sorted(profile.korsavto_stores.all(), key=lambda item: item.pk)
    profile_payload = {
        'id': int(profile.pk),
        'birth_date': _date_to_iso(profile.birth_date),
        'email': _clean_str(profile.email, 254),
        'phone': _clean_phone(profile.phone),
        'image_url': image_url,
        'view_checklist': bool(profile.view_checklist),
        'edit_sms_opros': bool(profile.edit_sms_opros),
        'eco_name': _clean_str(profile.eco_name, 512),
        'eco': bool(profile.eco),
        'eco_visible': bool(profile.eco_visible),
        'eco_page_price_info': bool(profile.eco_page_price_info),
        'eco_page_price_auto': bool(profile.eco_page_price_auto),
        'eco_toast': bool(profile.eco_toast),
        'korsavto_settings': bool(profile.korsavto_settings),
        'korsavto_settings_dc': bool(profile.korsavto_settings_dc),
        'korsavto_city': _clean_str(profile.korsavto_city, 512),
        'korsavto_auction': bool(profile.korsavto_auction),
        'user_sb': bool(profile.user_sb),
        'price_car_new': bool(profile.price_car_new),
        'price_car_new_director': bool(profile.price_car_new_director),
        'price_car_new_all': bool(profile.price_car_new_all),
        'price_car_bu': bool(profile.price_car_bu),
        'price_car_new_settings': bool(profile.price_car_new_settings),
        'price_car_bu_settings': bool(profile.price_car_bu_settings),
        'estimation_settings': bool(profile.estimation_settings),
        'estimation_report': bool(profile.estimation_report),
        'eco_report': bool(profile.eco_report),
        'available_units_data': [unit_to_ingest(unit) for unit in units],
        'korsavto_stores_data': [store_to_ingest(store) for store in stores],
    }
    payload['profile'] = profile_payload
    return payload


def staff_to_ingest(staff) -> dict:
    if staff is None or not staff.pk:
        return {}
    uin = _clean_str(getattr(staff, 'uin', ''), 200) or f"staff_{staff.pk}"
    name = _clean_str(staff.name, 200) or f"Сотрудник {staff.pk}"
    return {
        'id': int(staff.pk),
        'uin': uin,
        'name': name,
        'domain_login': _clean_str(getattr(staff, 'domain_login', ''), 100),
        'status': _clean_str(getattr(staff, 'status', ''), 100),
        'phone': _clean_str(getattr(staff, 'phone', ''), 100),
        'post': _clean_str(getattr(staff, 'post', ''), 100),
        'buauto': bool(getattr(staff, 'buauto', False)),
    }


def customer_to_ingest(cust) -> dict:
    if cust is None or not cust.pk:
        return {}
    uin = _clean_str(getattr(cust, 'uin', ''), 200) or f"customer_{cust.pk}"
    name = _clean_str(cust.name, 250) or f"Клиент {cust.pk}"
    return {
        'id': int(cust.pk),
        'uin': uin,
        'name': name,
        'full_name': _clean_str(getattr(cust, 'full_name', ''), 250),
        'phoneNorm': _clean_str(getattr(cust, 'phoneNorm', ''), 100),
        'email': _clean_str(getattr(cust, 'email', ''), 200),
        'inn': _clean_str(getattr(cust, 'inn', ''), 20),
        'kpp': _clean_str(getattr(cust, 'kpp', ''), 20),
        'actual_addres': _clean_str(getattr(cust, 'actual_addres', ''), 200),
        'addres': _clean_str(getattr(cust, 'addres', ''), 200),
        'description': _clean_str(getattr(cust, 'description', ''), 1000),
        'comment': _clean_str(getattr(cust, 'comment', ''), 1000),
        'company': bool(getattr(cust, 'company', False)),
    }


def car_ref_to_ingest(car) -> dict:
    if car is None or not car.pk:
        return {}
    vin = _clean_str(getattr(car, 'vin', ''), 18)
    if not vin:
        return {}
    return {
        'vin': vin,
        'vin2': _clean_str(getattr(car, 'vin2', ''), 18),
        'name': _clean_str(getattr(car, 'name', ''), 200),
        'year': _clean_int(getattr(car, 'year', 0)),
        'mark': _clean_str(getattr(car, 'mark', ''), 100),
        'model': _clean_str(getattr(car, 'model', ''), 100),
        'modification': _clean_str(getattr(car, 'modification', ''), 100),
    }


def doc_zn_works_to_ingest(doc) -> list:
    from documents.models import DocZNWork
    works = DocZNWork.objects.filter(zn=doc).select_related('work', 'type')
    result = []
    for w in works:
        work_data = None
        if w.work:
            work_data = {
                'uin': _clean_str(w.work.uin, 200),
                'name': _clean_str(w.work.name, 300),
                'article': _clean_str(getattr(w.work, 'article', ''), 150),
            }
        result.append({
            'uin': _clean_str(w.uin, 100),
            'work_data': work_data,
            'type_name': _clean_str(w.type.name, 100) if w.type else '',
            'quantity': float(w.quantity or 0.0),
            'price': float(w.price or 0.0),
            'discountPercentage': float(getattr(w, 'discountPercentage', 0.0) or 0.0),
            'discountAmount': float(getattr(w, 'discountAmount', 0.0) or 0.0),
            'amount': float(w.amount or 0.0),
            'amountResult': float(getattr(w, 'amountResult', 0.0) or 0.0),
        })
    return result


def doc_zn_products_to_ingest(doc) -> list:
    from documents.models import DocZNProduct
    products = DocZNProduct.objects.filter(zn=doc).select_related('product', 'type')
    result = []
    for p in products:
        product_data = None
        if p.product:
            product_data = {
                'uin': _clean_str(p.product.uin, 200),
                'name': _clean_str(p.product.name, 300),
                'article': _clean_str(getattr(p.product, 'article', ''), 150),
                'article_dop': _clean_str(getattr(p.product, 'article_dop', ''), 150),
                'manufacturer': _clean_str(getattr(p.product, 'manufacturer', ''), 150),
            }
        result.append({
            'uin': _clean_str(p.uin, 100),
            'product_data': product_data,
            'type_name': _clean_str(p.type.name, 100) if p.type else '',
            'quantity': float(p.quantity or 0.0),
            'price': float(p.price or 0.0),
            'discountPercentage': float(getattr(p, 'discountPercentage', 0.0) or 0.0),
            'discountAmount': float(getattr(p, 'discountAmount', 0.0) or 0.0),
            'amount': float(p.amount or 0.0),
            'amountResult': float(getattr(p, 'amountResult', 0.0) or 0.0),
        })
    return result


def doc_zn_customer_products_to_ingest(doc) -> list:
    from documents.models import DocZNProductCustomer
    items = DocZNProductCustomer.objects.filter(zn=doc)
    result = []
    for item in items:
        result.append({
            'product': _clean_str(item.product, 250),
            'article': _clean_str(getattr(item, 'article', ''), 250),
            'quantity': float(item.quantity or 0.0),
            'price': float(item.price or 0.0),
            'amount': float(item.amount or 0.0),
        })
    return result


def doc_zn_performers_to_ingest(doc) -> list:
    from documents.models import DocZNPerformers
    performers = DocZNPerformers.objects.filter(zn=doc).select_related('staff')
    result = []
    for perf in performers:
        result.append({
            'uin': _clean_str(perf.uin, 84),
            'staff_data': staff_to_ingest(perf.staff) if perf.staff else None,
            'percent': float(perf.percent or 0.0),
        })
    return result


def doc_zn_recommendations_to_ingest(doc) -> list:
    from documents.models import DocZNRecomendation
    recs = DocZNRecomendation.objects.filter(zn=doc)
    result = []
    for rec in recs:
        result.append({
            'uin': _clean_str(rec.uin, 84),
            'name': _clean_str(rec.name, 1000),
            'thisZN': bool(rec.thisZN),
            'close': bool(rec.close),
            'date': _date_to_iso(getattr(rec, 'date', None)),
            'description': _clean_str(getattr(rec, 'description', ''), 2500),
            'reasonClose': _clean_str(getattr(rec, 'reasonClose', ''), 2500),
            'show': bool(getattr(rec, 'show', False)),
        })
    return result


def doc_zn_extended_recommendations_to_ingest(doc) -> list:
    from documents.models import DoсRecomendation, DoсRecomendationWork, DoсRecomendationProduct, DocRecomendationFiles
    recs = DoсRecomendation.objects.filter(zn=doc)
    result = []
    for r in recs:
        works = []
        for w in DoсRecomendationWork.objects.filter(recomendation=r).select_related('work'):
            works.append({
                'work_data': {'uin': w.work.uin, 'name': w.work.name, 'article': getattr(w.work, 'article', '')} if w.work else None,
                'quantity': float(w.quantity or 0.0),
                'price': float(w.price or 0.0),
                'amount': float(w.amount or 0.0),
            })
        products = []
        for p in DoсRecomendationProduct.objects.filter(recomendation=r).select_related('product'):
            products.append({
                'product_data': {'uin': p.product.uin, 'name': p.product.name, 'article': getattr(p.product, 'article', '')} if p.product else None,
                'quantity': float(p.quantity or 0.0),
                'price': float(p.price or 0.0),
                'amount': float(p.amount or 0.0),
            })
        files = []
        for f in DocRecomendationFiles.objects.filter(recomendation=r):
            url = _photo_file_url(f, 'file')
            if url:
                files.append({'url': url})
        result.append({
            'name': _clean_str(r.name, 250),
            'dataTime': _date_to_iso(getattr(r, 'dataTime', None)),
            'dataTimeCutomerEvent': _date_to_iso(getattr(r, 'dataTimeCutomerEvent', None)),
            'customerStatus': _clean_int(getattr(r, 'customerStatus', 0)),
            'status': _clean_int(getattr(r, 'status', 0)),
            'kod_recomendation': _clean_int(getattr(r, 'kod_recomendation', 0)),
            'works': works,
            'products': products,
            'files': files,
        })
    return result


def doc_zn_extended_recommendations_mcu_to_ingest(doc) -> list:
    from documents.models import DoсRecomendationMCU, DocRecomendationFilesMCU
    recs = DoсRecomendationMCU.objects.filter(zn=doc)
    result = []
    for r in recs:
        files = []
        for f in DocRecomendationFilesMCU.objects.filter(recomendation=r):
            url = _photo_file_url(f, 'file')
            if url:
                files.append({'url': url})
        result.append({
            'name': _clean_str(r.name, 250),
            'dataTime': _date_to_iso(getattr(r, 'dataTime', None)),
            'dataTimeCutomerEvent': _date_to_iso(getattr(r, 'dataTimeCutomerEvent', None)),
            'customerStatus': _clean_int(getattr(r, 'customerStatus', 0)),
            'status': _clean_int(getattr(r, 'status', 0)),
            'files': files,
        })
    return result


def doc_zn_surveys_to_ingest(doc) -> list:
    from documents.models import DocOprosZN
    surveys = DocOprosZN.objects.filter(zn=doc)
    result = []
    for s in surveys:
        result.append({
            'uin': _clean_str(s.uin, 64),
            'dataTime': _date_to_iso(getattr(s, 'dataTime', None)),
            'dataClose': _date_to_iso(getattr(s, 'dataClose', None)),
            'v1': _clean_int(getattr(s, 'v1', 0)),
            'v2': _clean_int(getattr(s, 'v2', 0)),
            'v3': _clean_int(getattr(s, 'v3', 0)),
            'v4': _clean_int(getattr(s, 'v4', 0)),
            'v5': _clean_int(getattr(s, 'v5', 0)),
            'v6': _clean_int(getattr(s, 'v6', 0)),
            'v7': _clean_str(getattr(s, 'v7', ''), 250),
            'v8': _clean_str(getattr(s, 'v8', ''), 2500),
            'close': bool(getattr(s, 'close', False)),
            'canceled': bool(getattr(s, 'canceled', False)),
            'canceled_comment': _clean_str(getattr(s, 'canceled_comment', ''), 512),
            'number_base': _clean_str(getattr(s, 'number_base', ''), 64),
            'date_base': _date_to_iso(getattr(s, 'date_base', None)),
            'conclusions': _clean_str(getattr(s, 'conclusions', ''), 1024),
            'comment_tech_dir': _clean_str(getattr(s, 'comment_tech_dir', ''), 1024),
        })
    return result


def work_order_to_ingest_payload(doc, include_related: bool = True) -> dict:
    uin = _clean_str(getattr(doc, 'uin', ''), 64)
    if not uin:
        uin = f"zn_{doc.pk}"

    payload = {
        'uin': uin,
        'nomer': _clean_str(getattr(doc, 'nomer', ''), 25),
        'dataTime': _date_to_iso(getattr(doc, 'dataTime', None)),
        'dateStart': _date_to_iso(getattr(doc, 'dateStart', None)),
        'dateEnd': _date_to_iso(getattr(doc, 'dateEnd', None)),
        'carsGRZ': _clean_str(getattr(doc, 'carsGRZ', ''), 25),
        'clientName': _clean_str(getattr(doc, 'clientName', ''), 250),
        'customerWords': _clean_str(getattr(doc, 'customerWords', ''), 12500),
        'run': _clean_int(getattr(doc, 'run', 0)),
        'amount': float(getattr(doc, 'amount', 0.0) or 0.0),
        'gross_profit_work': float(getattr(doc, 'gross_profit_work', 0.0) or 0.0),
        'gross_profit_product': float(getattr(doc, 'gross_profit_product', 0.0) or 0.0),
        'typeIB': _clean_str(getattr(doc, 'typeIB', ''), 64),
        'recomendation': _clean_str(getattr(doc, 'recomendation', ''), 5024),
        'active': bool(getattr(doc, 'active', False)),
    }

    if doc.organization:
        payload['organization_data'] = organization_to_ingest(doc.organization)
    if doc.unit:
        payload['unit_data'] = unit_to_ingest(doc.unit)
    if doc.master:
        payload['master_data'] = staff_to_ingest(doc.master)
    if doc.masterOut:
        payload['master_out_data'] = staff_to_ingest(doc.masterOut)
    if doc.customer:
        payload['customer_data'] = customer_to_ingest(doc.customer)
    if doc.cars:
        car_data = car_ref_to_ingest(doc.cars)
        if car_data:
            payload['cars_data'] = car_data

    if doc.typeRemont:
        payload['type_remont_name'] = _clean_str(doc.typeRemont.name, 100)
    if doc.readyStatus:
        payload['ready_status_name'] = _clean_str(doc.readyStatus.name, 100)

    if include_related:
        works = doc_zn_works_to_ingest(doc)
        if works:
            payload['works_data'] = works
        prods = doc_zn_products_to_ingest(doc)
        if prods:
            payload['products_data'] = prods
        cust_prods = doc_zn_customer_products_to_ingest(doc)
        if cust_prods:
            payload['products_customer_data'] = cust_prods
        perfs = doc_zn_performers_to_ingest(doc)
        if perfs:
            payload['performers_data'] = perfs
        recs = doc_zn_recommendations_to_ingest(doc)
        if recs:
            payload['recommendations_data'] = recs
        ext_recs = doc_zn_extended_recommendations_to_ingest(doc)
        if ext_recs:
            payload['extended_recommendations_data'] = ext_recs
        ext_mcu = doc_zn_extended_recommendations_mcu_to_ingest(doc)
        if ext_mcu:
            payload['extended_recommendations_mcu_data'] = ext_mcu
        surveys = doc_zn_surveys_to_ingest(doc)
        if surveys:
            payload['surveys_data'] = surveys

    return payload


def work_order_ka_to_ingest_payload(doc, include_related: bool = True) -> dict:
    from documents.models import DocZNWorkKA, DocZNProductKA, DocZNServicesKA, DocZNPerformersKA
    uin = _clean_str(getattr(doc, 'uin', ''), 64) or f"znka_{doc.pk}"
    payload = {
        'uin': uin,
        'nomer': _clean_str(getattr(doc, 'nomer', ''), 25),
        'dataTime': _date_to_iso(getattr(doc, 'dataTime', None)),
        'nomer_dc': _clean_str(getattr(doc, 'nomer_dc', ''), 25),
        'dataTime_dc': _date_to_iso(getattr(doc, 'dataTime_dc', None)),
        'dateStart': _date_to_iso(getattr(doc, 'dateStart', None)),
        'dateEnd': _date_to_iso(getattr(doc, 'dateEnd', None)),
        'closed': bool(getattr(doc, 'closed', False)),
        'active': bool(getattr(doc, 'active', False)),
        'carsGRZ': _clean_str(getattr(doc, 'carsGRZ', ''), 25),
        'clientName': _clean_str(getattr(doc, 'clientName', ''), 250),
        'customerWords': _clean_str(getattr(doc, 'customerWords', ''), 12500),
        'run': _clean_int(getattr(doc, 'run', 0)),
        'amount': float(getattr(doc, 'amount', 0.0) or 0.0),
    }
    if doc.organization:
        payload['organization_data'] = organization_to_ingest(doc.organization)
    if doc.unit:
        payload['unit_data'] = unit_to_ingest(doc.unit)
    if doc.master:
        payload['master_data'] = staff_to_ingest(doc.master)
    if doc.masterOut:
        payload['master_out_data'] = staff_to_ingest(doc.masterOut)
    if doc.customer:
        payload['customer_data'] = customer_to_ingest(doc.customer)
    if doc.cars:
        car_data = car_ref_to_ingest(doc.cars)
        if car_data:
            payload['cars_data'] = car_data
    if getattr(doc, 'lo', None):
        payload['lo_uin'] = _clean_str(getattr(doc.lo, 'uin', ''), 64)
    if doc.typeRemont:
        payload['type_remont_name'] = _clean_str(doc.typeRemont.name, 100)
    if doc.readyStatus:
        payload['ready_status_name'] = _clean_str(doc.readyStatus.name, 100)

    if include_related:
        works = []
        for w in DocZNWorkKA.objects.filter(zn=doc).select_related('work', 'type'):
            works.append({
                'uin': _clean_str(w.uin, 100),
                'work_data': {'uin': w.work.uin, 'name': w.work.name, 'article': getattr(w.work, 'article', '')} if w.work else None,
                'type_name': _clean_str(w.type.name, 100) if w.type else '',
                'quantity': float(w.quantity or 0.0),
                'price': float(w.price or 0.0),
                'discountPercentage': float(getattr(w, 'discountPercentage', 0.0) or 0.0),
                'discountAmount': float(getattr(w, 'discountAmount', 0.0) or 0.0),
                'amount': float(w.amount or 0.0),
                'amountResult': float(getattr(w, 'amountResult', 0.0) or 0.0),
            })
        if works:
            payload['works_data'] = works

        products = []
        for p in DocZNProductKA.objects.filter(zn=doc).select_related('product', 'type'):
            products.append({
                'uin': _clean_str(p.uin, 100),
                'product_data': {'uin': p.product.uin, 'name': p.product.name, 'article': getattr(p.product, 'article', '')} if p.product else None,
                'type_name': _clean_str(p.type.name, 100) if p.type else '',
                'quantity': float(p.quantity or 0.0),
                'price': float(p.price or 0.0),
                'discountPercentage': float(getattr(p, 'discountPercentage', 0.0) or 0.0),
                'discountAmount': float(getattr(p, 'discountAmount', 0.0) or 0.0),
                'amount': float(p.amount or 0.0),
                'amountResult': float(getattr(p, 'amountResult', 0.0) or 0.0),
            })
        if products:
            payload['products_data'] = products

        services = []
        for s in DocZNServicesKA.objects.filter(zn=doc).select_related('service', 'type'):
            services.append({
                'uin': _clean_str(s.uin, 100),
                'service_data': {'uin': s.service.uin, 'name': s.service.name, 'article': getattr(s.service, 'article', '')} if s.service else None,
                'type_name': _clean_str(s.type.name, 100) if s.type else '',
                'quantity': float(s.quantity or 0.0),
                'price': float(s.price or 0.0),
                'discountPercentage': float(getattr(s, 'discountPercentage', 0.0) or 0.0),
                'discountAmount': float(getattr(s, 'discountAmount', 0.0) or 0.0),
                'amount': float(s.amount or 0.0),
                'amountResult': float(getattr(s, 'amountResult', 0.0) or 0.0),
            })
        if services:
            payload['services_data'] = services

        performers = []
        for perf in DocZNPerformersKA.objects.filter(zn=doc).select_related('staff'):
            performers.append({
                'uin': _clean_str(perf.uin, 100),
                'staff_data': staff_to_ingest(perf.staff) if perf.staff else None,
                'percent': float(perf.percent or 0.0),
            })
        if performers:
            payload['performers_data'] = performers

    return payload


def services_ka_to_ingest_payload(doc, include_related: bool = True) -> dict:
    from documents.models import DocServiceItem
    uin = _clean_str(getattr(doc, 'uin', ''), 64) or f"srvka_{doc.pk}"
    payload = {
        'uin': uin,
        'active': bool(getattr(doc, 'active', False)),
        'nomer': _clean_str(getattr(doc, 'nomer', ''), 25),
        'date_time': _date_to_iso(getattr(doc, 'date_time', None)),
        'nomer_dc': _clean_str(getattr(doc, 'nomer_dc', ''), 25),
        'date_time_dc': _date_to_iso(getattr(doc, 'date_time_dc', None)),
        'amount': float(getattr(doc, 'amount', 0.0) or 0.0),
    }
    if doc.organization:
        payload['organization_data'] = organization_to_ingest(doc.organization)
    if doc.unit:
        payload['unit_data'] = unit_to_ingest(doc.unit)
    if doc.author:
        payload['author_data'] = staff_to_ingest(doc.author)
    if doc.customer:
        payload['customer_data'] = customer_to_ingest(doc.customer)
    if getattr(doc, 'lo', None):
        payload['lo_uin'] = _clean_str(getattr(doc.lo, 'uin', ''), 64)
    if doc.type_cost:
        payload['type_cost_name'] = _clean_str(doc.type_cost.name, 150)

    if include_related:
        items = []
        for it in DocServiceItem.objects.filter(doc_service=doc).select_related('service', 'type_service'):
            items.append({
                'service_data': {'uin': it.service.uin, 'name': it.service.name, 'article': getattr(it.service, 'article', '')} if it.service else None,
                'type_service_name': _clean_str(it.type_service.name, 150) if it.type_service else '',
                'description': _clean_str(getattr(it, 'description', ''), 12500),
                'quantity': float(it.quantity or 0.0),
                'price': float(it.price or 0.0),
                'amount': float(it.amount or 0.0),
            })
        if items:
            payload['items_data'] = items
    return payload


def service_request_to_ingest_payload(doc, include_related: bool = True) -> dict:
    from documents.models import ResourcePlanning
    uin = _clean_str(getattr(doc, 'uin', ''), 64) or f"req_{doc.pk}"
    payload = {
        'uin': uin,
        'closed': bool(getattr(doc, 'closed', False)),
        'active': bool(getattr(doc, 'active', False)),
        'nomer': _clean_str(getattr(doc, 'nomer', ''), 25),
        'dataTime': _date_to_iso(getattr(doc, 'dataTime', None)),
        'dateStart': _date_to_iso(getattr(doc, 'dateStart', None)),
        'dateEnd': _date_to_iso(getattr(doc, 'dateEnd', None)),
        'carsGRZ': _clean_str(getattr(doc, 'carsGRZ', ''), 25),
        'clientName': _clean_str(getattr(doc, 'clientName', ''), 250),
        'customerWords': _clean_str(getattr(doc, 'customerWords', ''), 12500),
        'run': _clean_int(getattr(doc, 'run', 0)),
    }
    if doc.organization:
        payload['organization_data'] = organization_to_ingest(doc.organization)
    if doc.unit:
        payload['unit_data'] = unit_to_ingest(doc.unit)
    if doc.master:
        payload['master_data'] = staff_to_ingest(doc.master)
    if doc.masterOut:
        payload['master_out_data'] = staff_to_ingest(doc.masterOut)
    if doc.customer:
        payload['customer_data'] = customer_to_ingest(doc.customer)
    if doc.cars:
        car_data = car_ref_to_ingest(doc.cars)
        if car_data:
            payload['cars_data'] = car_data
    if doc.typeRemont:
        payload['type_remont_name'] = _clean_str(doc.typeRemont.name, 100)
    if doc.readyStatus:
        payload['ready_status_name'] = _clean_str(doc.readyStatus.name, 100)

    if include_related:
        plans = []
        for rp in ResourcePlanning.objects.filter(serviceRequest=doc).select_related('staff', 'type'):
            plans.append({
                'uin': _clean_str(rp.uin, 64),
                'active': bool(getattr(rp, 'active', False)),
                'dateStart': _date_to_iso(getattr(rp, 'dateStart', None)),
                'dateEnd': _date_to_iso(getattr(rp, 'dateEnd', None)),
                'staff_data': staff_to_ingest(rp.staff) if rp.staff else None,
                'type_name': _clean_str(rp.type.name, 100) if rp.type else '',
            })
        if plans:
            payload['planning_data'] = plans
    return payload


def worksheet_to_ingest_payload(doc, include_related: bool = True) -> dict:
    from documents.models import DocRLKEvents, SurveysOP, SurveysOP_questions, SurveysOP_tematics
    uin = _clean_str(getattr(doc, 'uin', ''), 100) or f"rlk_{doc.pk}"
    payload = {
        'uin': uin,
        'nomer': _clean_str(getattr(doc, 'nomer', ''), 25),
        'dataTime': _date_to_iso(getattr(doc, 'dataTime', None)),
        'dataEnd': _date_to_iso(getattr(doc, 'dataEnd', None)) or _date_to_iso(getattr(doc, 'dataTime', None)),
        'timeStr': _clean_str(getattr(doc, 'timeStr', ''), 5),
        'clientName': _clean_str(getattr(doc, 'clientName', ''), 250),
        'phone': _clean_str(getattr(doc, 'phone', ''), 2500),
        'tradeInModel': _clean_str(getattr(doc, 'tradeInModel', ''), 250),
        'vin_trade_in': _clean_str(getattr(doc, 'vin_trade_in', ''), 17),
        'estimation_id': _clean_int(getattr(doc, 'estimation_id', 0)),
        'listened': bool(getattr(doc, 'listened', False)),
        'no_records': bool(getattr(doc, 'no_records', False)),
        'archiveDayToDay': bool(getattr(doc, 'archiveDayToDay', False)),
        'is_missed': _clean_int(getattr(doc, 'is_missed', 0)),
        'eco': bool(getattr(doc, 'eco', False)),
        'archive': bool(getattr(doc, 'archive', False)),
        'dateArchive': _date_to_iso(getattr(doc, 'dateArchive', None)),
        'reasonArchive': _clean_str(getattr(doc, 'reasonArchive', ''), 1024),
        'commentAdministrator': _clean_str(getattr(doc, 'commentAdministrator', ''), 5112),
        'commentManager': _clean_str(getattr(doc, 'commentManager', ''), 5112),
        'manager_trade_in': _clean_str(getattr(doc, 'manager_trade_in', ''), 512),
        'dataTimeCreate': _date_to_iso(getattr(doc, 'dataTimeCreate', None)),
    }
    if doc.unit:
        payload['unit_data'] = unit_to_ingest(doc.unit)
    if getattr(doc, 'unit_dc', None):
        payload['unit_dc_data'] = unit_to_ingest(doc.unit_dc)
    if doc.staff:
        payload['staff_data'] = staff_to_ingest(doc.staff)
    if getattr(doc, 'staffECO1', None):
        payload['staff_eco1_data'] = staff_to_ingest(doc.staffECO1)
    if getattr(doc, 'staffECO2', None):
        payload['staff_eco2_data'] = staff_to_ingest(doc.staffECO2)
    if doc.customer:
        payload['customer_data'] = customer_to_ingest(doc.customer)
    if doc.cars:
        car_data = car_ref_to_ingest(doc.cars)
        if car_data:
            payload['cars_data'] = car_data
    if doc.type:
        payload['type_name'] = _clean_str(doc.type.name, 100)
    if doc.status:
        payload['status_name'] = _clean_str(doc.status.name, 100)
    if getattr(doc, 'type_archive', None):
        payload['type_archive_name'] = _clean_str(doc.type_archive.name, 100)
    if getattr(doc, 'contacType', None):
        payload['contact_type_name'] = _clean_str(doc.contacType.name, 100)

    if include_related:
        events = []
        for ev in DocRLKEvents.objects.filter(rlk=doc).select_related('staff', 'contacType', 'status'):
            events.append({
                'uin': _clean_str(ev.uin, 100),
                'dataTime': _date_to_iso(getattr(ev, 'dataTime', None)),
                'dataTimeEvent': _date_to_iso(getattr(ev, 'dataTimeEvent', None)),
                'comment': _clean_str(getattr(ev, 'comment', ''), 1024),
                'staff_data': staff_to_ingest(ev.staff) if ev.staff else None,
                'contact_type_name': _clean_str(ev.contacType.name, 100) if ev.contacType else '',
                'status_name': _clean_str(ev.status.name, 100) if ev.status else '',
            })
        if events:
            payload['events_data'] = events

        surveys = []
        for s in SurveysOP.objects.filter(rlk=doc).select_related('unit', 'staff'):
            questions = []
            for q in SurveysOP_questions.objects.filter(surveys=s):
                questions.append({
                    'name': _clean_str(q.name, 150),
                    'answer': _clean_int(getattr(q, 'answer', 0)),
                    'canceled': bool(getattr(q, 'canceled', False)),
                })
            tematics = []
            for t in SurveysOP_tematics.objects.filter(surveys=s):
                tematics.append({
                    'name': _clean_str(t.name, 150),
                    'entry_id': _clean_str(getattr(t, 'entry_id', ''), 20),
                    'record': _clean_str(getattr(t, 'record', ''), 512),
                })
            surveys.append({
                'uin': _clean_str(s.uin, 100),
                'dateTime': _date_to_iso(getattr(s, 'dateTime', None)),
                'nomer': _clean_str(getattr(s, 'nomer', ''), 25),
                'result': _clean_int(getattr(s, 'result', 0)),
                'conclusions': _clean_str(getattr(s, 'сonclusions', ''), 25024),
                'unit_data': unit_to_ingest(s.unit) if s.unit else None,
                'staff_data': staff_to_ingest(s.staff) if s.staff else None,
                'questions': questions,
                'tematics': tematics,
            })
        if surveys:
            payload['surveys_op_data'] = surveys

    return payload


def evaluation_to_ingest_payload(doc) -> dict:
    uin = _clean_str(getattr(doc, 'uin', ''), 64) or f"lo_{doc.pk}"
    payload = {
        'uin': uin,
        'active': bool(getattr(doc, 'active', False)),
        'nomer': _clean_str(getattr(doc, 'nomer', ''), 25),
        'dataTime': _date_to_iso(getattr(doc, 'dataTime', None)),
        'carsGRZ': _clean_str(getattr(doc, 'carsGRZ', ''), 25),
        'clientName': _clean_str(getattr(doc, 'clientName', ''), 250),
        'vin': _clean_str(getattr(doc, 'vin', ''), 21),
        'vin2': _clean_str(getattr(doc, 'vin2', ''), 21),
        'year': _clean_int(getattr(doc, 'year', 0)),
        'run': _clean_int(getattr(doc, 'run', 0)),
        'owners': _clean_int(getattr(doc, 'owners', 0)),
        'keys': _clean_int(getattr(doc, 'keys', 0)),
        'color': _clean_str(getattr(doc, 'color', ''), 1024),
        'cost_price': _clean_int(getattr(doc, 'cost_price', 0)),
        'bcp': _clean_int(getattr(doc, 'bcp', 0)),
        'recomendation': _clean_str(getattr(doc, 'recomendation', ''), 5024),
        'description_podgotovka': _clean_str(getattr(doc, 'description_podgotovka', ''), 15120),
        'description_op': _clean_str(getattr(doc, 'description_op', ''), 15120),
        'vin_new': _clean_str(getattr(doc, 'vin_new', ''), 21),
        'name_new_auto': _clean_str(getattr(doc, 'name_new_auto', ''), 512),
        'agreement_number': _clean_str(getattr(doc, 'agreement_number', ''), 512),
        'agreement_unit_bu': bool(getattr(doc, 'agreement_unit_bu', False)),
        'auction': bool(getattr(doc, 'auction', False)),
        'auction_comment': _clean_str(getattr(doc, 'auction_comment', ''), 1024),
    }
    if doc.organization:
        payload['organization_data'] = organization_to_ingest(doc.organization)
    if doc.unit:
        payload['unit_data'] = unit_to_ingest(doc.unit)
    if getattr(doc, 'filial', None):
        payload['filial_data'] = {'uin': _clean_str(doc.filial.uin, 200), 'name': _clean_str(doc.filial.name, 250)}
    if getattr(doc, 'store', None):
        payload['store_data'] = store_to_ingest(doc.store)
    if doc.staff:
        payload['staff_data'] = staff_to_ingest(doc.staff)
    if doc.customer:
        payload['customer_data'] = customer_to_ingest(doc.customer)
    if doc.cars:
        car_data = car_ref_to_ingest(doc.cars)
        if car_data:
            payload['cars_data'] = car_data
    if getattr(doc, 'rlk', None):
        payload['rlk_uin'] = _clean_str(getattr(doc.rlk, 'uin', ''), 100)
    if getattr(doc, 'type_reception', None):
        payload['type_reception_name'] = _clean_str(doc.type_reception.name, 100)

    return payload


def car_agreement_to_ingest_payload(doc) -> dict:
    uin = _clean_str(getattr(doc, 'uin', ''), 100) or f"agr_{doc.pk}"
    payload = {
        'uin': uin,
        'nomer': _clean_str(getattr(doc, 'nomer', ''), 25),
        'dataTime': _date_to_iso(getattr(doc, 'dataTime', None)),
        'timeStr': _clean_str(getattr(doc, 'timeStr', ''), 5),
        'active': bool(getattr(doc, 'active', False)),
        'clientName': _clean_str(getattr(doc, 'clientName', ''), 250),
        'amount': float(getattr(doc, 'amount', 0.0) or 0.0),
        'amountAddDiscountAmountTorg': float(getattr(doc, 'amountAddDiscountAmountTorg', 0.0) or 0.0),
        'cost_price': float(getattr(doc, 'cost_price', 0.0) or 0.0),
        'outlay': _clean_int(getattr(doc, 'outlay', 0)),
        'discountAmount': float(getattr(doc, 'discountAmount', 0.0) or 0.0),
        'discountAmountTorg': float(getattr(doc, 'discountAmountTorg', 0.0) or 0.0),
        'discountAmountTradeIN': float(getattr(doc, 'discountAmountTradeIN', 0.0) or 0.0),
        'discountAmountTorgComment': _clean_str(getattr(doc, 'discountAmountTorgComment', ''), 512),
        'discountAmountTradeINComment': _clean_str(getattr(doc, 'discountAmountTradeINComment', ''), 512),
        'run': _clean_int(getattr(doc, 'run', 0)),
        'owners': _clean_int(getattr(doc, 'owners', 0)),
        'typeSale': _clean_str(getattr(doc, 'typeSale', ''), 512),
        'check_estimated': bool(getattr(doc, 'check_estimated', False)),
        'check_actual': bool(getattr(doc, 'check_actual', False)),
        'check_date_time': _date_to_iso(getattr(doc, 'check_date_time', None)),
        'bu_wheels_est': float(getattr(doc, 'bu_wheels_est', 0.0) or 0.0),
        'bu_wheels_actual': float(getattr(doc, 'bu_wheels_actual', 0.0) or 0.0),
        'kso_est': float(getattr(doc, 'kso_est', 0.0) or 0.0),
        'kso_actual': float(getattr(doc, 'kso_actual', 0.0) or 0.0),
        'check_text': _clean_str(getattr(doc, 'check_text', ''), 2048),
        'cm_est': float(getattr(doc, 'cm_est', 0.0) or 0.0),
        'cm_min': float(getattr(doc, 'cm_min', 0.0) or 0.0),
        'cm_actual': float(getattr(doc, 'cm_actual', 0.0) or 0.0),
        'cm_goal': float(getattr(doc, 'cm_goal', 0.0) or 0.0),
        'date_planed_sale': _date_to_iso(getattr(doc, 'date_planed_sale', None)),
    }
    if doc.organization:
        payload['organization_data'] = organization_to_ingest(doc.organization)
    if doc.unit:
        payload['unit_data'] = unit_to_ingest(doc.unit)
    if getattr(doc, 'client', None):
        payload['client_data'] = customer_to_ingest(doc.client)
    if doc.staff:
        payload['staff_data'] = staff_to_ingest(doc.staff)
    if doc.cars:
        car_data = car_ref_to_ingest(doc.cars)
        if car_data:
            payload['cars_data'] = car_data
    if getattr(doc, 'rlk', None):
        payload['rlk_uin'] = _clean_str(getattr(doc.rlk, 'uin', ''), 100)
    if getattr(doc, 'lo', None):
        payload['lo_uin'] = _clean_str(getattr(doc.lo, 'uin', ''), 64)

    return payload


def car_shipment_to_ingest_payload(doc, include_related: bool = True) -> dict:
    from documents.models import DocOprosCarShipment
    uin = _clean_str(getattr(doc, 'uin', ''), 100) or f"ship_{doc.pk}"
    payload = {
        'uin': uin,
        'nomer': _clean_str(getattr(doc, 'nomer', ''), 25),
        'dataTime': _date_to_iso(getattr(doc, 'dataTime', None)),
        'timeStr': _clean_str(getattr(doc, 'timeStr', ''), 5),
        'active': bool(getattr(doc, 'active', False)),
        'clientName': _clean_str(getattr(doc, 'clientName', ''), 250),
        'amount': float(getattr(doc, 'amount', 0.0) or 0.0),
        'amountAddDiscountAmountTorg': float(getattr(doc, 'amountAddDiscountAmountTorg', 0.0) or 0.0),
        'cost_price': float(getattr(doc, 'cost_price', 0.0) or 0.0),
        'outlay': _clean_int(getattr(doc, 'outlay', 0)),
        'discountAmount': float(getattr(doc, 'discountAmount', 0.0) or 0.0),
        'discountAmountTorg': float(getattr(doc, 'discountAmountTorg', 0.0) or 0.0),
        'discountAmountTradeIN': float(getattr(doc, 'discountAmountTradeIN', 0.0) or 0.0),
        'discountAmountTorgComment': _clean_str(getattr(doc, 'discountAmountTorgComment', ''), 512),
        'discountAmountTradeINComment': _clean_str(getattr(doc, 'discountAmountTradeINComment', ''), 512),
        'run': _clean_int(getattr(doc, 'run', 0)),
        'owners': _clean_int(getattr(doc, 'owners', 0)),
        'typeSale': _clean_str(getattr(doc, 'typeSale', ''), 512),
    }
    if doc.organization:
        payload['organization_data'] = organization_to_ingest(doc.organization)
    if doc.unit:
        payload['unit_data'] = unit_to_ingest(doc.unit)
    if getattr(doc, 'client', None):
        payload['client_data'] = customer_to_ingest(doc.client)
    if doc.staff:
        payload['staff_data'] = staff_to_ingest(doc.staff)
    if doc.cars:
        car_data = car_ref_to_ingest(doc.cars)
        if car_data:
            payload['cars_data'] = car_data
    if getattr(doc, 'rlk', None):
        payload['rlk_uin'] = _clean_str(getattr(doc.rlk, 'uin', ''), 100)
    if getattr(doc, 'agreement', None):
        payload['agreement_uin'] = _clean_str(getattr(doc.agreement, 'uin', ''), 100)
    if getattr(doc, 'lo', None):
        payload['lo_uin'] = _clean_str(getattr(doc.lo, 'uin', ''), 64)

    if include_related:
        opros = DocOprosCarShipment.objects.filter(shipment=doc).first()
        if opros:
            payload['opros_data'] = {
                'uin': _clean_str(opros.uin, 64),
                'dataTime': _date_to_iso(getattr(opros, 'dataTime', None)),
                'dataClose': _date_to_iso(getattr(opros, 'dataClose', None)),
                'v1': _clean_int(getattr(opros, 'v1', 0)),
                'v2': _clean_int(getattr(opros, 'v2', 0)),
                'v3': _clean_int(getattr(opros, 'v3', 0)),
                'v4': _clean_int(getattr(opros, 'v4', 0)),
                'v5': _clean_int(getattr(opros, 'v5', 0)),
                'v6': _clean_int(getattr(opros, 'v6', 0)),
                'v7': _clean_str(getattr(opros, 'v7', ''), 250),
                'v8': _clean_str(getattr(opros, 'v8', ''), 2500),
                'close': bool(getattr(opros, 'close', False)),
                'canceled': bool(getattr(opros, 'canceled', False)),
                'number_base': _clean_str(getattr(opros, 'number_base', ''), 64),
                'conclusions': _clean_str(getattr(opros, 'conclusions', ''), 1024),
            }

    return payload


def sms_to_ingest_payload(doc) -> dict:
    uin = _clean_str(getattr(doc, 'uin', ''), 64) or f"sms_{doc.pk}"
    payload = {
        'uin': uin,
        'active': bool(getattr(doc, 'active', False)),
        'nomer': _clean_str(getattr(doc, 'nomer', ''), 25),
        'dateTime': _date_to_iso(getattr(doc, 'dateTime', None)),
        'dateSend': _date_to_iso(getattr(doc, 'dateSend', None)),
        'clientName': _clean_str(getattr(doc, 'clientName', ''), 250),
        'modelName': _clean_str(getattr(doc, 'modelName', ''), 250),
        'modelId': _clean_str(getattr(doc, 'modelId', ''), 250),
        'thema': _clean_str(getattr(doc, 'thema', ''), 250),
        'message': _clean_str(getattr(doc, 'message', ''), 2500),
        'error': _clean_str(getattr(doc, 'error', ''), 250),
        'errorProvider': _clean_str(getattr(doc, 'errorProvider', ''), 250),
        'phone': _clean_str(getattr(doc, 'phone', ''), 250),
        'phoneNorm': _clean_str(getattr(doc, 'phoneNorm', ''), 250),
        'messageId': _clean_str(getattr(doc, 'messageId', ''), 250),
    }
    if doc.organization:
        payload['organization_data'] = organization_to_ingest(doc.organization)
    if doc.unit:
        payload['unit_data'] = unit_to_ingest(doc.unit)
    if doc.staff:
        payload['staff_data'] = staff_to_ingest(doc.staff)
    if doc.customer:
        payload['customer_data'] = customer_to_ingest(doc.customer)
    if getattr(doc, 'statusBase', None):
        payload['status_base_name'] = _clean_str(doc.statusBase.name, 100)
    if getattr(doc, 'statusProvider', None):
        payload['status_provider_name'] = _clean_str(doc.statusProvider.name, 100)

    return payload


def payload_hash(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

