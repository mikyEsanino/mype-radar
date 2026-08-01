"""Servicios de compatibilidad y preparación de datos para MYPE Radar.

``analytics.analizar_mercado`` es el motor principal. Este módulo mantiene
las utilidades históricas de la aplicación y adapta el resultado normalizado
al formato que ya consume la interfaz Streamlit.
"""

from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .analytics import (
    analizar_mercado,
    normalizar_texto,
    obtener_catalogo_mercado,
)


STOPWORDS = {
    "empresa",
    "empresas",
    "brindamos",
    "ofrecemos",
    "vendemos",
    "realizamos",
    "producto",
    "productos",
    "servicio",
    "servicios",
    "para",
    "como",
    "con",
    "del",
    "las",
    "los",
    "una",
    "unos",
    "unas",
    "que",
    "por",
    "y",
    "de",
    "en",
    "su",
    "sus",
}

SAMPLE_DESCRIPTIONS = [
    ("Adquisición de computadoras portátiles y accesorios", "Bien"),
    ("Adquisición de impresoras multifuncionales", "Bien"),
    ("Servicio de mantenimiento preventivo de equipos informáticos", "Servicio"),
    ("Servicio de soporte técnico y mesa de ayuda", "Servicio"),
    ("Servicio integral de limpieza de oficinas", "Servicio"),
    ("Servicio de desinfección de instalaciones", "Servicio"),
    ("Adquisición de implementos de limpieza", "Bien"),
    ("Adquisición de alimentos para atención institucional", "Bien"),
    ("Servicio de catering para actividades institucionales", "Servicio"),
    ("Suministro de refrigerios para jornadas de capacitación", "Bien"),
    ("Servicio de reparación y acondicionamiento de infraestructura", "Servicio"),
    ("Servicio de pintura de ambientes institucionales", "Servicio"),
    ("Adquisición de materiales para reparaciones menores", "Bien"),
    ("Adquisición de útiles y materiales de oficina", "Bien"),
    ("Servicio de transporte institucional", "Servicio"),
]

DEPARTMENTS = [
    "Lima",
    "Arequipa",
    "La Libertad",
    "Piura",
    "Cusco",
    "Junín",
    "Áncash",
]

ENTITY_TYPES = [
    "Municipalidad Provincial",
    "Gobierno Regional",
    "Hospital Público",
    "Universidad Nacional",
    "Ministerio",
    "Instituto Público",
]

SUPPLIERS = [
    "Tecnología Andina SAC",
    "Servicios Integrales del Perú EIRL",
    "Comercializadora Nacional SAC",
    "Soluciones Institucionales SAC",
    "Grupo Empresarial del Sur SAC",
    "Proveedores del Pacífico EIRL",
]


def normalize_text(value: Any) -> str:
    """Alias histórico de la normalización utilizada por analytics."""
    return normalizar_texto(value)


def extract_keywords(description: str, manual_terms: str) -> list[str]:
    """Extrae términos locales y respeta primero los términos manuales."""
    manual = [
        term.strip()
        for term in re.split(r"[,;\n]+", manual_terms or "")
        if term.strip()
    ]
    if manual:
        return list(dict.fromkeys(manual))[:12]

    normalized = normalize_text(description)
    tokens = [
        token
        for token in normalized.split()
        if len(token) >= 4 and token not in STOPWORDS
    ]
    return list(dict.fromkeys(tokens))[:8]


