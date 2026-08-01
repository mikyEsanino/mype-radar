"""Búsqueda y análisis de órdenes públicas para MYPE Radar.

El módulo trabaja con los Parquet mensuales procesados y expone
``analizar_mercado`` como contrato principal entre la capa de datos,
Gemma y la interfaz Streamlit.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


MONTHLY_DIR = Path("data/processed/monthly")

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

SEARCH_COLUMNS = [
    "entidad",
    "departamento",
    "tipo_orden",
    "descripcion",
    "objeto_contractual",
    "monto_pen",
    "periodo",
    "proveedor",
    "texto_busqueda",
]

_COLUMN_ALIASES = {
    "entidad": "entidad",
    "ruc entidad": "ruc_entidad",
    "ruc_entidad": "ruc_entidad",
    "fecha registro": "fecha_registro",
    "fecha_registro": "fecha_registro",
    "fecha de emision": "fecha_emision",
    "fecha emision": "fecha_emision",
    "fecha_emision": "fecha_emision",
    "fecha compromiso presupuestal": "fecha_compromiso_presupuestal",
    "fecha_compromiso_presupuestal": "fecha_compromiso_presupuestal",
    "fecha de notificacion": "fecha_notificacion",
    "fecha notificacion": "fecha_notificacion",
    "fecha_notificacion": "fecha_notificacion",
    "tipoorden": "tipo_orden",
    "tipo orden": "tipo_orden",
    "tipo_orden": "tipo_orden",
    "nro de orden": "numero_orden",
    "numero orden": "numero_orden",
    "numero_orden": "numero_orden",
    "orden": "orden",
    "descripcion orden": "descripcion",
    "descripcion_orden": "descripcion",
    "descripcion": "descripcion",
    "moneda": "moneda",
    "monto total orden original": "monto_pen",
    "monto_total_orden_original": "monto_pen",
    "monto pen": "monto_pen",
    "monto_pen": "monto_pen",
    "objetocontractual": "objeto_contractual",
    "objeto contractual": "objeto_contractual",
    "objeto_contractual": "objeto_contractual",
    "estadocontratacion": "estado_contratacion",
    "estado contratacion": "estado_contratacion",
    "estado_contratacion": "estado_contratacion",
    "tipodecontratacion": "tipo_contratacion",
    "tipo contratacion": "tipo_contratacion",
    "tipo_contratacion": "tipo_contratacion",
    "departamento": "departamento",
    "ruc contratista": "ruc_proveedor",
    "ruc proveedor": "ruc_proveedor",
    "ruc_contratista": "ruc_proveedor",
    "ruc_proveedor": "ruc_proveedor",
    "nombre razon contratista": "proveedor",
    "nombre_razon_contratista": "proveedor",
    "proveedor": "proveedor",
    "periodo": "periodo",
    "mes": "periodo",
    "texto busqueda": "texto_busqueda",
    "texto_busqueda": "texto_busqueda",
}

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

_DATE_COLUMNS = [
    "fecha_registro",
    "fecha_emision",
    "fecha_compromiso_presupuestal",
    "fecha_notificacion",
]


def normalizar_texto(texto: Any) -> str:
    """Normaliza una palabra o frase para búsquedas y comparaciones."""
    resultado = "" if texto is None else str(texto)
    resultado = resultado.strip().lower()
    resultado = unicodedata.normalize("NFKD", resultado)
    resultado = "".join(
        caracter
        for caracter in resultado
        if not unicodedata.combining(caracter)
    )
    resultado = re.sub(r"[^a-z0-9]+", " ", resultado)
    resultado = re.sub(r"\s+", " ", resultado)
    return resultado.strip()


def _normalizar_columnas(frame: pd.DataFrame) -> pd.DataFrame:
    """Convierte esquemas históricos o normalizados al esquema canónico."""
    data = frame.copy()
    renames: dict[Any, str] = {}
    reserved = {str(column) for column in data.columns}

    for column in data.columns:
        raw = str(column)
        normalized = normalizar_texto(raw)
        target = _COLUMN_ALIASES.get(raw.lower()) or _COLUMN_ALIASES.get(normalized)
        if not target or raw == target:
            continue
        if target in reserved or target in renames.values():
            continue
        renames[column] = target
        reserved.add(target)

    if renames:
        data = data.rename(columns=renames)

    for column, default in _DEFAULTS.items():
        if column not in data.columns:
            data[column] = default

    for column in _DATE_COLUMNS:
        data[column] = pd.to_datetime(data[column], errors="coerce")

    data["monto_pen"] = pd.to_numeric(
        data["monto_pen"],
        errors="coerce",
    ).fillna(0.0)

    string_columns = [
        column
        for column in CANONICAL_COLUMNS
        if column not in _DATE_COLUMNS and column != "monto_pen"
    ]
    for column in string_columns:
        data[column] = data[column].fillna("").astype(str).str.strip()

    missing_period = data["periodo"].eq("")
    if missing_period.any():
        generated_period = data["fecha_emision"].dt.to_period("M").astype(str)
        generated_period = generated_period.replace("NaT", "")
        data.loc[missing_period, "periodo"] = generated_period.loc[missing_period]

    object_missing = data["objeto_contractual"].map(normalizar_texto).isin(
        {"", "no indicado"}
    )
    if object_missing.any():
        normalized_type = data["tipo_orden"].map(normalizar_texto)
        inferred = pd.Series("No indicado", index=data.index, dtype="object")
        inferred.loc[normalized_type.str.contains(r"compra|bien", regex=True)] = "Bien"
        inferred.loc[normalized_type.str.contains(r"servicio", regex=True)] = "Servicio"
        data.loc[object_missing, "objeto_contractual"] = inferred.loc[object_missing]

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

    return data[CANONICAL_COLUMNS].copy()


def obtener_archivos_parquet(
    monthly_dir: str | Path | None = None,
) -> list[Path]:
    """Devuelve los archivos mensuales procesados."""
    directory = Path(monthly_dir) if monthly_dir is not None else MONTHLY_DIR
    archivos = sorted(directory.glob("*.parquet"))

    if not archivos:
        raise FileNotFoundError(
            f"No se encontraron archivos Parquet en {directory}. "
            "Primero ejecuta el procesamiento de datos."
        )

    return archivos


def crear_patron_busqueda(palabras_clave: Iterable[str]) -> str:
    """Crea una expresión regular segura con las palabras indicadas."""
    palabras_normalizadas = []
    for palabra in palabras_clave:
        normalized = normalizar_texto(palabra)
        if normalized:
            palabras_normalizadas.append(normalized)

    palabras_unicas = list(dict.fromkeys(palabras_normalizadas))
    if not palabras_unicas:
        raise ValueError("Debes indicar al menos una palabra clave válida.")

    return "|".join(re.escape(palabra) for palabra in palabras_unicas)


def _normalizar_filtro(
    value: str | Iterable[str] | None,
    *,
    sentinels: set[str],
) -> list[str]:
    if value is None:
        return []

    values = [value] if isinstance(value, str) else list(value)
    normalized: list[str] = []
    for item in values:
        term = normalizar_texto(item)
        if term and term not in sentinels:
            normalized.append(term)
    return list(dict.fromkeys(normalized))


def _aplicar_filtros(
    frame: pd.DataFrame,
    *,
    patron: str,
    departamento: str | Iterable[str] | None,
    tipo_orden: str | Iterable[str] | None,
    objeto_contractual: str | Iterable[str] | None,
) -> pd.DataFrame:
    mascara = frame["texto_busqueda"].fillna("").str.contains(
        patron,
        case=False,
        regex=True,
    )

    departamentos = _normalizar_filtro(
        departamento,
        sentinels={"todo el peru", "todos", "todo"},
    )
    if departamentos:
        normalized_series = frame["departamento"].map(normalizar_texto)
        mascara &= normalized_series.isin(departamentos)

    tipos = _normalizar_filtro(
        tipo_orden,
        sentinels={"ambos", "todos", "todo"},
    )
    if tipos:
        normalized_series = frame["tipo_orden"].map(normalizar_texto)
        type_mask = pd.Series(False, index=frame.index)
        for term in tipos:
            type_mask |= normalized_series.str.contains(
                re.escape(term),
                regex=True,
                na=False,
            )
        mascara &= type_mask

    objetos = _normalizar_filtro(
        objeto_contractual,
        sentinels={"ambos", "todos", "todo"},
    )
    if objetos:
        normalized_series = frame["objeto_contractual"].map(normalizar_texto)
        mascara &= normalized_series.isin(objetos)

    return frame.loc[mascara].copy()


def buscar_ordenes(
    palabras_clave: list[str],
    departamento: str | list[str] | None = None,
    tipo_orden: str | list[str] | None = None,
    objeto_contractual: str | list[str] | None = None,
    *,
    monthly_dir: str | Path | None = None,
    datos: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Busca órdenes relacionadas en los Parquet o en un DataFrame de respaldo."""
    patron = crear_patron_busqueda(palabras_clave)

    if datos is not None:
        frame = _normalizar_columnas(datos)
        return _aplicar_filtros(
            frame,
            patron=patron,
            departamento=departamento,
            tipo_orden=tipo_orden,
            objeto_contractual=objeto_contractual,
        ).reset_index(drop=True)

    resultados: list[pd.DataFrame] = []
    for archivo in obtener_archivos_parquet(monthly_dir):
        frame = _normalizar_columnas(pd.read_parquet(archivo))
        missing_order = frame["orden"].eq("")
        if missing_order.any():
            generated = [
                f"{archivo.stem}-{position + 1:06d}"
                for position in range(len(frame))
            ]
            frame.loc[missing_order, "orden"] = pd.Series(
                generated,
                index=frame.index,
            ).loc[missing_order]

        coincidencias = _aplicar_filtros(
            frame,
            patron=patron,
            departamento=departamento,
            tipo_orden=tipo_orden,
            objeto_contractual=objeto_contractual,
        )
        if not coincidencias.empty:
            resultados.append(coincidencias)

    if not resultados:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    return pd.concat(resultados, ignore_index=True)


