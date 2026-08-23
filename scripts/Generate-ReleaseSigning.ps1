[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$signingRoot = "F:\AI\MangaLens\signing"
$keystore = Join-Path $signingRoot "mangalens-release.jks"
$metadata = Join-Path $signingRoot "signing.json"
$keytool = "C:\Program Files\Java\jdk-17\bin\keytool.exe"
if (-not (Test-Path -LiteralPath $keytool -PathType Leaf)) {
    $keytoolCommand = Get-Command keytool.exe -ErrorAction SilentlyContinue
    if (-not $keytoolCommand) { throw "ไม่พบ JDK keytool.exe" }
    $keytool = $keytoolCommand.Source
}
if ((Test-Path -LiteralPath $keystore -PathType Leaf) -and (Test-Path -LiteralPath $metadata -PathType Leaf)) {
    Write-Host "ใช้ release signing key เดิมที่ $keystore"
    exit 0
}
if ((Test-Path -LiteralPath $keystore) -or (Test-Path -LiteralPath $metadata)) {
    throw "พบ signing material ไม่ครบที่ $signingRoot กรุณาสำรองและตรวจด้วยตนเอง"
}

New-Item -ItemType Directory -Force -Path $signingRoot | Out-Null
$bytes = [byte[]]::new(36)
[Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
$password = [Convert]::ToBase64String($bytes).Replace("/", "A").Replace("+", "B")
$alias = "mangalens"

& $keytool -genkeypair -noprompt -keystore $keystore -storetype JKS -storepass $password `
    -keypass $password -alias $alias -keyalg RSA -keysize 4096 -validity 10000 `
    -dname "CN=MangaLens Suite, OU=Release, O=Trivico, C=TH" | Out-Null
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $keystore -PathType Leaf)) {
    throw "สร้าง Android release key ไม่สำเร็จ"
}

$record = [ordered]@{
    keystore = $keystore.Replace("\", "/")
    alias = $alias
    storePassword = $password
    keyPassword = $password
    createdAt = (Get-Date).ToUniversalTime().ToString("o")
}
[IO.File]::WriteAllText($metadata, ($record | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
Write-Host "สร้าง release signing key แล้ว กรุณาสำรองทั้งโฟลเดอร์ $signingRoot"