def build_sample_orders(rows: int = 420) -> pd.DataFrame:
    """Genera datos demostrativos con el esquema histórico de la interfaz."""
    rng = random.Random(2026)
    records = []

    for index in range(rows):
        description, object_type = rng.choice(SAMPLE_DESCRIPTIONS)
        emission = pd.Timestamp("2026-01-01") + pd.Timedelta(
            days=rng.randint(0, 180)
        )
        registration = emission - pd.Timedelta(days=rng.randint(0, 5))
        commitment = emission + pd.Timedelta(days=rng.randint(0, 8))
        notification = commitment + pd.Timedelta(days=rng.randint(0, 5))
        department = rng.choice(DEPARTMENTS)
        entity = f"{rng.choice(ENTITY_TYPES)} de {department}"
        order_type = (
            "Orden de Compra"
            if object_type == "Bien"
            else "Orden de Servicio"
        )
        amount = round(
            rng.choice([2500, 4800, 7900, 12500, 24000, 46000, 85000])
            * rng.uniform(0.85, 1.35),
            2,
        )

        records.append(
            {
                "ENTIDAD": entity,
                "RUC_ENTIDAD": str(
                    20000000000 + rng.randint(1000000, 9999999)
                ),
                "FECHA_REGISTRO": registration.date(),
                "FECHA_DE_EMISION": emission.date(),
                "FECHA_COMPROMISO_PRESUPUESTAL": commitment.date(),
                "FECHA_DE_NOTIFICACION": notification.date(),
                "TIPOORDEN": order_type,
                "NRO_DE_ORDEN": f"{rng.randint(1, 9999):04d}",
                "ORDEN": (
                    f"{'OC' if object_type == 'Bien' else 'OS'}-"
                    f"{index + 1:05d}-2026"
                ),
                "DESCRIPCION_ORDEN": description,
                "MONEDA": "PEN",
                "MONTO_TOTAL_ORDEN_ORIGINAL": amount,
                "OBJETOCONTRACTUAL": object_type,
                "ESTADOCONTRATACION": rng.choices(
                    ["Emitida", "Comprometida", "Devengada", "Anulada"],
                    weights=[22, 28, 44, 6],
                )[0],
                "TIPODECONTRATACION": rng.choice(
                    [
                        "Contrataciones hasta 8 UIT",
                        "Catálogo electrónico",
                        "Contratación directa",
                        "Otras contrataciones sin proceso previo",
                    ]
                ),
                "DEPARTAMENTO": department,
                "RUC_CONTRATISTA": str(
                    20100000000 + rng.randint(1000000, 9999999)
                ),
                "NOMBRE_RAZON_CONTRATISTA": rng.choice(SUPPLIERS),
            }
        )

    return pd.DataFrame(records)


