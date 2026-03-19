$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$releaseExe = Join-Path $projectRoot "target\release\google_tools_cli.exe"
$outExe = Join-Path $projectRoot "google_tools_cli.exe"

$cargoCmd = "cargo"
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    $cargoCandidate = Join-Path $env:USERPROFILE ".cargo\bin\cargo.exe"
    if (Test-Path $cargoCandidate) {
        $cargoCmd = $cargoCandidate
    } else {
        throw "cargo が見つかりません。Rustをインストールしてください。"
    }
}

Push-Location $projectRoot
try {
    & $cargoCmd build --release
    Copy-Item -Force $releaseExe $outExe
    Write-Output "Build completed: $outExe"
} finally {
    Pop-Location
}
