# Multi-tenant reporting SaaS

Production-oriented starter for automated business reporting: **FastAPI** + **PostgreSQL** + **React (Vite)** with JWT auth, per-user data isolation, CSV/Excel ingestion (Pandas), KPI engine, dashboards (Recharts), and PDF reports (WeasyPrint).

## Architecture

- **Backend**: `backend/` — FastAPI, SQLAlchemy, Alembic, JWT (bcrypt passwords), role `admin` | `user`.
- **Frontend**: `frontend/` — React, TailwindCSS, Recharts.
- **Infra**: `docker-compose.yml` — Postgres, API, static UI (nginx).

API routes are prefixed with `/api`:

| Area        | Prefix        |
|------------|----------------|
| Auth       | `/api/auth`    |
| Users      | `/api/users`   |
| Upload     | `/api/upload`  |
| Dashboard  | `/api/dashboard` |
| Reports    | `/api/reports` |

**Admin** is not automatic. Set **`ADMIN_EMAILS`** in `.env` (comma-separated addresses). Those accounts get `role=admin` when they register, on login, on `GET /api/users/me`, and on API startup. Everyone else registers as a normal **user**.

## Quick start (Docker)

1. Copy environment template:

   ```bash
   cp .env.example .env
   ```

   Set `SECRET_KEY` to a long random string. Set **`ADMIN_EMAILS`** to your own email (and any other admins), e.g. `ADMIN_EMAILS=you@company.com`. Leave **`VITE_API_URL` empty** for Docker: the UI is served on port 80 and nginx proxies `/api` to the backend, so the browser does not call `:8000` directly. Set `VITE_API_URL` only if you host the static UI and API on different public URLs.

2. Build and run with the local-development overlay:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
   ```

3. Open **http://localhost** for the UI and **http://localhost:8000/docs** for OpenAPI. Register with an address listed in **`ADMIN_EMAILS`** if you need the Admin panel; other addresses are regular users. Upload a `.csv` or `.xlsx`, then open the dashboard and generate a PDF report.

Volumes persist Postgres data, uploads, and generated PDFs.

## Production on EC2

Use the base compose file plus the production overlay for EC2:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d --build
```

### Why the compose files are split

- `docker-compose.yml` contains the shared services and no host-port bindings.
- `docker-compose.dev.yml` exposes the local-friendly ports: UI on `80`, API on `8000`, Postgres on `5432`.
- `docker-compose.prod.yml` exposes only loopback ports for Nginx: UI on `127.0.0.1:8080`, API on `127.0.0.1:8001`.
- This avoids the merge problem where local ports leaked into production and caused EC2 conflicts on ports `80` and `8000`.

### Production setup steps

1. Copy the production env template:

   ```bash
   cp .env.production.example .env.production
   ```

2. Edit `.env.production` and set real values:

   - `SECRET_KEY`
   - `POSTGRES_PASSWORD`
   - `CORS_ORIGINS`
   - `VITE_API_URL`
   - `ADMIN_EMAILS` and `PUBLIC_APP_URL`
   - `SMTP_*` if you want trial reminders and payment emails (Gmail: App Password; `SMTP_FROM` usually matches `SMTP_USER`)
   - optional Stripe price IDs and keys when billing is live
   - optionally `DATABASE_URL` if you use AWS RDS instead of the bundled Postgres container

3. Start the stack:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d --build
   ```

4. Install the sample Nginx site config from `deploy/nginx/reportingsaas.conf`, replace `example.com`, then enable it:

   ```bash
   sudo cp deploy/nginx/reportingsaas.conf /etc/nginx/sites-available/reportingsaas
   sudo nano /etc/nginx/sites-available/reportingsaas
   sudo ln -s /etc/nginx/sites-available/reportingsaas /etc/nginx/sites-enabled/reportingsaas
   sudo nginx -t
   sudo systemctl restart nginx
   ```

5. Add HTTPS:

   ```bash
   sudo certbot --nginx -d example.com -d www.example.com
   ```

### Production notes

- **Email not sending?** Set **`SMTP_HOST`**, **`SMTP_USER`**, **`SMTP_PASSWORD`**, **`SMTP_FROM`** in the env file the stack uses: **`.env.production`** is loaded into the backend container when you use **`docker-compose.prod.yml`**; local Docker with **`docker-compose.dev.yml`** loads **`.env`**. Non-Docker runs use project **`backend/.env`** or root **`.env`** (see [backend app config](backend/app/core/config.py)). Check **`GET /health`** → **`"smtp_configured": true`**.
- Do not expose PostgreSQL publicly in production.
- Keep only ports `22`, `80`, and `443` open in the EC2 security group.
- Prefer a read-only GitHub deploy key on the server.
- Consider AWS RDS for PostgreSQL if this moves beyond a single-instance deployment.
- Back up the database, uploads, and generated reports.

## Local development (without Docker UI)

### Database

Run Postgres 16 locally and create DB/user matching `DATABASE_URL`, or expose only the `postgres` service with the dev overlay:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env      # or set env vars
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Before accepting real payments, see **[docs/GO_LIVE.md](docs/GO_LIVE.md)** (Stripe webhooks, `PUBLIC_APP_URL`, backups, secrets).

WeasyPrint needs system libraries on macOS/Linux (e.g. Pango/Cairo). On macOS: `brew install pango cairo gdk-pixbuf libffi`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit **http://localhost:5173**. The dev server proxies **`/api`** to **`http://127.0.0.1:8000`** (override with env **`VITE_API_PROXY_TARGET`** if needed). Leave **`VITE_API_URL`** unset so the app uses relative `/api` like in Docker.

If the UI and API run on different hosts during dev, set `VITE_API_URL` to the API origin (no trailing slash) in `.env.development.local`.

## Security notes

- Change `SECRET_KEY` and database credentials for any shared environment.
- CORS is driven by `CORS_ORIGINS` (comma-separated).
- Uploads are limited by `MAX_UPLOAD_MB` and extension (`.csv`, `.xlsx`).
- All business tables are scoped by `user_id`; repositories always filter on the authenticated user.

## Project layout

```
backend/app/
  core/          # config, security, deps, logging
  models/        # SQLAlchemy models
  schemas/       # Pydantic
  repositories/  # DB access
  services/      # business logic (upload, KPI, PDF)
  routers/       # HTTP routes
frontend/src/
  api/           # Axios client
  context/       # Auth
  pages/         # Screens
  components/    # Layout, etc.
```

## License

Provided as sample code for your consultancy project; adjust licensing as needed.
