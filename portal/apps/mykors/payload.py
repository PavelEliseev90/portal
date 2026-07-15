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
    return {
        'id': int(unit.pk),
        'uin': _clean_str(getattr(unit, 'uin', ''), 200),
        'name': _clean_str(unit.name, 200),
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
    return {
        'id': int(store.pk),
        'uin': _clean_str(getattr(store, 'uin', ''), 200),
        'name': _clean_str(store.name, 200),
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
    """Относительный /media/... → абсолютный URL на портале."""
    text = _clean_str(url, 1024)
    if not text:
        return ''
    if text.startswith('http://') or text.startswith('https://'):
        return text
    if not text.startswith('/'):
        text = '/' + text
    return conf.portal_public_base_url() + text


def _photo_file_url(photo, attr_name: str) -> str:
    field = getattr(photo, attr_name, None)
    if field:
        try:
            return _absolutize_url(field.url)
        except Exception:
            pass
    return ''


def photo_to_ingest(photo) -> dict:
    url = _clean_str(getattr(photo, 'url', ''), 512)
    url_mini = _clean_str(getattr(photo, 'url_mini', ''), 512)
    if not url:
        url = _photo_file_url(photo, 'file')
    else:
        url = _absolutize_url(url)
    if not url_mini:
        url_mini = _photo_file_url(photo, 'file_mini') or url
    else:
        url_mini = _absolutize_url(url_mini)
    if not url:
        return {}
    return {
        'id': int(photo.pk) if photo.pk else None,
        'url': url,
        'url_mini': url_mini or url,
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


def payload_hash(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()
