[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$TaskName = "HiveGreatSage-PCControl-Watchdog"
)

$ErrorActionPreference = "Stop"

$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $Task) {
    Write-Host "Scheduled task not found: $TaskName"
    return
}

if ($PSCmdlet.ShouldProcess($TaskName, "Unregister scheduled task")) {
    try {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    } catch {
        Write-Verbose "Stop-ScheduledTask ignored: $_"
    }

    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Scheduled task uninstalled: $TaskName"
}
