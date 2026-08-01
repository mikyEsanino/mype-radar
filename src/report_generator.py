"""Generación del informe de inteligencia de mercado mediante Gemma."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "gemma-4-26b-a4b-it"


class ReportGenerationError(RuntimeError):
    """Error controlado durante la generación del informe."""


def _load_environment() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    module_dir = Path(__file__).resolve().parent
    candidates = [
        module_dir.parent / "api.env",
        module_dir / "api.env",
        Path.cwd() / "api.env",
    ]
    for path in candidates:
        if path.exists():
            load_dotenv(path, override=False)
            return
    load_dotenv(override=False)


def _get_client() -> Any:
    _load_environment()
    try:
        from google import genai
    except ImportError as exc:
        raise ReportGenerationError(
            "Falta la dependencia google-genai. Instálala con "
            "`pip install google-genai`."
        ) from exc

    if not (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    ):
        raise ReportGenerationError(
            "No se encontró GEMINI_API_KEY ni GOOGLE_API_KEY en el entorno."
        )

    try:
        return genai.Client()
    except Exception as exc:
        raise ReportGenerationError(
            f"No se pudo inicializar el cliente de Gemma: {exc}"
        ) from exc


def generar_informe(
    contexto_datos: dict[str, Any],
    *,
    client: Any | None = None,
    model: str | None = None,
) -> str:
    """Redacta el informe usando únicamente agregados calculados por analytics."""
    if not isinstance(contexto_datos, dict) or not contexto_datos:
        raise ReportGenerationError(
            "El contexto del informe está vacío o no es válido."
        )

    try:
        context_json = json.dumps(
            contexto_datos,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    except (TypeError, ValueError) as exc:
        raise ReportGenerationError(
            f"No se pudo serializar el contexto del informe: {exc}"
        ) from exc

    prompt = f"""
Eres un analista de inteligencia de mercado para MYPE peruanas.

Usa ÚNICAMENTE el siguiente JSON, calculado por la función
analytics.analizar_mercado. No inventes entidades, cifras, fechas,
procesos activos ni información externa:

{context_json}

Los registros representan compras históricas realizadas por entidades públicas
a distintos proveedores. NO son ventas de la empresa usuaria. La empresa está
evaluando este mercado.

Redacta en Markdown exactamente estas secciones:

### Lectura ejecutiva
Máximo 120 palabras. Explica el volumen histórico, monto, entidades y periodos
más relevantes. Toda cifra mencionada debe coincidir exactamente con el JSON.

### Recomendaciones iniciales
Máximo 120 palabras. Propón entre 2 y 4 acciones generales de preparación
derivadas exclusivamente de los patrones observados.

### Alcance
Máximo 45 palabras. Aclara que es información histórica, que no identifica
oportunidades activas y que no garantiza una contratación.

No agregues introducciones, despedidas ni bloques de código.
""".strip()

    active_client = client or _get_client()
    active_model = (
        model
        or os.getenv("GEMMA_MODEL")
        or DEFAULT_MODEL
    )

    try:
        response = active_client.models.generate_content(
            model=active_model,
            contents=prompt,
        )
    except Exception as exc:
        raise ReportGenerationError(
            f"No se pudo generar el informe con Gemma: {exc}"
        ) from exc

    report = str(getattr(response, "text", "") or "").strip()
    if not report:
        raise ReportGenerationError(
            "Gemma devolvió un informe vacío."
        )

    return report
