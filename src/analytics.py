"""Búsqueda y análisis de órdenes públicas para MYPE Radar."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd


MONTHLY_DIR = Path("data/processed/monthly")

PARQUET_COLUMNS = [
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
]


LEGACY_TO_CANONICAL = {
    "ENTIDAD": "entidad",
    "RUC_ENTIDAD": "ruc_entidad",
    "FECHA_REGISTRO": "fecha_registro",
    "FECHA_DE_EMISION": "fecha_emision",
    "FECHA_COMPROMISO_PRESUPUESTAL": (
        "fecha_compromiso_presupuestal"
    ),
    "FECHA_DE_NOTIFICACION": "fecha_notificacion",
    "TIPOORDEN": "tipo_orden",
    "NRO_DE_ORDEN": "numero_orden",
    "ORDEN": "orden",
    "DESCRIPCION_ORDEN": "descripcion",
    "MONEDA": "moneda",
    "MONTO_TOTAL_ORDEN_ORIGINAL": "monto",
    "OBJETOCONTRACTUAL": "objeto_contractual",
    "ESTADOCONTRATACION": "estado_contratacion",
    "TIPODECONTRATACION": "tipo_contratacion",
    "DEPARTAMENTO": "departamento",
    "RUC_CONTRATISTA": "ruc_proveedor",
    "NOMBRE_RAZON_CONTRATISTA": "proveedor",
    "_DESCRIPTION_NORMALIZED": "texto_busqueda",
}


DEFAULT_COLUMNS: dict[str, Any] = {
    "entidad": "",
    "ruc_entidad": "",
    "fecha_registro": pd.NaT,
    "fecha_emision": pd.NaT,
    "fecha_compromiso_presupuestal": pd.NaT,
    "fecha_notificacion": pd.NaT,
    "tipo_orden": "",
    "numero_orden": "",
    "orden": "",
    "descripcion": "",
    "moneda": "PEN",
    "monto": 0.0,
    "monto_pen": pd.NA,
    "objeto_contractual": "",
    "estado_contratacion": "",
    "tipo_contratacion": "",
    "departamento": "",
    "ruc_proveedor": "",
    "proveedor": "",
    "periodo": pd.NA,
    "texto_busqueda": "",
}


def normalizar_texto(texto: Any) -> str:
    """Normaliza texto para comparaciones y búsquedas."""
    if texto is None or texto is pd.NA:
        return ""

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


def normalizar_texto_serie(series: pd.Series) -> pd.Series:
    """Normaliza una serie de Pandas."""
    resultado = series.astype("string").fillna("")
    resultado = resultado.str.normalize("NFKD")
    resultado = resultado.str.encode(
        "ascii",
        errors="ignore",
    ).str.decode("utf-8")
    resultado = resultado.str.lower()
    resultado = resultado.str.replace(
        r"[^a-z0-9]+",
        " ",
        regex=True,
    )
    resultado = resultado.str.replace(
        r"\s+",
        " ",
        regex=True,
    )

    return resultado.str.strip()


def _como_lista(valor: Any) -> list[str]:
    """Acepta un texto, lista o conjunto de filtros."""
    if valor is None:
        return []

    if isinstance(valor, str):
        valores = [valor]
    else:
        try:
            valores = list(valor)
        except TypeError:
            valores = [valor]

    return [
        str(elemento).strip()
        for elemento in valores
        if str(elemento).strip()
    ]


def _normalizar_objeto(valor: Any) -> str:
    """Unifica Compra/Bien y Servicio."""
    texto = normalizar_texto(valor)

    if texto in {"", "ambos", "todos", "todo"}:
        return ""

    if "servicio" in texto:
        return "servicio"

    if (
        "bien" in texto
        or "compra" in texto
        or "adquisicion" in texto
    ):
        return "bien"

    return texto


def _normalizar_objeto_serie(
    objeto_contractual: pd.Series,
    tipo_orden: pd.Series,
) -> pd.Series:
    """Normaliza Bien y Servicio e infiere valores faltantes."""
    objetos = normalizar_texto_serie(objeto_contractual)
    tipos = normalizar_texto_serie(tipo_orden)

    resultado = pd.Series(
        "",
        index=objetos.index,
        dtype="string",
    )

    resultado.loc[
        objetos.str.contains(
            "servicio",
            regex=False,
            na=False,
        )
    ] = "servicio"

    resultado.loc[
        objetos.str.contains(
            r"bien|compra|adquisicion",
            regex=True,
            na=False,
        )
    ] = "bien"

    vacios = resultado.eq("")

    resultado.loc[
        vacios
        & tipos.str.contains(
            "servicio",
            regex=False,
            na=False,
        )
    ] = "servicio"

    resultado.loc[
        vacios
        & tipos.str.contains(
            r"compra|adquisicion",
            regex=True,
            na=False,
        )
    ] = "bien"

    return resultado


def _canonizar_datos(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Convierte datos Parquet o históricos al esquema interno."""
    datos = dataframe.copy()

    rename_map = {
        columna: LEGACY_TO_CANONICAL[columna]
        for columna in datos.columns
        if columna in LEGACY_TO_CANONICAL
    }

    datos = datos.rename(columns=rename_map)

    if (
        "estado" in datos.columns
        and "estado_contratacion" not in datos.columns
    ):
        datos = datos.rename(
            columns={"estado": "estado_contratacion"}
        )

    for columna, valor in DEFAULT_COLUMNS.items():
        if columna not in datos.columns:
            datos[columna] = valor

    date_columns = [
        "fecha_registro",
        "fecha_emision",
        "fecha_compromiso_presupuestal",
        "fecha_notificacion",
    ]

    for columna in date_columns:
        datos[columna] = pd.to_datetime(
            datos[columna],
            errors="coerce",
        )

    datos["monto"] = pd.to_numeric(
        datos["monto"],
        errors="coerce",
    )

    monto_pen_actual = pd.to_numeric(
        datos["monto_pen"],
        errors="coerce",
    )

    moneda_normalizada = normalizar_texto_serie(
        datos["moneda"]
    )

    es_pen = moneda_normalizada.str.contains(
        r"\bpen\b|sol",
        regex=True,
        na=False,
    )

    datos["monto_pen"] = monto_pen_actual.fillna(
        datos["monto"].where(es_pen)
    )

    objetos = _normalizar_objeto_serie(
        datos["objeto_contractual"],
        datos["tipo_orden"],
    )

    objeto_vacio = (
        datos["objeto_contractual"]
        .astype("string")
        .fillna("")
        .str.strip()
        .eq("")
    )

    datos.loc[
        objeto_vacio & objetos.eq("bien"),
        "objeto_contractual",
    ] = "Bien"

    datos.loc[
        objeto_vacio & objetos.eq("servicio"),
        "objeto_contractual",
    ] = "Servicio"

    fecha_analisis = datos["fecha_registro"].fillna(
        datos["fecha_emision"]
    )

    periodo_calculado = (
        fecha_analisis
        .dt.to_period("M")
        .astype("string")
    )

    periodo_actual = (
        datos["periodo"]
        .astype("string")
        .fillna("")
        .str.strip()
    )

    datos["periodo"] = periodo_actual.where(
        periodo_actual.ne(""),
        periodo_calculado,
    )

    texto_calculado = normalizar_texto_serie(
        datos["descripcion"].fillna("")
        + " "
        + datos["objeto_contractual"].fillna("")
    )

    texto_actual = (
        datos["texto_busqueda"]
        .astype("string")
        .fillna("")
        .str.strip()
    )

    datos["texto_busqueda"] = texto_actual.where(
        texto_actual.ne(""),
        texto_calculado,
    )

    return datos


