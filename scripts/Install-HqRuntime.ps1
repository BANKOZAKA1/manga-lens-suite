[CmdletBinding()]
param(
    [switch]$SkipModel
)

$ErrorActionPreference = "Stop"
$runtimeRoot = "F:\AI\MangaLens"
$download = Join-Path $runtimeRoot "cache\ollama-windows-amd64.zip"
$ollamaRoot = Join-Path $runtimeRoot "ollama"
$archiveUrl = "https://ollama.com/download/ollama-windows-amd64.zip"
$python = "F:\AI\manga-image-translator-runtime\.venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path (Split-Path $download), $ollamaRoot, (Join-Path $runtimeRoot "models\ollama") | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $ollamaRoot "ollama.exe") -PathType Leaf)) {
    Write-Host "Downloading official Ollama Windows archive (resumable)..."
    & curl.exe -L --fail --retry 5 --continue-at - --output $download $archiveUrl
    if ($LASTEXITCODE -ne 0) { throw "ดาวน์โหลด Ollama ไม่สำเร็จ" }
    Expand-Archive -LiteralPath $download -DestinationPath $ollamaRoot -Force
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "ไม่พบ manga-image-translator Python runtime: $python"
}
& $python -m pip install --disable-pip-version-check -r (Join-Path $PSScriptRoot "..\server\requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "ติดตั้ง dependency ของ gateway ไม่สำเร็จ" }

if (-not $SkipModel) {
    $env:OLLAMA_HOST = "127.0.0.1:11434"
    $env:OLLAMA_MODELS = Join-Path $runtimeRoot "models\ollama"
    $ollama = Join-Path $ollamaRoot "ollama.exe"
    $serve = Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden -PassThru
    try {
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            try { Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep -Seconds 1 }
        }
        & $ollama pull translategemma:4b
        if ($LASTEXITCODE -ne 0) { throw "ดาวน์โหลด translategemma:4b ไม่สำเร็จ" }
    } finally {
        Stop-Process -Id $serve.Id -Force -ErrorAction SilentlyContinue
    }
}
Write-Host "HQ runtime พร้อมที่ $runtimeRoot" -ForegroundColor Green

