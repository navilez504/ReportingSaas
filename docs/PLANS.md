# Subscription plans and enforcement

## Plans

| Plan        | Trial duration | File uploads                          | Notes                          |
| ----------- | -------------- | ------------------------------------- | ------------------------------ |
| `trial`     | **3 days**     | Max **1** file (lifetime)             | Pro-equivalent BI/PDF; `trial_started_at` sets clock |
| `starter`   | —              | Max **3** files per **UTC month**     | Calendar month in UTC         |
| `pro`       | —              | Unlimited                             |                                |
| `enterprise`| —              | Unlimited                             | **Multi-tenant**: `organization_id` links users to an `organizations` row; admin creates the org when upgrading to enterprise. Datasets and reports remain scoped by **user id** today; you can extend listing rules to “all members of `organization_id`” in repositories if you need shared workspaces. |

## Where limits apply

- **Upload** (`POST /api/upload`): calls `ensure_upload_allowed()` → inactive account, expired trial, or file cap → **403** with a localized `detail` message.
- **Reports** (`POST /api/reports`): calls `ensure_account_can_write()` → inactive or **expired trial** → **403** (generating new PDFs is blocked; downloads of existing reports are still allowed).
- **Auth**: inactive users cannot log in and receive **403** `account_deactivated`. Valid JWTs for deactivated users fail on `GET /api/users/me` with the same error.
- **Dashboard / BI** (`GET /api/dashboard`, `/summary`, etc.): not blocked on trial expiry so users can still inspect existing data; product actions that create data obey the rules above.

## Plan KPIs (subscription)

`GET /api/dashboard/plan-summary` returns usage and flags for the **current** user.  
*(Business-intelligence KPIs remain at `GET /api/dashboard/summary`.)*

### Example: trial user

```json
{
  "plan": "trial",
  "is_active": true,
  "trial_started_at": "2026-04-01T12:00:00+00:00",
  "trial_ends_at": "2026-04-04T12:00:00+00:00",
  "trial_days_remaining": 1.5,
  "trial_expired": false,
  "organization_id": null,
  "files_total": 1,
  "files_this_month": 1,
  "file_limit": 1,
  "file_limit_scope": "total",
  "files_toward_limit": 1,
  "can_upload": true,
  "can_write": true,
  "notifications": []
}
```

### Example: starter at monthly cap

```json
{
  "plan": "starter",
  "is_active": true,
  "trial_started_at": null,
  "trial_ends_at": null,
  "trial_days_remaining": null,
  "trial_expired": false,
  "organization_id": null,
  "files_total": 10,
  "files_this_month": 3,
  "file_limit": 3,
  "file_limit_scope": "month",
  "files_toward_limit": 3,
  "can_upload": false,
  "can_write": true,
  "notifications": ["file_limit_reached"]
}
```

### Example: enterprise

```json
{
  "plan": "enterprise",
  "is_active": true,
  "trial_started_at": null,
  "trial_ends_at": null,
  "trial_days_remaining": null,
  "trial_expired": false,
  "organization_id": 2,
  "files_total": 4,
  "files_this_month": 1,
  "file_limit": null,
  "file_limit_scope": "none",
  "files_toward_limit": 4,
  "can_upload": true,
  "can_write": true,
  "notifications": []
}
```

`notifications` may include `trial_expiring_soon` (≤ 1 day left), `trial_expired`, or `file_limit_reached`.

## Admin API (`ADMIN` role)

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/api/admin/users` | Query: `plan`, `is_active`, `skip`, `limit` |
| GET | `/api/admin/users/export?format=csv|pdf` | Same filters as list |
| GET | `/api/admin/users/{id}` | User + embedded `plan_summary` |
| POST | `/api/admin/users/{id}/upgrade` | Body: `{ "plan": "pro", "organization_name": "Optional" }` |
| POST | `/api/admin/users/{id}/renew` | Restarts trial clock if `plan === trial` |
| POST | `/api/admin/users/{id}/status` | Body: `{ "active": true|false }` |

### Example: admin user list item

```json
{
  "id": 5,
  "email": "a@example.com",
  "full_name": "Alex",
  "role": "user",
  "plan": "starter",
  "trial_started_at": null,
  "is_active": true,
  "organization_id": null,
  "files_uploaded": 2,
  "created_at": "2026-04-05T10:00:00+00:00"
}
```

## Database migration

Apply after pulling changes:

```bash
cd backend && alembic upgrade head
```

Revision `002_subscription` adds `organizations`, `users.plan`, `users.trial_started_at`, `users.is_active`, `users.organization_id`. Existing users default to `plan=starter` (see migration `server_default`).

## Optional: Stripe

- Setting `STRIPE_WEBHOOK_SECRET` enables `POST /api/webhooks/stripe` (stub). In production, verify the payload with `stripe.Webhook.construct_event`, map subscription/product to `plan`, and call the same logic as `POST /api/admin/users/{id}/upgrade`.
- Email notifications for expiry or limits are not wired in this codebase; hook them from your worker or Stripe events.
