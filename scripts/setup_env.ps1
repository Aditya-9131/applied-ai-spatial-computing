$pythonDir = "C:\Users\HP\python311"
$scriptsDir = "C:\Users\HP\python311\Scripts"

# Add to user PATH
$regPath = "HKCU:\Environment"
$currentPath = (Get-ItemProperty -Path $regPath -Name PATH -ErrorAction SilentlyContinue).PATH
if (-not $currentPath) {
    $currentPath = ""
}

if ($currentPath -notlike "*$pythonDir*") {
    $updatedPath = "$pythonDir;$scriptsDir;$currentPath"
    Set-ItemProperty -Path $regPath -Name PATH -Value $updatedPath
    Write-Host "Updated HKCU User PATH"
}

# Add python.ps1 and pip.ps1 wrappers in workspace for immediate PowerShell invocation
$pyScript = @"
& "C:\Users\HP\python311\python.exe" `$args
"@
Set-Content -Path "$PSScriptRoot\..\python.ps1" -Value $pyScript -Force

$pipScript = @"
& "C:\Users\HP\python311\Scripts\pip.exe" `$args
"@
Set-Content -Path "$PSScriptRoot\..\pip.ps1" -Value $pipScript -Force

Write-Host "Wrappers python.ps1 and pip.ps1 created in workspace root"
