"""Motor único de búsqueda y análisis de órdenes públicas para MYPE Radar.

Este módulo concentra toda la lectura de fuentes, normalización de esquemas,
filtrado y cálculo. ``app.py`` usa ``analizar_mercado`` como única entrada para
obtener métricas, gráficos y evidencia. ``data_service.py`` no vuelve a leer ni
analizar los Parquet.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Iterator

import pandas as pd


CANONICAL_COLUMNS = [
    "entidad",
    "ruc_entidad",
    "fecha_registro",
    "fecha_emision",
    "fecha_compromiso_presupuestal",
    "fecha_notificacion",
    "tipo_orden",
    "numero_orden",
    "orden",
    "descripcion",
    "moneda",
    "monto_pen",
    "objeto_contractual",
    "estado_contratacion",
    "tipo_contratacion",
    "departamento",
    "ruc_proveedor",
    "proveedor",
    "periodo",
    "texto_busqueda",
]

_DATE_COLUMNS = [
    "fecha_registro",
    "fecha_emision",
    "fecha_compromiso_presupuestal",
    "fecha_notificacion",
]

_DEFAULTS: dict[str, Any] = {
    "entidad": "Entidad no indicada",
    "ruc_entidad": "",
    "fecha_registro": pd.NaT,
    "fecha_emision": pd.NaT,
    "fecha_compromiso_presupuestal": pd.NaT,
    "fecha_notificacion": pd.NaT,
    "tipo_orden": "No indicado",
    "numero_orden": "",
    "orden": "",
    "descripcion": "",
    "moneda": "PEN",
    "monto_pen": 0.0,
    "objeto_contractual": "No indicado",
    "estado_contratacion": "No indicado",
    "tipo_contratacion": "No indicado",
    "departamento": "No indicado",
    "ruc_proveedor": "",
    "proveedor": "No indicado",
    "periodo": "",
    "texto_busqueda": "",
}

# Las claves están normalizadas por ``normalizar_texto``.
_COLUMN_ALIASES = {
    "entidad": "entidad",
    "ruc entidad": "ruc_entidad",
    "fecha registro": "fecha_registro",
    "fecha de emision": "fecha_emision",
    "fecha emision": "fecha_emision",
    "fecha compromiso presupuestal": "fecha_compromiso_presupuestal",
    "fecha de notificacion": "fecha_notificacion",
    "fecha notificacion": "fecha_notificacion",
    "tipoorden": "tipo_orden",
    "tipo orden": "tipo_orden",
    "nro de orden": "numero_orden",
    "numero de orden": "numero_orden",
    "numero orden": "numero_orden",
    "orden": "orden",
    "descripcion orden": "descripcion",
    "descripcion de orden": "descripcion",
    "descripcion": "descripcion",
    "moneda": "moneda",
    "monto total orden original": "monto_pen",
    "monto pen": "monto_pen",
    "monto": "monto_pen",
    "objetocontractual": "objeto_contractual",
    "objeto contractual": "objeto_contractual",
    "estadocontratacion": "estado_contratacion",
    "estado contratacion": "estado_contratacion",
    "tipodecontratacion": "tipo_contratacion",
    "tipo de contratacion": "tipo_contratacion",
    "tipo contratacion": "tipo_contratacion",
    "departamento": "departamento",
    "ruc contratista": "ruc_proveedor",
    "ruc proveedor": "ruc_proveedor",
    "nombre razon contratista": "proveedor",
    "nombre o razon social contratista": "proveedor",
    "proveedor": "proveedor",
    "periodo": "periodo",
    "mes": "periodo",
    "texto busqueda": "texto_busqueda",
}

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
]

_DEMO_DEPARTMENTS = ["Lima", "Arequipa", "La Libertad", "Piura", "Cusco", "Junín"]
_DEMO_ENTITIES = [
    "Municipalidad Provincial",
    "Gobierno Regional",
    "Hospital Público",
    "Universidad Nacional",
    "Ministerio",
]
_DEMO_SUPPLIERS = [
    "Tecnología Andina SAC",
    "Servicios Integrales del Perú EIRL",
    "Comercializadora Nacional SAC",
    "Soluciones Institucionales SAC",
]


def normalizar_texto(texto: Any) -> str:
    """Normaliza texto para búsquedas y comparaciones estables."""
    resultado = "" if texto is None else str(texto)
    resultado = unicodedata.normalize("NFKD", resultado.strip().lower())
    resultado = "".join(
        caracter for caracter in resultado if not unicodedata.combining(caracter)
    )
    resultado = re.sub(r"[^a-z0-9]+", " ", resultado)
    return re.sub(r"\s+", " ", resultado).strip()


def _canonical_column_name(column: Any) -> str | None:
    return _COLUMN_ALIASES.get(normalizar_texto(column))


def _normalizar_columnas(frame: pd.DataFrame) -> pd.DataFrame:
    """Convierte esquemas en mayúsculas o minúsculas al esquema canónico."""
    data = frame.copy()
    renames: dict[Any, str] = {}
    occupied = {str(column) for column in data.columns}

    for column in data.columns:
        target = _canonical_column_name(column)
        if not target or str(column) == target:
            continue
        if target in occupied or target in renames.values():
            continue
        renames[column] = target
        occupied.add(target)

    if renames:
        data = data.rename(columns=renames)

    for column, default in _DEFAULTS.items():
        if column not in data.columns:
            data[column] = default

    for column in _DATE_COLUMNS:
        data[column] = pd.to_datetime(data[column], errors="coerce")

    data["monto_pen"] = pd.to_numeric(
        data["monto_pen"], errors="coerce"
    ).fillna(0.0)

    for column in CANONICAL_COLUMNS:
        if column in _DATE_COLUMNS or column == "monto_pen":
            continue
        data[column] = data[column].fillna("").astype(str).str.strip()

    missing_period = data["periodo"].eq("")
    if missing_period.any():
        generated = data["fecha_emision"].dt.to_period("M").astype(str)
        generated = generated.replace("NaT", "")
        data.loc[missing_period, "periodo"] = generated.loc[missing_period]

    missing_object = data["objeto_contractual"].map(normalizar_texto).isin(
        {"", "no indicado"}
    )
    if missing_object.any():
        order_type = data["tipo_orden"].map(normalizar_texto)
        inferred = pd.Series("No indicado", index=data.index, dtype="object")
        inferred.loc[order_type.str.contains(r"compra|bien", regex=True)] = "Bien"
        inferred.loc[order_type.str.contains("servicio", regex=False)] = "Servicio"
        data.loc[missing_object, "objeto_contractual"] = inferred.loc[missing_object]

    search_parts = [
        "entidad",
        "departamento",
        "tipo_orden",
        "descripcion",
        "objeto_contractual",
        "proveedor",
    ]
    generated_search = (
        data[search_parts]
        .fillna("")
        .astype(str)
        .agg(" ".join, axis=1)
        .map(normalizar_texto)
    )
    missing_search = data["texto_busqueda"].eq("")
    data.loc[missing_search, "texto_busqueda"] = generated_search.loc[missing_search]
    data["texto_busqueda"] = data["texto_busqueda"].map(normalizar_texto)

    empty_order = data["orden"].eq("")
    if empty_order.any():
        generated_ids = [f"ORD-{index + 1:07d}" for index in range(len(data))]
        data.loc[empty_order, "orden"] = pd.Series(generated_ids, index=data.index)[
            empty_order
        ]

    return data[CANONICAL_COLUMNS].copy()


def _build_sample_orders(rows: int = 420) -> pd.DataFrame:
    """Genera datos determinísticos solo cuando no existe una fuente procesada."""
    import random

    rng = random.Random(2026)
    records: list[dict[str, Any]] = []
    for index in range(rows):
        description, object_type = rng.choice(SAMPLE_DESCRIPTIONS)
        emission = pd.Timestamp("2025-01-01") + pd.Timedelta(days=rng.randint(0, 364))
        department = rng.choice(_DEMO_DEPARTMENTS)
        entity = f"{rng.choice(_DEMO_ENTITIES)} de {department}"
        order_type = "Orden de Compra" if object_type == "Bien" else "Orden de Servicio"
        amount = round(
            rng.choice([2500, 4800, 7900, 12500, 24000, 46000, 85000])
            * rng.uniform(0.85, 1.35),
            2,
        )
        records.append(
            {
                "entidad": entity,
                "ruc_entidad": str(20000000000 + rng.randint(1000000, 9999999)),
                "fecha_registro": emission - pd.Timedelta(days=rng.randint(0, 5)),
                "fecha_emision": emission,
                "fecha_compromiso_presupuestal": emission
                + pd.Timedelta(days=rng.randint(0, 8)),
                "fecha_notificacion": emission + pd.Timedelta(days=rng.randint(1, 12)),
                "tipo_orden": order_type,
                "numero_orden": f"{rng.randint(1, 9999):04d}",
                "orden": f"{'OC' if object_type == 'Bien' else 'OS'}-{index + 1:05d}-2025",
                "descripcion": description,
                "moneda": "PEN",
                "monto_pen": amount,
                "objeto_contractual": object_type,
                "estado_contratacion": rng.choices(
                    ["Emitida", "Comprometida", "Devengada", "Anulada"],
                    weights=[22, 28, 44, 6],
                )[0],
                "tipo_contratacion": "Contrataciones hasta 8 UIT",
                "departamento": department,
                "ruc_proveedor": str(20100000000 + rng.randint(1000000, 9999999)),
                "proveedor": rng.choice(_DEMO_SUPPLIERS),
            }
        )
    return _normalizar_columnas(pd.DataFrame(records))


def _source_descriptor(app_dir: str | Path) -> dict[str, Any]:
    root = Path(app_dir).resolve()
    monthly_dir = root / "data" / "processed" / "monthly"
    monthly_files = sorted(monthly_dir.glob("*.parquet"))
    if monthly_files:
        return {
            "kind": "monthly",
            "files": monthly_files,
            "label": "data/processed/monthly/*.parquet",
            "is_demo": False,
        }

    parquet_path = root / "data" / "processed" / "ordenes_limpias.parquet"
    if parquet_path.exists():
        return {
            "kind": "parquet",
            "files": [parquet_path],
            "label": "data/processed/ordenes_limpias.parquet",
            "is_demo": False,
        }

    csv_path = root / "data" / "processed" / "ordenes_muestra.csv"
    if csv_path.exists():
        return {
            "kind": "csv",
            "files": [csv_path],
            "label": "data/processed/ordenes_muestra.csv",
            "is_demo": False,
        }

    return {
        "kind": "demo",
        "files": [],
        "label": "datos de ejemplo con la estructura de compras públicas",
        "is_demo": True,
    }


def obtener_firma_fuente(app_dir: str | Path) -> str:
    """Firma barata para invalidar la caché cuando cambia una fuente."""
    source = _source_descriptor(app_dir)
    pieces = [source["kind"]]
    for path in source["files"]:
        stat = path.stat()
        pieces.append(f"{path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}")
    return hashlib.sha256("|".join(pieces).encode("utf-8")).hexdigest()


def _parquet_schema_names(path: Path) -> list[str] | None:
    try:
        import pyarrow.parquet as pq

        return list(pq.ParquetFile(path).schema.names)
    except Exception:
        return None


def _parquet_row_count(path: Path) -> int | None:
    try:
        import pyarrow.parquet as pq

        return int(pq.ParquetFile(path).metadata.num_rows)
    except Exception:
        return None


def _read_parquet_canonical(
    path: Path,
    wanted: set[str] | None = None,
) -> pd.DataFrame:
    """Lee únicamente columnas necesarias cuando el esquema lo permite."""
    schema_names = _parquet_schema_names(path)
    selected: list[str] | None = None
    if schema_names is not None and wanted:
        selected = [
            name
            for name in schema_names
            if _canonical_column_name(name) in wanted
        ]
        if not selected:
            selected = None
    try:
        frame = pd.read_parquet(path, columns=selected)
    except (KeyError, ValueError):
        frame = pd.read_parquet(path)
    return _normalizar_columnas(frame)


def _iter_source_frames(
    app_dir: str | Path,
    *,
    wanted: set[str] | None = None,
) -> Iterator[pd.DataFrame]:
    source = _source_descriptor(app_dir)
    if source["kind"] in {"monthly", "parquet"}:
        for path in source["files"]:
            yield _read_parquet_canonical(path, wanted=wanted)
        return
    if source["kind"] == "csv":
        yield _normalizar_columnas(pd.read_csv(source["files"][0]))
        return
    yield _build_sample_orders()


def obtener_catalogo_mercado(app_dir: str | Path) -> dict[str, Any]:
    """Devuelve opciones y metadatos sin cargar todas las columnas en cada rerun."""
    source = _source_descriptor(app_dir)
    departments: set[str] = set()
    object_types: set[str] = set()
    total_records = 0
    wanted = {"departamento", "objeto_contractual"}

    if source["kind"] == "demo":
        frames = [_build_sample_orders()]
    else:
        frames = []
        for path in source["files"]:
            if path.suffix.lower() == ".parquet":
                count = _parquet_row_count(path)
                frame = _read_parquet_canonical(path, wanted=wanted)
                total_records += count if count is not None else len(frame)
            else:
                frame = _normalizar_columnas(pd.read_csv(path))
                total_records += len(frame)
            frames.append(frame)

    for frame in frames:
        if source["kind"] == "demo":
            total_records += len(frame)
        departments.update(
            value
            for value in frame["departamento"].dropna().astype(str)
            if value and normalizar_texto(value) != "no indicado"
        )
        object_types.update(
            value
            for value in frame["objeto_contractual"].dropna().astype(str)
            if value and normalizar_texto(value) != "no indicado"
        )

    return {
        "departments": sorted(departments),
        "object_types": sorted(object_types),
        "total_records": int(total_records),
        "source_label": source["label"],
        "is_demo": bool(source["is_demo"]),
        "source_kind": source["kind"],
        "fingerprint": obtener_firma_fuente(app_dir),
    }


def crear_patron_busqueda(palabras_clave: Iterable[str]) -> str:
    terms = [
        normalizar_texto(value)
        for value in palabras_clave
        if normalizar_texto(value)
    ]
    terms = list(dict.fromkeys(terms))
    if not terms:
        raise ValueError("Debes indicar al menos una palabra clave válida.")
    return "|".join(re.escape(term) for term in terms)


def _filter_values(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    raw_values = [value] if isinstance(value, str) else list(value)
    return [normalizar_texto(item) for item in raw_values if normalizar_texto(item)]


def _apply_filters(
    frame: pd.DataFrame,
    *,
    pattern: str,
    departments: list[str],
    order_types: list[str],
    object_types: list[str],
) -> pd.DataFrame:
    mask = frame["texto_busqueda"].fillna("").str.contains(
        pattern, case=False, regex=True, na=False
    )

    if departments and "todo el peru" not in departments:
        normalized = frame["departamento"].map(normalizar_texto)
        mask &= normalized.isin(departments)

    if order_types and "ambos" not in order_types:
        normalized = frame["tipo_orden"].map(normalizar_texto)
        order_mask = pd.Series(False, index=frame.index)
        for value in order_types:
            order_mask |= normalized.str.contains(re.escape(value), regex=True, na=False)
        mask &= order_mask

    if object_types and "ambos" not in object_types:
        normalized = frame["objeto_contractual"].map(normalizar_texto)
        mask &= normalized.isin(object_types)

    return frame.loc[mask].copy()


def buscar_ordenes(
    palabras_clave: list[str],
    departamento: str | list[str] | None = None,
    tipo_orden: str | list[str] | None = None,
    *,
    departamentos: list[str] | None = None,
    objetos_contractuales: list[str] | None = None,
    objeto_contractual: str | list[str] | None = None,
    app_dir: str | Path = ".",
    datos: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Busca coincidencias sin mezclar responsabilidades con ``data_service``."""
    pattern = crear_patron_busqueda(palabras_clave)
    selected_departments = _filter_values(departamentos or departamento)
    selected_order_types = _filter_values(tipo_orden)
    selected_objects = _filter_values(objetos_contractuales or objeto_contractual)

    frames = [_normalizar_columnas(datos)] if datos is not None else _iter_source_frames(app_dir)
    results: list[pd.DataFrame] = []
    for frame in frames:
        matched = _apply_filters(
            frame,
            pattern=pattern,
            departments=selected_departments,
            order_types=selected_order_types,
            object_types=selected_objects,
        )
        if not matched.empty:
            results.append(matched)

    if not results:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)
    return pd.concat(results, ignore_index=True)


