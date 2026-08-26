<#
.SYNOPSIS
    Installs a Windows Scheduled Task that runs the LLM speed benchmark
    every 3 hours for 24 hours, once every 8 days, using 250 max_tokens.

.DESCRIPTION
    This removes the is-tempo Docker container from the trigger path for the
    speed benchmark. It creates one scheduled task with eight daily triggers
    (repeating every 8 days at 00:00, 03:00, 06:00, 09:00, 12:00, 15:00,
    18:00, 21:00 UTC) and a single action that runs one round.

    If the script is run from an Administrator PowerShell, the task runs as
    SYSTEM and works whether or not anyone is logged on. If not, it runs as
    the current user and only when the user is logged on.
#>

$ErrorActionPreference = "Stop"

$repoDir = "C:\Repos\LLM-Bench-Data"
$scriptPath = Join-Path $repoDir "scripts\speed-weekly.py"

$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) {
    $uv = "$env:USERPROFILE\.local\bin\uv.exe"
}
if (-not (Test-Path $uv)) {
    throw "Could not find uv.exe. Please install uv or ensure it is on PATH."
}

$action = New-ScheduledTaskAction `
    -Execute $uv `
    -Argument "run python `"$scriptPath`" --rounds 1 --no-wait --max-tokens 250 --resume" `
    -WorkingDirectory $repoDir

$base = Get-Date -Year 2026 -Month 8 -Day 31 -Hour 0 -Minute 0 -Second 0 -Millisecond 0
$triggers = @(0, 3, 6, 9, 12, 15, 18, 21) | ForEach-Object {
    $at = $base.AddHours($_)
    New-ScheduledTaskTrigger -Daily -DaysInterval 8 -At $at
}

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($isAdmin) {
    $principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    $logonNote = "running as SYSTEM"
} else {
    $userId = "$env:USERDOMAIN\$env:USERNAME"
    $principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive
    $logonNote = "running as $userId (interactive logon only)"
}

$task = New-ScheduledTask `
    -Action $action `
    -Trigger $triggers `
    -Settings $settings `
    -Description "Clock Lobster weekly LLM speed benchmark: 8 rounds/day, 250 tokens, every 8 days" `
    -Principal $principal

Register-ScheduledTask -InputObject $task -TaskName "ClockLobster-Speed-Weekly" -Force | Out-Null

Write-Host "Scheduled task 'ClockLobster-Speed-Weekly' installed."
Write-Host "Task has $($triggers.Count) triggers, first snapshot starts at $base UTC, repeats every 8 days."
Write-Host "The task is configured as: $logonNote."
