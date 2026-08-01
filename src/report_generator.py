from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class ReportGenerationError(RuntimeError):
    """Error controlado al generar el informe con Gemma."""


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
            "Falta la dependencia google-genai."
        ) from exc

    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        raise ReportGenerationError(
            "No se encontró GEMINI_API_KEY ni GOOGLE_API_KEY en el entorno."
        )

    try:
        return genai.Client()
    except Exception as exc:
        raise ReportGenerationError(
            f"No se pudo inicializar el cliente de Gemma: {exc}"
        ) from exc


def generar_informe(contexto_datos: dict) -> str:
    prompt = f"""
    Eres un analista de mercado. Usa ÚNICAMENTE estos datos, no inventes
    entidades, montos ni oportunidades activas:
    {contexto_datos}

    IMPORTANTE: Estos datos representan órdenes de compra que entidades públicas
    ya han realizado en el mercado (a distintos proveedores), NO el historial del
    negocio del usuario. El usuario es una MYPE que está EVALUANDO si entrar a este
    mercado, no alguien que ya vendió estos servicios.

    Escribe un informe de inteligencia de mercado con dos partes:

    1. RESUMEN DEL MERCADO (máximo 100 palabras): explica qué demanda existe en el
    mercado estatal para su rubro según estos datos: cuántas órdenes se han
    registrado, qué entidades compran más, y en qué meses hay más actividad.

    2. RECOMENDACIONES Y RUTA DE PREPARACIÓN (máximo 100 palabras): basándote
    ÚNICAMENTE en los patrones de estos datos (no en información externa), sugiere
    2-3 pasos generales que el MYPE podría considerar para prepararse ante este tipo
    de mercado. No prometas contratos, no menciones licitaciones activas específicas,
    y no des a entender que estos son resultados propios del negocio del usuario.
    """
    client = _get_client()
    try:
        response = client.models.generate_content(
            model="gemma-4-26b-a4b-it",
            contents=prompt
        )
    except Exception as exc:
        raise ReportGenerationError(
            f"No se pudo generar el informe con Gemma: {exc}"
        ) from exc

    text = getattr(response, "text", None)
    if not text:
        raise ReportGenerationError("Gemma no devolvió contenido de texto.")
    return text.strip()