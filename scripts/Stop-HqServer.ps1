[CmdletBinding(SupportsShouldProcess)]
param()

$ErrorActionPreference = "Stop"
$pidFile = "F:\AI\MangaLens\server\pids.json"
if (-not (Test-Path -LiteralPath $pidFile -PathType Leaf)) {
    Write-Host "ไม่พบรายการ process ของ MangaLens HQ"
    exit 0
}

$owned = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
$roots = @($owned.gateway, $owned.mit, $owned.ollama) | Where-Object { $_ -is [int] -or $_ -is [long] }
$allProcesses = Get-CimInstance Win32_Process

function Get-OwnedTree([int]$ParentId) {
    foreach ($child in $allProcesses | Where-Object ParentProcessId -eq $ParentId) {
        Get-OwnedTree -ParentId $child.ProcessId
    }
    $ParentId
}

$targets = @($roots | ForEach-Object { Get-OwnedTree -ParentId ([int]$_) }) | Select-Object -Unique
foreach ($target in $targets) {
    $process = Get-Process -Id $target -ErrorAction SilentlyContinue
    if ($process -and $PSCmdlet.ShouldProcess("PID $target ($($process.ProcessName))", "Stop MangaLens HQ process")) {
        Stop-Process -Id $target -Force -ErrorAction SilentlyContinue
    }
}
Remove-Item -LiteralPath $pidFile -Force
Write-Host "หยุด MangaLens HQ Server แล้ว"

