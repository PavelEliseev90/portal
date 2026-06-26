# Daily PostgreSQL backup for portal.
# Task Scheduler: backup_postgres.bat (e.g. 02:00 daily)

$ErrorActionPreference = "Stop"

$ScriptDir     = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackupDir     = "E:\buck_up"
$LogDir        = Join-Path $BackupDir "logs"
$RetentionDays = 30

$DbHost = "127.0.0.1"
$DbPort = "5432"
$DbName = "postgres"
$DbUser = "postgres"
$PgBinDir = "D:\programm\postgres13\13\bin"

$configPath = Join-Path $ScriptDir "backup_postgres_config.ps1"
if (Test-Path $configPath) {
    . $configPath
}

if (-not $DbPassword -and $env:PORTAL_DB_PASSWORD) {
    $DbPassword = $env:PORTAL_DB_PASSWORD
}

function Write-Log {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $line
    if ($script:LogFile) {
        Add-Content -Path $script:LogFile -Value $line -Encoding ASCII
    }
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

try {
    if (-not $DbPassword) {
        throw "Set DbPassword in backup_postgres_config.ps1 (copy from .example)"
    }

    if (-not (Test-Path $BackupDir)) {
        New-Item -ItemType Directory -Path $BackupDir | Out-Null
    }
    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir | Out-Null
    }

    $script:LogFile = Join-Path $LogDir ("backup_{0}.log" -f (Get-Date -Format "yyyyMMdd"))
    $stamp = Get-Date -Format "yyyyMMdd"
    $outFile = Join-Path $BackupDir ("portal_{0}.dump" -f $stamp)
    $pgDump = Find-PgExecutable "pg_dump"

    Write-Log ("Start backup {0} -> {1}" -f $DbName, $outFile)
    $env:PGPASSWORD = $DbPassword

    & $pgDump `
        -h $DbHost `
        -p $DbPort `
        -U $DbUser `
        -d $DbName `
        -F c `
        -f $outFile `
        --no-owner `
        --no-acl

    if ($LASTEXITCODE -ne 0) {
        throw ("pg_dump failed with exit code {0}" -f $LASTEXITCODE)
    }

    $sizeMb = [math]::Round((Get-Item $outFile).Length / 1MB, 2)
    Write-Log ("Done: {0} ({1} MB)" -f $outFile, $sizeMb)

    $cutoff = (Get-Date).AddDays(-$RetentionDays)
    $removed = Get-ChildItem $BackupDir -Filter "portal_*.dump" |
        Where-Object { $_.LastWriteTime -lt $cutoff }

    foreach ($old in $removed) {
        Remove-Item $old.FullName -Force
        Write-Log ("Removed old backup: {0}" -f $old.Name)
    }

    $oldLogs = Get-ChildItem $LogDir -Filter "backup_*.log" |
        Where-Object { $_.LastWriteTime -lt $cutoff }

    foreach ($oldLog in $oldLogs) {
        Remove-Item $oldLog.FullName -Force
    }

    exit 0
}
catch {
    Write-Log ("ERROR: {0}" -f $_.Exception.Message)
    exit 1
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
