# Create main project directory
New-Item -Name "CIS610" -ItemType Directory -Force
Set-Location -Path "CIS610"

# Define all directories to create
$directories = @(
    "data\raw",
    "data\processed",
    "data\external",
    "scripts",
    "notebooks",
    "models",
    "plots\eda",
    "plots\ml",
    "app\templates",
    "app\static",
    "tests"
)

# Create all directories
foreach ($dir in $directories) {
    New-Item -Name $dir -ItemType Directory -Force
}

# Create virtual environment (optional)
# python -m venv .venv

Write-Host "Project structure created successfully!"