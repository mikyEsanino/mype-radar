"""Interpretación del perfil empresarial mediante Gemma."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "gemma-4-26b-a4b-it"


class GemmaAgentError(RuntimeError):
    """Error controlado al interpretar el perfil con Gemma."""


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
        raise GemmaAgentError(
            "Falta la dependencia google-genai. Instálala con "
            "`pip install google-genai`."
        ) from exc

    if not (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    ):
        raise GemmaAgentError(
            "No se encontró GEMINI_API_KEY ni GOOGLE_API_KEY en el entorno."
        )

    try:
        return genai.Client()
    except Exception as exc:
        raise GemmaAgentError(
            f"No se pudo inicializar el cliente de Gemma: {exc}"
        ) from exc


def _response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text is None:
        raise GemmaAgentError("Gemma no devolvió contenido de texto.")
    return str(text).strip()


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = (
        text.replace("```json", "")
        .replace("```JSON", "")
        .replace("```", "")
        .strip()
    )

    candidates = [cleaned]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        candidates.append(cleaned[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise GemmaAgentError(
        "Gemma devolvió una respuesta que no contiene un JSON válido."
    )


def _clean_list(value: Any, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []

    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        key = " ".join(text.casefold().split())
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def analizar_negocio(
    descripcion: str,
    *,
    client: Any | None = None,
    model: str | None = None,
) -> dict[str, list[str]]:
    """Obtiene categorías y términos de búsqueda para la MYPE.

    La salida siempre tiene las claves ``categorias`` y ``palabras_clave``.
    Los cálculos de mercado no se realizan aquí; se ejecutan posteriormente
    mediante ``analytics.analizar_mercado``.
    """
    description = (descripcion or "").strip()
    if not description:
        raise GemmaAgentError("La descripción empresarial está vacía.")

    prompt = f"""
Analiza la siguiente descripción de una MYPE peruana:

"{description}"

Devuelve SOLO un objeto JSON válido, sin Markdown ni texto adicional:

{{
  "categorias": ["categoría 1", "categoría 2"],
  "palabras_clave": ["término 1", "término 2"]
}}

Reglas:
- Incluye entre 1 y 4 categorías concretas.
- Incluye entre 2 y 10 términos o frases útiles para buscar órdenes públicas.
- Prioriza nombres de productos, servicios, especialidades y sinónimos comerciales.
- Evita términos genéricos aislados como empresa, producto, servicio o cliente.
- No inventes productos, capacidades ni certificaciones no descritas.
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
        raise GemmaAgentError(
            f"No se pudo analizar la descripción con Gemma: {exc}"
        ) from exc

    payload = _extract_json(_response_text(response))
    categories = _clean_list(payload.get("categorias"), limit=4)
    keywords = _clean_list(payload.get("palabras_clave"), limit=10)

    if not keywords:
        raise GemmaAgentError(
            "Gemma no devolvió palabras clave utilizables."
        )

    return {
        "categorias": categories,
        "palabras_clave": keywords,
    }
