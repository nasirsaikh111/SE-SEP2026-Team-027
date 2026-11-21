#!/usr/bin/env bash
# Sangam Local Runner (Ollama + Django + Vite)
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "=========================================="
echo " Starting Sangam Local Environment"
echo "=========================================="

# 1. Check Ollama
if curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "✓ Ollama is running on http://127.0.0.1:11434"
else
    echo "Starting Ollama service..."
    ollama serve >/dev/null 2>&1 &
    sleep 2
fi

# 2. Start Backend Django API
cd "$BACKEND_DIR"
source .venv/bin/activate
python manage.py runserver 127.0.0.1:8000 &
BACKEND_PID=$!
echo "✓ Django REST API running at http://127.0.0.1:8000/api/v1 (PID: $BACKEND_PID)"

# 3. Start Frontend React Vite App
cd "$FRONTEND_DIR"
npm run dev -- --host 127.0.0.1 &
FRONTEND_PID=$!
echo "✓ React Frontend running at http://127.0.0.1:5173 (PID: $FRONTEND_PID)"

echo "=========================================="
echo " Ready! Open: http://127.0.0.1:5173"
echo " Test accounts password: SangamDemo!2026"
echo " Student: hemant@ds.study.iitm.ac.in"
echo " Admin:   iic.admin@iitm.ac.in"
echo " Mentor:  arjun.k@alumni.example.org"
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
