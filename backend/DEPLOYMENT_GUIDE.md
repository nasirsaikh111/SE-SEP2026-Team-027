# Sangam Backend Deployment Guide (Render / Railway / Koyeb)

This directory is production-ready for deployment using Docker + Gunicorn across all top cloud platforms.

---

## Option 1: Render.com (Recommended - 100% Free Tier Available)

1. Go to [dashboard.render.com](https://dashboard.render.com) and log in with GitHub.
2. Click **New +** $\rightarrow$ **Web Service**.
3. Select your repository: `SE-SEP2026-Team-027` (or upload the backend folder).
4. Configure the service settings:
   - **Root Directory:** `backend` (if repo root) or `.`
   - **Environment:** `Python` or `Docker` (both configured!)
   - **Build Command:** `pip install --upgrade pip && pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - **Start Command:** `python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120`
5. Add Environment Variables in Render Dashboard:
   - `DJANGO_SECRET_KEY`: `<your-random-secret-key>`
   - `DJANGO_DEBUG`: `false`
   - `DJANGO_ALLOWED_HOSTS`: `.onrender.com,localhost,127.0.0.1`
   - `DATABASE_URL`: Your Supabase/Neon PostgreSQL connection URL
   - `CORS_ALLOWED_ORIGINS`: `https://frontend-orpin-iota-73.vercel.app,https://sangam-step2.vercel.app`
6. Click **Deploy Web Service**! Render will automatically build the service and give you a public URL (e.g., `https://sangam-backend.onrender.com`).

---

## Option 2: Railway.app

1. Go to [railway.com](https://railway.com) and sign in with GitHub.
2. Click **New Project** $\rightarrow$ **Deploy from GitHub Repo**.
3. Select the repository and set the root directory to `backend`.
4. Railway will automatically detect `railway.json` and the `Dockerfile`.
5. Under **Variables**, add:
   - `DJANGO_SECRET_KEY`: `<your-random-secret-key>`
   - `DJANGO_DEBUG`: `false`
   - `DJANGO_ALLOWED_HOSTS`: `.railway.app,localhost,127.0.0.1`
   - `DATABASE_URL`: Your PostgreSQL database URL
   - `CORS_ALLOWED_ORIGINS`: `https://frontend-orpin-iota-73.vercel.app`
6. Under Settings $\rightarrow$ **Networking**, click **Generate Domain**.

---

## Option 3: Koyeb

1. Go to [app.koyeb.com](https://app.koyeb.com) and create an account.
2. Click **Create Service** $\rightarrow$ **GitHub**.
3. Select the repository and set directory to `backend`.
4. Koyeb detects `Dockerfile` and `koyeb.yaml`.
5. Set environment variables (`DJANGO_SECRET_KEY`, `DATABASE_URL`, etc.).
6. Click **Deploy**.

---

## After Deployment: Connect Frontend to Backend

Once your backend is live (e.g. `https://sangam-backend.onrender.com`):
In your Vercel Dashboard for `frontend-orpin-iota-73`:
1. Go to **Settings** $\rightarrow$ **Environment Variables**.
2. Update `VITE_API_BASE_URL` to `https://sangam-backend.onrender.com/api/v1`.
3. Redeploy the frontend.
