# Download Qwen3.5-4B-3D-Coder (Q4 + vision projector) onto drive E.
$ErrorActionPreference = "Stop"
$ModelDir = "E:\Dự án FPT\CrackInspect\models\Qwen3.5-4B-3D-Coder"
$HfHome = "E:\Dự án FPT\models\huggingface"
New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null
New-Item -ItemType Directory -Force -Path $HfHome | Out-Null
$env:HF_HOME = $HfHome
$env:HUGGINGFACE_HUB_CACHE = Join-Path $HfHome "hub"
$env:HF_HUB_DISABLE_XET = "1"

Write-Host "HF_HOME = $env:HF_HOME"
Write-Host "Model dir = $ModelDir"
Write-Host "Downloading Q4_K_M (~2.7 GB) + mmproj (~0.64 GB) onto E: ..."

python -m pip install -q "huggingface_hub>=0.26"
python -c @"
import os
os.environ['HF_HUB_DISABLE_XET'] = '1'
os.environ['HF_HOME'] = r'$HfHome'
from huggingface_hub import hf_hub_download
repo = 'ccore/Qwen3.5-4B-3D-Coder'
local = r'$ModelDir'
for name in [
    'Qwen3.5-4B-3D-Coder-Q4_K_M.gguf',
    'mmproj-Qwen3.5-4B-BF16.gguf',
    'README.md',
    'LICENSE',
]:
    print('GET', name, flush=True)
    path = hf_hub_download(repo_id=repo, filename=name, local_dir=local)
    print('OK', path, flush=True)
print('done')
"@

Get-ChildItem $ModelDir | Select-Object Name, @{N='GB';E={[math]::Round($_.Length/1GB,2)}} | Format-Table -AutoSize
Write-Host "Xong. Model tren E, khong ghi vao C:\Users\...\ .cache\huggingface"
