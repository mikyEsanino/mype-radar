from __future__ import annotations

import random
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd


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
    text = "" if value is None else str(value)
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def extract_keywords(description: str, manual_terms: str) -> list[str]:
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


def load_orders(app_dir: Path) -> tuple[pd.DataFrame, str, bool]:
    parquet_path = (
        app_dir / "data" / "processed" / "ordenes_limpias.parquet"
    )
    csv_path = app_dir / "data" / "processed" / "ordenes_muestra.csv"

    if parquet_path.exists():
        dataframe = pd.read_parquet(parquet_path)
        return (
            prepare_orders(dataframe),
            "data/processed/ordenes_limpias.parquet",
            False,
        )

    if csv_path.exists():
        dataframe = pd.read_csv(csv_path)
        return (
            prepare_orders(dataframe),
            "data/processed/ordenes_muestra.csv",
            False,
        )

    return (
        prepare_orders(build_sample_orders()),
        "datos de ejemplo con la estructura del diccionario de compras",
        True,
    )


def analyze_orders(
    orders: pd.DataFrame,
    *,
    keywords: list[str],
    departments: list[str] | None = None,
    object_types: list[str] | None = None,
) -> dict[str, Any]:
    normalized_keywords = [
        normalize_text(keyword)
        for keyword in keywords
        if normalize_text(keyword)
    ]

    if not normalized_keywords:
        raise ValueError("Se requiere al menos una palabra clave.")

    mask = pd.Series(False, index=orders.index)
    for keyword in normalized_keywords:
        mask = mask | orders["_DESCRIPTION_NORMALIZED"].str.contains(
            re.escape(keyword),
            case=False,
            na=False,
            regex=True,
        )

    matched = orders[mask].copy()

    if departments:
        matched = matched[
            matched["DEPARTAMENTO"].isin(departments)
        ]

    if object_types:
        matched = matched[
            matched["OBJETOCONTRACTUAL"].isin(object_types)
        ]

    cancelled = matched[
        matched["ESTADOCONTRATACION"].str.lower() == "anulada"
    ].copy()
    valid = matched[
        matched["ESTADOCONTRATACION"].str.lower() != "anulada"
    ].copy()

    if not valid.empty:
        valid["MES"] = (
            pd.to_datetime(valid["FECHA_DE_EMISION"], errors="coerce")
            .dt.to_period("M")
            .astype(str)
        )
    else:
        valid["MES"] = pd.Series(dtype="string")

    entities = (
        valid.groupby(["ENTIDAD", "DEPARTAMENTO"], as_index=False)
        .agg(
            ordenes=("ORDEN", "count"),
            monto_total=("MONTO_TOTAL_ORDEN_ORIGINAL", "sum"),
        )
        .sort_values(
            ["ordenes", "monto_total"],
            ascending=False,
        )
    )

    monthly = (
        valid.groupby("MES", as_index=False)
        .agg(
            ordenes=("ORDEN", "count"),
            monto_total=("MONTO_TOTAL_ORDEN_ORIGINAL", "sum"),
        )
        .sort_values("MES")
    )

    departments_summary = (
        valid.groupby("DEPARTAMENTO", as_index=False)
        .agg(
            ordenes=("ORDEN", "count"),
            monto_total=("MONTO_TOTAL_ORDEN_ORIGINAL", "sum"),
            entidades=("ENTIDAD", "nunique"),
        )
        .sort_values("monto_total", ascending=False)
    )

    objects = (
        valid.groupby("OBJETOCONTRACTUAL", as_index=False)
        .agg(
            ordenes=("ORDEN", "count"),
            monto_total=("MONTO_TOTAL_ORDEN_ORIGINAL", "sum"),
        )
    )

    peak_month = (
        str(monthly.loc[monthly["ordenes"].idxmax(), "MES"])
        if not monthly.empty
        else "Sin datos"
    )

    return {
        "keywords": keywords,
        "summary": {
            "total_orders": int(len(valid)),
            "total_amount": float(
                valid["MONTO_TOTAL_ORDEN_ORIGINAL"].sum()
            ),
            "entity_count": int(valid["ENTIDAD"].nunique()),
            "supplier_count": int(
                valid["NOMBRE_RAZON_CONTRATISTA"].nunique()
            ),
            "peak_month": peak_month,
            "cancelled_orders": int(len(cancelled)),
        },
        "entities": entities,
        "monthly": monthly,
        "departments": departments_summary,
        "objects": objects,
        "evidence": valid,
    }
