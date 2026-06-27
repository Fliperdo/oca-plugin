# Install and Update OCA Plugin for GIMP

$src = "C:\Users\clift\IdeaProjects\oca-plugin\oca-plugin"
$dst = "C:\Users\clift\AppData\Roaming\GIMP\3.2\plug-ins\oca-plugin"

if (-not (Test-Path $src)) {
    Write-Host "ERROR: Source not found at $src" -ForegroundColor Red
    exit 1
}

if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
Copy-Item $src $dst -Recurse -Force

Write-Host "Done! Restart GIMP to load the plugin." -ForegroundColor Green
