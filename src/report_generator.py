from dotenv import load_dotenv
from google import genai

load_dotenv("api.env")
client = genai.Client()
#buenas tardes
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
    response = client.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=prompt
    )
    return response.text