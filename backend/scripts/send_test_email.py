#!/usr/bin/env python3
"""Send one test email using the same SMTP settings as the API.

Usage (from repo root with backend deps installed):

  cd backend && PYTHONPATH=. python scripts/send_test_email.py you@example.com

Or with Docker (loads env from your compose / --env-file):

  docker compose -f docker-compose.yml -f docker-compose.prod.yml \\
    --env-file .env.production run --rm backend \\
    python scripts/send_test_email.py you@example.com
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure `app` package resolves when run as `python scripts/send_test_email.py`
_backend = Path(__file__).resolve().parents[1]
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/send_test_email.py recipient@example.com", file=sys.stderr)
        sys.exit(2)
    to = sys.argv[1].strip()
    from app.core.config import get_settings
    from app.services.email_service import send_email

    s = get_settings()
    if not s.smtp_host:
        print("ERROR: SMTP_HOST is empty. Set SMTP_* in .env (or pass --env-file to Docker).", file=sys.stderr)
        sys.exit(1)
    ok = send_email(
        s,
        to,
        "Test — Reporting SaaS",
        "This is a test from scripts/send_test_email.py.\n\nIf you received it, SMTP is working.",
    )
    print("send_email:", "ok" if ok else "failed")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
