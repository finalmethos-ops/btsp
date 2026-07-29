[CmdletBinding()]
param(
    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$InterfaceAlias = "Ethernet 2",

    [Parameter()]
    [ValidateRange(1, 65535)]
    [int[]]$Ports = @(18080, 18443),

    [Parameter()]
    [ValidatePattern(
        "^(10\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\/\d{1,2}|192\.168\.\d{1,3}\.\d{1,3}\/\d{1,2})$"
    )]
    [string]$RemoteSubnet = "192.168.0.0/24"
)

$ErrorActionPreference = "Stop"
$ruleName = "BTSP Intranet"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
$isAdministrator = $principal.IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)

if (-not $isAdministrator) {
    throw "Run this script from an elevated PowerShell session."
}

$profile = Get-NetConnectionProfile -InterfaceAlias $InterfaceAlias
if ($profile.IPv4Connectivity -eq "Disconnected") {
    throw "The selected network adapter is disconnected: $InterfaceAlias"
}

$existingRule = Get-NetFirewallRule `
    -DisplayName "$ruleName*" `
    -ErrorAction SilentlyContinue
if ($existingRule) {
    $existingRule | Remove-NetFirewallRule
}

New-NetFirewallRule `
    -DisplayName $ruleName `
    -Description "Allow BTSP only from the trusted private intranet subnet." `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort $Ports `
    -RemoteAddress $RemoteSubnet `
    -Profile Private | Out-Null

Set-NetConnectionProfile `
    -InterfaceAlias $InterfaceAlias `
    -NetworkCategory Private

Set-NetFirewallProfile -Profile Domain, Private, Public -Enabled True

$appliedProfile = Get-NetConnectionProfile -InterfaceAlias $InterfaceAlias
$appliedRule = Get-NetFirewallRule -DisplayName $ruleName
$portFilter = $appliedRule | Get-NetFirewallPortFilter
$addressFilter = $appliedRule | Get-NetFirewallAddressFilter

[pscustomobject]@{
    InterfaceAlias = $appliedProfile.InterfaceAlias
    NetworkCategory = $appliedProfile.NetworkCategory
    FirewallEnabled = (
        (Get-NetFirewallProfile | Where-Object Enabled).Count -eq 3
    )
    Rule = $appliedRule.DisplayName
    Action = $appliedRule.Action
    Profile = $appliedRule.Profile
    Protocol = $portFilter.Protocol
    LocalPort = $portFilter.LocalPort
    RemoteAddress = $addressFilter.RemoteAddress
} | Format-List
