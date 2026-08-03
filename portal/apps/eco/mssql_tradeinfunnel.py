"""Синхронизация TradeInFunnel → MSSQL (очистка периода + вставка)."""

from __future__ import annotations

import datetime as DT
from typing import Iterable, Optional


def mssql_config() -> dict:
    from django.conf import settings
    cfg = getattr(settings, 'MSSQL_TRADEINFUNNEL', None) or {}
    return {
        'enabled': bool(cfg.get('enabled')),
        'driver': cfg.get('driver') or 'ODBC Driver 17 for SQL Server',
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
    parts = [
        f"DRIVER={{{cfg['driver']}}}",
        f"SERVER={cfg['server']}",
        f"DATABASE={cfg['database']}",
        f"Encrypt={cfg['encrypt']}",
        f"TrustServerCertificate={cfg['trust_server_certificate']}",
    ]
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


def funnel_item_to_row(item) -> tuple:
    """Кортеж значений под INSERT в dbo.TradeInFunnel (латинские колонки)."""
    est_dt = _safe_dt(item.date_start_estimation)
    rlk_dt = _safe_dt(item.date_rlk)
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
    'Accepted',
    'Stage',
    'CostPreparation',
    'CostMcu',
    'CostSs',
    'PriceBeforeKd',
    'PriceAfterKd',
    'MarketPriceRub',
)


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
    1) DELETE по EstimationDate в периоде (+ опционально UnitName / UnitSourceName)
    2) INSERT строк из items
    """
    cfg = mssql_config()
    table = cfg['table']
    rows = [funnel_item_to_row(item) for item in items]

    conn = _connect()
    try:
        cur = conn.cursor()
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
        return {
            'ok': True,
            'deleted': deleted,
            'inserted': inserted,
            'table': table,
            'server': cfg['server'],
            'database': cfg['database'],
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
