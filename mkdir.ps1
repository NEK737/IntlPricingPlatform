# Create FastAPI app structure inside CIS610
$base = "C:\Projects\CIS610\fastapi_app"

# Create main folder
New-Item -ItemType Directory -Force -Path $base

# Create subfolders
New-Item -ItemType Directory -Force -Path "$base\routers"
New-Item -ItemType Directory -Force -Path "$base\__pycache__"

# Create empty files
New-Item -ItemType File -Force -Path "$base\main.py"
New-Item -ItemType File -Force -Path "$base\routers\chat.py"
New-Item -ItemType File -Force -Path "$base\routers\facilities.py"
New-Item -ItemType File -Force -Path "$base\utils.py"

Write-Output "✅ FastAPI directory structure created at $base"
