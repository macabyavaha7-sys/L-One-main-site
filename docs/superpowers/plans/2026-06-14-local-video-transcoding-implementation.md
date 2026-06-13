# L-One Local Video Transcoding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a D-drive-only, resumable FFmpeg pipeline that converts 10 representative source MP4 files into website-ready MP4, WebP, WebM, metadata, manifest, logs, and an audit report while keeping the entire source library unchanged.

**Architecture:** A portable FFmpeg installation lives under `D:\L-One Center\Tools`. A PowerShell module owns deterministic scanning, IDs, paths, FFprobe parsing, FFmpeg argument construction, metadata, and manifest generation; thin command scripts invoke the module for conversion and auditing. Every asset is written through `.working` files and published only after automated validation succeeds.

**Tech Stack:** PowerShell 7/Windows PowerShell 5.1-compatible scripts, portable FFmpeg/FFprobe, JSON/JSONL, HTML report, Node-free local execution.

---

## File Structure

```text
D:\L-One Center\
  视频素材参考2026\                    # read-only source
  Tools\ffmpeg\bin\
    ffmpeg.exe
    ffprobe.exe
  L-One素材库上传包\
    media\
    data\assets.json
    logs\completed.jsonl
    logs\failed.jsonl
    logs\skipped.jsonl
    reports\conversion-summary.json
    reports\conversion-summary.html
    tools\TranscodeLibrary.psm1
    tools\transcode-library.ps1
    tools\audit-transcoded-library.ps1
    tools\tests\transcode-library.tests.ps1
```

`TranscodeLibrary.psm1` contains all reusable logic. The runner only parses parameters and coordinates work. The audit script never modifies media and returns a non-zero exit code on any violation.

### Task 1: Install Portable FFmpeg and Create Isolated Directories

**Files:**
- Create: `D:\L-One Center\Tools\ffmpeg\bin\ffmpeg.exe`
- Create: `D:\L-One Center\Tools\ffmpeg\bin\ffprobe.exe`
- Create: `D:\L-One Center\L-One素材库上传包\media\`
- Create: `D:\L-One Center\L-One素材库上传包\data\`
- Create: `D:\L-One Center\L-One素材库上传包\logs\`
- Create: `D:\L-One Center\L-One素材库上传包\reports\`
- Create: `D:\L-One Center\L-One素材库上传包\tools\tests\`

- [ ] **Step 1: Capture the source-library fingerprint**

Run:

```powershell
$source = 'D:\L-One Center\视频素材参考2026'
Get-ChildItem -LiteralPath $source -Recurse -File |
  Sort-Object FullName |
  Select-Object FullName, Length, LastWriteTimeUtc |
  ConvertTo-Json -Depth 3 |
  Set-Content -Encoding UTF8 'D:\L-One Center\source-library-before.json'
```

Expected: the fingerprint contains 3049 records and is stored outside the source directory.

- [ ] **Step 2: Download FFmpeg to D drive**

Run:

```powershell
$download = 'D:\L-One Center\Tools\ffmpeg-release-essentials.zip'
$extract = 'D:\L-One Center\Tools\ffmpeg-extract'
New-Item -ItemType Directory -Force 'D:\L-One Center\Tools' | Out-Null
Invoke-WebRequest 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile $download
Expand-Archive -LiteralPath $download -DestinationPath $extract -Force
$build = Get-ChildItem -LiteralPath $extract -Directory | Select-Object -First 1
New-Item -ItemType Directory -Force 'D:\L-One Center\Tools\ffmpeg\bin' | Out-Null
Copy-Item -LiteralPath (Join-Path $build.FullName 'bin\ffmpeg.exe') 'D:\L-One Center\Tools\ffmpeg\bin\ffmpeg.exe'
Copy-Item -LiteralPath (Join-Path $build.FullName 'bin\ffprobe.exe') 'D:\L-One Center\Tools\ffmpeg\bin\ffprobe.exe'
Remove-Item -LiteralPath $download -Force
Remove-Item -LiteralPath $extract -Recurse -Force
```

Expected: only the two required executables remain under `D:\L-One Center\Tools\ffmpeg\bin`.

- [ ] **Step 3: Verify codec support**

Run:

```powershell
& 'D:\L-One Center\Tools\ffmpeg\bin\ffmpeg.exe' -hide_banner -encoders 2>&1 |
  Select-String 'libx264|libvpx-vp9|libwebp|aac'
