"""Синхронизация TradeInFunnel → MSSQL (очистка периода + вставка)."""

from __future__ import annotations

import datetime as DT
from typing import Iterable, Optional


# Предпочтительный порядок, если DRIVER не задан явно / не установлен.
_DRIVER_CANDIDATES = (
    'ODBC Driver 18 for SQL Server',
    'ODBC Driver 17 for SQL Server',
    'ODBC Driver 13 for SQL Server',
    'SQL Server Native Client 11.0',
    'SQL Server',  # старый драйвер Windows (часто единственный на сервере)
)


def _installed_odbc_drivers() -> list:
    try:
        import pyodbc
        return list(pyodbc.drivers())
    except Exception:
        return []


def resolve_odbc_driver(preferred: str = '') -> str:
    """Вернуть имя установленного ODBC-драйвера SQL Server."""
    installed = _installed_odbc_drivers()
    preferred = (preferred or '').strip()
    if preferred and preferred in installed:
        return preferred
    for name in _DRIVER_CANDIDATES:
        if name in installed:
            return name
    # ничего подходящего — вернём preferred или дефолт (ошибка уже на connect)
    return preferred or _DRIVER_CANDIDATES[0]


def _is_modern_msodbcsql(driver: str) -> bool:
    """Encrypt/TrustServerCertificate поддерживают ODBC Driver 13+."""
    return 'ODBC Driver' in (driver or '') and 'SQL Server' in (driver or '')


def mssql_config() -> dict:
    from django.conf import settings
    cfg = getattr(settings, 'MSSQL_TRADEINFUNNEL', None) or {}
    preferred = (cfg.get('driver') or '').strip()
    return {
        'enabled': bool(cfg.get('enabled')),
        'driver': resolve_odbc_driver(preferred),
        'server': (cfg.get('server') or '').strip(),
        'database': (cfg.get('database') or '').strip(),
        'user': (cfg.get('user') or '').strip(),
        'password': cfg.get('password') or '',
        'trusted': bool(cfg.get('trusted')),
        'table': (cfg.get('table') or 'dbo.TradeInFunnel').strip(),
        'encrypt': cfg.get('encrypt', 'yes'),
        'trust_server_certificate': cfg.get('trust_server_certificate', 'yes'),
    }


def mssql_configured() -> bool:
    cfg = mssql_config()
    if not cfg['enabled']:
        return False
    if not cfg['server'] or not cfg['database']:
        return False
    if not cfg['trusted'] and not cfg['user']:
        return False
    return True


def _connection_string(cfg: dict) -> str:
    driver = cfg['driver']
    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={cfg['server']}",
        f"DATABASE={cfg['database']}",
    ]
    # Encrypt=* есть у Microsoft ODBC Driver 13/17/18; у старого "SQL Server" — нет
    if _is_modern_msodbcsql(driver):
        parts.append(f"Encrypt={cfg['encrypt']}")
        parts.append(f"TrustServerCertificate={cfg['trust_server_certificate']}")
    if cfg['trusted']:
        parts.append('Trusted_Connection=yes')
    else:
        parts.append(f"UID={cfg['user']}")
        parts.append(f"PWD={cfg['password']}")
    return ';'.join(parts)


def _connect():
    try:
        import pyodbc
    except ImportError as exc:
        raise RuntimeError(
            'Не установлен pyodbc. Установите: pip install pyodbc'
        ) from exc
    cfg = mssql_config()
    if not mssql_configured():
        raise RuntimeError(
            'MSSQL не настроен. Задайте MSSQL_TRADEINFUNNEL_* в окружении / settings '
            '(ENABLED=1, SERVER, DATABASE, USER/PASSWORD или TRUSTED=1).'
        )
    return pyodbc.connect(_connection_string(cfg), timeout=30)


def _safe_dt(value):
    invalid = DT.datetime(1, 1, 1)
    if not value or value == invalid or (getattr(value, 'year', 0) or 0) <= 1:
        return None
    return value


