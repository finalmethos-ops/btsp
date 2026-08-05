[CmdletBinding()]
param(
    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$Distro = "Ubuntu",

    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$TaskName = "BTSP Production Monitor",

    [Parameter()]
    [ValidateRange(1, 60)]
    [int]$EveryMinutes = 5
)

$ErrorActionPreference = "Stop"
$repositoryWindows = Split-Path -Parent $PSScriptRoot
$driveLetter = $repositoryWindows.Substring(0, 1).ToLowerInvariant()
$repositoryLinux = "/mnt/$driveLetter" + ($repositoryWindows.Substring(2) -replace '\\', '/')
if (-not (Test-Path -LiteralPath $repositoryWindows)) {
    throw "The repository path does not exist: $repositoryWindows"
}

$logDirectory = "$repositoryLinux/.runtime/monitoring"
$bashCommand = "mkdir -p '$logDirectory'; cd '$repositoryLinux'; ./scripts/monitor-btsp-production.sh >> '$logDirectory/watchdog.log' 2>&1"
$launcherDirectory = Join-Path $repositoryWindows ".runtime\task-launchers"
$launcherPath = Join-Path $launcherDirectory "btsp-production-monitor.vbs"
New-Item -ItemType Directory -Path $launcherDirectory -Force | Out-Null
$wslCommand = "wsl.exe -d $Distro -- bash -lc `"$bashCommand`""
$vbsCommand = $wslCommand.Replace('"', '""')
@"
Set shell = CreateObject("WScript.Shell")
exitCode = shell.Run("$vbsCommand", 0, True)
WScript.Quit exitCode
"@ | Set-Content -LiteralPath $launcherPath -Encoding ASCII
$action = New-ScheduledTaskAction `
    -Execute "$env:SystemRoot\System32\wscript.exe" `
    -Argument "//B //NoLogo `"$launcherPath`""
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $EveryMinutes)
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 4) `
    -MultipleInstances IgnoreNew `
    -Hidden
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
    -Description "Check BTSP public health, containers, storage, backups, and recent server errors." `
    -Force | Out-Null

Write-Host "Registered '$TaskName' to run every $EveryMinutes minute(s) under $($principal.UserId)."
Write-Host "Events: $repositoryWindows\.runtime\monitoring\events.jsonl"
Write-Host "Task output: $repositoryWindows\.runtime\monitoring\watchdog.log"
