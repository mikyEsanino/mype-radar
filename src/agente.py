import sys
sys.path.append("src")

from gemma_agent import analizar_negocio
from analytics import buscar_ordenes, calcular_resumen, obtener_entidades_principales, obtener_tendencia_mensual
from report_generator import generar_informe


def flujo_completo(descripcion: str) -> dict:
    analisis = analizar_negocio(descripcion)

    resultados_df = buscar_ordenes(palabras_clave=analisis["palabras_clave"])
    resumen = calcular_resumen(resultados_df)
    entidades_top = obtener_entidades_principales(resultados_df, limite=5)
    tendencia = obtener_tendencia_mensual(resultados_df)

    contexto = {
        **analisis,
        **resumen,
        "entidades_principales": entidades_top.to_dict("records"),
        "tendencia_mensual": tendencia.to_dict("records"),
    }
    return contexto


if __name__ == "__main__":
    contexto = flujo_completo("Empresa de servicios generales que ofrece limpieza, pintura y mantenimiento de locales")
    print(contexto)
    print()
    print(generar_informe(contexto))