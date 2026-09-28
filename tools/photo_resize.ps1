# Make the web portraits in photos/ from original photos, with Windows' own imaging
# (JPEG, PNG, HEIC and WebP decoders; no installs). For each job: apply the photo's
# own orientation flag, then an extra rotation (degrees clockwise), then a crop
# (fractions of the upright image: left, top, right, bottom), then shrink to at most
# `max` pixels on the long side and save as JPEG.
#   powershell -NoProfile -File tools\photo_resize.ps1 jobs.json
#   jobs.json: [{"src": "...", "dst": "photos/I123.jpg", "max": 480, "crop": [l,t,r,b] | null, "rotate": 0|90|180|270}]
# The crops and rotations live in pipeline/profiles/photos.json; the originals stay outside the repo.
param([Parameter(Mandatory = $true)][string]$JobFile)
Add-Type -AssemblyName PresentationCore
$jobs = Get-Content -Raw -Encoding UTF8 $JobFile | ConvertFrom-Json
$ok = 0; $bad = @()
foreach ($j in $jobs) {
  try {
    $fs = [System.IO.File]::OpenRead($j.src)
    $dec = [System.Windows.Media.Imaging.BitmapDecoder]::Create($fs, [System.Windows.Media.Imaging.BitmapCreateOptions]::PreservePixelFormat, [System.Windows.Media.Imaging.BitmapCacheOption]::OnLoad)
    $fs.Close()
    $f = $dec.Frames[0]
    $orient = 1
    try { $m = $f.Metadata; if ($m) { $o = $m.GetQuery('System.Photo.Orientation'); if ($o) { $orient = [int]$o } } } catch {}
    $angle = switch ($orient) { 3 { 180 } 6 { 90 } 8 { 270 } default { 0 } }
    if ($j.rotate) { $angle = ($angle + [int]$j.rotate) % 360 }
    # a plain 24-bit bitmap first: cropping some formats (indexed colour, odd DPI) otherwise fails
    $src = New-Object System.Windows.Media.Imaging.FormatConvertedBitmap($f, [System.Windows.Media.PixelFormats]::Bgr24, $null, 0)
    if ($angle -ne 0) { $src = New-Object System.Windows.Media.Imaging.TransformedBitmap($src, (New-Object System.Windows.Media.RotateTransform($angle))) }
    if ($j.crop) {
      # (PowerShell names ignore case: $imgW and $cropW must not be $W and $w)
      $imgW = $src.PixelWidth; $imgH = $src.PixelHeight
      $x = [int]([double]$j.crop[0] * $imgW); $y = [int]([double]$j.crop[1] * $imgH)
      $cropW = [int](([double]$j.crop[2] - [double]$j.crop[0]) * $imgW); $cropH = [int](([double]$j.crop[3] - [double]$j.crop[1]) * $imgH)
      $cropW = [Math]::Min($cropW, $imgW - $x); $cropH = [Math]::Min($cropH, $imgH - $y)
      # widen (never narrow) to a 4:5 portrait around the crop's centre, inside the image, so every
      # display box (all 4:5) shows the whole crop with the face where it was put
      $cx = $x + $cropW / 2.0; $cy = $y + $cropH / 2.0
      # (when the image isn't big enough to widen, trim the other side instead)
      if ($cropW / $cropH -lt 0.8) { $cropW = [int]($cropH * 0.8); if ($cropW -gt $imgW) { $cropW = $imgW; $cropH = [int]($imgW / 0.8) } }
      else { $cropH = [int]($cropW / 0.8); if ($cropH -gt $imgH) { $cropH = $imgH; $cropW = [int]($imgH * 0.8) } }
      $x = [int][Math]::Max(0, [Math]::Min($imgW - $cropW, $cx - $cropW / 2.0)); $y = [int][Math]::Max(0, [Math]::Min($imgH - $cropH, $cy - $cropH / 2.0))
      # copy the pixels out directly (CroppedBitmap fails on some scans' DPI settings)
      $stride = $cropW * 3; $buf = New-Object byte[] ($stride * $cropH)
      $src.CopyPixels((New-Object System.Windows.Int32Rect($x, $y, $cropW, $cropH)), $buf, $stride, 0)
      $src = [System.Windows.Media.Imaging.BitmapSource]::Create($cropW, $cropH, 96, 96, [System.Windows.Media.PixelFormats]::Bgr24, $null, $buf, $stride)
    }
    $scale = [Math]::Min(1.0, [double]$j.max / [Math]::Max($src.PixelWidth, $src.PixelHeight))
    if ($scale -lt 1.0) { $src = New-Object System.Windows.Media.Imaging.TransformedBitmap($src, (New-Object System.Windows.Media.ScaleTransform($scale, $scale))) }
    $conv = New-Object System.Windows.Media.Imaging.FormatConvertedBitmap($src, [System.Windows.Media.PixelFormats]::Bgr24, $null, 0)
    $enc = New-Object System.Windows.Media.Imaging.JpegBitmapEncoder
    $enc.QualityLevel = 85
    $enc.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($conv))
    $out = [System.IO.File]::Create($j.dst); $enc.Save($out); $out.Close()
    $ok++
  } catch { $bad += ($j.src + ': ' + $_.Exception.Message) }
}
"converted $ok of $($jobs.Count)"
$bad