def obtener_archivos_parquet(
    monthly_dir: Path | str = MONTHLY_DIR,
) -> list[Path]:
    """Devuelve los archivos Parquet mensuales."""
    directorio = Path(monthly_dir)
    archivos = sorted(directorio.glob("*.parquet"))

    if not archivos:
        raise FileNotFoundError(
            "No se encontraron archivos Parquet en "
            f"{directorio.resolve()}."
        )

    return archivos


def obtener_catalogo_mercado(
    monthly_dir: Path | str = MONTHLY_DIR,
) -> dict[str, Any]:
    """Obtiene filtros disponibles para Streamlit."""
    departamentos: set[str] = set()
    objetos_contractuales: set[str] = set()
    total_registros = 0

    for archivo in obtener_archivos_parquet(monthly_dir):
        frame = pd.read_parquet(
            archivo,
            columns=[
                "departamento",
                "objeto_contractual",
                "tipo_orden",
            ],
        )

        total_registros += len(frame)

        departamentos.update(
            str(valor).strip()
            for valor in frame["departamento"].dropna().unique()
            if str(valor).strip()
        )

        objetos = _normalizar_objeto_serie(
            frame["objeto_contractual"],
            frame["tipo_orden"],
        )

        for objeto in objetos.dropna().unique():
            if objeto == "bien":
                objetos_contractuales.add("Bien")
            elif objeto == "servicio":
                objetos_contractuales.add("Servicio")

    return {
        "departamentos": sorted(
            departamentos,
            key=str.casefold,
        ),
        "objetos_contractuales": sorted(
            objetos_contractuales,
            key=str.casefold,
        ),
        "total_registros": int(total_registros),
    }