def _mascara_anuladas(resultados: pd.DataFrame) -> pd.Series:
    if resultados.empty:
        return pd.Series(False, index=resultados.index, dtype=bool)
    states = resultados["estado_contratacion"].map(normalizar_texto)
    return states.str.contains(r"\banulad", regex=True, na=False)


def calcular_resumen(
    resultados: pd.DataFrame,
    *,
    ordenes_anuladas: int = 0,
) -> dict[str, Any]:
    """Calcula las métricas principales del mercado encontrado."""
    if resultados.empty:
        return {
            "total_ordenes": 0,
            "monto_total_pen": 0.0,
            "monto_promedio_pen": 0.0,
            "monto_mediano_pen": 0.0,
            "total_entidades": 0,
            "total_proveedores": 0,
            "ordenes_anuladas": int(ordenes_anuladas),
            "entidad_principal": None,
            "periodo_principal": None,
            "departamento_principal": None,
        }

    montos = resultados["monto_pen"].dropna()
    montos = montos[montos >= 0]

    entidades = resultados["entidad"].replace("", pd.NA).dropna().value_counts()
    periodos = resultados["periodo"].replace("", pd.NA).dropna().value_counts()
    departamentos = (
        resultados["departamento"].replace("", pd.NA).dropna().value_counts()
    )
    proveedores = resultados["proveedor"].replace("", pd.NA).dropna()

    return {
        "total_ordenes": int(len(resultados)),
        "monto_total_pen": float(montos.sum()) if not montos.empty else 0.0,
        "monto_promedio_pen": float(montos.mean()) if not montos.empty else 0.0,
        "monto_mediano_pen": float(montos.median()) if not montos.empty else 0.0,
        "total_entidades": int(resultados["entidad"].nunique(dropna=True)),
        "total_proveedores": int(proveedores.nunique()),
        "ordenes_anuladas": int(ordenes_anuladas),
        "entidad_principal": entidades.index[0] if not entidades.empty else None,
        "periodo_principal": periodos.index[0] if not periodos.empty else None,
        "departamento_principal": (
            departamentos.index[0] if not departamentos.empty else None
        ),
    }


