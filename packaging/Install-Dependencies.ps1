$ErrorActionPreference = "Stop"
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw "Install Microsoft App Installer from Microsoft Store, then retry." }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    winget install --id Gyan.FFmpeg --exact --source winget
    if ($LASTEXITCODE -ne 0) { throw "FFmpeg installation failed." }
}
$webview = Get-ChildItem "${env:ProgramFiles(x86)}\Microsoft\EdgeWebView\Application" -Directory -ErrorAction SilentlyContinue
if (-not $webview) {
    winget install --id Microsoft.EdgeWebView2Runtime --exact --source winget
    if ($LASTEXITCODE -ne 0) { throw "WebView2 installation failed." }
}
Write-Host "Dependency setup finished. Restart this application."
Read-Host "Press Enter to close"