def _num(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def enrich_footing_op_fields(items: Iterable) -> None:
    """
    Подставляет номер/дату РЛ ОП (footing) из DocRLK, если в воронке пусто.
    Мутирует объекты в памяти (для Excel / MSSQL), в БД портала не пишет.
    """
    items = list(items) if not isinstance(items, list) else items
    need_ids = set()
    for item in items:
        fid = int(getattr(item, 'footing_rlk_id', None) or 0)
        if fid <= 0:
            continue
        has_number = bool((getattr(item, 'footing_rlk_number', None) or '').strip())
        has_date = _safe_dt(getattr(item, 'footing_rlk_date', None)) is not None
        if not has_number or not has_date:
            need_ids.add(fid)
    if not need_ids:
        return
    try:
        from documents.models import DocRLK
    except Exception:
        return
    by_id = {
        row['id']: row
        for row in DocRLK.objects.filter(pk__in=need_ids).values('id', 'nomer', 'dataTime')
    }
    for item in items:
        fid = int(getattr(item, 'footing_rlk_id', None) or 0)
        row = by_id.get(fid)
        if not row:
            continue
        if not (getattr(item, 'footing_rlk_number', None) or '').strip():
            item.footing_rlk_number = row.get('nomer') or ''
        if _safe_dt(getattr(item, 'footing_rlk_date', None)) is None:
            item.footing_rlk_date = row.get('dataTime')


def funnel_item_to_row(item) -> tuple:
    """Кортеж значений под INSERT в dbo.TradeInFunnel (латинские колонки)."""
    est_dt = _safe_dt(item.date_start_estimation)
    rlk_dt = _safe_dt(item.date_rlk)
    footing_dt = _safe_dt(getattr(item, 'footing_rlk_date', None))
    reception_success_dt = _safe_dt(item.date_reception_success)
    accepted_txt = 'Да' if reception_success_dt else 'Нет'
    return (
        est_dt,
        item.unit_name or '',
        item.unit_source_name or '',
        item.type_reception_name or '',
        item.mark_name or '',
        item.model_name or '',
        int(item.run or 0),
        int(item.year or 0),
        item.vin or '',
        item.rlk_number or '',
        rlk_dt,
        getattr(item, 'footing_rlk_number', None) or '',
        footing_dt,
        accepted_txt,
        item.stage or '',
        _num(item.cost_plan_preparation),
        _num(item.cost_plan_mcu),
        _num(item.cost_plan_ss),
        _num(item.price_before),
        _num(item.price_after),
        _num(item.zna),
    )


INSERT_COLUMNS = (
    'EstimationDate',
    'UnitName',
    'UnitSourceName',
    'TypeReceptionName',
    'MarkName',
    'ModelName',
    'RunKm',
    '[Year]',
    'Vin',
    'RlkNumber',
    'RlkDate',
    'SourceOpRlkNumber',
    'SourceOpRlkDate',
    'Accepted',
    'Stage',
    'CostPreparation',
    'CostMcu',
    'CostSs',
    'PriceBeforeKd',
    'PriceAfterKd',
    'MarketPriceRub',
)

# Колонки, которые могли появиться позже — при загрузке создаём, если отсутствуют.
_ENSURE_COLUMNS = (
    ('SourceOpRlkNumber', 'NVARCHAR(255) NULL'),
    ('SourceOpRlkDate', 'DATETIME2(0) NULL'),
)


def _table_parts(table: str) -> tuple[str, str]:
    """dbo.TradeInFunnel → ('dbo', 'TradeInFunnel')."""
    raw = (table or 'dbo.TradeInFunnel').strip()
    if '.' in raw:
        schema, name = raw.split('.', 1)
        return schema.strip('[]') or 'dbo', name.strip('[]')
    return 'dbo', raw.strip('[]')


def ensure_mssql_tradeinfunnel_columns(cursor, table: str) -> list[str]:
    """
    Создаёт недостающие столбцы РЛ ОП в MSSQL-таблице.
    Возвращает список добавленных имён колонок.
    """
    schema, name = _table_parts(table)
    added: list[str] = []
    for col_name, col_type in _ENSURE_COLUMNS:
        cursor.execute(
            """
            SELECT 1
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND COLUMN_NAME = ?
            """,
            (schema, name, col_name),
        )
        if cursor.fetchone():
            continue
        cursor.execute(
            f'ALTER TABLE [{schema}].[{name}] ADD [{col_name}] {col_type}'
        )
        added.append(col_name)
    return added


def sync_tradeinfunnel_to_mssql(
    *,
    date_start: DT.datetime,
    date_end: DT.datetime,
    items: Iterable,
    unit_name: Optional[str] = None,
    unit_source_name: Optional[str] = None,
    chunk_size: int = 500,
) -> dict:
    """
    1) При необходимости ADD недостающих столбцов (SourceOpRlk*)
    2) DELETE по EstimationDate в периоде (+ опционально UnitName / UnitSourceName)
    3) INSERT строк из items
    """
    cfg = mssql_config()
    table = cfg['table']
    items_list = list(items)
    enrich_footing_op_fields(items_list)
    rows = [funnel_item_to_row(item) for item in items_list]

    conn = _connect()
    try:
        cur = conn.cursor()
        columns_added = ensure_mssql_tradeinfunnel_columns(cur, table)

        delete_sql = f'DELETE FROM {table} WHERE EstimationDate >= ? AND EstimationDate <= ?'
        delete_params = [date_start, date_end]
        if unit_name:
            delete_sql += ' AND UnitName = ?'
            delete_params.append(unit_name)
        if unit_source_name:
            delete_sql += ' AND UnitSourceName = ?'
            delete_params.append(unit_source_name)

        cur.execute(delete_sql, delete_params)
        deleted = cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else 0

        placeholders = ','.join('?' for _ in INSERT_COLUMNS)
        cols = ','.join(INSERT_COLUMNS)
        insert_sql = f'INSERT INTO {table} ({cols}) VALUES ({placeholders})'

        inserted = 0
        if rows:
            # fast_executemany ускоряет bulk на MSSQL
            try:
                cur.fast_executemany = True
            except Exception:
                pass
            for offset in range(0, len(rows), chunk_size):
                chunk = rows[offset:offset + chunk_size]
                cur.executemany(insert_sql, chunk)
                inserted += len(chunk)

        conn.commit()

        filtr_parts = [
            f"{date_start.strftime('%Y-%m-%d')}…{date_end.strftime('%Y-%m-%d')}",
        ]
        if unit_name:
            filtr_parts.append(f'Unit={unit_name}')
        if unit_source_name:
            filtr_parts.append(f'Source={unit_source_name}')
        filtr = '; '.join(filtr_parts)

        try:
            from powerbi.views import add_statistic
            add_statistic('TradeInFunnel', inserted, deleted, filtr)
        except Exception:
            # История в bi_logs не должна ломать саму выгрузку
            pass

        return {
            'ok': True,
            'deleted': deleted,
            'inserted': inserted,
            'table': table,
            'server': cfg['server'],
            'database': cfg['database'],
            'filtr': filtr,
            'columns_added': columns_added,
        }
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass


def run_tradeinfunnel_mssql_sync(days: int = 60) -> dict:
    """
    Выгрузка за последние N дней от «сейчас»: DELETE периода + INSERT.
    Пишет запись в bi_logs (внутри sync_tradeinfunnel_to_mssql).
    """
    from analytics.models import TradeInFunnel

    if days < 1:
        raise ValueError('days must be >= 1')
    if not mssql_configured():
        raise RuntimeError(
            'MSSQL не настроен (MSSQL_TRADEINFUNNEL_ENABLED / SERVER / DATABASE / …)'
        )

    now = DT.datetime.now()
    date_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    date_start = (now - DT.timedelta(days=days)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    qs = TradeInFunnel.objects.filter(
        date_start_estimation__gte=date_start,
        date_start_estimation__lte=date_end,
    ).exclude(date_start_estimation__isnull=True)
    items = list(qs.order_by('date_start_estimation').iterator(chunk_size=2000))
    result = sync_tradeinfunnel_to_mssql(
        date_start=date_start,
        date_end=date_end,
        items=items,
    )
    result['days'] = days
    result['date_start'] = date_start
    result['date_end'] = date_end
    result['source_count'] = len(items)
    return result
