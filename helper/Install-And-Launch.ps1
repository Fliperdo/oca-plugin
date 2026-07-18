# Installs/updates the plugin, then launches GIMP and (optionally) opens a file
[CmdletBinding()]
param(
    [string]$FileToOpen = "C:\Users\clift\OneDrive\Desktop\Original.oca",
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'

# Resolve helper script paths relative to this script
$scriptRoot = $PSScriptRoot
$installScript = Join-Path $scriptRoot 'install-and-update.ps1'
$launchScript  = Join-Path $scriptRoot 'Launch-GIMP.ps1'

Write-Host "[Install-And-Launch] Starting..." -ForegroundColor Cyan
Write-Host "[Install-And-Launch] Script root: $scriptRoot"

# 1) Run install/update unless skipped
if (-not $SkipInstall) {
    if (Test-Path -LiteralPath $installScript) {
        Write-Host "[Install-And-Launch] Running installer: $installScript" -ForegroundColor Yellow
        & $installScript @args
        if ($LASTEXITCODE -ne $null -and $LASTEXITCODE -ne 0) {
            Write-Host "[Install-And-Launch] Installer exited with code $LASTEXITCODE" -ForegroundColor Red
            exit $LASTEXITCODE
        }
    } else {
        Write-Host "[Install-And-Launch] WARNING: Installer not found at $installScript" -ForegroundColor Red
    }
} else {
    Write-Host "[Install-And-Launch] Skipping install per flag" -ForegroundColor DarkYellow
}

# 2) Launch GIMP via Launch-GIMP.ps1, passing the file to open if present
if (-not (Test-Path -LiteralPath $launchScript)) {
    Write-Host "[Install-And-Launch] ERROR: Launch script not found at $launchScript" -ForegroundColor Red
    exit 1
}

Write-Host "[Install-And-Launch] Launching GIMP..." -ForegroundColor Green
# Pass the FileToOpen parameter explicitly and forward any extra args
& $launchScript -FileToOpen $FileToOpen @args

# Propagate exit code from child if provided
if ($LASTEXITCODE -ne $null) { exit $LASTEXITCODE } else { exit 0 }
