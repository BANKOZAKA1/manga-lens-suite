[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$BaseUrl,
    [string]$TokenFile = "F:\AI\MangaLens\server\pairing-token.txt"
)

$ErrorActionPreference = "Stop"
$base = $BaseUrl.TrimEnd("/")
$token = (Get-Content -LiteralPath $TokenFile -Raw).Trim()
$health = Invoke-RestMethod "$base/v1/health" -TimeoutSec 5
$models = Invoke-RestMethod "$base/v1/models" -Headers @{ Authorization = "Bearer $token" } -TimeoutSec 5
if ($health.service -ne "mangalens-hq") { throw "Health response ไม่ถูกต้อง" }
if (-not $models.data) { throw "Models response ว่าง" }
$health | ConvertTo-Json -Depth 5

