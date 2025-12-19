Write-Host "🚀 Starting Windows Deployment..." -ForegroundColor Cyan

# 1. Reset Environment (Optional: prevents conflicts)
if (Test-Path ".venv") {
    Write-Host "Removing old .venv..."
    Remove-Item -Recurse -Force .venv
}

# 2. Create Virtual Environment
Write-Host "Creating virtual environment..."
python -m venv .venv

# 3. Activate
Write-Host "Activating .venv..."
# In PowerShell scripts, we must 'dot source' the activate script to keep it active
. .venv\Scripts\Activate.ps1

# 4. Install Dependencies
Write-Host "Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# 5. Start Server
Write-Host "✅ Starting Server on Port 8080..." -ForegroundColor Green
# We use 'python -m uvicorn' to ensure it runs inside the venv
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload