[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$TaskName = "HiveGreatSage-PCControl-Watchdog",
    [string]$PythonExe = "",
    [switch]$RunNow
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$WatchdogScript = Join-Path $RepoRoot "scripts\pccontrol_watchdog.py"

if (-not (Test-Path -LiteralPath $WatchdogScript)) {
    throw "Watchdog script not found: $WatchdogScript"
}

function Resolve-PythonExe {
    param([string]$Preferred)

    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($Preferred)) {
        $candidates += $Preferred
    }
    $candidates += "D:\ProgramData\anaconda3\envs\TZYMIR\pythonw.exe"
    $candidates += "D:\ProgramData\anaconda3\envs\TZYMIR\python.exe"

    foreach ($commandName in @("pythonw.exe", "python.exe")) {
        $cmd = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source) {
            $candidates += $cmd.Source
        }
    }

    foreach ($item in $candidates) {
        if ([string]::IsNullOrWhiteSpace($item)) {
            continue
        }
        if (Test-Path -LiteralPath $item) {
            return (Resolve-Path -LiteralPath $item).Path
        }
        $found = Get-Command $item -ErrorAction SilentlyContinue
        if ($found -and $found.Source) {
            return $found.Source
        }
    }

    throw "Python executable not found. Pass -PythonExe with the TZYMIR python path."
}

$ResolvedPython = Resolve-PythonExe -Preferred $PythonExe
$UserId = if ($env:USERDOMAIN) { "$env:USERDOMAIN\$env:USERNAME" } else { $env:USERNAME }

$Action = New-ScheduledTaskAction `
    -Execute $ResolvedPython `
    -Argument ('"{0}"' -f $WatchdogScript) `
    -WorkingDirectory $RepoRoot

$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $UserId
$Principal = New-ScheduledTaskPrincipal `
    -UserId $UserId `
    -LogonType Interactive `
    -RunLevel Limited

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew

$Description = "Starts HiveGreatSage PCControl watchdog at user logon. The watchdog launches main.py and restarts it after abnormal exit when runtime.restart_on_crash is enabled."

if ($PSCmdlet.ShouldProcess($TaskName, "Register scheduled task")) {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Principal $Principal `
        -Settings $Settings `
        -Description $Description `
        -Force | Out-Null

    Write-Host "Scheduled task installed: $TaskName"
    Write-Host "User: $UserId"
    Write-Host "Python: $ResolvedPython"
    Write-Host "Watchdog: $WatchdogScript"

    if ($RunNow) {
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "Scheduled task started: $TaskName"
    }
}