& 'D:\L-One Center\Tools\ffmpeg\bin\ffprobe.exe' -version | Select-Object -First 1
```

Expected: output lists `libx264`, `libvpx-vp9`, `libwebp`, and `aac`; FFprobe prints a version.

- [ ] **Step 4: Create output folders**

Run:

```powershell
@('media','data','logs','reports','tools','tools\tests') | ForEach-Object {
  New-Item -ItemType Directory -Force (Join-Path 'D:\L-One Center\L-One素材库上传包' $_) | Out-Null
}
```

Expected: all directories in the file structure exist and the source tree is untouched.

### Task 2: Test Deterministic Source Scanning and Output Identity

**Files:**
- Create: `D:\L-One Center\L-One素材库上传包\tools\tests\transcode-library.tests.ps1`
- Create: `D:\L-One Center\L-One素材库上传包\tools\TranscodeLibrary.psm1`

- [ ] **Step 1: Write failing scanner and identity tests**

Create the test script with these assertions:

```powershell
$ErrorActionPreference = 'Stop'
$module = 'D:\L-One Center\L-One素材库上传包\tools\TranscodeLibrary.psm1'
Import-Module $module -Force

function Assert-Equal($Actual, $Expected, $Message) {
  if ($Actual -ne $Expected) { throw "$Message Expected=[$Expected] Actual=[$Actual]" }
}
function Assert-True($Value, $Message) {
  if (-not $Value) { throw $Message }
}

$fixture = Join-Path $PSScriptRoot 'fixture-scan'
Remove-Item -LiteralPath $fixture -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force (Join-Path $fixture 'A'), (Join-Path $fixture 'B') | Out-Null
Set-Content -Encoding Byte (Join-Path $fixture 'A\同名.mp4') ([byte[]](1,2,3))
Set-Content -Encoding Byte (Join-Path $fixture 'B\同名.MP4') ([byte[]](4,5,6))
Set-Content -Encoding Byte (Join-Path $fixture 'A\跳过.gif') ([byte[]](7))

$items = @(Get-VideoSources -SourceRoot $fixture)
Assert-Equal $items.Count 2 'Only MP4 files should be scanned.'
Assert-Equal $items[0].RelativePath 'A/同名.mp4' 'Paths should be normalized and sorted.'
Assert-True ($items[0].Id -ne $items[1].Id) 'Same filenames in different folders need unique IDs.'
Assert-True ($items[0].OutputRelativePath -match '^media/A/.+--[a-f0-9]{10}$') 'Output path should preserve folders and include a short hash.'
Assert-True (-not $items[0].OutputRelativePath.Contains(':')) 'Published output paths must stay relative.'

Remove-Item -LiteralPath $fixture -Recurse -Force
'Scanner tests passed.'
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\L-One Center\L-One素材库上传包\tools\tests\transcode-library.tests.ps1'
```

Expected: FAIL because `TranscodeLibrary.psm1` or `Get-VideoSources` does not exist.

- [ ] **Step 3: Implement deterministic scanning and ID helpers**

Create `TranscodeLibrary.psm1` with:

```powershell
Set-StrictMode -Version Latest
$script:PipelineVersion = 1

function Get-StableHash([string]$Value, [int]$Length = 10) {
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try {
    $bytes = [Text.Encoding]::UTF8.GetBytes($Value.ToLowerInvariant())
    $hash = -join ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') })
    return $hash.Substring(0, $Length)
  } finally { $sha.Dispose() }
}

function ConvertTo-SafeName([string]$Value) {
  $safe = $Value -replace '[\\/:*?"<>|#%{}^~`\[\]]+', '-'
  $safe = ($safe -replace '\s+', '-').Trim('-','.',' ')
  if ([string]::IsNullOrWhiteSpace($safe)) { return 'video' }
  return $safe.Substring(0, [Math]::Min(80, $safe.Length))
}

