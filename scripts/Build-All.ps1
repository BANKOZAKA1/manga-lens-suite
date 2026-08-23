[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$suiteRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$workspaceRoot = (Resolve-Path (Join-Path $suiteRoot "..")).Path
$artifacts = Join-Path $suiteRoot "artifacts"
$llvmMingw = "F:\AI\MangaLens\toolchains\llvm-mingw-20260616-ucrt-x86_64"
$env:GRADLE_USER_HOME = "F:\AI\MangaLens\gradle-cache"
$env:CMAKE_BUILD_PARALLEL_LEVEL = "2"
$env:MANGALENS_LLVM_MINGW = $llvmMingw
$env:Path = "$(Join-Path $llvmMingw 'bin');$env:Path"
$env:PYTHONUTF8 = "1"
$signingJson = "F:\AI\MangaLens\signing\signing.json"
$signingScript = Join-Path $PSScriptRoot "Generate-ReleaseSigning.ps1"

if (-not (Test-Path -LiteralPath "M:\")) {
    & subst.exe M: $workspaceRoot
    if ($LASTEXITCODE -ne 0) { throw "สร้าง M: path สำหรับ Android build ไม่สำเร็จ" }
}
New-Item -ItemType Directory -Force -Path $artifacts | Out-Null
if (-not (Test-Path -LiteralPath $signingJson -PathType Leaf)) {
    & $signingScript
}
$signing = Get-Content -LiteralPath $signingJson -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $signing.keystore -PathType Leaf)) {
    throw "ไม่พบ release keystore: $($signing.keystore)"
}
$env:RELEASE_KEYSTORE_PATH = $signing.keystore
$env:RELEASE_KEYSTORE_PASSWORD = $signing.storePassword
$env:RELEASE_KEY_ALIAS = $signing.alias
$env:RELEASE_KEY_PASSWORD = $signing.keyPassword

function Invoke-Gradle([string]$Project, [string[]]$Tasks) {
    Push-Location $Project
    try {
        & java -classpath "gradle\wrapper\gradle-wrapper.jar" org.gradle.wrapper.GradleWrapperMain --no-daemon --max-workers=2 @Tasks
        if ($LASTEXITCODE -ne 0) { throw "Gradle failed in $Project" }
    } finally {
        Pop-Location
    }
}

$readerSigningProperties = Join-Path $suiteRoot "reader\keystore.properties"
$readerSigningText = @(
    "storeFile=$($signing.keystore)"
    "storePassword=$($signing.storePassword)"
    "keyAlias=$($signing.alias)"
    "keyPassword=$($signing.keyPassword)"
) -join "`n"

Invoke-Gradle "M:\manga-lens-suite\overlay" @("`:app:testDebugUnitTest", "`:app:assembleRelease")
try {
    [IO.File]::WriteAllText($readerSigningProperties, $readerSigningText, [Text.UTF8Encoding]::new($false))
    Invoke-Gradle "M:\manga-lens-suite\reader" @("`:app:testDebugUnitTest", "`:app:assembleRelease")
} finally {
    if (Test-Path -LiteralPath $readerSigningProperties) {
        Remove-Item -LiteralPath $readerSigningProperties -Force
    }
}

$overlayApk = Join-Path $suiteRoot "overlay\app\build\outputs\apk\release\app-release.apk"
$readerApk = Join-Path $suiteRoot "reader\app\build\outputs\apk\release\app-arm64-v8a-release.apk"
if (-not (Test-Path -LiteralPath $overlayApk) -or -not (Test-Path -LiteralPath $readerApk)) {
    throw "APK output ไม่ครบ"
}
Copy-Item -LiteralPath $overlayApk -Destination (Join-Path $artifacts "MangaLens-Overlay-1.0.0-arm64-v8a.apk") -Force
Copy-Item -LiteralPath $readerApk -Destination (Join-Path $artifacts "MangaLens-Reader-1.0.0-arm64-v8a.apk") -Force

$hashLines = Get-ChildItem -LiteralPath $artifacts -Filter "*.apk" | Sort-Object Name | ForEach-Object {
    $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash *$($_.Name)"
}
[IO.File]::WriteAllLines((Join-Path $artifacts "SHA256SUMS.txt"), $hashLines, [Text.UTF8Encoding]::new($false))
Get-Content -LiteralPath (Join-Path $artifacts "SHA256SUMS.txt")
