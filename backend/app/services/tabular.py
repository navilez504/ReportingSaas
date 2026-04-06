"""
Robust CSV / flat-table parsing: delimiter sniffing and repair when pandas
reads the whole row as a single column (common with ';' CSV or bad exports).
"""

from __future__ import annotations

import csv
import io
import re
from typing import Any

import pandas as pd

from app.services.kpi import _clean_scalar_number


def expand_stale_columns_hint(columns_hint: list[str] | None) -> list[str] | None:
    """
    DB metadata sometimes stores column names as one CSV string:
    ['id,fecha,cliente,...'] instead of separate names. Split that into a real list.
    """
    if not columns_hint:
        return None
    if len(columns_hint) != 1:
        return [str(c).strip() for c in columns_hint]
    s = str(columns_hint[0]).strip()
    if "," not in s and ";" not in s:
        return [s]
    sep = _detect_sep(s + "\n")
    parts = split_line_smart(s, sep)
    if len(parts) >= 2:
        return [p.strip() for p in parts]
    return [s]


def _tokens_look_like_header_row(parts: list[str]) -> bool:
    """Heuristic: first row of file is a header row (names) vs first data row."""
    if len(parts) < 2:
        return False
    head = [p.strip().lower() for p in parts[: min(10, len(parts))]]
    keywords = {
        "id",
        "fecha",
        "date",
        "cliente",
        "customer",
        "producto",
        "product",
        "categoria",
        "category",
        "cantidad",
        "qty",
        "quantity",
        "precio",
        "price",
        "region",
        "vendedor",
        "nombre",
        "name",
        "total",
        "importe",
    }
    if any(h in keywords for h in head):
        return True

    def looks_numeric_token(t: str) -> bool:
        t = t.replace(",", "").replace(".", "")
        if not t:
            return False
        if re.match(r"^-?\d+$", t):
            return True
        if re.match(r"^\d{4}-\d{2}-\d{2}", t):
            return True
        return False

    non_numeric = sum(1 for h in head if h and not looks_numeric_token(h))
    return non_numeric >= max(2, (len(head) + 1) // 2)


def collapse_us_thousands_groups(parts: list[str]) -> list[str]:
    """
    Merge adjacent all-digit tokens where each chunk after the first has length 3
    (US-style thousands: 4 + 200 -> 4200; 1 + 234 + 567 -> 1234567).
    Does not merge when the next token is not exactly 3 digits (avoids dates / EU decimals).
    """
    if not parts:
        return parts
    out: list[str] = []
    i = 0
    while i < len(parts):
        p = parts[i]
        if not p.isdigit():
            out.append(p)
            i += 1
            continue
        acc = p
        i += 1
        while i < len(parts):
            nxt = parts[i]
            if nxt.isdigit() and len(nxt) == 3:
                acc += nxt
                i += 1
            else:
                break
        out.append(acc)
    return out


def split_line_smart(line: str, sep: str) -> list[str]:
    """
    Split a CSV line using csv.reader (respects quotes). Do not merge digit groups here:
    merging 4+120 would break separate cantidad/precio columns; money thousands belong in
    preprocess_csv_text_merge_thousands / quoted fields / ';' delimited files.
    """
    line = line.rstrip("\r\n")
    if sep == ",":
        try:
            row = next(csv.reader([line], delimiter=","))
        except Exception:
            row = line.split(",")
        return [p.strip() for p in row]
    if sep == ";":
        try:
            row = next(csv.reader([line], delimiter=";"))
        except Exception:
            row = line.split(";")
        return [p.strip() for p in row]
    return [p.strip() for p in line.split(sep)]


def preprocess_csv_text_merge_thousands(text: str) -> str:
    """
    Rewrite comma-delimited CSV so unquoted money like 4,200 becomes a single field
    before pandas tokenizes on commas.
    """
    sample = text[: 8192]
    sep = _detect_sep(sample)
    if sep != ",":
        return text
    lines = text.splitlines()
    out_lines: list[str] = []
    for line in lines:
        if not line.strip():
            out_lines.append(line)
            continue
        try:
            row = next(csv.reader([line], delimiter=","))
        except Exception:
            out_lines.append(line)
            continue
        parts = [p.strip() for p in row]
        parts = collapse_us_thousands_groups(parts)
        buf = io.StringIO()
        csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="").writerow(parts)
        out_lines.append(buf.getvalue())
    result = "\n".join(out_lines)
    if text.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    return result


def _detect_sep(sample: str) -> str:
    """Prefer ; for EU CSV when it dominates commas inside fields."""
    if not sample:
        return ","
    semi = sample.count(";")
    comma = sample.count(",")
    tab = sample.count("\t")
    if tab >= max(semi, comma, 1) and tab > 0:
        return "\t"
    if semi > comma:
        return ";"
    return ","


def _read_csv_string(text: str, **kwargs: Any) -> pd.DataFrame:
    """pandas 1.x vs 2.x: on_bad_lines may be unavailable."""
    kw = dict(kwargs)
    try:
        return pd.read_csv(io.StringIO(text), on_bad_lines="skip", **kw)
    except TypeError:
        return pd.read_csv(io.StringIO(text), **kw)


def read_csv_bytes(content: bytes) -> pd.DataFrame:
    """Read CSV with delimiter sniffing; avoids single-column false reads."""
    text = content.decode("utf-8-sig", errors="replace")
    text = preprocess_csv_text_merge_thousands(text)
    sample = text[: 1024 * 8]
    sep = _detect_sep(sample)

    for try_sep in [sep, ",", ";", "\t", "|"]:
        try:
            df = _read_csv_string(text, sep=try_sep, engine="python")
            if df.shape[1] >= 2:
                return df
        except Exception:
            continue
    try:
        return _read_csv_string(text, sep=None, engine="python")
    except Exception:
        return _read_csv_string(text, sep=",", engine="python")


