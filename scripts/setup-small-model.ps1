$ErrorActionPreference = "Stop"
$root = Join-Path $env:USERPROFILE ".yat"
$manifest = Join-Path $root "bin/manifest.json"
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
    throw "Existing CLI manifest not found. Run setup-local.ps1 first."
}
$models = Join-Path $root "models"
New-Item -ItemType Directory -Force -Path $models | Out-Null
$name = "ggml-small.en.bin"
$target = Join-Path $models $name
$download = Join-Path $models ("yat-small-" + [guid]::NewGuid().ToString("N") + ".download")
$backup = "$download.bak"
$expected = "c6138d6d58ecc8322097e0f987c32f1be8bb0a18532a3f88f734d1bbf9c41e5d"
try {
    Invoke-WebRequest "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$name" -OutFile $download
    if ((Get-FileHash -LiteralPath $download -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
        throw "Small model hash mismatch"
    }
    if (Test-Path -LiteralPath $target) {
        [System.IO.File]::Replace($download, $target, $backup)
        Remove-Item -LiteralPath $backup -Force
    } else {
        [System.IO.File]::Move($download, $target)
    }
    Write-Host "Installed and verified small.en. Run 'yat model select small.en' to use it."
} finally {
    Remove-Item -LiteralPath $download -Force -ErrorAction SilentlyContinue
}
