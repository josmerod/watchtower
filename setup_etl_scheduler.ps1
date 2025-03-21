$action = New-ScheduledTaskAction -Execute "C:\Windows\System32\cmd.exe" -Argument "/c $PSScriptRoot\run_all_etl.bat"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 3)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Create and register the task (run as current user)
Register-ScheduledTask -TaskName "WatchtowerETL" -Action $action -Trigger $trigger -Settings $settings -Description "Runs all ETL processes every 3 hours"

Write-Host "Scheduled task 'WatchtowerETL' created successfully."
Write-Host "The ETL scripts will run every 3 hours." 