def crear_patron_busqueda(
    palabras_clave: list[str],
) -> str:
    """Crea una expresión regular segura."""
    palabras_normalizadas: list[str] = []

    for palabra in palabras_clave:
        normalizada = normalizar_texto(palabra)

        if (
            normalizada
            and normalizada not in palabras_normalizadas
        ):
            palabras_normalizadas.append(normalizada)

    if not palabras_normalizadas:
        raise ValueError(
            "Debes indicar al menos una palabra clave válida."
        )

    return "|".join(
        re.escape(palabra)
        for palabra in palabras_normalizadas
    )


def _filtrar_frame(
    frame: pd.DataFrame,
    *,
    patron: str,
    departamento: str | list[str] | None,
    objeto_contractual: str | list[str] | None,
) -> pd.DataFrame:
    """Aplica palabras clave, departamento y objeto contractual."""
    datos = _canonizar_datos(frame)

    mascara = datos["texto_busqueda"].str.contains(
        patron,
        case=False,
        regex=True,
        na=False,
    )

    departamentos = {
        normalizar_texto(valor)
        for valor in _como_lista(departamento)
        if normalizar_texto(valor)
        not in {
            "",
            "todo el peru",
            "todos",
            "todo",
        }
    }

    if departamentos:
        departamentos_datos = normalizar_texto_serie(
            datos["departamento"]
        )

        mascara &= departamentos_datos.isin(
            departamentos
        )

    objetos = {
        _normalizar_objeto(valor)
        for valor in _como_lista(objeto_contractual)
        if _normalizar_objeto(valor)
    }

    if objetos:
        objetos_datos = _normalizar_objeto_serie(
            datos["objeto_contractual"],
            datos["tipo_orden"],
        )

        mascara &= objetos_datos.isin(objetos)

    return datos.loc[mascara].copy()


def buscar_ordenes(
    palabras_clave: list[str],
    departamento: str | list[str] | None = None,
    objeto_contractual: str | list[str] | None = None,
    datos: pd.DataFrame | None = None,
    *,
    tipo_orden: str | list[str] | None = None,
    monthly_dir: Path | str = MONTHLY_DIR,
) -> pd.DataFrame:
    """Busca órdenes en los Parquet o en un DataFrame directo."""
    if (
        objeto_contractual is None
        and tipo_orden is not None
    ):
        objeto_contractual = tipo_orden

    patron = crear_patron_busqueda(palabras_clave)
    directorio = Path(monthly_dir)

    # data_service entrega un catálogo liviano cuando existen
    # los archivos mensuales. En ese caso hay que leer los Parquet.
    if (
        datos is not None
        and datos.attrs.get("source_type") == "monthly"
    ):
        ruta_mensual = datos.attrs.get("monthly_dir")

        if ruta_mensual:
            directorio = Path(ruta_mensual)

        datos = None

    resultados: list[pd.DataFrame] = []

    if datos is not None:
        coincidencias = _filtrar_frame(
            datos,
            patron=patron,
            departamento=departamento,
            objeto_contractual=objeto_contractual,
        )

        if not coincidencias.empty:
            resultados.append(coincidencias)

    else:
        for archivo in obtener_archivos_parquet(
            directorio
        ):
            frame = pd.read_parquet(
                archivo,
                columns=PARQUET_COLUMNS,
            )

            coincidencias = _filtrar_frame(
                frame,
                patron=patron,
                departamento=departamento,
                objeto_contractual=objeto_contractual,
            )

            if not coincidencias.empty:
                resultados.append(coincidencias)

    if not resultados:
        return _canonizar_datos(pd.DataFrame())

    return pd.concat(
        resultados,
        ignore_index=True,
    )


def _serie_no_vacia(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .fillna("")
        .str.strip()
        .ne("")
    )


