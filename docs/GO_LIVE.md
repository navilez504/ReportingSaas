# Go-live checklist (billing and operations)

Use this before taking real payments. It complements `.env.example` and Docker/README setup.

## Stripe

1. Create **Products** and recurring **Prices** in Stripe (USD recommended for automatic price display on `/api/billing/plans`; other currencies fall back to static copy).
2. Set **`STRIPE_SECRET_KEY`** (live), **`STRIPE_PRICE_*`** to each Price API id, and **`STRIPE_WEBHOOK_SECRET`** from a **live** webhook endpoint.
3. Webhook URL: `https://YOUR_API_ORIGIN/api/webhooks/stripe`. Enable at least: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`.
4. Configure **Customer portal** in Stripe Dashboard (which products customers can switch to, invoice history, cancellation behavior).
5. Decide on **Stripe Tax** and enable if you need tax calculation.

## App URLs

- Set **`PUBLIC_APP_URL`** to the **browser-visible** origin where users land after Checkout and Billing Portal (no trailing slash).  
  Examples: `https://app.example.com`, local Vite `http://localhost:5173`, Docker UI on port 80 `http://localhost`.
- Ensure **`CORS_ORIGINS`** includes that same UI origin.

## Secrets and database

- Replace **`SECRET_KEY`** with a strong random value; plan how you will rotate JWTs if it changes.
- Use unique DB credentials in production; **`DATABASE_URL`** must not use defaults from examples.
- Schedule **Postgres backups** (snapshot or `pg_dump`) and test a **restore** at least once.
- Run migrations after deploy: `alembic upgrade head` (Docker image already runs this on container start).

## Email

- Set **`SMTP_*`** for real sends, or leave **`SMTP_HOST`** empty for log-only mode (not acceptable for customer-facing production).

## Legal

- Replace or have counsel review in-app **Terms**, **Privacy**, and **Refunds** copy under `frontend/src/i18n/translations.js` (`legal.*` keys).
- For EU-focused traffic, consider a cookie/consent banner beyond the registration acknowledgment.

## Reconciliation

- The API runs a **daily Stripe reconciliation** job (subscription rows vs Stripe). Monitor logs for `Stripe reconciliation updated` and webhook errors.

## Postgres: `password authentication failed for user "reporting"`

The bundled Postgres image sets the **`reporting`** user password **only on first start**, when the **`pgdata` volume is empty**. After that, changing **`POSTGRES_PASSWORD`** in `.env.production` does **not** change the database password—the backend will still need the password that was used when the volume was created.

**Fix (pick one):**

1. **Keep existing data** — Set **`POSTGRES_PASSWORD`** in `.env.production` to the **same** password that was used the first time the stack created the DB volume (and redeploy so the backend’s `DATABASE_URL` matches).

2. **Reset DB (destroys all data)** — From the app directory:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production down
   docker volume ls | grep pgdata   # note exact volume name, e.g. reportingsaas_pgdata
   docker volume rm THAT_VOLUME_NAME
   docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d --build
   ```

   Then Postgres boots with the **`POSTGRES_PASSWORD`** currently in `.env.production`.

Ensure **`POSTGRES_USER`**, **`POSTGRES_PASSWORD`**, and **`POSTGRES_DB`** in `.env.production` match what you intend; the backend URL is built from these values in `docker-compose.prod.yml`. Passwords with **`@` `: `#` `%` `+`** must be **URL-encoded** if you ever set **`DATABASE_URL`** manually.
