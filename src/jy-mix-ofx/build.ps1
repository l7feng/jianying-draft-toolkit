param([string]$Compiler="", [string]$BuildDirectory="")
$ErrorActionPreference="Stop"
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$build=if($BuildDirectory){[IO.Path]::GetFullPath($BuildDirectory)}else{Join-Path $repo "build\ofx-mix-aaf-v0.7"}
if(-not $Compiler){$Compiler=Join-Path $repo "build\ofx-audio-v0.2\toolchain\tcc\tcc.exe"}
$target=Join-Path $build "JYMixBridge.ofx.bundle\Contents\Win64"
New-Item -ItemType Directory -Path $target -Force | Out-Null
& $Compiler -shared -Wall -I (Join-Path $repo "src\jy-ofx-probe\vendor\openfx\include") -o (Join-Path $target "JYMixBridge.ofx") (Join-Path $PSScriptRoot "mix_plugin.c") -lshell32 -luser32
if($LASTEXITCODE -ne 0){throw "OFX build failed"}
Get-FileHash -LiteralPath (Join-Path $target "JYMixBridge.ofx")

Copy-Item -LiteralPath (Join-Path $repo "src\jy-ofx-probe\vendor\openfx\LICENSE.md") -Destination (Join-Path $target "..\LICENSE-OpenFX.txt") -Force
