$scriptDir = $PSScriptRoot
$batFilePath = Join-Path $scriptDir "start_streamlit.bat"
$shortcutPath = [System.IO.Path]::Combine([Environment]::GetFolderPath("Startup"), "WatchtowerStreamlit.lnk")

# Create a shortcut in the Windows Startup folder
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = $batFilePath
$Shortcut.WorkingDirectory = $scriptDir
$Shortcut.Description = "Start Watchtower Streamlit App"
$Shortcut.Save()

Write-Host "Shortcut created in Windows Startup folder."
Write-Host "Watchtower Streamlit app will start automatically when you log in to Windows."
Write-Host "You can access it at: http://localhost:8501" 