def calcular_resumen(
    resultados: pd.DataFrame,
) -> dict[str, Any]:
    """Calcula las métricas principales."""
    if resultados.empty:
        return {
            "total_ordenes": 0,
            "monto_total_pen": 0.0,
            "monto_promedio_pen": 0.0,
            "monto_mediano_pen": 0.0,
            "total_entidades": 0,
            "total_proveedores": 0,
            "ordenes_anuladas": 0,
            "entidad_principal": None,
            "periodo_principal": None,
            "departamento_principal": None,
        }

    montos = pd.to_numeric(
        resultados["monto_pen"],
        errors="coerce",
    ).dropna()

    montos = montos[montos >= 0]

    entidades = resultados.loc[
        _serie_no_vacia(resultados["entidad"]),
        "entidad",
    ]

    proveedores = resultados.loc[
        _serie_no_vacia(resultados["proveedor"]),
        "proveedor",
    ]

    periodos = resultados.loc[
        _serie_no_vacia(resultados["periodo"]),
        "periodo",
    ].value_counts()

    departamentos = resultados.loc[
        _serie_no_vacia(resultados["departamento"]),
        "departamento",
    ].value_counts()

    estados = normalizar_texto_serie(
        resultados["estado_contratacion"]
    )

    return {
        "total_ordenes": int(len(resultados)),
        "monto_total_pen": (
            float(montos.sum())
            if not montos.empty
            else 0.0
        ),
        "monto_promedio_pen": (
            float(montos.mean())
            if not montos.empty
            else 0.0
        ),
        "monto_mediano_pen": (
            float(montos.median())
            if not montos.empty
            else 0.0
        ),
        "total_entidades": int(
            entidades.nunique()
        ),
        "total_proveedores": int(
            proveedores.nunique()
        ),
        "ordenes_anuladas": int(
            estados.str.contains(
                "anulad",
                regex=False,
                na=False,
            ).sum()
        ),
        "entidad_principal": (
            entidades.value_counts().index[0]
            if not entidades.empty
            else None
        ),
        "periodo_principal": (
            periodos.index[0]
            if not periodos.empty
            else None
        ),
        "departamento_principal": (
            departamentos.index[0]
            if not departamentos.empty
            else None
        ),
    }


def obtener_entidades_principales(
    resultados: pd.DataFrame,
    limite: int = 10,
) -> pd.DataFrame:
    """Agrupa las órdenes por entidad y departamento."""
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
        resultados.groupby(
            ["entidad", "departamento"],
            dropna=True,
        )
        .agg(
            cantidad_ordenes=("entidad", "size"),
            monto_total_pen=("monto_pen", "sum"),
        )
        .reset_index()
        .sort_values(
            [
                "cantidad_ordenes",
                "monto_total_pen",
            ],
            ascending=[False, False],
        )
        .head(limite)
    )


def obtener_tendencia_mensual(
    resultados: pd.DataFrame,
) -> pd.DataFrame:
    """Agrupa las órdenes por año y mes."""
    if resultados.empty:
        return pd.DataFrame(
            columns=[
                "periodo",
                "cantidad_ordenes",
                "monto_total_pen",
            ]
        )

    return (
        resultados.groupby(
            "periodo",
            dropna=True,
        )
        .agg(
            cantidad_ordenes=("periodo", "size"),
            monto_total_pen=("monto_pen", "sum"),
        )
        .reset_index()
        .sort_values("periodo")
    )


def obtener_resumen_departamentos(
    resultados: pd.DataFrame,
) -> pd.DataFrame:
    """Agrupa resultados por departamento."""
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
        resultados.groupby(
            "departamento",
            dropna=True,
        )
        .agg(
            cantidad_ordenes=("departamento", "size"),
            monto_total_pen=("monto_pen", "sum"),
            cantidad_entidades=("entidad", "nunique"),
        )
        .reset_index()
        .sort_values(
            [
                "cantidad_ordenes",
                "monto_total_pen",
            ],
            ascending=[False, False],
        )
    )


