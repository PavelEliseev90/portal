"""Синхронизация стока интернет-магазина из 1C API."""
import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import ImProduct, ImSyncLog
from website.views import server_im, time_out_im


def parse_price(val):
    """Извлечь число из строки цены (1 404,15 или 1404)."""
    if val is None:
        return None
    s = str(val).replace(' ', '').replace('\xa0', '').replace(',', '.')
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def parse_int(val, default=0):
    """Безопасный парсинг int."""
    if val is None or val == '':
        return default
    try:
        return int(float(str(val).replace(' ', '').replace('\xa0', '')))
    except (ValueError, TypeError):
        return default


def product_from_json(item):
    """Преобразование JSON-объекта в поля ImProduct."""
    code_nom = str(item.get('НоменклатураКод', item.get('Код', ''))).strip() or str(item.get('Код', ''))
    if not code_nom:
        return None

    price_str = item.get('Price') or item.get('Цена') or item.get('Цена12') or ''
    price_val = parse_price(price_str)

    return {
        'nomenclature_code': code_nom[:100],
        'code': str(item.get('Код', ''))[:100],
        'nomenclature': str(item.get('Номенклатура', ''))[:500],
        'title': str(item.get('Объявление', item.get('Наименование', item.get('Номенклатура', ''))))[:500],
        'profile': str(item.get('Профиль', ''))[:100],
        'category': str(item.get('Категория', ''))[:200],
        'category_avito': str(item.get('КатегорияАвито', ''))[:200],
        'manufacturer': str(item.get('Производитель', ''))[:200],
        'article': str(item.get('Артикул', ''))[:100],
        'storage_cell': str(item.get('ЯчейкаХранения', ''))[:100],
        'address': str(item.get('Address', ''))[:500],
        'price_display': str(price_str)[:50] if price_str else '',
        'price_value': price_val,
        'quantity_balance': parse_int(item.get('КоличествоОстаток')),
        'photo_count': parse_int(item.get('КоличествоФото')),
        'avito_id': str(item.get('AvitoId', ''))[:50],
        'ad_status': str(item.get('AdStatus', ''))[:50],
        'status_text': str(item.get('Статус', ''))[:100],
        'views_count': parse_int(item.get('Просмотров')),
        'contacts_count': parse_int(item.get('Контактов')),
        'favorites_count': parse_int(item.get('Избранное')),
        'raw_json': item,
        'synced_at': timezone.now(),
    }


class Command(BaseCommand):
    help = 'Синхронизация стока интернет-магазина из 1C API'

    def add_arguments(self, parser):
        parser.add_argument('--url', type=str, default='', help='Доп. query string для API (например ?name=test)')

    def handle(self, *args, **options):
        url_suffix = options.get('url', '')
        full_url = server_im + 'stok/' + url_suffix
        log = ImSyncLog(
            sync_type='full_stok',
            direction='in',
            request_url=full_url,
        )
        log.save()

        try:
            resp = requests.get(full_url, timeout=time_out_im)
            log.response_code = resp.status_code

            if resp.status_code != 200:
                log.status = 'error'
                log.error_message = f'HTTP {resp.status_code}: {resp.text[:500]}'
                log.finished_at = timezone.now()
                log.save()
                self.stderr.write(self.style.ERROR(log.error_message))
                return

            data = resp.json()
            items = data if isinstance(data, list) else data.get('items', data.get('answer', data.get('objects', [])))
            if not isinstance(items, list):
                items = [data] if isinstance(data, dict) else []

            log.items_total = len(items)
            ok = 0
            failed = 0

            for item in items:
                try:
                    vals = product_from_json(item)
                    if vals:
                        ImProduct.objects.update_or_create(
                            nomenclature_code=vals['nomenclature_code'],
                            defaults=vals,
                        )
                        ok += 1
                except Exception as e:
                    failed += 1
                    self.stderr.write(f'Ошибка записи {item.get("НоменклатураКод", item)}: {e}')

            log.items_ok = ok
            log.items_failed = failed
            log.status = 'error' if failed and not ok else ('partial' if failed else 'success')
            log.finished_at = timezone.now()
            log.save()

            self.stdout.write(self.style.SUCCESS(
                f'Синхронизация завершена: {ok} успешно, {failed} ошибок'
            ))
        except Exception as e:
            log.status = 'error'
            log.error_message = str(e)[:2000]
            log.finished_at = timezone.now()
            log.save()
            self.stderr.write(self.style.ERROR(str(e)))
            raise
