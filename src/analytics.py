"""Búsqueda y análisis de órdenes públicas para MYPE Radar."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd


MONTHLY_DIR = Path("data/processed/monthly")

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


def normalizar_texto(texto: str) -> str:
    """Normaliza una palabra o frase para buscarla en el dataset."""
    resultado = str(texto).strip().lower()
    resultado = unicodedata.normalize("NFKD", resultado)
    resultado = "".join(
        caracter
        for caracter in resultado
        if not unicodedata.combining(caracter)
    )
    resultado = re.sub(r"[^a-z0-9]+", " ", resultado)
    resultado = re.sub(r"\s+", " ", resultado)
    return resultado.strip()


def obtener_archivos_parquet() -> list[Path]:
    """Devuelve los archivos mensuales procesados."""
    archivos = sorted(MONTHLY_DIR.glob("*.parquet"))

    if not archivos:
        raise FileNotFoundError(
            "No se encontraron archivos Parquet. "
            "Primero ejecuta src/data_processing.py."
        )

    return archivos


def crear_patron_busqueda(palabras_clave: list[str]) -> str:
    """Crea una expresión regular segura con las palabras indicadas."""
    palabras_normalizadas = [
        normalizar_texto(palabra)
        for palabra in palabras_clave
        if normalizar_texto(palabra)
    ]

    if not palabras_normalizadas:
        raise ValueError("Debes indicar al menos una palabra clave válida.")

    return "|".join(
        re.escape(palabra)
        for palabra in palabras_normalizadas
    )


def buscar_ordenes(
    palabras_clave: list[str],
    departamento: str | None = None,
    tipo_orden: str | None = None,
) -> pd.DataFrame:
    """Busca órdenes relacionadas en todos los archivos mensuales."""
    patron = crear_patron_busqueda(palabras_clave)
    resultados: list[pd.DataFrame] = []

    for archivo in obtener_archivos_parquet():
        frame = pd.read_parquet(
            archivo,
            columns=SEARCH_COLUMNS,
        )

        mascara = frame["texto_busqueda"].fillna("").str.contains(
            patron,
            case=False,
            regex=True,
        )

        if departamento and departamento.lower() != "todo el peru":
            departamento_normalizado = normalizar_texto(departamento)

            departamentos = (
                frame["departamento"]
                .fillna("")
                .map(normalizar_texto)
            )

            mascara &= departamentos.eq(departamento_normalizado)

        if tipo_orden and tipo_orden.lower() != "ambos":
            tipo_normalizado = normalizar_texto(tipo_orden)

            tipos = (
                frame["tipo_orden"]
                .fillna("")
                .map(normalizar_texto)
            )

            mascara &= tipos.str.contains(
                re.escape(tipo_normalizado),
                regex=True,
            )

        coincidencias = frame.loc[mascara].copy()

        if not coincidencias.empty:
            resultados.append(coincidencias)

    if not resultados:
        return pd.DataFrame(columns=SEARCH_COLUMNS)

    return pd.concat(
        resultados,
        ignore_index=True,
    )


def calcular_resumen(resultados: pd.DataFrame) -> dict[str, Any]:
    """Calcula las métricas principales del mercado encontrado."""
    if resultados.empty:
        return {
            "total_ordenes": 0,
            "monto_total_pen": 0.0,
            "monto_promedio_pen": 0.0,
            "monto_mediano_pen": 0.0,
            "entidad_principal": None,
            "periodo_principal": None,
            "departamento_principal": None,
        }

    montos = resultados["monto_pen"].dropna()
    montos = montos[montos >= 0]

    entidades = resultados["entidad"].dropna().value_counts()
    periodos = resultados["periodo"].dropna().value_counts()
    departamentos = resultados["departamento"].dropna().value_counts()

    return {
        "total_ordenes": int(len(resultados)),
        "monto_total_pen": float(montos.sum()) if not montos.empty else 0.0,
        "monto_promedio_pen": float(montos.mean()) if not montos.empty else 0.0,
        "monto_mediano_pen": float(montos.median()) if not montos.empty else 0.0,
        "entidad_principal": (
            entidades.index[0] if not entidades.empty else None
        ),
        "periodo_principal": (
            periodos.index[0] if not periodos.empty else None
        ),
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
            columns=["entidad", "cantidad_ordenes", "monto_total_pen"]
        )

    tabla = (
        resultados.groupby("entidad", dropna=True)
        .agg(
            cantidad_ordenes=("entidad", "size"),
            monto_total_pen=("monto_pen", "sum"),
        )
        .reset_index()
        .sort_values(
            ["cantidad_ordenes", "monto_total_pen"],
            ascending=[False, False],
        )
        .head(limite)
    )

    return tabla


def obtener_tendencia_mensual(
    resultados: pd.DataFrame,
) -> pd.DataFrame:
    """Agrupa los resultados por año y mes."""
    if resultados.empty:
        return pd.DataFrame(
            columns=["periodo", "cantidad_ordenes", "monto_total_pen"]
        )

    tabla = (
        resultados.groupby("periodo", dropna=True)
        .agg(
            cantidad_ordenes=("periodo", "size"),
            monto_total_pen=("monto_pen", "sum"),
        )
        .reset_index()
        .sort_values("periodo")
    )

    return tabla


if __name__ == "__main__":
    palabras = [
        "limpieza",
        "pintura",
        "mantenimiento",
    ]

    ordenes = buscar_ordenes(
        palabras_clave=palabras,
        tipo_orden="servicio",
    )

    resumen = calcular_resumen(ordenes)

    print("\nResumen:")
    for clave, valor in resumen.items():
        print(f"- {clave}: {valor}")

    print("\nEntidades principales:")
    print(obtener_entidades_principales(ordenes).to_string(index=False))

    print("\nTendencia mensual:")
    print(obtener_tendencia_mensual(ordenes).to_string(index=False))