def obtener_resumen_objetos(
    resultados: pd.DataFrame,
) -> pd.DataFrame:
    """Agrupa los resultados entre Bien y Servicio."""
    if resultados.empty:
        return pd.DataFrame(
            columns=[
                "objeto_contractual",
                "cantidad_ordenes",
                "monto_total_pen",
            ]
        )

    datos = resultados.copy()

    objetos = _normalizar_objeto_serie(
        datos["objeto_contractual"],
        datos["tipo_orden"],
    )

    datos["objeto_contractual"] = objetos.map(
        {
            "bien": "Bien",
            "servicio": "Servicio",
        }
    ).fillna("No indicado")

    return (
        datos.groupby(
            "objeto_contractual",
            dropna=False,
        )
        .agg(
            cantidad_ordenes=(
                "objeto_contractual",
                "size",
            ),
            monto_total_pen=("monto_pen", "sum"),
        )
        .reset_index()
        .sort_values(
            [
                "cantidad_ordenes",
                "monto_total_pen",
            ],
            ascending=[False, False],
        )
    )


def _registros_serializables(
    frame: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Convierte un DataFrame a registros utilizables por JSON."""
    if frame.empty:
        return []

    datos = frame.copy()

    for columna in datos.columns:
        if pd.api.types.is_datetime64_any_dtype(
            datos[columna]
        ):
            datos[columna] = datos[columna].dt.strftime(
                "%Y-%m-%d"
            )

    datos = datos.where(
        pd.notna(datos),
        None,
    )

    return datos.to_dict(orient="records")


def obtener_ordenes_evidencia(
    resultados: pd.DataFrame,
    limite: int = 20,
) -> list[dict[str, Any]]:
    """Selecciona órdenes reales para Streamlit y Gemma."""
    if resultados.empty:
        return []

    columnas = [
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
    ]

    evidencia = (
        resultados[columnas]
        .sort_values(
            "monto_pen",
            ascending=False,
            na_position="last",
        )
        .head(limite)
    )

    return _registros_serializables(evidencia)


def analizar_mercado(
    palabras_clave: list[str],
    departamento: str | list[str] | None = None,
    objeto_contractual: str | list[str] | None = None,
    datos: pd.DataFrame | None = None,
    *,
    tipo_orden: str | list[str] | None = None,
    limite_entidades: int = 10,
    limite_evidencia: int = 20,
    monthly_dir: Path | str = MONTHLY_DIR,
) -> dict[str, Any]:
    """Ejecuta el análisis completo para Streamlit y Gemma."""
    resultados = buscar_ordenes(
        palabras_clave=palabras_clave,
        departamento=departamento,
        objeto_contractual=objeto_contractual,
        datos=datos,
        tipo_orden=tipo_orden,
        monthly_dir=monthly_dir,
    )

    resumen = calcular_resumen(resultados)

    entidades = obtener_entidades_principales(
        resultados,
        limite=limite_entidades,
    )

    tendencia = obtener_tendencia_mensual(
        resultados
    )

    departamentos = obtener_resumen_departamentos(
        resultados
    )

    objetos = obtener_resumen_objetos(
        resultados
    )

    evidencia = obtener_ordenes_evidencia(
        resultados,
        limite=limite_evidencia,
    )

    return {
        "consulta": {
            "palabras_clave": list(palabras_clave),
            "departamento": (
                _como_lista(departamento)
                or ["Todo el Perú"]
            ),
            "objeto_contractual": (
                _como_lista(
                    objeto_contractual
                    if objeto_contractual is not None
                    else tipo_orden
                )
                or ["Bien", "Servicio"]
            ),
        },
        "resumen": resumen,
        "entidades_principales": (
            _registros_serializables(entidades)
        ),
        "tendencia_mensual": (
            _registros_serializables(tendencia)
        ),
        "departamentos": (
            _registros_serializables(departamentos)
        ),
        "objetos_contractuales": (
            _registros_serializables(objetos)
        ),
        "ordenes_evidencia": evidencia,

        # Compatibilidad con tu versión anterior.
        "ordenes_ejemplo": evidencia,
    }


if __name__ == "__main__":
    resultado = analizar_mercado(
        palabras_clave=[
            "computadora",
            "laptop",
            "impresora",
            "toner",
        ],
        departamento=["Lima"],
        objeto_contractual=["Bien"],
    )

    print("\nRESUMEN")

    for clave, valor in resultado["resumen"].items():
        print(f"- {clave}: {valor}")

    print("\nEVIDENCIA")

    for orden in resultado["ordenes_evidencia"][:5]:
        print(
            f"- {orden['descripcion']} | "
            f"{orden['entidad']} | "
            f"S/ {orden['monto_pen']}"
        )