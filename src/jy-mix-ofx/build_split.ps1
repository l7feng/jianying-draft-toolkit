param([string]$Compiler="",[string]$BuildDirectory="")
$ErrorActionPreference="Stop"
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$build=if($BuildDirectory){[IO.Path]::GetFullPath($BuildDirectory)}else{Join-Path $repo "build\ofx-split-v0.8"}
if(-not $Compiler){$Compiler=Join-Path $repo "build\ofx-audio-v0.2\toolchain\tcc\tcc.exe"}
$variants=@(
    @{Name='JYAAFExport';Mode=0;Label='剪映AAF导出 v0.8';Id='local.jytools.AAFExport'},
    @{Name='JYTrackExport';Mode=2;Label='剪映单集分轨 v0.8';Id='local.jytools.TrackExport'},
    @{Name='JYBatchTrackExport';Mode=3;Label='剪映多集分轨 v0.8';Id='local.jytools.BatchTrackExport'}
)
$records=foreach($v in $variants){
    $bundle=Join-Path $build ($v.Name+'.ofx.bundle')
    $target=Join-Path $bundle 'Contents\Win64'
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    $file=Join-Path $target ($v.Name+'.ofx')
    & $Compiler -shared -Wall ('-DJY_PLUGIN_MODE='+$v.Mode) -I (Join-Path $repo 'src\jy-ofx-probe\vendor\openfx\include') -o $file (Join-Path $PSScriptRoot 'mix_plugin.c') -lshell32 -luser32
    if($LASTEXITCODE -ne 0){throw ('Build failed: '+$v.Name)}
    Copy-Item -LiteralPath (Join-Path $repo 'src\jy-ofx-probe\vendor\openfx\LICENSE.md') -Destination (Join-Path $bundle 'Contents\LICENSE-OpenFX.txt') -Force
    [pscustomobject]@{Name=$v.Name;Label=$v.Label;Id=$v.Id;Mode=$v.Mode;Bundle=$bundle;File=$file;SHA256=(Get-FileHash -LiteralPath $file).Hash}
}
$records | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $build 'delivery.json') -Encoding utf8
$records | Format-Table Label,SHA256
