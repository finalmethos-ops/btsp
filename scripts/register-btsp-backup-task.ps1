[CmdletBinding()]
param(
    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$Distro = "Ubuntu",

    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$TaskName = "BTSP Production Backup",

    [Parameter()]
    [ValidatePattern("^([01]?\d|2[0-3]):[0-5]\d$")]
    [string]$At = "02:00"
)

$ErrorActionPreference = "Stop"
$repositoryWindows = Split-Path -Parent $PSScriptRoot
$driveLetter = $repositoryWindows.Substring(0, 1).ToLowerInvariant()
$repositoryLinux = "/mnt/$driveLetter" + ($repositoryWindows.Substring(2) -replace '\\', '/')
if (-not (Test-Path -LiteralPath $repositoryWindows)) {
    throw "The repository path does not exist: $repositoryWindows"
}

$logDirectory = "$repositoryLinux/.runtime/backup-logs"
$bashCommand = "mkdir -p '$logDirectory'; cd '$repositoryLinux'; ./scripts/backup-and-upload-btsp-production.sh >> '$logDirectory/nightly.log' 2>&1"
$escapedBashCommand = $bashCommand.Replace('"', '\"')
$action = New-ScheduledTaskAction `
    -Execute "wsl.exe" `
    -Argument "-d $Distro -- bash -lc `"$escapedBashCommand`""
$trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::ParseExact($At, "HH:mm", $null))
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Create, verify, and upload the encrypted BTSP production recovery bundle to private Cloudflare R2." `
    -Force | Out-Null

Write-Host "Registered '$TaskName' for $At daily under $($principal.UserId)."
Write-Host "Logs: $repositoryWindows\.runtime\backup-logs\nightly.log"
