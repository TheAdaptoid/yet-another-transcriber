$ErrorActionPreference = "Stop"
$root = Join-Path $env:USERPROFILE ".yat"
$models = Join-Path $root "models"
$manifestPath = Join-Path $root "bin/manifest.json"
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Existing CLI manifest not found. Run setup-local.ps1 first."
}
$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
$expected = "29940d98d42b91fbd05ce489f3ecf7c72f0a42f027e4875919a28fb4c04ea2cf"
$name = "ggml-silero-v5.1.2.bin"
$target = Join-Path $models $name
$nonce = [guid]::NewGuid().ToString("N")
$download = Join-Path $models ("yat-vad-" + $nonce + ".download")
$manifestTemp = "$manifestPath.$nonce.tmp"
$manifestBackup = "$manifestPath.$nonce.bak"
$modelBackup = "$target.$nonce.bak"
New-Item -ItemType Directory -Force -Path $models | Out-Null
try {
    Invoke-WebRequest "https://huggingface.co/ggml-org/whisper-vad/resolve/main/$name" -OutFile $download
    if ((Get-FileHash -LiteralPath $download -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
        throw "VAD model hash mismatch"
    }
    $manifest | Add-Member -NotePropertyName vad_sha256 -NotePropertyValue $expected -Force
    $manifest | ConvertTo-Json -Depth 10 | Set-Content -Encoding utf8 -LiteralPath $manifestTemp
    $hadModel = Test-Path -LiteralPath $target -PathType Leaf
    if ($hadModel) { Copy-Item -LiteralPath $target -Destination $modelBackup }
    Move-Item -LiteralPath $download -Destination $target -Force
    try {
        [System.IO.File]::Replace($manifestTemp, $manifestPath, $manifestBackup)
    } catch {
        if ($hadModel) {
            [System.IO.File]::Copy($modelBackup, $target, $true)
            Remove-Item -LiteralPath $modelBackup -Force
        } else {
            Remove-Item -LiteralPath $target -Force
        }
        throw
    }
    if ($hadModel) { Remove-Item -LiteralPath $modelBackup -Force }
    Remove-Item -LiteralPath $manifestBackup -Force
    Write-Host "Installed and verified offline Silero VAD."
} finally {
    Remove-Item -LiteralPath $download, $manifestTemp -Force -ErrorAction SilentlyContinue
}
