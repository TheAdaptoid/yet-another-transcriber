$ErrorActionPreference = "Stop"
foreach ($tool in @("git", "cmake")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "Required setup tool not found: $tool"
    }
}
$root = Join-Path $env:USERPROFILE ".yat"
$bin = Join-Path $root "bin"
$models = Join-Path $root "models"
$tmp = Join-Path $root "tmp"
New-Item -ItemType Directory -Force -Path $bin, $models, $tmp | Out-Null
$commit = "d1be6fde11ac6e0407606b4e42fe72d34add8037"
$source = Join-Path $tmp ("whisper-build-" + [guid]::NewGuid().ToString("N"))
git clone --no-checkout https://github.com/ggml-org/whisper.cpp.git $source
if ($LASTEXITCODE -ne 0) { throw "Source download failed" }
git -C $source checkout --detach $commit
if ($LASTEXITCODE -ne 0) { throw "Source checkout failed" }
$tagCommit = git -C $source rev-list -n 1 v1.9.5
if ($LASTEXITCODE -ne 0 -or $tagCommit -ne $commit) { throw "Release tag mismatch" }
cmake -S $source -B "$source/build" -A x64 -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_EXAMPLES=ON
if ($LASTEXITCODE -ne 0) { throw "CMake configure failed" }
cmake --build "$source/build" --config Release --target whisper-cli
if ($LASTEXITCODE -ne 0) { throw "whisper-cli build failed" }
$release = Join-Path $source "build/bin/Release"
if (-not (Test-Path "$release/whisper-cli.exe")) { throw "CLI missing after build" }
Copy-Item "$release/*.exe" $bin -Force
Copy-Item "$release/*.dll" $bin -Force
$versionText = & "$bin/whisper-cli.exe" --version
if ($LASTEXITCODE -ne 0 -or "$versionText" -notmatch "1\.9\.5") {
    throw "Built CLI did not report version 1.9.5"
}
$model = Join-Path $models "ggml-base.en.bin"
$download = "$model.download"
Invoke-WebRequest "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin" -OutFile $download
$expected = "a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002"
if ((Get-FileHash $download -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
    throw "Model hash mismatch; downloaded file retained for inspection"
}
Move-Item $download $model -Force
$cliHash = (Get-FileHash "$bin/whisper-cli.exe" -Algorithm SHA256).Hash.ToLowerInvariant()
$dllHashes = @{}
Get-ChildItem "$release/*.dll" | ForEach-Object {
    $dllHashes[$_.Name] = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
}
@{
    version = "v1.9.5"
    source_commit = $commit
    model_sha256 = $expected
    cli_sha256 = $cliHash
    dll_sha256 = $dllHashes
} | ConvertTo-Json | Set-Content -Encoding utf8 "$bin/manifest.json"
Write-Host "Installed whisper.cpp v1.9.5 CPU CLI and verified model."
