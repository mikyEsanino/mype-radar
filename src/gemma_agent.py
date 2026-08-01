from dotenv import load_dotenv
from google import genai
import json

load_dotenv("api.env")
client = genai.Client()

def analizar_negocio(descripcion: str) -> dict:
    prompt = f"""
    Analiza esta descripción de una MYPE peruana: "{descripcion}"
    Devuelve SOLO un JSON válido, sin texto adicional ni marcado de código, con esta forma:
    {{
      "categorias": ["...", "..."],
      "palabras_clave": ["...", "..."]
    }}
    """
    response = client.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=prompt
    )
    texto = response.text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        print("JSON crudo recibido:", texto)
        raise