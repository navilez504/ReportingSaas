"""Localized API error and meta strings (English / Spanish) via Accept-Language."""

from __future__ import annotations

from typing import Literal

MsgLang = Literal["en", "es"]

MESSAGES: dict[str, dict[MsgLang, str]] = {
    "not_authenticated": {
        "en": "Not authenticated",
        "es": "No autenticado",
    },
    "invalid_or_expired_token": {
        "en": "Invalid or expired token",
        "es": "Token no válido o caducado",
    },
    "invalid_token_subject": {
        "en": "Invalid token subject",
        "es": "Identificador de token no válido",
    },
    "user_not_found": {
        "en": "User not found",
        "es": "Usuario no encontrado",
    },
    "admin_role_required": {
        "en": "Admin role required",
        "es": "Se requiere rol de administrador",
    },
    "no_dataset_upload_first": {
        "en": "No dataset found. Upload data first.",
        "es": "No hay conjunto de datos. Suba datos primero.",
    },
    "dataset_not_found": {
        "en": "Dataset not found",
        "es": "Conjunto de datos no encontrado",
    },
    "bi_requires_columns": {
        "en": "BI requires columns: fecha, cantidad, precio_unitario (or recognized aliases).",
        "es": "El análisis BI requiere columnas: fecha, cantidad, precio_unitario (o alias reconocidos).",
    },
    "report_not_found": {
        "en": "Report not found",
        "es": "Informe no encontrado",
    },
    "file_missing_server": {
        "en": "File missing on server",
        "es": "El archivo no está en el servidor",
    },
    "metric_not_found": {
        "en": "Metric not found",
        "es": "Métrica no encontrada",
    },
    "unsupported_file_type": {
        "en": "Unsupported file type",
        "es": "Tipo de archivo no admitido",
    },
    "filename_required": {
        "en": "Filename required",
        "es": "Se requiere nombre de archivo",
    },
    "invalid_extension": {
        "en": "Invalid extension. Allowed: {allowed}",
        "es": "Extensión no válida. Permitidas: {allowed}",
    },
    "file_too_large": {
        "en": "File too large (max {max_mb} MB)",
        "es": "Archivo demasiado grande (máx. {max_mb} MB)",
    },
    "could_not_parse_file": {
        "en": "Could not parse file: {error}",
        "es": "No se pudo analizar el archivo: {error}",
    },
    "no_data_rows": {
        "en": "No data rows found",
        "es": "No se encontraron filas de datos",
    },
    "email_already_registered": {
        "en": "Email already registered",
        "es": "El correo ya está registrado",
    },
    "incorrect_email_or_password": {
        "en": "Incorrect email or password",
        "es": "Correo o contraseña incorrectos",
    },
    "upload_dataset_kpis": {
        "en": "Upload a dataset to see KPIs",
        "es": "Suba un conjunto de datos para ver los KPIs",
    },
}


def normalize_lang(lang: str | None) -> MsgLang:
    if lang and str(lang).lower().startswith("es"):
        return "es"
    return "en"


def parse_accept_language(header: str | None) -> MsgLang:
    """Parse Accept-Language; prefers first matching es or en."""
    if not header or not str(header).strip():
        return "en"
    for part in str(header).split(","):
        token = part.split(";")[0].strip().lower()
        if not token:
            continue
        primary = token.split("-")[0]
        if primary == "es":
            return "es"
        if primary == "en":
            return "en"
    return "en"


def api_msg(key: str, lang: str | MsgLang, **kwargs: str | float) -> str:
    """Return localized message; unknown keys fall back to the key itself."""
    l = normalize_lang(lang) if isinstance(lang, str) else lang
    row = MESSAGES.get(key)
    if row is None:
        return key
    template = row.get(l) or row["en"]
    if kwargs:
        return template.format(**kwargs)
    return template
