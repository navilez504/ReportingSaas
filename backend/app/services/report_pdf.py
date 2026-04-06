import html
import uuid
from datetime import datetime
from pathlib import Path

from weasyprint import HTML

from app.core.config import get_settings
from app.models.report import Report
from app.repositories.report import ReportRepository
from app.services.dashboard import DashboardService
from app.services.report_i18n import pdf_strings


def _fmt2(x: float) -> str:
    try:
        return f"{float(x):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _html_document(title: str, body_html: str, meta_line: str) -> str:
    esc_title = html.escape(title)
    esc_meta = html.escape(meta_line)
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>{esc_title}</title>
  <style>
    body {{ font-family: DejaVu Sans, Helvetica, Arial, sans-serif; margin: 40px; color: #111; }}
    h1 {{ font-size: 22px; margin-bottom: 8px; }}
    h2 {{ font-size: 16px; margin-top: 24px; margin-bottom: 8px; }}
    .meta {{ color: #555; font-size: 12px; margin-bottom: 24px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 12px; margin-bottom: 8px; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; font-size: 12px; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>{esc_title}</h1>
  <div class="meta">{esc_meta}</div>
  {body_html}
</body>
</html>"""


def _kpi_row(label: str, value_html: str) -> str:
    return f"<tr><td>{html.escape(label)}</td><td>{value_html}</td></tr>"


class ReportPdfService:
    def __init__(self, report_repo: ReportRepository, dashboard: DashboardService):
        self.report_repo = report_repo
        self.dashboard = dashboard

    def generate_pdf(
        self,
        user_id: int,
        title: str,
        dataset_id: int | None,
        language: str = "en",
    ) -> Report:
        settings = get_settings()
        s = pdf_strings(language)
        dash = self.dashboard.get_dashboard(user_id, dataset_id, None, None)
        meta = f"{s['generated']} {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} {s['utc']}"

        parts: list[str] = []

        if dash.dataset_id is None:
            parts.append(f"<p>{html.escape(s['no_dataset'])}</p>")
        else:
            _ds, summary, insights = self.dashboard.get_bi_report_payload(
                user_id, dataset_id, language=language
            )
            parts.append(
                f"<p><strong>{html.escape(s['dataset'])}</strong> ID: {dash.dataset_id}</p>"
            )

            if summary and insights:
                parts.append(f"<h2>{html.escape(s['summary_title'])}</h2>")
                parts.append("<table>")
                parts.append(
                    f"<tr><th>{html.escape(s['kpi'])}</th><th>{html.escape(s['value'])}</th></tr>"
                )
                parts.append(_kpi_row(s["total_sales"], _fmt2(summary["total_sales"])))
                parts.append(
                    _kpi_row(s["total_orders"], str(int(summary["total_orders"])))
                )
                parts.append(
                    _kpi_row(s["avg_order"], _fmt2(summary["average_order_value"]))
                )
                parts.append(
                    _kpi_row(s["total_qty"], _fmt2(summary["total_quantity"]))
                )
                if "total_cost" in summary:
                    parts.append(_kpi_row(s["total_cost"], _fmt2(summary["total_cost"])))
                    parts.append(_kpi_row(s["profit"], _fmt2(summary["profit"])))
                    pm = float(summary["profit_margin"]) * 100.0
                    parts.append(
                        _kpi_row(s["margin"], f"{_fmt2(pm)}%")
                    )
                parts.append("</table>")

                parts.append(f"<h2>{html.escape(s['insights_title'])}</h2>")
                parts.append("<table>")
                parts.append(
                    f"<tr><th>{html.escape(s['kpi'])}</th><th>{html.escape(s['value'])}</th></tr>"
                )
                if insights.get("top_seller"):
                    parts.append(
                        _kpi_row(
                            s["top_seller"],
                            html.escape(str(insights["top_seller"])),
                        )
                    )
                if insights.get("top_product"):
                    parts.append(
                        _kpi_row(
                            s["top_product"],
                            html.escape(str(insights["top_product"])),
                        )
                    )
                if insights.get("top_region"):
                    parts.append(
                        _kpi_row(
                            s["top_region"],
                            html.escape(str(insights["top_region"])),
                        )
                    )
                tr = insights.get("trend") or ""
                parts.append(
                    _kpi_row(s["trend"], html.escape(str(tr)))
                )
                parts.append("</table>")
            else:
                parts.append(f"<p>{html.escape(s['no_bi'])}</p>")

            if dash.kpis:
                parts.append(f"<h2>{html.escape(s['kpi_title'])}</h2>")
                parts.append("<table>")
                parts.append(
                    f"<tr><th>{html.escape(s['kpi'])}</th><th>{html.escape(s['value'])}</th></tr>"
                )
                for k in dash.kpis:
                    u = (k.unit or "").strip()
                    num = _fmt2(k.value)
                    if u:
                        cell = f"{num} {html.escape(u)}"
                    else:
                        cell = num
                    parts.append(
                        f"<tr><td>{html.escape(k.label)}</td><td>{cell}</td></tr>"
                    )
                parts.append("</table>")

        body = "".join(parts)
        html_doc = _html_document(title, body, meta)

        reports_root = Path(settings.reports_dir) / str(user_id)
        reports_root.mkdir(parents=True, exist_ok=True)
        fname = f"{uuid.uuid4().hex}.pdf"
        out_path = reports_root / fname
        HTML(string=html_doc).write_pdf(str(out_path))
        size = out_path.stat().st_size

        report = Report(
            user_id=user_id,
            dataset_id=dash.dataset_id,
            title=title[:512],
            file_path=str(out_path),
            file_size_bytes=size,
        )
        return self.report_repo.create(report)
