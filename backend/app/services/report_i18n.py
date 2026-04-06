"""PDF report strings (English / Spanish)."""

PDF_COPY: dict[str, dict[str, str]] = {
    "en": {
        "generated": "Generated at",
        "utc": "UTC",
        "dataset": "Dataset",
        "summary_title": "Business summary",
        "total_sales": "Total sales",
        "total_orders": "Total orders",
        "avg_order": "Average order value",
        "total_qty": "Total quantity",
        "total_cost": "Total cost",
        "profit": "Profit",
        "margin": "Profit margin",
        "insights_title": "Top performers & trend",
        "top_seller": "Top seller",
        "top_product": "Best-selling product",
        "top_region": "Top region / area / country",
        "trend": "Trend",
        "kpi_title": "Additional KPIs",
        "kpi": "KPI",
        "value": "Value",
        "no_bi": "Structured metrics require columns: fecha, cantidad, precio_unitario.",
        "no_dataset": "No dataset uploaded. Upload data to generate a full report.",
    },
    "es": {
        "generated": "Generado el",
        "utc": "UTC",
        "dataset": "Conjunto de datos",
        "summary_title": "Resumen de negocio",
        "total_sales": "Ventas totales",
        "total_orders": "Total de pedidos",
        "avg_order": "Valor medio de pedido",
        "total_qty": "Cantidad total",
        "total_cost": "Coste total",
        "profit": "Beneficio",
        "margin": "Margen de beneficio",
        "insights_title": "Destacados y tendencia",
        "top_seller": "Mejor vendedor",
        "top_product": "Producto más vendido",
        "top_region": "Región / área / país líder",
        "trend": "Tendencia",
        "kpi_title": "Otros indicadores",
        "kpi": "Indicador",
        "value": "Valor",
        "no_bi": "Las métricas estructuradas requieren columnas: fecha, cantidad, precio_unitario.",
        "no_dataset": "No hay conjunto de datos cargado. Suba datos para generar un informe completo.",
    },
}


def pdf_strings(lang: str) -> dict[str, str]:
    l = lang if lang in PDF_COPY else "en"
    return PDF_COPY[l]
