param([string]$Compiler = "")
$ErrorActionPreference = "Stop"
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$buildDir = Join-Path $repoRoot "build\ofx-probe"
if (-not $Compiler) { $Compiler = Join-Path $buildDir "toolchain\tcc\tcc.exe" }
if (-not (Test-Path -LiteralPath $Compiler)) { throw "Specify the path to an x64 TinyCC compiler with -Compiler." }
New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
$output = Join-Path $buildDir "JYInterfaceProbe.ofx"
& $Compiler -shared -Wall -I (Join-Path $PSScriptRoot "vendor\openfx\include") -o $output (Join-Path $PSScriptRoot "probe.c")
if ($LASTEXITCODE -ne 0) { throw "OFX compilation failed." }
$bundleDir = Join-Path $buildDir "JYInterfaceProbe.ofx.bundle\Contents\Win64"
New-Item -ItemType Directory -Path $bundleDir -Force | Out-Null
Copy-Item -LiteralPath $output -Destination (Join-Path $bundleDir "JYInterfaceProbe.ofx") -Force
Get-FileHash -LiteralPath $output -Algorithm SHA256

