# Create Desktop Shortcut
# Right-click this file and select "Run with PowerShell"

$shortcutName = "AI Teaching Assistant"
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$targetPath = Join-Path $currentDir "启动AI教学助手.bat"
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutFile = Join-Path $desktopPath "$shortcutName.lnk"

# Create shortcut
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutFile)
$shortcut.TargetPath = $targetPath
$shortcut.WorkingDirectory = $currentDir
$shortcut.IconLocation = "%SystemRoot%\System32\imageres.dll,5"
$shortcut.Description = "AI Teaching Assistant"
$shortcut.Save()

Write-Host "Shortcut created successfully!" -ForegroundColor Green
Write-Host "Location: $shortcutFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "Double-click the shortcut on your desktop to start the app" -ForegroundColor Yellow
Write-Host ""
pause
