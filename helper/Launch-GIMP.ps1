# Launch GIMP 3.2
# This script starts GIMP 3.2.4 installed on this system and optionally opens a file on startup.

param(
    [string]$FileToOpen = "C:\Users\clift\OneDrive\Desktop\SunnyDay.oca"
)

$gimpPath = "C:\Users\clift\AppData\Local\Programs\GIMP 3\bin\gimp-3.exe"

if (-not (Test-Path $gimpPath)) {
    Write-Host "Error: GIMP executable not found at $gimpPath"
    Write-Host "Please verify GIMP 3.2 is installed."
    exit 1
}

# Build argument list
$argList = @("--debug-handlers")

# If a file path is provided and exists, pass it to GIMP to open on startup
if ($FileToOpen -and (Test-Path -LiteralPath $FileToOpen)) {
    Write-Host "Launching GIMP 3.2 with verbose logging and opening file: $FileToOpen"
    $argList += $FileToOpen
} else {
    Write-Host "Launching GIMP 3.2 with verbose logging..."
    if ($FileToOpen) {
        Write-Host "Warning: File not found, not passing to GIMP: $FileToOpen"
    }
}

# Also pass through any extra arguments provided by the caller
if ($args.Count -gt 0) {
    $argList += $args
}

# Launch GIMP
& $gimpPath @argList
