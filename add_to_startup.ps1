$scriptDir = $PSScriptRoot
$batFilePath = Join-Path $scriptDir "run_streamlit.bat"  # Updated to match actual bat file name
$shortcutPath = Join-Path ([Environment]::GetFolderPath("Startup")) "WatchtowerStreamlit.lnk"

# Create startup shortcut
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = $batFilePath
$Shortcut.WorkingDirectory = $scriptDir
$Shortcut.Description = "Watchtower Streamlit App"
$Shortcut.Save()

Write-Host "✅ Shortcut created in Windows Startup folder"
Write-Host "📊 App will auto-start on login: http://localhost:8501"