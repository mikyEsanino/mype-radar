import pytest
from src.gemma_agent import analizar_negocio

def test_analizar_negocio_estructura():
    resultado = analizar_negocio(
        "Empresa de servicios generales que ofrece limpieza, pintura y mantenimiento"
    )
    assert isinstance(resultado, dict)
    assert "categorias" in resultado
    assert "palabras_clave" in resultado
    assert isinstance(resultado["palabras_clave"], list)
    assert len(resultado["palabras_clave"]) > 0

def test_analizar_negocio_no_vacio():
    resultado = analizar_negocio("Bodega de abarrotes")
    assert len(resultado["categorias"]) > 0