def obtener_entidades_principales(
    resultados: pd.DataFrame,
    limite: int = 10,
) -> pd.DataFrame:
    """Devuelve las entidades con más órdenes relacionadas."""
    if resultados.empty:
        return pd.DataFrame(
            columns=[
                "entidad",
                "departamento",
                "cantidad_ordenes",
                "monto_total_pen",
            ]
        )

    return (
        resultados.groupby(["entidad", "departamento"], dropna=False)
        .agg(
            cantidad_ordenes=("orden", "size"),
            monto_total_pen=("monto_pen", "sum"),
        )
        .reset_index()
        .sort_values(
            ["cantidad_ordenes", "monto_total_pen"],
            ascending=[False, False],
        )
        .head(limite)
    )


def obtener_tendencia_mensual(resultados: pd.DataFrame) -> pd.DataFrame:
    """Agrupa los resultados por año y mes."""
    if resultados.empty:
        return pd.DataFrame(
            columns=["periodo", "cantidad_ordenes", "monto_total_pen"]
        )

    return (
        resultados.groupby("periodo", dropna=False)
        .agg(
            cantidad_ordenes=("orden", "size"),
            monto_total_pen=("monto_pen", "sum"),
        )
        .reset_index()
        .sort_values("periodo")
    )


def obtener_resumen_departamentos(resultados: pd.DataFrame) -> pd.DataFrame:
    """Agrupa órdenes, monto y entidades por departamento."""
    if resultados.empty:
        return pd.DataFrame(
            columns=[
                "departamento",
                "cantidad_ordenes",
                "monto_total_pen",
                "cantidad_entidades",
            ]
        )

    return (
        resultados.groupby("departamento", dropna=False)
        .agg(
            cantidad_ordenes=("orden", "size"),
            monto_total_pen=("monto_pen", "sum"),
            cantidad_entidades=("entidad", "nunique"),
        )
        .reset_index()
        .sort_values("monto_total_pen", ascending=False)
    )


