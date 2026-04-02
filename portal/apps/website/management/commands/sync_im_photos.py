"""Синхронизация фото товаров интернет-магазина из 1C API."""
import os
import re
import requests
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils import timezone
from django.conf import settings

from website.models import ImProduct, ImProductPhoto, ImSyncLog
from website.views import server_im, time_out_im


def parse_photo_urls(data):
    """Извлечь список URL фото из ответа API продукта."""
    urls = []
    # МассивФото — строка через точку с запятой
    raw = data.get('МассивФото') or data.get('массивФото') or data.get('Фото')
    if raw is None:
        return urls
    if isinstance(raw, str):
        parts = [s.strip() for s in raw.split(';') if s.strip()]
        urls.extend(parts)
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, str) and item.strip().startswith(('http://', 'https://')):
                urls.append(item.strip())
            elif isinstance(item, dict):
                u = item.get('url') or item.get('URL') or item.get('Url') or item.get('Ссылка')
                if u and str(u).strip().startswith(('http://', 'https://')):
                    urls.append(str(u).strip())
    return urls


def url_to_filename(url):
    """Сгенерировать безопасное имя файла из URL."""
    # Берём последнюю часть пути (имя файла) или хеш
    match = re.search(r'/([^/?#]+\.(jpg|jpeg|png|gif|webp))(?:\?|$)', url, re.I)
    if match:
        base = match.group(1)
    else:
        import hashlib
        base = hashlib.md5(url.encode()).hexdigest()[:16] + '.jpg'
    # Очищаем от недопустимых символов
    base = re.sub(r'[^\w\-\.]', '_', base)[:200]
    return base


class Command(BaseCommand):
    help = 'Синхронизация фото товаров из 1C API: проверка URL, загрузка отсутствующих'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0,
                            help='Максимум товаров для обработки (0 = без ограничений)')

    def handle(self, *args, **options):
        limit = options.get('limit', 0)
        products = ImProduct.objects.filter(photo_count__gt=0).order_by('-photo_count', 'nomenclature_code')
        if limit:
            products = products[:limit]

        log = ImSyncLog(
            sync_type='photo_sync',
            direction='in',
            request_url=server_im + 'product/',
        )
        log.save()

        total_products = 0
        total_downloaded = 0
        total_skipped = 0
        total_errors = 0

        for product in products:
            total_products += 1
            try:
                url = f'{server_im}product/?kod={product.nomenclature_code}'
                resp = requests.get(url, timeout=time_out_im, verify=False)
                if resp.status_code != 200:
                    total_errors += 1
                    continue

                data = resp.json()
                photo_urls = parse_photo_urls(data)
                if not photo_urls:
                    continue

                for idx, photo_url in enumerate(photo_urls):
                    if not photo_url.strip().startswith(('http://', 'https://')):
                        continue
                    exists = ImProductPhoto.objects.filter(
                        product=product, source_url=photo_url
                    ).exists()
                    if exists:
                        total_skipped += 1
                        continue

                    try:
                        img_resp = requests.get(photo_url, timeout=30, verify=False)
                        if img_resp.status_code != 200:
                            total_errors += 1
                            continue

                        content_type = img_resp.headers.get('Content-Type', '')
                        if 'image' not in content_type and not img_resp.content[:10]:
                            total_errors += 1
                            continue

                        fname = url_to_filename(photo_url)
                        photo = ImProductPhoto(
                            product=product,
                            source_url=photo_url,
                            sort_order=idx,
                            upload_1c_status=ImProductPhoto.UPLOAD_1C_NA,
                        )
                        photo.file.save(fname, ContentFile(img_resp.content), save=True)
                        total_downloaded += 1
                    except Exception as e:
                        total_errors += 1
                        self.stderr.write(f'Ошибка загрузки {photo_url[:60]}...: {e}')

            except Exception as e:
                total_errors += 1
                self.stderr.write(f'Ошибка товара {product.nomenclature_code}: {e}')

        log.items_total = total_products
        log.items_ok = total_downloaded + total_skipped
        log.items_failed = total_errors
        log.status = 'error' if total_errors and not total_downloaded else ('partial' if total_errors else 'success')
        log.finished_at = timezone.now()
        log.details_json = {
            'downloaded': total_downloaded,
            'skipped': total_skipped,
            'errors': total_errors,
        }
        log.save()

        self.stdout.write(self.style.SUCCESS(
            f'Синхронизация фото: обработано {total_products} товаров, '
            f'загружено {total_downloaded}, пропущено {total_skipped}, ошибок {total_errors}'
        ))