def prepare_orders(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Completa y tipa el esquema histórico esperado por la UI."""
    data = dataframe.copy()

    required_defaults = {
        "ENTIDAD": "Entidad no indicada",
        "RUC_ENTIDAD": "",
        "FECHA_REGISTRO": pd.NaT,
        "FECHA_DE_EMISION": pd.NaT,
        "FECHA_COMPROMISO_PRESUPUESTAL": pd.NaT,
        "FECHA_DE_NOTIFICACION": pd.NaT,
        "TIPOORDEN": "No indicado",
        "NRO_DE_ORDEN": "",
        "ORDEN": "",
        "DESCRIPCION_ORDEN": "",
        "MONEDA": "PEN",
        "MONTO_TOTAL_ORDEN_ORIGINAL": 0.0,
        "OBJETOCONTRACTUAL": "No indicado",
        "ESTADOCONTRATACION": "No indicado",
        "TIPODECONTRATACION": "No indicado",
        "DEPARTAMENTO": "No indicado",
        "RUC_CONTRATISTA": "",
        "NOMBRE_RAZON_CONTRATISTA": "No indicado",
    }

    for column, default in required_defaults.items():
        if column not in data.columns:
            data[column] = default

    date_columns = [
        "FECHA_REGISTRO",
        "FECHA_DE_EMISION",
        "FECHA_COMPROMISO_PRESUPUESTAL",
        "FECHA_DE_NOTIFICACION",
    ]
    for column in date_columns:
        data[column] = pd.to_datetime(
            data[column],
            errors="coerce",
        ).dt.date

    data["MONTO_TOTAL_ORDEN_ORIGINAL"] = pd.to_numeric(
        data["MONTO_TOTAL_ORDEN_ORIGINAL"],
        errors="coerce",
    ).fillna(0.0)

    string_columns = [
        "ENTIDAD",
        "RUC_ENTIDAD",
        "TIPOORDEN",
        "NRO_DE_ORDEN",
        "ORDEN",
        "DESCRIPCION_ORDEN",
        "MONEDA",
        "OBJETOCONTRACTUAL",
        "ESTADOCONTRATACION",
        "TIPODECONTRATACION",
        "DEPARTAMENTO",
        "RUC_CONTRATISTA",
        "NOMBRE_RAZON_CONTRATISTA",
    ]
    for column in string_columns:
        data[column] = data[column].fillna("").astype(str)

    data["_DESCRIPTION_NORMALIZED"] = data[
        "DESCRIPCION_ORDEN"
    ].map(normalize_text)

    return data


def _catalog_frame(catalog: dict[str, Any]) -> pd.DataFrame:
    departments = list(catalog.get("departamentos", []))
    object_types = list(catalog.get("objetos_contractuales", []))
    row_count = max(len(departments), len(object_types), 1)

    departments += [None] * (row_count - len(departments))
    object_types += [None] * (row_count - len(object_types))
    frame = pd.DataFrame(
        {
            "DEPARTAMENTO": departments,
            "OBJETOCONTRACTUAL": object_types,
        }
    )
    frame.attrs["total_records"] = int(catalog.get("total_registros", 0))
    frame.attrs["source_type"] = "monthly"
    return frame


def load_orders(app_dir: Path) -> tuple[pd.DataFrame, str, bool]:
    """Carga el catálogo mensual o las fuentes históricas de respaldo.

    Cuando existen Parquet mensuales se devuelve un DataFrame liviano para
    poblar filtros. El análisis real se ejecuta después con ``analizar_mercado``.
    """
    monthly_dir = app_dir / "data" / "processed" / "monthly"
    if any(monthly_dir.glob("*.parquet")):
        catalog = obtener_catalogo_mercado(monthly_dir)
        frame = _catalog_frame(catalog)
        frame.attrs["monthly_dir"] = str(monthly_dir)
        return (
            frame,
            "data/processed/monthly/*.parquet",
            False,
        )

    parquet_path = (
        app_dir / "data" / "processed" / "ordenes_limpias.parquet"
    )
    csv_path = app_dir / "data" / "processed" / "ordenes_muestra.csv"

    if parquet_path.exists():
        dataframe = prepare_orders(pd.read_parquet(parquet_path))
        dataframe.attrs["total_records"] = len(dataframe)
        dataframe.attrs["source_type"] = "single"
        return (
            dataframe,
            "data/processed/ordenes_limpias.parquet",
            False,
        )

    if csv_path.exists():
        dataframe = prepare_orders(pd.read_csv(csv_path))
        dataframe.attrs["total_records"] = len(dataframe)
        dataframe.attrs["source_type"] = "single"
        return (
            dataframe,
            "data/processed/ordenes_muestra.csv",
            False,
        )

    dataframe = prepare_orders(build_sample_orders())
    dataframe.attrs["total_records"] = len(dataframe)
    dataframe.attrs["source_type"] = "demo"
    return (
        dataframe,
        "datos de ejemplo con la estructura del diccionario de compras",
        True,
    )


def source_record_count(orders: pd.DataFrame) -> int:
    """Devuelve el volumen real aunque ``orders`` sea solo un catálogo."""
    return int(orders.attrs.get("total_records", len(orders)))


_CANONICAL_TO_LEGACY = {
    "entidad": "ENTIDAD",
    "ruc_entidad": "RUC_ENTIDAD",
    "fecha_registro": "FECHA_REGISTRO",
    "fecha_emision": "FECHA_DE_EMISION",
    "fecha_compromiso_presupuestal": "FECHA_COMPROMISO_PRESUPUESTAL",
    "fecha_notificacion": "FECHA_DE_NOTIFICACION",
    "tipo_orden": "TIPOORDEN",
    "numero_orden": "NRO_DE_ORDEN",
    "orden": "ORDEN",
    "descripcion": "DESCRIPCION_ORDEN",
    "moneda": "MONEDA",
    "monto_pen": "MONTO_TOTAL_ORDEN_ORIGINAL",
    "objeto_contractual": "OBJETOCONTRACTUAL",
    "estado_contratacion": "ESTADOCONTRATACION",
    "tipo_contratacion": "TIPODECONTRATACION",
    "departamento": "DEPARTAMENTO",
    "ruc_proveedor": "RUC_CONTRATISTA",
    "proveedor": "NOMBRE_RAZON_CONTRATISTA",
}


def _frame(records: Any, columns: list[str]) -> pd.DataFrame:
    frame = pd.DataFrame(records or [])
    for column in columns:
        if column not in frame.columns:
            frame[column] = pd.Series(dtype="object")
    return frame[columns].copy()


def adapt_analytics_result(payload: dict[str, Any]) -> dict[str, Any]:
    """Adapta ``analizar_mercado`` al contrato histórico de ``app.py``."""
    resumen = payload.get("resumen", {})
    consulta = payload.get("consulta", {})

    entities = _frame(
        payload.get("entidades_principales"),
        ["entidad", "departamento", "cantidad_ordenes", "monto_total_pen"],
    ).rename(
        columns={
            "entidad": "ENTIDAD",
            "departamento": "DEPARTAMENTO",
            "cantidad_ordenes": "ordenes",
            "monto_total_pen": "monto_total",
        }
    )

    monthly = _frame(
        payload.get("tendencia_mensual"),
        ["periodo", "cantidad_ordenes", "monto_total_pen"],
    ).rename(
        columns={
            "periodo": "MES",
            "cantidad_ordenes": "ordenes",
            "monto_total_pen": "monto_total",
        }
    )

    departments = _frame(
        payload.get("departamentos"),
        [
            "departamento",
            "cantidad_ordenes",
            "monto_total_pen",
            "cantidad_entidades",
        ],
    ).rename(
        columns={
            "departamento": "DEPARTAMENTO",
            "cantidad_ordenes": "ordenes",
            "monto_total_pen": "monto_total",
            "cantidad_entidades": "entidades",
        }
    )

    objects = _frame(
        payload.get("objetos_contractuales"),
        ["objeto_contractual", "cantidad_ordenes", "monto_total_pen"],
    ).rename(
        columns={
            "objeto_contractual": "OBJETOCONTRACTUAL",
            "cantidad_ordenes": "ordenes",
            "monto_total_pen": "monto_total",
        }
    )

    evidence = pd.DataFrame(payload.get("ordenes_evidencia") or [])
    evidence = evidence.rename(columns=_CANONICAL_TO_LEGACY)
    evidence = prepare_orders(evidence)

    keywords = [
        str(term)
        for term in consulta.get("palabras_clave", [])
        if str(term).strip()
    ]

    return {
        "keywords": keywords,
        "summary": {
            "total_orders": int(resumen.get("total_ordenes", 0) or 0),
            "total_amount": float(resumen.get("monto_total_pen", 0.0) or 0.0),
            "entity_count": int(resumen.get("total_entidades", 0) or 0),
            "supplier_count": int(resumen.get("total_proveedores", 0) or 0),
            "peak_month": resumen.get("periodo_principal") or "Sin datos",
            "cancelled_orders": int(resumen.get("ordenes_anuladas", 0) or 0),
        },
        "entities": entities,
        "monthly": monthly,
        "departments": departments,
        "objects": objects,
        "evidence": evidence,
        "market_payload": payload,
    }


def analyze_orders(
    orders: pd.DataFrame,
    *,
    keywords: list[str],
    departments: list[str] | None = None,
    object_types: list[str] | None = None,
) -> dict[str, Any]:
    """Compatibilidad: ejecuta el motor nuevo sobre un DataFrame histórico."""
    payload = analizar_mercado(
        palabras_clave=keywords,
        departamento=departments,
        objeto_contractual=object_types,
        datos=orders,
    )
    return adapt_analytics_result(payload)


def _records_for_context(
    frame: pd.DataFrame,
    columns: list[str],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    selected = frame[[column for column in columns if column in frame.columns]]
    selected = selected.head(limit).copy()
    for column in selected.columns:
        if pd.api.types.is_datetime64_any_dtype(selected[column]):
            selected[column] = selected[column].astype(str)
        elif selected[column].dtype == "object":
            selected[column] = selected[column].map(
                lambda value: value.isoformat()
                if hasattr(value, "isoformat")
                else value
            )
    return selected.where(pd.notna(selected), None).to_dict(orient="records")


def build_report_context(
    analysis: dict[str, Any],
    *,
    business_description: str,
    categories: list[str] | None = None,
) -> dict[str, Any]:
    """Construye un contexto compacto; no envía toda la evidencia a Gemma."""
    return {
        "descripcion_empresa": (business_description or "").strip(),
        "categorias_interpretadas": list(categories or []),
        "palabras_clave_utilizadas": list(analysis.get("keywords", [])),
        "resumen": dict(analysis.get("summary", {})),
        "entidades_principales": _records_for_context(
            analysis.get("entities", pd.DataFrame()),
            ["ENTIDAD", "DEPARTAMENTO", "ordenes", "monto_total"],
        ),
        "tendencia_mensual": _records_for_context(
            analysis.get("monthly", pd.DataFrame()),
            ["MES", "ordenes", "monto_total"],
            limit=24,
        ),
        "departamentos_principales": _records_for_context(
            analysis.get("departments", pd.DataFrame()),
            ["DEPARTAMENTO", "ordenes", "monto_total", "entidades"],
        ),
        "objetos_contractuales": _records_for_context(
            analysis.get("objects", pd.DataFrame()),
            ["OBJETOCONTRACTUAL", "ordenes", "monto_total"],
        ),
        "ordenes_ejemplo": _records_for_context(
            analysis.get("evidence", pd.DataFrame()).sort_values(
                "MONTO_TOTAL_ORDEN_ORIGINAL",
                ascending=False,
            )
            if not analysis.get("evidence", pd.DataFrame()).empty
            else pd.DataFrame(),
            [
                "ENTIDAD",
                "DEPARTAMENTO",
                "TIPOORDEN",
                "DESCRIPCION_ORDEN",
                "MONTO_TOTAL_ORDEN_ORIGINAL",
                "FECHA_DE_EMISION",
            ],
        ),
        "advertencia": (
            "Son órdenes históricas del mercado público, no ventas de la MYPE "
            "ni oportunidades activas."
        ),
    }
