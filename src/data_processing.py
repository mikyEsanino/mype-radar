"""Procesamiento de órdenes públicas para MYPE Radar."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


RAW_DIR = Path("data/raw/2026")
PROCESSED_DIR = Path("data/processed")
MONTHLY_DIR = PROCESSED_DIR / "monthly"

SAMPLE_PATH = PROCESSED_DIR / "ordenes_muestra.csv"
SUMMARY_PATH = PROCESSED_DIR / "resumen_dataset.json"


COLUMN_ALIASES: dict[str, list[str]] = {
    "entidad": [
        "entidad",
        "nombre_entidad",
        "razon_social_entidad",
    ],
    "departamento": [
        "departamento_entidad",
        "departamento",
    ],
    "tipo_orden": [
        "tipoorden",
        "tipo_orden",
    ],
    "descripcion": [
        "descripcion_orden",
        "descripcion",
        "descripcion_del_bien_o_servicio",
    ],
    "objeto_contractual": [
        "objetocontractual",
        "objeto_contractual",
    ],
    "estado": [
        "estadocontratacion",
        "estado_contratacion",
    ],
    "tipo_contratacion": [
        "tipodecontratacion",
        "tipo_de_contratacion",
    ],
    "monto": [
        "monto_total_orden_original",
        "monto_total",
        "monto",
    ],
    "moneda": [
        "moneda",
    ],
    "fecha_registro": [
        "fecha_registro",
    ],
    "fecha_emision": [
        "fecha_de_emision",
        "fecha_emision",
    ],
    "proveedor": [
        "proveedor",
        "nombre_proveedor",
        "razon_social_proveedor",
    ],
    "ruc_proveedor": [
        "ruc_proveedor",
    ],
}


OUTPUT_COLUMNS = [
    "entidad",
    "departamento",
    "tipo_orden",
    "descripcion",
    "objeto_contractual",
    "estado",
    "tipo_contratacion",
    "monto",
    "monto_pen",
    "moneda",
    "fecha_registro",
    "fecha_emision",
    "periodo",
    "proveedor",
    "ruc_proveedor",
    "texto_busqueda",
    "archivo_origen",
]


def normalizar_nombre_columna(value: object) -> str:
    """Convierte el nombre de una columna a un formato uniforme."""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def normalizar_texto_serie(series: pd.Series) -> pd.Series:
    """Normaliza texto para las búsquedas posteriores."""
    result = series.astype("string").fillna("")
    result = result.str.normalize("NFKD")
    result = result.str.encode("ascii", errors="ignore").str.decode("utf-8")
    result = result.str.lower()
    result = result.str.replace(r"[^a-z0-9]+", " ", regex=True)
    result = result.str.replace(r"\s+", " ", regex=True)
    return result.str.strip()


def detectar_columnas(path: Path) -> dict[str, str]:
    """Relaciona las columnas reales del Excel con nombres internos."""
    header = pd.read_excel(
        path,
        engine="openpyxl",
        nrows=0,
    )

    normalized_to_original = {
        normalizar_nombre_columna(column): str(column)
        for column in header.columns
    }

    selected: dict[str, str] = {}

    for canonical_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized_to_original:
                selected[canonical_name] = normalized_to_original[alias]
                break

    return selected


def convertir_monto(series: pd.Series) -> pd.Series:
    """Convierte la columna de montos a valores numéricos."""
    numeric = pd.to_numeric(series, errors="coerce")

    missing_mask = numeric.isna() & series.notna()

    if missing_mask.any():
        text = series.loc[missing_mask].astype(str)
        text = text.str.replace(r"[^\d,.\-]", "", regex=True)

        both_separators = text.str.contains(",", regex=False) & text.str.contains(
            ".", regex=False
        )

        text.loc[both_separators] = text.loc[both_separators].str.replace(
            ",", "", regex=False
        )

        only_comma = text.str.contains(",", regex=False) & ~text.str.contains(
            ".", regex=False
        )

        text.loc[only_comma] = text.loc[only_comma].str.replace(
            ",", ".", regex=False
        )

        numeric.loc[missing_mask] = pd.to_numeric(
            text,
            errors="coerce",
        )

    return numeric


def convertir_fecha(series: pd.Series) -> pd.Series:
    """Convierte texto, fechas de Excel y timestamps a datetime."""
    parsed = pd.to_datetime(
        series,
        errors="coerce",
        dayfirst=True,
    )

    numeric = pd.to_numeric(series, errors="coerce")
    serial_mask = parsed.isna() & numeric.notna()

    if serial_mask.any():
        parsed.loc[serial_mask] = (
            pd.Timestamp("1899-12-30")
            + pd.to_timedelta(numeric.loc[serial_mask], unit="D")
        )

    return parsed


def normalizar_moneda(series: pd.Series) -> pd.Series:
    """Normaliza los principales códigos de moneda."""
    text = normalizar_texto_serie(series)

    result = pd.Series("OTRA", index=series.index, dtype="string")

    result.loc[
        text.str.contains(r"\bpen\b|sol|nuevos soles", regex=True)
    ] = "PEN"

    result.loc[
        text.str.contains(r"\busd\b|dolar", regex=True)
    ] = "USD"

    result.loc[
        text.str.contains(r"\beur\b|euro", regex=True)
    ] = "EUR"

    return result


def cargar_y_limpiar(path: Path) -> pd.DataFrame:
    """Carga solo las columnas necesarias y limpia un archivo mensual."""
    selected = detectar_columnas(path)

    required = {"entidad", "descripcion", "monto"}

    missing = required - set(selected)

    if missing:
        raise ValueError(
            f"{path.name}: faltan columnas obligatorias: {sorted(missing)}"
        )

    usecols = list(selected.values())

    print(f"\nLeyendo {path.name}")
    print(f"Columnas detectadas: {list(selected.keys())}")

    frame = pd.read_excel(
        path,
        engine="openpyxl",
        usecols=usecols,
        dtype=object,
    )

    rename_map = {
        original_name: canonical_name
        for canonical_name, original_name in selected.items()
    }

    frame = frame.rename(columns=rename_map)

    for column in COLUMN_ALIASES:
        if column not in frame.columns:
            frame[column] = pd.NA

    text_columns = [
        "entidad",
        "departamento",
        "tipo_orden",
        "descripcion",
        "objeto_contractual",
        "estado",
        "tipo_contratacion",
        "proveedor",
        "ruc_proveedor",
    ]

    for column in text_columns:
        frame[column] = frame[column].astype("string").str.strip()

    frame["monto"] = convertir_monto(frame["monto"])
    frame["moneda"] = normalizar_moneda(frame["moneda"])

    frame["monto_pen"] = frame["monto"].where(
        frame["moneda"].eq("PEN")
    )

    frame["fecha_registro"] = convertir_fecha(frame["fecha_registro"])
    frame["fecha_emision"] = convertir_fecha(frame["fecha_emision"])

    # Para analizar la demanda usamos la fecha de emisión.
    # Si está vacía, usamos la fecha de registro como respaldo.
    analysis_date = frame["fecha_emision"].fillna(
        frame["fecha_registro"]
    )

    # Solo utilizaremos año y mes: 2026-01, 2026-02, etc.
    frame["periodo"] = (
        analysis_date
        .dt.to_period("M")
        .astype("string")
    )

    frame["texto_busqueda"] = normalizar_texto_serie(
        frame["descripcion"].fillna("")
        + " "
        + frame["objeto_contractual"].fillna("")
    )

    frame["archivo_origen"] = path.name

    frame = frame[
        frame["descripcion"].notna()
        & frame["descripcion"].str.strip().ne("")
    ].copy()

    frame = frame.drop_duplicates(
        subset=[
            "entidad",
            "descripcion",
            "monto",
            "fecha_registro",
            "proveedor",
        ]
    )

    return frame[OUTPUT_COLUMNS]


def procesar_archivos() -> None:
    """Procesa todos los archivos mensuales encontrados."""
    files = sorted(RAW_DIR.glob("*.xlsx"))

    if not files:
        raise FileNotFoundError(
            f"No existen archivos XLSX en {RAW_DIR.resolve()}"
        )

    MONTHLY_DIR.mkdir(parents=True, exist_ok=True)

    summaries: list[dict] = []
    samples: list[pd.DataFrame] = []

    for file in files:
        try:
            frame = cargar_y_limpiar(file)

            output_path = MONTHLY_DIR / f"{file.stem}.parquet"

            frame.to_parquet(
                output_path,
                index=False,
                compression="snappy",
            )

            sample_size = min(1500, len(frame))

            if sample_size > 0:
                samples.append(
                    frame.sample(
                        n=sample_size,
                        random_state=42,
                    )
                )

            summaries.append(
                {
                    "archivo": file.name,
                    "filas_limpias": int(len(frame)),
                    "entidades": int(frame["entidad"].nunique()),
                    "departamentos": int(frame["departamento"].nunique()),
                    "monto_pen_total": float(
                        frame["monto_pen"].sum(skipna=True)
                    ),
                    "periodos": sorted(
                        frame["periodo"].dropna().unique().tolist()
                    ),
                }
            )

            print(
                f"Procesado: {len(frame):,} filas → {output_path.name}"
            )

        except Exception as error:
            print(f"ERROR en {file.name}: {error}")

    if not summaries:
        raise RuntimeError("No se pudo procesar ningún archivo.")

    if samples:
        combined_sample = pd.concat(
            samples,
            ignore_index=True,
        )

        combined_sample.to_csv(
            SAMPLE_PATH,
            index=False,
            encoding="utf-8-sig",
        )

        print(f"\nMuestra guardada: {SAMPLE_PATH}")

    total_rows = sum(item["filas_limpias"] for item in summaries)

    general_summary = {
        "cantidad_archivos": len(summaries),
        "total_filas_limpias": total_rows,
        "archivos": summaries,
    }

    with SUMMARY_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            general_summary,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Resumen guardado: {SUMMARY_PATH}")
    print(f"Total procesado: {total_rows:,} registros")


if __name__ == "__main__":
    procesar_archivos()