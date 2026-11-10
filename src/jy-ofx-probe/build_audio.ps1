param([string]$Compiler="")
$ErrorActionPreference="Stop"
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$build=Join-Path $repo "build\ofx-audio-v0.2"
if(-not $Compiler){$Compiler=Join-Path $build "toolchain\tcc\tcc.exe"}
New-Item -ItemType Directory -Path $build -Force | Out-Null
$out=Join-Path $build "JYAudioToolkit.ofx"
& $Compiler -shared -Wall -I (Join-Path $PSScriptRoot "vendor\openfx\include") -o $out (Join-Path $PSScriptRoot "audio_plugin.c") -lshell32 -luser32
if($LASTEXITCODE -ne 0){throw "Audio OFX build failed"}
$bundle=Join-Path $build "JYAudioToolkit.ofx.bundle\Contents\Win64"
New-Item -ItemType Directory -Path $bundle -Force | Out-Null
Copy-Item -LiteralPath $out -Destination (Join-Path $bundle "JYAudioToolkit.ofx") -Force
Get-FileHash -LiteralPath $out

