# Restore backup into target database (for test).

param(
    [Parameter(Mandatory = $true)]
    [string]$DumpFile,

    [Parameter(Mandatory = $true)]
    [string]$TargetDb,

    [string]$DbHost = "127.0.0.1",
    [string]$DbPort = "5432",
    [string]$DbUser = "postgres",
    [switch]$Clean
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
    throw "Set DbPassword in backup_postgres_config.ps1"
}
if (-not (Test-Path $DumpFile)) {
    throw ("Dump file not found: {0}" -f $DumpFile)
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

    $searchRoots = @(
        "D:\programm\postgres13\13",
        "C:\Program Files\PostgreSQL"
    )

    foreach ($root in $searchRoots) {
        if (-not (Test-Path $root)) {
            continue
        }

        $directBin = Join-Path $root ("bin\{0}.exe" -f $Name)
        if (Test-Path $directBin) {
            return $directBin
        }

        $installs = Get-ChildItem $root -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending
        foreach ($install in $installs) {
            $candidate = Join-Path $install.FullName ("bin\{0}.exe" -f $Name)
            if (Test-Path $candidate) {
                return $candidate
            }
        }
    }

    throw ("{0} not found. Set PgBinDir in backup_postgres_config.ps1" -f $Name)
}

$env:PGPASSWORD = $DbPassword
try {
    $createdb = Find-PgExecutable "createdb"
    $pgRestore = Find-PgExecutable "pg_restore"
    $psql = Find-PgExecutable "psql"

    $dbExists = & $psql -h $DbHost -p $DbPort -U $DbUser -d postgres -tAc ("SELECT 1 FROM pg_database WHERE datname='{0}'" -f $TargetDb)
    if ($dbExists -ne "1") {
        Write-Host ("Creating database {0}" -f $TargetDb)
        & $createdb -h $DbHost -p $DbPort -U $DbUser $TargetDb
    }

    $restoreArgs = @(
        "-h", $DbHost,
        "-p", $DbPort,
        "-U", $DbUser,
        "-d", $TargetDb,
        $DumpFile
    )
    if ($Clean) {
        $restoreArgs = @("-c") + $restoreArgs
    }

    Write-Host ("Restore {0} -> {1}" -f $DumpFile, $TargetDb)
    & $pgRestore @restoreArgs
    if ($LASTEXITCODE -ne 0) {
        throw ("pg_restore failed with exit code {0}" -f $LASTEXITCODE)
    }
    Write-Host "Done"
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