def obtener_resumen_objetos(resultados: pd.DataFrame) -> pd.DataFrame:
    """Agrupa las órdenes por objeto contractual."""
    if resultados.empty:
        return pd.DataFrame(
            columns=["objeto_contractual", "cantidad_ordenes", "monto_total_pen"]
        )

    return (
        resultados.groupby("objeto_contractual", dropna=False)
        .agg(
            cantidad_ordenes=("orden", "size"),
            monto_total_pen=("monto_pen", "sum"),
        )
        .reset_index()
        .sort_values("cantidad_ordenes", ascending=False)
    )


def _serializable_value(value: Any) -> Any:
    if value is None or value is pd.NA:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass
    return value


def _records_serializables(frame: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for record in frame.to_dict(orient="records"):
        records.append(
            {key: _serializable_value(value) for key, value in record.items()}
        )
    return records


def analizar_mercado(
    palabras_clave: list[str],
    departamento: str | list[str] | None = None,
    tipo_orden: str | list[str] | None = None,
    limite_entidades: int = 10,
    *,
    objeto_contractual: str | list[str] | None = None,
    monthly_dir: str | Path | None = None,
    datos: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Ejecuta el análisis completo y devuelve datos serializables.

    Esta función es el contrato entre Gemma, la capa de datos y Streamlit.
    Los cálculos siempre se realizan sobre los registros encontrados; Gemma
    únicamente interpreta la descripción y redacta el informe.
    """
    encontrados = buscar_ordenes(
        palabras_clave=palabras_clave,
        departamento=departamento,
        tipo_orden=tipo_orden,
        objeto_contractual=objeto_contractual,
        monthly_dir=monthly_dir,
        datos=datos,
    )

    cancelled_mask = _mascara_anuladas(encontrados)
    anuladas = encontrados.loc[cancelled_mask].copy()
    resultados = encontrados.loc[~cancelled_mask].copy()

    resumen = calcular_resumen(
        resultados,
        ordenes_anuladas=len(anuladas),
    )
    entidades = obtener_entidades_principales(
        resultados,
        limite=limite_entidades,
    )
    tendencia = obtener_tendencia_mensual(resultados)
    departamentos = obtener_resumen_departamentos(resultados)
    objetos = obtener_resumen_objetos(resultados)

    ejemplos = (
        resultados.sort_values("monto_pen", ascending=False).head(10)
        if not resultados.empty
        else resultados
    )

    return {
        "consulta": {
            "palabras_clave": list(palabras_clave),
            "departamento": departamento or "Todo el Perú",
            "tipo_orden": tipo_orden or "Ambos",
            "objeto_contractual": objeto_contractual or "Ambos",
        },
        "resumen": resumen,
        "entidades_principales": _records_serializables(entidades),
        "tendencia_mensual": _records_serializables(tendencia),
        "departamentos": _records_serializables(departamentos),
        "objetos_contractuales": _records_serializables(objetos),
        "ordenes_evidencia": _records_serializables(resultados),
        "ordenes_ejemplo": _records_serializables(ejemplos),
    }


def obtener_catalogo_mercado(
    monthly_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Obtiene opciones y volumen de la fuente sin conservar todos los registros."""
    departments: set[str] = set()
    objects: set[str] = set()
    total = 0
    files = obtener_archivos_parquet(monthly_dir)

    for archivo in files:
        frame = _normalizar_columnas(pd.read_parquet(archivo))
        total += len(frame)
        departments.update(
            value
            for value in frame["departamento"].dropna().astype(str)
            if value and value != "No indicado"
        )
        objects.update(
            value
            for value in frame["objeto_contractual"].dropna().astype(str)
            if value and value != "No indicado"
        )

    return {
        "total_registros": int(total),
        "departamentos": sorted(departments),
        "objetos_contractuales": sorted(objects),
        "archivos": [str(path) for path in files],
    }


if __name__ == "__main__":
    resultado = analizar_mercado(
        palabras_clave=[
            "servicio de limpieza",
            "limpieza de oficinas",
            "pintado de ambientes",
            "mantenimiento de locales",
        ],
        departamento="Lima",
        tipo_orden="servicio",
    )

    print("\nRESUMEN")
    for clave, valor in resultado["resumen"].items():
        print(f"- {clave}: {valor}")
