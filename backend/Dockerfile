# Production Dockerfile for Sangam Django Backend
FROM python:3.12-slim

# Prevent Python from writing .pyc files & enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir gunicorn uvicorn && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application source code
COPY . .

# Collect static files (with placeholder secret key)
RUN DJANGO_SECRET_KEY=temp-build-key python manage.py collectstatic --noinput || true

# Port exposed by hosting services (Render/Railway/Koyeb sets PORT automatically)
EXPOSE 8000

# Run migrations and start Gunicorn server with dynamic $PORT
CMD sh -c "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120"