def repair_single_column_dataframe(
    df: pd.DataFrame,
    columns_hint: list[str] | None = None,
) -> pd.DataFrame:
    """Split a single text column that actually contains comma/semicolon-separated values."""
    if df.empty or df.shape[1] != 1:
        return df
    hint = expand_stale_columns_hint(list(columns_hint) if columns_hint is not None else None)

    col = df.columns[0]
    series = df.iloc[:, 0].astype(str)
    probe = str(col) + "\n" + (series.iloc[0] if len(series) else "")
    sep = _detect_sep(probe)

    # Metadata listed all names as one CSV string — split every row to real columns
    if hint and len(hint) >= 2:
        w = len(hint)
        rows: list[dict[str, Any]] = []
        for i in range(len(series)):
            parts = split_line_smart(str(series.iloc[i]), sep)
            if len(parts) < w:
                parts = parts + [""] * (w - len(parts))
            elif len(parts) > w:
                parts = parts[:w]
            rows.append(dict(zip(hint, parts)))
        if rows:
            out = pd.DataFrame(rows)
            out.columns = [str(c).strip() for c in out.columns]
            return out
        return df

    col_s = str(col)
    name_parts = split_line_smart(col_s, sep) if ("," in col_s or ";" in col_s or "\t" in col_s) else []
    first_parts = split_line_smart(str(series.iloc[0]), sep) if len(series) else []

    if len(name_parts) >= 2 and all(not p.isdigit() for p in name_parts[:3]):
        headers = name_parts
        start_idx = 0
    elif len(first_parts) >= 2:
        if _tokens_look_like_header_row(first_parts):
            headers = first_parts
            start_idx = 1
        else:
            headers = [f"column_{i}" for i in range(len(first_parts))]
            start_idx = 0
    else:
        return df

    w = len(headers)
    rows = []
    for i in range(start_idx, len(series)):
        parts = split_line_smart(str(series.iloc[i]), sep)
        if len(parts) < w:
            parts = parts + [""] * (w - len(parts))
        elif len(parts) > w:
            parts = parts[:w]
        rows.append(dict(zip(headers, parts)))

    if not rows:
        return df
    out = pd.DataFrame(rows)
    out.columns = [str(c).strip() for c in out.columns]
    return out


def normalize_records_from_flat_string(
    records: list[dict[str, Any]],
    columns_hint: list[str] | None,
) -> list[dict[str, Any]]:
    """
    When each row is a single dict with one key whose value is a whole CSV line
    (bad delimiter read), expand into proper dicts using columns_hint or first line.
    """
    if not records:
        return records
    r0 = records[0]
    if len(r0) > 1:
        best_key = None
        best_score = -1
        for k, v in r0.items():
            s = str(v) if v is not None else ""
            score = s.count(",")
            if score >= 3 and score > best_score:
                best_score = score
                best_key = k
        if best_key is not None:
            slim = [{best_key: str(r.get(best_key, "") if r.get(best_key) is not None else "")} for r in records]
            return normalize_records_from_flat_string(slim, columns_hint)
        return records
    hint = expand_stale_columns_hint(columns_hint)
    key = next(iter(records[0].keys()))
    lines = [str(records[0][key])] + [str(r[key]) for r in records[1:]]
    sep = _detect_sep(lines[0] + ("\n" + lines[1] if len(lines) > 1 else ""))

    if hint and len(hint) >= 2:
        headers = [str(c).strip() for c in hint]
        w = len(headers)
        start = 0
        p0 = split_line_smart(lines[0], sep)
        if len(p0) == w and all(a.lower() == b.lower() for a, b in zip(p0, headers)):
            start = 1
        out: list[dict[str, Any]] = []
        for line in lines[start:]:
            parts = split_line_smart(line, sep)
            if len(parts) < w:
                parts = parts + [""] * (w - len(parts))
            elif len(parts) > w:
                parts = parts[:w]
            out.append(dict(zip(headers, parts)))
        return out

    p0 = split_line_smart(lines[0], sep)
    if len(p0) < 2:
        return records
    # First line looks like header (not mostly numeric)
    head_like = sum(1 for x in p0[:5] if not x.replace(".", "").isdigit())
    if head_like >= max(1, len(p0) // 2):
        headers = p0
        body = lines[1:]
    else:
        return records
    w = len(headers)
    out = []
    for line in body:
        parts = split_line_smart(line, sep)
        if len(parts) < w:
            parts = parts + [""] * (w - len(parts))
        elif len(parts) > w:
            parts = parts[:w]
        out.append(dict(zip(headers, parts)))
    return out if out else records


def coerce_typed_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Best-effort: parse dates and numbers on known column name patterns."""
    df = df.copy()
    for col in df.columns:
        lc = str(col).lower()
        if any(x in lc for x in ("fecha", "date", "time", "dia")):
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
        elif any(x in lc for x in ("cantidad", "qty", "quantity")) and df[col].dtype == object:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ".", regex=False), errors="coerce")
        elif lc == "id" or lc.endswith("_id"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif any(x in lc for x in ("precio", "price", "importe", "monto", "total", "valor", "costo", "cost")):
            df[col] = df[col].map(_clean_scalar_number)
    return df
