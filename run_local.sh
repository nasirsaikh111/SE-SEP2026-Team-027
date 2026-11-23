#!/usr/bin/env bash
# Sangam Local Runner (Auto-setup + Ollama + Django + Vite)
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "=========================================="
echo " Starting Sangam Local Environment"
echo "=========================================="

# 1. Python & Backend Environment Setup
cd "$BACKEND_DIR"

PYTHON_BIN="python3"
if ! command -v python3 >/dev/null 2>&1; then
    if command -v python >/dev/null 2>&1; then
        PYTHON_BIN="python"
    else
        echo "Error: Python 3 is required but not found."
        exit 1
    fi
fi

if [ ! -f ".venv/bin/activate" ]; then
    echo "Creating Python virtual environment (.venv)..."
    rm -rf .venv
    $PYTHON_BIN -m venv .venv
    source .venv/bin/activate
    echo "Installing backend dependencies (this may take a minute on first run)..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
else
    source .venv/bin/activate
fi

# Ensure local backend environment file exists
if [ ! -f ".env" ]; then
    echo "Creating backend .env file..."
    cat <<EOF > .env
USE_SUPABASE=0
AI_PROVIDER=ollama
SANGAM_EMBEDDING_BACKEND=none
EOF
fi

# Apply migrations and seed demo data if database is fresh
echo "Checking local database..."
python manage.py migrate --no-input >/dev/null 2>&1 || python manage.py migrate

python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.accounts.models import User
if not User.objects.filter(email='hemant@ds.study.iitm.ac.in').exists():
    from django.core.management import call_command
    print('Seeding demo database with 15 test accounts...')
    call_command('seed_sangam_demo')
" 2>/dev/null || true

# 2. Frontend Environment Setup
cd "$FRONTEND_DIR"

if [ ! -f ".env" ]; then
    echo "Creating frontend .env..."
    echo "VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1" > .env
fi

if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies (npm install)..."
    npm install
fi

# 3. Check Ollama (Optional Local AI)
if curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "✓ Ollama is running on http://127.0.0.1:11434"
elif command -v ollama >/dev/null 2>&1; then
    echo "Starting Ollama service..."
    ollama serve >/dev/null 2>&1 &
    sleep 2
else
    echo "ℹ Ollama not detected (AI features will use graceful fallback)."
fi

# 4. Start Backend Server
cd "$BACKEND_DIR"
python manage.py runserver 127.0.0.1:8000 >/dev/null 2>&1 &
BACKEND_PID=$!
echo "✓ Django REST API running at http://127.0.0.1:8000/api/v1 (PID: $BACKEND_PID)"

# 5. Start Frontend Dev Server
cd "$FRONTEND_DIR"
npm run dev -- --host 127.0.0.1 &
FRONTEND_PID=$!
echo "✓ React Frontend running at http://127.0.0.1:5173 (PID: $FRONTEND_PID)"

echo "=========================================="
echo " Ready! Open your browser at:"
echo "   http://127.0.0.1:5173"
echo ""
echo " Demo Accounts (Password: SangamDemo!2026):"
echo "   Student: hemant@ds.study.iitm.ac.in"
echo "   Admin:   iic.admin@iitm.ac.in"
echo "   Mentor:  arjun.k@alumni.example.org"
echo "   (Or click the 'Demo Quick Access' buttons on /login)"
echo "=========================================="
echo "Press Ctrl+C to stop all services"

cleanup() {
    echo ""
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup INT TERM
wait
