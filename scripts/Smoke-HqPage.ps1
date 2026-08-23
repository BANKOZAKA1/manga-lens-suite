[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ImagePath,
    [ValidateSet("ja", "ko", "zh")][string]$SourceLanguage = "ja",
    [ValidateSet("balanced", "hq")][string]$QualityProfile = "balanced",
    [string]$BaseUrl = "http://192.168.1.8:8765",
    [string]$TokenFile = "F:\AI\MangaLens\server\pairing-token.txt",
    [string]$OutputPath = "F:\AI\MangaLens\server\smoke-result.png",
    [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = "Stop"
$image = Get-Item -LiteralPath $ImagePath
$token = (Get-Content -LiteralPath $TokenFile -Raw).Trim()
$headers = @{ Authorization = "Bearer $token" }
$base = $BaseUrl.TrimEnd("/")
$health = Invoke-RestMethod -Uri "$base/v1/health" -TimeoutSec 10
if (-not $health.ready) { throw "MangaLens HQ ยังไม่พร้อม" }

$config = @{
    source_language = $SourceLanguage
    target_language = "THA"
    quality_profile = $QualityProfile
    reading_order = if ($SourceLanguage -eq "ja") { "rtl" } else { "vertical" }
    glossary_version = "smoke"
    selected_sfx = @()
} | ConvertTo-Json -Compress

$job = Invoke-RestMethod -Uri "$base/v1/pages" -Method Post -Headers $headers -Form @{
    image = $image
    config = $config
} -TimeoutSec 30
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Milliseconds 500
    $state = Invoke-RestMethod -Uri "$base/v1/jobs/$($job.id)" -Headers $headers -TimeoutSec 15
    Write-Progress -Activity "MangaLens HQ" -Status $state.stage -PercentComplete $state.progress
    if ((Get-Date) -gt $deadline) {
        Invoke-RestMethod -Uri "$base/v1/jobs/$($job.id)" -Method Delete -Headers $headers -TimeoutSec 15 | Out-Null
        throw "HQ smoke test หมดเวลา"
    }
} while ($state.state -notin @("completed", "failed", "cancelled"))
Write-Progress -Activity "MangaLens HQ" -Completed

if ($state.state -ne "completed") { throw ($state.error ?? "HQ smoke test ไม่สำเร็จ") }
Invoke-WebRequest -Uri "$base/v1/jobs/$($job.id)/result" -Headers $headers -OutFile $OutputPath -TimeoutSec 60
$hash = Get-FileHash -LiteralPath $OutputPath -Algorithm SHA256
[PSCustomObject]@{
    Job = $job.id
    State = $state.state
    ServerMs = $state.timings_ms.hq_total
    Output = $OutputPath
    SHA256 = $hash.Hash
}
