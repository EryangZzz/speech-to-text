$ErrorActionPreference = "Stop"

$resourceDir = Join-Path $PSScriptRoot "..\src-tauri\resources"
$resourceDir = [System.IO.Path]::GetFullPath($resourceDir)
New-Item -ItemType Directory -Force -Path $resourceDir | Out-Null

$targetPath = Join-Path $resourceDir "ffmpeg-windows-x64.exe"
$existingSize = 0
if (Test-Path $targetPath) {
  $existingSize = (Get-Item $targetPath).Length
}

if ($existingSize -ge 1000000) {
  Write-Host "Using existing Windows ffmpeg binary: $targetPath"
  exit 0
}

$zipPath = Join-Path $env:TEMP "ffmpeg-win.zip"
$extractDir = Join-Path $env:TEMP "ffmpeg-win"

if (Test-Path $extractDir) {
  Remove-Item -Recurse -Force $extractDir
}

Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile $zipPath
Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force

$ffmpeg = Get-ChildItem -Path $extractDir -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
if (-not $ffmpeg) {
  throw "ffmpeg.exe not found in downloaded archive"
}

Copy-Item $ffmpeg.FullName $targetPath -Force
$preparedSize = (Get-Item $targetPath).Length
if ($preparedSize -lt 1000000) {
  throw "Prepared ffmpeg.exe is too small: $preparedSize"
}

Write-Host "Prepared Windows ffmpeg binary: $targetPath"