def _legacy_evidence(frame: pd.DataFrame) -> pd.DataFrame:
    evidence = frame.rename(columns=_CANONICAL_TO_LEGACY).copy()
    for canonical, legacy in _CANONICAL_TO_LEGACY.items():
        if legacy not in evidence.columns:
            evidence[legacy] = _DEFAULTS[canonical]
    for legacy in [
        "FECHA_REGISTRO",
        "FECHA_DE_EMISION",
        "FECHA_COMPROMISO_PRESUPUESTAL",
        "FECHA_DE_NOTIFICACION",
    ]:
        evidence[legacy] = pd.to_datetime(evidence[legacy], errors="coerce").dt.date
    return evidence[list(_CANONICAL_TO_LEGACY.values())].copy()


def analizar_mercado(
    palabras_clave: list[str],
    departamento: str | list[str] | None = None,
    tipo_orden: str | list[str] | None = None,
    limite_entidades: int = 10,
    *,
    departamentos: list[str] | None = None,
    objetos_contractuales: list[str] | None = None,
    objeto_contractual: str | list[str] | None = None,
    app_dir: str | Path = ".",
    datos: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Ejecuta el análisis completo y devuelve el contrato exacto de ``app.py``."""
    matched = buscar_ordenes(
        palabras_clave=palabras_clave,
        departamento=departamento,
        tipo_orden=tipo_orden,
        departamentos=departamentos,
        objetos_contractuales=objetos_contractuales,
        objeto_contractual=objeto_contractual,
        app_dir=app_dir,
        datos=datos,
    )

    if matched.empty:
        valid = matched.copy()
        cancelled = matched.copy()
    else:
        cancelled_mask = matched["estado_contratacion"].map(normalizar_texto).str.contains(
            "anulad", regex=False, na=False
        )
        cancelled = matched.loc[cancelled_mask].copy()
        valid = matched.loc[~cancelled_mask].copy()

    if not valid.empty:
        valid["periodo"] = valid["periodo"].where(
            valid["periodo"].ne(""),
            valid["fecha_emision"].dt.to_period("M").astype(str).replace("NaT", ""),
        )

    entities = (
        valid.groupby(["entidad", "departamento"], as_index=False)
        .agg(
            ordenes=("orden", "count"),
            monto_total=("monto_pen", "sum"),
        )
        .sort_values(["ordenes", "monto_total"], ascending=False)
        .head(limite_entidades)
        .rename(columns={"entidad": "ENTIDAD", "departamento": "DEPARTAMENTO"})
    )

    monthly = (
        valid.groupby("periodo", as_index=False)
        .agg(ordenes=("orden", "count"), monto_total=("monto_pen", "sum"))
        .sort_values("periodo")
        .rename(columns={"periodo": "MES"})
    )

    departments_summary = (
        valid.groupby("departamento", as_index=False)
        .agg(
            ordenes=("orden", "count"),
            monto_total=("monto_pen", "sum"),
            entidades=("entidad", "nunique"),
        )
        .sort_values("monto_total", ascending=False)
        .rename(columns={"departamento": "DEPARTAMENTO"})
    )

    objects = (
        valid.groupby("objeto_contractual", as_index=False)
        .agg(ordenes=("orden", "count"), monto_total=("monto_pen", "sum"))
        .sort_values("ordenes", ascending=False)
        .rename(columns={"objeto_contractual": "OBJETOCONTRACTUAL"})
    )

    peak_month = (
        str(monthly.loc[monthly["ordenes"].idxmax(), "MES"])
        if not monthly.empty
        else "Sin datos"
    )

    return {
        "keywords": list(palabras_clave),
        "summary": {
            "total_orders": int(len(valid)),
            "total_amount": float(valid["monto_pen"].sum()) if not valid.empty else 0.0,
            "entity_count": int(valid["entidad"].nunique()) if not valid.empty else 0,
            "supplier_count": int(valid["proveedor"].nunique()) if not valid.empty else 0,
            "peak_month": peak_month,
            "cancelled_orders": int(len(cancelled)),
        },
        "entities": entities,
        "monthly": monthly,
        "departments": departments_summary,
        "objects": objects,
        "evidence": _legacy_evidence(valid),
    }
