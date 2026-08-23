[CmdletBinding()]
param(
    [int]$Port = 8765,
    [string]$LanAddress = ""
)

$ErrorActionPreference = "Stop"
$suiteRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeRoot = "F:\AI\MangaLens"
$serverState = Join-Path $runtimeRoot "server"
$python = "F:\AI\manga-image-translator-runtime\.venv\Scripts\python.exe"
$ollama = Join-Path $runtimeRoot "ollama\ollama.exe"
$tokenFile = Join-Path $serverState "pairing-token.txt"
$pidFile = Join-Path $serverState "pids.json"
$qrFile = Join-Path $serverState "pairing.png"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "ไม่พบ Python runtime: $python"
}
if (-not (Test-Path -LiteralPath $ollama -PathType Leaf)) {
    throw "ไม่พบ Ollama portable: $ollama`nรัน scripts\Install-HqRuntime.ps1 ก่อน"
}

New-Item -ItemType Directory -Force -Path $serverState, (Join-Path $runtimeRoot "models\ollama"), (Join-Path $runtimeRoot "cache") | Out-Null
if (-not (Test-Path -LiteralPath $tokenFile -PathType Leaf)) {
    $bytes = [byte[]]::new(32)
    [Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    $token = [Convert]::ToHexString($bytes).ToLowerInvariant()
    [IO.File]::WriteAllText($tokenFile, $token, [Text.UTF8Encoding]::new($false))
} else {
    $token = (Get-Content -LiteralPath $tokenFile -Raw).Trim()
}
if ($token.Length -lt 32) {
    throw "Pairing token สั้นผิดปกติ กรุณาย้ายไฟล์ $tokenFile แล้วเริ่มใหม่"
}

if (-not $LanAddress) {
    $candidates = Get-NetIPConfiguration | Where-Object {
        $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq "Up" -and $_.IPv4Address
    } | ForEach-Object {
        [PSCustomObject]@{
            Address = $_.IPv4Address.IPAddress
            Score = if ($_.InterfaceAlias -match "Wi-?Fi|Wireless") { 0 } else { 1 }
        }
    } | Where-Object { $_.Address -notmatch "^(127|169\.254)\." } | Sort-Object Score
    $LanAddress = $candidates | Select-Object -First 1 -ExpandProperty Address
}
if (-not $LanAddress -or $LanAddress -notmatch "^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)") {
    throw "หา private LAN IPv4 ไม่ได้ ใช้ -LanAddress 192.168.x.x ระบุเอง"
}
$baseUrl = "http://${LanAddress}:$Port"

$env:OLLAMA_HOST = "127.0.0.1:11434"
$env:OLLAMA_MODELS = Join-Path $runtimeRoot "models\ollama"
$env:OLLAMA_KEEP_ALIVE = "10m"
$env:HF_HOME = Join-Path $runtimeRoot "cache\huggingface"
$env:HUGGINGFACE_HUB_CACHE = Join-Path $env:HF_HOME "hub"
$env:MANGALENS_PAIRING_TOKEN = $token
$env:MANGALENS_TOKEN_FILE = $tokenFile
$env:MANGALENS_MODEL_DIR = Join-Path $runtimeRoot "models"
$env:MANGALENS_MIT_ROOT = (Resolve-Path (Join-Path $suiteRoot "..\manga-image-translator")).Path
$env:MANGALENS_MIT_URL = "http://127.0.0.1:8766"
$env:MANGALENS_OLLAMA_URL = "http://127.0.0.1:11434"
$env:MANGALENS_TRANSLATION_MODEL = "translategemma:4b"
$env:CUSTOM_OPENAI_API_KEY = $token
$env:CUSTOM_OPENAI_API_BASE = "$baseUrl/v1"
$env:CUSTOM_OPENAI_MODEL = "translategemma:4b"
$env:PYTHONUTF8 = "1"

$processes = [ordered]@{}
try {
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null
    } catch {
        $ollamaProcess = Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput (Join-Path $serverState "ollama.out.log") `
            -RedirectStandardError (Join-Path $serverState "ollama.err.log")
        $processes.ollama = $ollamaProcess.Id
    }

    $mitProcess = Start-Process -FilePath $python -ArgumentList @((Join-Path $suiteRoot "server\mit_runner.py")) `
        -WorkingDirectory $suiteRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $serverState "mit.out.log") `
        -RedirectStandardError (Join-Path $serverState "mit.err.log")
    $processes.mit = $mitProcess.Id

    $gatewayArgs = @("-m", "uvicorn", "app:app", "--app-dir", (Join-Path $suiteRoot "server"), "--host", $LanAddress, "--port", "$Port")
    $gatewayProcess = Start-Process -FilePath $python -ArgumentList $gatewayArgs -WorkingDirectory $suiteRoot `
        -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $serverState "gateway.out.log") `
        -RedirectStandardError (Join-Path $serverState "gateway.err.log")
    $processes.gateway = $gatewayProcess.Id
    [IO.File]::WriteAllText($pidFile, ($processes | ConvertTo-Json), [Text.UTF8Encoding]::new($false))

    & $python (Join-Path $suiteRoot "server\make_qr.py") --base-url $baseUrl --token $token --output $qrFile | Out-Null
    $health = $null
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        try {
            $health = Invoke-RestMethod -Uri "$baseUrl/v1/health" -TimeoutSec 3
            if ($health.ready) { break }
            $health = $null
        } catch {
        }
        Start-Sleep -Milliseconds 750
    }
    if (-not $health) {
        throw "Gateway ไม่ตอบสนอง ดู log ที่ $serverState"
    }

    Write-Host "MangaLens HQ Server เริ่มแล้ว" -ForegroundColor Green
    Write-Host "Base URL: $baseUrl/v1"
    Write-Host "Pairing token: $token"
    Write-Host "QR: $qrFile"
    Write-Host "Ready: $($health.ready)"
} catch {
    Write-Error $_
    Write-Host "ถ้ามี process ค้าง ให้รัน .\scripts\Stop-HqServer.ps1"
    exit 1
}
