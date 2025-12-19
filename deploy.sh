#!/bin/bash

echo "🚀 Starting Linux Deployment..."

# 1. Detect Python Command
# Checks if 'python3' exists, otherwise falls back to 'python'
if command -v python3 &> /dev/null; then
    PY_CMD="python3"
else
    PY_CMD="python"
fi

echo "Using Python command: $PY_CMD"

# 2. Create Virtual Environment
# --without-pip prevents crashes on some systems; we install pip manually next
$PY_CMD -m venv .venv --without-pip

# 3. Activate Virtual Environment
source .venv/bin/activate

# 4. Install Pip & Dependencies
# Force install pip to be safe
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
rm get-pip.py

echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# 5. Start the Server in Background
echo "Starting Uvicorn server on port 8080..."
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8080 > server.log 2>&1 &

echo "✅ Deployment Complete. Server running in background."