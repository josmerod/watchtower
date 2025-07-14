# Windows Task Scheduler Setup Guide
## Automated Udemy Course Enrollment

This guide will help you set up automated Udemy course enrollment using Windows Task Scheduler.

## Prerequisites

1. **UV Package Manager** - Ensure UV is installed and available in your PATH
   ```powershell
   # Install UV if not already installed
   irm https://astral.sh/uv/install.ps1 | iex
   ```

2. **Configuration File** - Ensure your configuration file is properly set up:
   - `src/miners/udemy-universal/default-duce-cli-settings.json`

3. **Browser Cookies** - Make sure your browser cookies are accessible for authentication

## Available Scripts

### 1. Batch Script (Recommended for simplicity)
- **File**: `run_udemy_enroller.bat`
- **Features**: Simple, reliable, good error handling
- **Use when**: You want a straightforward setup

### 2. PowerShell Script (Recommended for advanced users)
- **File**: `run_udemy_enroller.ps1`
- **Features**: Advanced error handling, parameters, verbose logging
- **Use when**: You need more control and better error reporting

## Setting Up Windows Task Scheduler

### Method 1: Using Task Scheduler GUI

1. **Open Task Scheduler**
   - Press `Win + R`, type `taskschd.msc`, press Enter
   - Or search for "Task Scheduler" in Start menu

2. **Create Basic Task**
   - Click "Create Basic Task..." in the Actions panel
   - Name: `Udemy Course Enroller`
   - Description: `Automated enrollment in free Udemy courses`

3. **Set Trigger**
   - Choose "Daily" for daily enrollment
   - Set your preferred time (e.g., 9:00 AM)
   - Check "Recur every: 1 days"

4. **Set Action**
   
   **For Batch Script:**
   - Action: "Start a program"
   - Program/script: `cmd.exe`
   - Arguments: `/c "C:\path\to\watchtower\run_udemy_enroller.bat"`
   - Start in: `C:\path\to\watchtower`

   **For PowerShell Script:**
   - Action: "Start a program"
   - Program/script: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "C:\path\to\watchtower\run_udemy_enroller.ps1"`
   - Start in: `C:\path\to\watchtower`

5. **Configure Additional Settings**
   - Open the task properties after creation
   - Go to "General" tab:
     - Check "Run whether user is logged on or not"
     - Check "Run with highest privileges"
   - Go to "Settings" tab:
     - Check "Allow task to be run on demand"
     - Check "Stop the task if it runs longer than: 2 hours"
     - If task fails, restart every: 10 minutes
     - Attempt to restart up to: 3 times

### Method 2: Using PowerShell Command

Create the task using PowerShell (run as Administrator):

```powershell
# Define task parameters
$TaskName = "Udemy Course Enroller"
$TaskPath = "C:\path\to\watchtower"  # Update this path
$ScriptPath = Join-Path $TaskPath "run_udemy_enroller.bat"  # Or .ps1

# Create task action
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$ScriptPath`"" -WorkingDirectory $TaskPath

# Create task trigger (daily at 9:00 AM)
$Trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM

# Create task settings
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# Create task principal (run as system)
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# Register the task
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "Automated enrollment in free Udemy courses"
```

### Method 3: Using XML Import

Create a task definition file and import it:

```xml
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2024-01-01T09:00:00</StartBoundary>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>cmd.exe</Command>
      <Arguments>/c "C:\path\to\watchtower\run_udemy_enroller.bat"</Arguments>
      <WorkingDirectory>C:\path\to\watchtower</WorkingDirectory>
    </Exec>
  </Actions>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <RestartOnFailure>
      <Interval>PT10M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Principal>
    <UserId>S-1-5-18</UserId>
    <RunLevel>HighestAvailable</RunLevel>
  </Principal>
</Task>
```

## PowerShell Script Advanced Usage

The PowerShell script supports additional parameters:

```powershell
# Run with verbose output
.\run_udemy_enroller.ps1 -Verbose

# Run with dry-run mode (testing)
.\run_udemy_enroller.ps1 -DryRun

# Use custom configuration file
.\run_udemy_enroller.ps1 -ConfigFile "custom-settings.json"

# Combination of options
.\run_udemy_enroller.ps1 -Verbose -DryRun -ConfigFile "test-settings.json"
```

## Recommended Schedule Options

### Daily Enrollment
- **Time**: 9:00 AM (courses are often released overnight)
- **Frequency**: Every day
- **Best for**: Maximum course discovery

### Weekly Enrollment
- **Time**: Monday 9:00 AM
- **Frequency**: Every Monday
- **Best for**: Balanced approach, less frequent but still effective

### Multiple Times Per Day
- **Times**: 9:00 AM, 3:00 PM, 9:00 PM
- **Frequency**: Three times daily
- **Best for**: Catching time-sensitive deals

## Monitoring and Troubleshooting

### Log Files
- Location: `logs/udemy_enroller_YYYY-MM-DD_HH-mm-ss.log`
- Automatic cleanup: Keeps last 30 days
- Manual cleanup: Delete old files in `logs/` directory

### Task Scheduler History
1. Open Task Scheduler
2. Find your task
3. Click "History" tab
4. Review execution results

### Common Issues and Solutions

**Task not running:**
- Check if UV is in system PATH
- Verify script paths are correct
- Ensure task has proper permissions

**Script fails with UV error:**
- Reinstall UV: `irm https://astral.sh/uv/install.ps1 | iex`
- Check UV version: `uv --version`

**Authentication issues:**
- Update browser cookies
- Check configuration file settings
- Verify browser profile paths

**Network issues:**
- Ensure "Run only if network available" is checked
- Check firewall settings
- Verify internet connectivity

## Testing Your Setup

Before setting up the automated task:

1. **Test manually:**
   ```cmd
   # From watchtower directory
   run_udemy_enroller.bat
   ```

2. **Test with PowerShell:**
   ```powershell
   # From watchtower directory
   .\run_udemy_enroller.ps1 -DryRun -Verbose
   ```

3. **Test task scheduler:**
   - Create task with immediate trigger
   - Run once to verify it works
   - Then update to your desired schedule

## Security Considerations

1. **Permissions**: Run with lowest required privileges
2. **Paths**: Use full paths to avoid security issues
3. **Logging**: Monitor logs for suspicious activity
4. **Updates**: Keep UV and dependencies updated

## Performance Tips

1. **Timing**: Avoid peak hours (12-2 PM) for better performance
2. **Frequency**: Don't run too frequently (minimum 6-hour intervals)
3. **Resources**: Monitor CPU and memory usage
4. **Cleanup**: Regularly clean up old logs and data

## Support and Maintenance

- **Update checking**: The script includes automatic update checking
- **Log rotation**: Automatic cleanup of old log files
- **Error recovery**: Built-in retry mechanisms
- **Statistics**: Enrollment statistics are logged and reported

## Example Task Scheduler Entry

Here's what your task should look like in Task Scheduler:

```
Name: Udemy Course Enroller
Location: \
Author: Your Name
Description: Automated enrollment in free Udemy courses
Triggers: Daily at 9:00 AM
Actions: Start cmd.exe with arguments /c "C:\path\to\watchtower\run_udemy_enroller.bat"
Settings: 
  - Run whether user is logged on or not
  - Run with highest privileges
  - Allow task to be run on demand
  - Stop if runs longer than 2 hours
  - Restart on failure every 10 minutes (3 attempts)
```

This setup will ensure reliable, automated course enrollment with proper error handling and logging. 