# Диагностика PostgreSQL: долгие и тяжёлые запросы (портал).
# Использование:
#   .\pg_query_diagnostics.ps1
#   .\pg_query_diagnostics.ps1 -DbName postgres -Top 30
#   .\pg_query_diagnostics.ps1 -EnablePgStatStatements

param(
    [string]$DbHost = "127.0.0.1",
    [string]$DbPort = "5432",
    [string]$DbUser = "postgres",
    [string]$DbName = "postgres",
    [int]$Top = 20,
    [switch]$EnablePgStatStatements,
    [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PgBinDir = "D:\programm\postgres13\13\bin"

$configPath = Join-Path $ScriptDir "backup_postgres_config.ps1"
if (Test-Path $configPath) {
    . $configPath
}
if (-not $DbPassword -and $env:PORTAL_DB_PASSWORD) {
    $DbPassword = $env:PORTAL_DB_PASSWORD
}
if (-not $DbPassword) {
    throw "Set DbPassword in backup_postgres_config.ps1 or env PORTAL_DB_PASSWORD"
}

function Find-PgExecutable {
    param([string]$Name)

    if ($PgBinDir) {
        $fromConfig = Join-Path $PgBinDir ("{0}.exe" -f $Name)
        if (Test-Path $fromConfig) {
            return $fromConfig
        }
    }

    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    throw ("{0} not found. Set PgBinDir in backup_postgres_config.ps1" -f $Name)
}

function Invoke-PgQuery {
    param(
        [string]$Title,
        [string]$Sql
    )

    $line = ("`n{0}`n{1}`n" -f ("=" * 60), $Title)
    if ($OutFile) {
        Add-Content -Path $OutFile -Value $line -Encoding UTF8
    }
    Write-Host $line -ForegroundColor Cyan

    $psql = Find-PgExecutable "psql"
    $output = & $psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -X -q -c $Sql 2>&1
    $text = ($output | Out-String).TrimEnd()
    if ($OutFile) {
        Add-Content -Path $OutFile -Value $text -Encoding UTF8
    }
    Write-Host $text
}

$env:PGPASSWORD = $DbPassword
try {
    if ($OutFile) {
        $header = "pg_query_diagnostics {0} DB={1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $DbName
        Set-Content -Path $OutFile -Value $header -Encoding UTF8
    }

    Invoke-PgQuery -Title "Подключения" -Sql @"
SELECT (SELECT count(*) FROM pg_stat_activity) AS connections,
       (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_connections;
"@

    Invoke-PgQuery -Title "Сейчас выполняются (не idle)" -Sql @"
SELECT pid, usename, datname, state, wait_event_type, wait_event,
       now() - query_start AS duration,
       left(query, 150) AS query
FROM pg_stat_activity
WHERE pid <> pg_backend_pid()
  AND state <> 'idle'
ORDER BY query_start NULLS LAST
LIMIT $Top;
"@

    Invoke-PgQuery -Title "Idle in transaction (висят транзакции)" -Sql @"
SELECT pid, datname, now() - state_change AS idle_age,
       left(query, 150) AS last_query
FROM pg_stat_activity
WHERE state = 'idle in transaction'
ORDER BY state_change
LIMIT $Top;
"@

    Invoke-PgQuery -Title "Накопленный temp по базам" -Sql @"
SELECT datname, numbackends, temp_files,
       pg_size_pretty(temp_bytes) AS temp_total
FROM pg_stat_database
WHERE datname IS NOT NULL
ORDER BY temp_bytes DESC;
"@

    Invoke-PgQuery -Title "Таблицы: много sequential scan" -Sql @"
SELECT schemaname, relname AS table_name,
       seq_scan, seq_tup_read, idx_scan, n_live_tup,
       pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_tup_read DESC
LIMIT $Top;
"@

    Invoke-PgQuery -Title "Блокировки" -Sql @"
SELECT blocked.pid AS blocked_pid,
       left(blocked.query, 80) AS blocked_query,
       blocking.pid AS blocking_pid,
       left(blocking.query, 80) AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
  ON blocking.pid = ANY (pg_blocking_pids(blocked.pid))
WHERE blocked.pid <> pg_backend_pid();
"@

    $extCheck = & (Find-PgExecutable "psql") -h $DbHost -p $DbPort -U $DbUser -d $DbName -X -tAc `
        "SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements';"

    if ($extCheck -ne "1") {
        Write-Host "`npg_stat_statements НЕ установлен — истории запросов нет." -ForegroundColor Yellow
        Write-Host "Включить (от суперпользователя, затем перезапуск PostgreSQL):" -ForegroundColor Yellow
        Write-Host @"

-- postgresql.conf:
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.track = all
pg_stat_statements.max = 10000

-- после перезапуска:
CREATE EXTENSION pg_stat_statements;

"@ -ForegroundColor DarkGray

        if ($EnablePgStatStatements) {
            Write-Host "Попытка CREATE EXTENSION (без preload может не сработать)..." -ForegroundColor Yellow
            & (Find-PgExecutable "psql") -h $DbHost -p $DbPort -U $DbUser -d $DbName -c `
                "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
        }
    }
    else {
        $psql = Find-PgExecutable "psql"
        $verNum = [int](& $psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -X -tAc "SHOW server_version_num;")
        if ($verNum -ge 140000) {
            $colTotal = "total_exec_time"
            $colMean = "mean_exec_time"
            $colMax = "max_exec_time"
        }
        else {
            $colTotal = "total_time"
            $colMean = "mean_time"
            $colMax = "max_time"
        }
        Write-Host ("pg_stat_statements: {0}, {1}, {2} (server_version_num={3})" -f $colTotal, $colMean, $colMax, $verNum) -ForegroundColor DarkGray

        Invoke-PgQuery -Title "ТОП по среднему времени (pg_stat_statements)" -Sql @"
SELECT calls,
       round($colTotal::numeric, 2) AS total_ms,
       round($colMean::numeric, 2) AS mean_ms,
       round($colMax::numeric, 2) AS max_ms,
       rows, temp_blks_written,
       left(query, 150) AS query
FROM pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
ORDER BY $colMean DESC
LIMIT $Top;
"@

        Invoke-PgQuery -Title "ТОП по суммарному времени (pg_stat_statements)" -Sql @"
SELECT calls,
       round($colTotal::numeric, 2) AS total_ms,
       round($colMean::numeric, 2) AS mean_ms,
       temp_blks_written,
       left(query, 150) AS query
FROM pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
ORDER BY $colTotal DESC
LIMIT $Top;
"@

        Invoke-PgQuery -Title "ТОП по записи во temp (pg_stat_statements)" -Sql @"
SELECT calls,
       temp_blks_written,
       pg_size_pretty(temp_blks_written::bigint * 8192) AS temp_written,
       round($colMean::numeric, 2) AS mean_ms,
       left(query, 150) AS query
FROM pg_stat_statements
WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
  AND temp_blks_written > 0
ORDER BY temp_blks_written DESC
LIMIT $Top;
"@
    }

    if ($OutFile) {
        Write-Host "`nОтчёт сохранён: $OutFile" -ForegroundColor Green
    }
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
