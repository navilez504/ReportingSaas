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

The first registered user becomes **admin**; subsequent users are **user**.

## Quick start (Docker)

1. Copy environment template:

   ```bash
   cp .env.example .env
   ```

   Set `SECRET_KEY` to a long random string. Adjust `VITE_API_URL` if ports differ (browser must reach the API; default `http://localhost:8000`).

2. Build and run:

   ```bash
   docker compose up --build
   ```

3. Open **http://localhost** for the UI and **http://localhost:8000/docs** for OpenAPI. Register, upload a `.csv` or `.xlsx`, then open the dashboard and generate a PDF report.

Volumes persist Postgres data, uploads, and generated PDFs.

## Local development (without Docker UI)

### Database

Run Postgres 16 locally and create DB/user matching `DATABASE_URL`, or use only the `postgres` service:

```bash
docker compose up -d postgres
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

WeasyPrint needs system libraries on macOS/Linux (e.g. Pango/Cairo). On macOS: `brew install pango cairo gdk-pixbuf libffi`.

### Frontend

```bash
cd frontend
npm install
echo 'VITE_API_URL=http://localhost:8000' > .env.development
npm run dev
```

Visit **http://localhost:5173**.

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
