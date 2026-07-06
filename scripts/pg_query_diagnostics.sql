-- Диагностика PostgreSQL: долгие и тяжёлые запросы
-- PostgreSQL 14+: total_exec_time, mean_exec_time, max_exec_time
-- PostgreSQL 13:  total_time, mean_time, max_time (замените в блоках 3–5)
-- Запуск: psql -f pg_query_diagnostics.sql
-- или вставить блоки в pgAdmin → Query Tool
\echo '========== 1. Сейчас выполняются (не idle) =========='
SELECT pid,
       usename,
       datname,
       state,
       wait_event_type,
       wait_event,
       now() - query_start AS duration,
       now() - xact_start AS xact_age,
       left(query, 200) AS query
FROM pg_stat_activity
WHERE pid <> pg_backend_pid()
  AND state <> 'idle'
ORDER BY query_start NULLS LAST;

\echo '========== 2. Долгие idle in transaction (опасно) =========='
SELECT pid,
       datname,
       now() - state_change AS idle_in_tx_age,
       left(query, 200) AS last_query
FROM pg_stat_activity
WHERE state = 'idle in transaction'
ORDER BY state_change;

\echo '========== 3. pg_stat_statements — топ по среднему времени =========='
\echo '(нужно расширение pg_stat_statements)'
SELECT calls,
       round(total_exec_time::numeric, 2) AS total_ms,
       round(mean_exec_time::numeric, 2) AS mean_ms,
       round(max_exec_time::numeric, 2) AS max_ms,       rows,
       shared_blks_read,
       shared_blks_hit,
       temp_blks_written,
       left(query, 180) AS query
FROM pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
ORDER BY mean_exec_time DESC
LIMIT 25;

\echo '========== 4. pg_stat_statements — топ по суммарному времени =========='
SELECT calls,
       round(total_exec_time::numeric, 2) AS total_ms,
       round(mean_exec_time::numeric, 2) AS mean_ms,       rows,
       temp_blks_written,
       left(query, 180) AS query
FROM pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
ORDER BY total_exec_time DESC
LIMIT 25;

\echo '========== 5. pg_stat_statements — больше всего temp на диск =========='
SELECT calls,
       temp_blks_written,
       pg_size_pretty(temp_blks_written::bigint * 8192) AS temp_written,
       round(mean_exec_time::numeric, 2) AS mean_ms,
       left(query, 180) AS query
FROM pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
  AND temp_blks_written > 0
ORDER BY temp_blks_written DESC
LIMIT 25;

\echo '========== 6. Таблицы: много seq scan (кандидаты на индекс) =========='
SELECT schemaname,
       relname AS table_name,
       seq_scan,
       seq_tup_read,
       idx_scan,
       n_live_tup,
       pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_stat_user_tables
WHERE seq_scan > 100
ORDER BY seq_tup_read DESC
LIMIT 30;

\echo '========== 7. Накопленный temp по базам =========='
SELECT datname,
       numbackends,
       temp_files,
       pg_size_pretty(temp_bytes) AS temp_total
FROM pg_stat_database
WHERE datname IS NOT NULL
ORDER BY temp_bytes DESC;

\echo '========== 8. Блокировки =========='
SELECT blocked.pid AS blocked_pid,
       left(blocked.query, 80) AS blocked_query,
       blocking.pid AS blocking_pid,
       left(blocking.query, 80) AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
  ON blocking.pid = ANY (pg_blocking_pids(blocked.pid))
WHERE blocked.pid <> pg_backend_pid();
