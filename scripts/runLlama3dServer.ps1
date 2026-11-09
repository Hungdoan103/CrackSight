# Serve Qwen3.5-4B-3D-Coder from E: via llama.cpp (vision projector attached).
$ErrorActionPreference = "Stop"
$ModelDir = "E:\Dự án FPT\CrackInspect\models\Qwen3.5-4B-3D-Coder"
$Gguf = Join-Path $ModelDir "Qwen3.5-4B-3D-Coder-Q4_K_M.gguf"
$Mmproj = Join-Path $ModelDir "mmproj-Qwen3.5-4B-BF16.gguf"

if (-not (Test-Path $Gguf)) {
    Write-Host "Chua co model. Chay truoc: scripts\downloadQwen353dCoder.ps1"
    exit 1
}

$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')
$llama = Get-Command llama-server -ErrorAction SilentlyContinue
if (-not $llama) {
    $candidates = @(
        "$env:LOCALAPPDATA\llama.cpp\llama-server.exe",
        "C:\Program Files\llama.cpp\llama-server.exe",
        "$env:USERPROFILE\llama.cpp\build\bin\Release\llama-server.exe"
    )
    $winget = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Filter "llama-server.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($winget) { $candidates = @($winget.FullName) + $candidates }
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) { $llama = Get-Item $c; break }
    }
}
if (-not $llama) {
    Write-Host "Khong thay llama-server. Cai llama.cpp (https://github.com/ggml-org/llama.cpp) roi them vao PATH."
    exit 1
}

$exe = if ($llama -is [System.Management.Automation.CommandInfo]) { $llama.Source } else { $llama.FullName }
Write-Host "Using $exe"
Write-Host "Model $Gguf"

$args = @(
    "-m", $Gguf,
    "--host", "127.0.0.1",
    "--port", "8080",
    "--n-gpu-layers", "999",
    "--ctx-size", "8192",
    "--parallel", "1"
)
if (Test-Path $Mmproj) {
    $args += @("--mmproj", $Mmproj)
}

& $exe @args
