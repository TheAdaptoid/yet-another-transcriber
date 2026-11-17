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
New-Item -ItemType Directory -Force -Path $models | Out-Null
try {
    Invoke-WebRequest "https://huggingface.co/ggml-org/whisper-vad/resolve/main/$name" -OutFile $download
    if ((Get-FileHash -LiteralPath $download -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
        throw "VAD model hash mismatch"
    }
    $manifest | Add-Member -NotePropertyName vad_sha256 -NotePropertyValue $expected -Force
    $manifest | ConvertTo-Json -Depth 10 | Set-Content -Encoding utf8 -LiteralPath $manifestTemp
    Move-Item -LiteralPath $download -Destination $target -Force
    [System.IO.File]::Replace($manifestTemp, $manifestPath, $manifestBackup)
    Remove-Item -LiteralPath $manifestBackup -Force
    Write-Host "Installed and verified offline Silero VAD."
} finally {
    Remove-Item -LiteralPath $download, $manifestTemp -Force -ErrorAction SilentlyContinue
}