function Get-VideoSources([string]$SourceRoot) {
  $root = [IO.Path]::GetFullPath($SourceRoot).TrimEnd('\')
  Get-ChildItem -LiteralPath $root -Recurse -File |
    Where-Object { $_.Extension -ieq '.mp4' } |
    ForEach-Object {
      $relative = $_.FullName.Substring($root.Length).TrimStart('\') -replace '\\','/'
      $folder = [IO.Path]::GetDirectoryName($relative) -replace '\\','/'
      $stem = [IO.Path]::GetFileNameWithoutExtension($_.Name)
      $id = Get-StableHash $relative
      $leaf = "$(ConvertTo-SafeName $stem)--$id"
      [pscustomobject]@{
        Id = $id
        Title = $stem
        Category = ($relative -split '/')[0]
        FolderPath = $folder
        FileName = $_.Name
        FullName = $_.FullName
        RelativePath = $relative
        SizeBytes = $_.Length
        LastWriteTimeUtc = $_.LastWriteTimeUtc
        OutputRelativePath = ((Join-Path 'media' (Join-Path $folder $leaf)) -replace '\\','/')
      }
    } | Sort-Object RelativePath
}

Export-ModuleMember -Function Get-StableHash, ConvertTo-SafeName, Get-VideoSources
```

- [ ] **Step 4: Run the test and verify GREEN**

Run the same test command.

Expected: `Scanner tests passed.`

### Task 3: Test FFprobe Parsing and FFmpeg Command Construction

**Files:**
- Modify: `D:\L-One Center\L-One素材库上传包\tools\tests\transcode-library.tests.ps1`
- Modify: `D:\L-One Center\L-One素材库上传包\tools\TranscodeLibrary.psm1`

- [ ] **Step 1: Add failing probe and command tests**

Append tests that generate three synthetic MP4 fixtures under the output package: landscape with audio, portrait without audio, and a 0.8-second clip.

```powershell
$ffmpeg = 'D:\L-One Center\Tools\ffmpeg\bin\ffmpeg.exe'
$ffprobe = 'D:\L-One Center\Tools\ffmpeg\bin\ffprobe.exe'
$mediaFixture = Join-Path $PSScriptRoot 'fixture-media'
New-Item -ItemType Directory -Force $mediaFixture | Out-Null

& $ffmpeg -y -f lavfi -i 'testsrc2=size=1920x1080:rate=30:duration=3' -f lavfi -i 'sine=frequency=440:duration=3' -c:v libx264 -pix_fmt yuv420p -c:a aac (Join-Path $mediaFixture 'landscape.mp4')
& $ffmpeg -y -f lavfi -i 'testsrc2=size=720x1280:rate=30:duration=3' -c:v libx264 -pix_fmt yuv420p -an (Join-Path $mediaFixture 'portrait.mp4')
& $ffmpeg -y -f lavfi -i 'testsrc2=size=640x360:rate=30:duration=.8' -c:v libx264 -pix_fmt yuv420p -an (Join-Path $mediaFixture 'short.mp4')

$landscape = Get-MediaProbe -Path (Join-Path $mediaFixture 'landscape.mp4') -FfprobePath $ffprobe
$portrait = Get-MediaProbe -Path (Join-Path $mediaFixture 'portrait.mp4') -FfprobePath $ffprobe
Assert-True $landscape.HasAudio 'Audio should be detected.'
Assert-True (-not $portrait.HasAudio) 'Silent input should stay silent.'
Assert-Equal (Get-SeekStart -Duration .8) 0 'Sub-one-second clips should seek from zero.'
Assert-Equal (Get-SeekStart -Duration 3) 1 'Normal clips should seek from one second.'

$args = Get-FullVideoArguments -InputPath 'in.mp4' -OutputPath 'out.mp4' -HasAudio $true -Width 1920 -Height 1080 -FrameRate 30
$joined = $args -join ' '
Assert-True ($joined -match 'libx264') 'Full video must use H.264.'
Assert-True ($joined -match 'aac') 'Audio input must be transcoded to AAC.'
Assert-True ($joined -match '96k') 'Audio bitrate must be 96kbps.'
Assert-True ($joined -match 'faststart') 'MP4 must be optimized for web start.'
Assert-True ($joined -match 'min\(1280') 'Scale must avoid upscaling and cap the longest edge.'
```

- [ ] **Step 2: Run and verify RED**

Expected: FAIL because probe and argument functions are undefined.

- [ ] **Step 3: Implement probe and argument functions**

Add these exported functions to the module:

```powershell
function Get-MediaProbe([string]$Path, [string]$FfprobePath) {
  $json = & $FfprobePath -v error -print_format json -show_format -show_streams -- $Path
  if ($LASTEXITCODE -ne 0) { throw "FFprobe failed: $Path" }
  $data = ($json -join "`n") | ConvertFrom-Json
  $video = @($data.streams | Where-Object codec_type -eq 'video')[0]
  $audio = @($data.streams | Where-Object codec_type -eq 'audio')
  $rateParts = [string]$video.avg_frame_rate -split '/'
  $fps = if ($rateParts.Count -eq 2 -and [double]$rateParts[1]) { [double]$rateParts[0] / [double]$rateParts[1] } else { 0 }
  [pscustomobject]@{
    Duration = [double]$data.format.duration
    Width = [int]$video.width
    Height = [int]$video.height
    FrameRate = $fps
    VideoCodec = [string]$video.codec_name
    PixelFormat = [string]$video.pix_fmt
    HasAudio = $audio.Count -gt 0
    AudioCodec = if ($audio.Count) { [string]$audio[0].codec_name } else { $null }
  }
}

function Get-SeekStart([double]$Duration) {
  if ($Duration -le 1) { return 0 }
  return 1
}

function Get-ScaleFilter([int]$MaxEdge, [double]$FrameRate = 0) {
  $scale = "scale='if(gte(iw,ih),min($MaxEdge,iw),-2)':'if(gte(iw,ih),-2,min($MaxEdge,ih))'"
  if ($FrameRate -gt 60) { return "$scale,fps=60" }
  return $scale
}

function Get-FullVideoArguments($InputPath, $OutputPath, $HasAudio, $Width, $Height, $FrameRate) {
  $args = @('-y','-hide_banner','-loglevel','error','-i',$InputPath,'-map_metadata','-1','-vf',(Get-ScaleFilter 1280 $FrameRate),'-c:v','libx264','-preset','medium','-crf','24','-maxrate','2M','-bufsize','4M','-pix_fmt','yuv420p','-movflags','+faststart')
  if ($HasAudio) { $args += @('-c:a','aac','-b:a','96k') } else { $args += '-an' }
  return $args + $OutputPath
}

function Get-ThumbnailArguments($InputPath, $OutputPath, $Duration) {
  @('-y','-hide_banner','-loglevel','error','-ss',[string](Get-SeekStart $Duration),'-i',$InputPath,'-vf',(Get-ScaleFilter 640),'-frames:v','1','-c:v','libwebp','-quality','72',$OutputPath)
}

function Get-PreviewArguments($InputPath, $OutputPath, $Duration) {
  $length = [Math]::Min(4, [Math]::Max(.1, $Duration - (Get-SeekStart $Duration)))
  @('-y','-hide_banner','-loglevel','error','-ss',[string](Get-SeekStart $Duration),'-t',[string]$length,'-i',$InputPath,'-vf',"$(Get-ScaleFilter 640),fps=15",'-an','-c:v','libvpx-vp9','-b:v','0','-crf','42','-deadline','good','-row-mt','1',$OutputPath)
}
```

Export all new functions.

- [ ] **Step 4: Run tests and verify GREEN**

Expected: all scanner, probe, and command tests pass.

### Task 4: Implement and Test Atomic Single-Asset Conversion

**Files:**
- Modify: `D:\L-One Center\L-One素材库上传包\tools\tests\transcode-library.tests.ps1`
- Modify: `D:\L-One Center\L-One素材库上传包\tools\TranscodeLibrary.psm1`

- [ ] **Step 1: Add a failing conversion test**

Use the synthetic landscape fixture and assert that:

```powershell
$outputRoot = Join-Path $PSScriptRoot 'fixture-output'
Remove-Item -LiteralPath $outputRoot -Recurse -Force -ErrorAction SilentlyContinue
$source = [pscustomobject]@{
  Id='abc1234567'; Title='测试横屏'; Category='测试'; FolderPath='测试'; FileName='landscape.mp4'
  FullName=(Join-Path $mediaFixture 'landscape.mp4'); RelativePath='测试/landscape.mp4'
  SizeBytes=(Get-Item (Join-Path $mediaFixture 'landscape.mp4')).Length
  LastWriteTimeUtc=(Get-Item (Join-Path $mediaFixture 'landscape.mp4')).LastWriteTimeUtc
  OutputRelativePath='media/测试/测试横屏--abc1234567'
}
$result = Convert-VideoAsset -Source $source -OutputRoot $outputRoot -FfmpegPath $ffmpeg -FfprobePath $ffprobe -Batch 'test'
Assert-Equal $result.Status 'completed' 'Conversion should complete.'
@('video.mp4','thumbnail.webp','preview.webm','metadata.json') | ForEach-Object {
  Assert-True (Test-Path -LiteralPath (Join-Path $outputRoot "media\测试\测试横屏--abc1234567\$_")) "Missing $_"
}
Assert-Equal (Get-ChildItem -LiteralPath $outputRoot -Recurse -File -Filter '*.working').Count 0 'No temporary files may remain.'
```

- [ ] **Step 2: Run and verify RED**

Expected: FAIL because `Convert-VideoAsset` is undefined.

- [ ] **Step 3: Implement atomic conversion**

Implement `Convert-VideoAsset` with this sequence:

1. Resolve the output directory under `OutputRoot` and reject any path escaping it.
2. Probe the input.
3. Build a parameter fingerprint from pipeline version, CRF, maximum dimensions, preview duration, and audio bitrate.
4. When an existing metadata file has the same fingerprint and all three media files pass validation, return `skipped`.
5. Create `video.mp4.working`, `thumbnail.webp.working`, and `preview.webm.working` in the destination directory.
6. Run the three FFmpeg commands and check `$LASTEXITCODE` after each process.
7. Probe the working files and call `Test-OutputBundle`.
8. Move each working file to its final filename with `Move-Item -Force`.
9. Write `metadata.json.working`, then atomically rename it to `metadata.json`.
10. On exception, remove only `*.working` in the destination and return a failed result containing a short error message.

Metadata paths must use forward slashes and remain relative to `OutputRoot`. `createdAt` uses UTC ISO-8601. `outputSizeBytes` is the sum of the three published files.

- [ ] **Step 4: Implement output validation**

`Test-OutputBundle` must throw when any condition fails:

```powershell
$video.VideoCodec -eq 'h264'
$video.PixelFormat -eq 'yuv420p'
[Math]::Max($video.Width, $video.Height) -le 1280
(-not $sourceProbe.HasAudio) -or ($video.HasAudio -and $video.AudioCodec -eq 'aac')
$thumbnail.VideoCodec -eq 'webp'
[Math]::Max($thumbnail.Width, $thumbnail.Height) -le 640
$preview.VideoCodec -eq 'vp9'
-not $preview.HasAudio
[Math]::Max($preview.Width, $preview.Height) -le 640
$preview.Duration -le 4.25
```

- [ ] **Step 5: Run tests twice**

First run expected: conversion completes. Second call to `Convert-VideoAsset` expected: status is `skipped`, output modification times remain unchanged.

### Task 5: Build the Batch Runner, Logs, Manifest, and Reports

**Files:**
- Create: `D:\L-One Center\L-One素材库上传包\tools\transcode-library.ps1`
- Modify: `D:\L-One Center\L-One素材库上传包\tools\TranscodeLibrary.psm1`
- Modify: `D:\L-One Center\L-One素材库上传包\tools\tests\transcode-library.tests.ps1`

- [ ] **Step 1: Add failing manifest tests**

Assert that `Build-AssetManifest` reads only valid metadata files, sorts by `sourceRelativePath`, rejects duplicate IDs/paths, emits no absolute `D:\` path, and writes UTF-8 JSON to `data\assets.json`.

- [ ] **Step 2: Implement JSONL and manifest helpers**

Add:

```powershell
function Write-JsonLine([string]$Path, $Record) {
  New-Item -ItemType Directory -Force ([IO.Path]::GetDirectoryName($Path)) | Out-Null
  Add-Content -Encoding UTF8 -LiteralPath $Path (($Record | ConvertTo-Json -Compress -Depth 8))
}

function Build-AssetManifest([string]$OutputRoot) {
  $items = Get-ChildItem -LiteralPath (Join-Path $OutputRoot 'media') -Recurse -File -Filter metadata.json |
    ForEach-Object { Get-Content -Raw -Encoding UTF8 -LiteralPath $_.FullName | ConvertFrom-Json } |
    Sort-Object sourceRelativePath
  if (@($items.id | Group-Object | Where-Object Count -gt 1).Count) { throw 'Duplicate asset IDs.' }
  if (@($items.sourceRelativePath | Group-Object | Where-Object Count -gt 1).Count) { throw 'Duplicate source paths.' }
  $json = @($items) | ConvertTo-Json -Depth 10
  if ($json -match '[A-Za-z]:\\') { throw 'Manifest contains an absolute Windows path.' }
  Set-Content -Encoding UTF8 -LiteralPath (Join-Path $OutputRoot 'data\assets.json') ($json + "`n")
  return @($items)
}
```

- [ ] **Step 3: Implement runner parameters**

`transcode-library.ps1` must expose:

```powershell
param(
  [string]$SourceRoot = 'D:\L-One Center\视频素材参考2026',
  [string]$OutputRoot = 'D:\L-One Center\L-One素材库上传包',
  [string]$FfmpegRoot = 'D:\L-One Center\Tools\ffmpeg\bin',
  [ValidateSet('Pilot','All','Path')][string]$Mode = 'Pilot',
  [int]$PilotCount = 10,
  [string]$RelativePath,
  [switch]$Force
)
```

Runner rules:

- Validate all paths before processing.
- Record the source fingerprint summary before conversion.
- `Pilot` calls `Select-PilotSources` and processes at most `PilotCount` entries.
- `Path` requires an exact normalized relative MP4 path.
- `All` requires an explicit `-ConfirmAll` switch added to the parameter list; without it, exit with code 2.
- Append one JSONL record per result to the matching log.
- Rebuild manifest and both reports at the end.
- Exit code 1 when any selected item failed; exit code 0 when all selected items completed or skipped.

- [ ] **Step 4: Implement representative pilot selection**

`Select-PilotSources` probes candidates in stable path order until it can choose, where available:

- one landscape with audio
- one landscape without audio
- one portrait
- one duration under 2 seconds
- one duration over 10 seconds
- one maximum edge at or below 720
- one maximum edge above 1280
- one filename containing spaces
- one filename containing Chinese characters
- sources spanning at least five top-level categories

Deduplicate by stable ID and fill remaining positions from stable path order. Save the selected set to `reports\pilot-selection.json` before conversion.

- [ ] **Step 5: Generate JSON and HTML summaries**

The report includes:

- selected/completed/skipped/failed counts
- source and output byte totals and compression ratio
- per-asset title, category, dimensions, duration, source size, output size, status, thumbnail, preview, and playable MP4 link
- failures with source-relative paths and short error text

HTML must use relative links so it opens directly from D drive. It includes a compact grid with `<img loading="lazy">` and muted looping `<video>` previews.

- [ ] **Step 6: Run all unit/integration tests**

Expected: tests pass and fixture output contains no source-library paths, temporary files, GIF entries, or PNG entries.

### Task 6: Build the Independent Audit Tool

**Files:**
- Create: `D:\L-One Center\L-One素材库上传包\tools\audit-transcoded-library.ps1`
- Modify: `D:\L-One Center\L-One素材库上传包\tools\tests\transcode-library.tests.ps1`

- [ ] **Step 1: Add a failing audit test**

Run the audit against the valid synthetic bundle and expect exit code 0. Copy the bundle, delete `preview.webm`, run again, and expect a non-zero exit code with `missing preview.webm`.

- [ ] **Step 2: Implement audit parameters and checks**

```powershell
param(
  [string]$OutputRoot = 'D:\L-One Center\L-One素材库上传包',
  [string]$FfprobePath = 'D:\L-One Center\Tools\ffmpeg\bin\ffprobe.exe',
  [string]$SourceRoot = 'D:\L-One Center\视频素材参考2026',
  [string]$SourceFingerprint = 'D:\L-One Center\source-library-before.json'
)
```

Checks:

- FFprobe exists.
- Every metadata directory contains the four formal files and no `.working` file.
- All media constraints from Task 4 pass.
- Every manifest record resolves to existing files under `OutputRoot`.
- Manifest count equals valid metadata count.
- IDs and source relative paths are unique.
- No GIF, PNG, absolute local path, or URI outside the planned media root appears in manifest.
- Current source fingerprint count, length, and `LastWriteTimeUtc` exactly match the saved fingerprint.

Print all failures, then exit 1. Print counts and `Audit passed` only when no failures exist.

- [ ] **Step 3: Run valid and intentionally broken audit cases**

Expected: valid case passes; broken case fails for the injected reason; restoring the preview makes it pass again.

### Task 7: Execute the 10-Video Pilot Only

**Files:**
- Create: `D:\L-One Center\L-One素材库上传包\reports\pilot-selection.json`
- Create/update: generated media, manifest, logs, and reports under `D:\L-One Center\L-One素材库上传包\`

- [ ] **Step 1: Record the pre-run source summary**

Run:

```powershell
$source='D:\L-One Center\视频素材参考2026'
$files=Get-ChildItem -LiteralPath $source -Recurse -File
[pscustomobject]@{
  FileCount=$files.Count
  Mp4Count=@($files | Where-Object Extension -ieq '.mp4').Count
  GifCount=@($files | Where-Object Extension -ieq '.gif').Count
  PngCount=@($files | Where-Object Extension -ieq '.png').Count
  TotalBytes=($files | Measure-Object Length -Sum).Sum
} | ConvertTo-Json
```

Expected: 3049 total, 1523 MP4, 1510 GIF, 16 PNG, 21763041741 bytes.

- [ ] **Step 2: Dry-run selection**

Add and invoke `-DryRun` so the runner writes `pilot-selection.json` without creating media.

Expected: exactly 10 unique MP4 records, at least five categories where available, no GIF/PNG.

- [ ] **Step 3: Run the pilot**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\L-One Center\L-One素材库上传包\tools\transcode-library.ps1' -Mode Pilot -PilotCount 10
```

Expected: no more than 10 items processed; failures do not stop remaining items.

- [ ] **Step 4: Run the independent audit**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\L-One Center\L-One素材库上传包\tools\audit-transcoded-library.ps1'
```

Expected: `Audit passed`, 10 valid manifest entries, zero working files, unchanged source fingerprint.

- [ ] **Step 5: Open the visual report for manual review**

Open:

```text
D:\L-One Center\L-One素材库上传包\reports\conversion-summary.html
```

Review all ten thumbnails and hover previews; fully play at least one landscape/audio, one portrait, and one silent asset.

- [ ] **Step 6: Compare size and quality**

Report:

- total source size
- total output size
- average and largest compression ratio
- any visible artifacts
- any category or filename mapping errors
- projected storage for all 1523 MP4 files based on pilot ratio and duration mix

Do not start `-Mode All` during this task.

### Task 8: Record Pilot Results and Commit Documentation

**Files:**
- Modify: `D:\L-One Lab\03_独立项目\L-One-main-site\SITE_STATUS.md`
- Create: `D:\L-One Lab\03_独立项目\L-One-main-site\docs\transcoding\2026-06-14-pilot-results.md`

- [ ] **Step 1: Write the pilot result report**

Include exact FFmpeg version, selected source paths, automatic audit output, source/output sizes, compression projection, failures, and the decision required before full conversion.

- [ ] **Step 2: Update site status**

Record that the local conversion tool and pilot package exist on D drive, while the website and server media remain unchanged. State that full conversion and upload await pilot approval.

- [ ] **Step 3: Run final verification**

Run:

```powershell
git diff --check
node scripts/site-audit.js
node scripts/audit-motion-library.js
powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\L-One Center\L-One素材库上传包\tools\tests\transcode-library.tests.ps1'
powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\L-One Center\L-One素材库上传包\tools\audit-transcoded-library.ps1'
```

Expected: all commands exit 0.

- [ ] **Step 4: Commit only documentation changes in the website repository**

```powershell
git add SITE_STATUS.md docs/transcoding/2026-06-14-pilot-results.md docs/superpowers/plans/2026-06-14-local-video-transcoding-implementation.md
git commit -m "docs: record video transcoding pilot"
```

The generated media package and FFmpeg binaries stay outside the Git repository.

---

## Full-Batch Gate

The 1523-video full batch may begin only after the user approves:

- pilot visual quality
- total projected storage
- metadata and category mapping
- report and website preview behavior
- any failed or exceptional source files

The later command will require both `-Mode All` and `-ConfirmAll`, preserving an explicit safety boundary.
