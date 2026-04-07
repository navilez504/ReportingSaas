"""HTTP helpers (client IP behind reverse proxy)."""

from fastapi import Request


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()[:45]
    if request.client and request.client.host:
        return str(request.client.host)[:45]
    return ""


def user_agent_string(request: Request) -> str:
    ua = request.headers.get("user-agent") or ""
    return ua[:512]
