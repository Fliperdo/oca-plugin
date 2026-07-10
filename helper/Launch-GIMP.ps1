# Launch GIMP 3.2
# This script starts GIMP 3.2.4 installed on this system

$gimpPath = "C:\Users\clift\AppData\Local\Programs\GIMP 3\bin\gimp-3.exe"

if (-not (Test-Path $gimpPath)) {
    Write-Host "Error: GIMP executable not found at $gimpPath"
    Write-Host "Please verify GIMP 3.2 is installed."
    exit 1
}

Write-Host "Launching GIMP 3.2 with verbose logging..."
# Add verbose flags for debugging: --verbose shows more info, --debug-handlers shows procedure calls
& $gimpPath --debug-handlers @args
