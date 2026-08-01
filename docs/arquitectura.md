# Arquitectura — MYPE Radar

## Flujo
1. Usuario describe su negocio en lenguaje natural (Streamlit).
2. `gemma_agent.analizar_negocio(descripcion)` → Gemma interpreta el perfil y
   devuelve `categorias` y `palabras_clave`.
3. `analytics.buscar_ordenes(palabras_clave)` → filtra el dataset de órdenes de
   compra públicas (Plataforma Nacional de Datos Abiertos).
4. `analytics.calcular_resumen()`, `obtener_entidades_principales()`,
   `obtener_tendencia_mensual()` → agregan los resultados.
5. `report_generator.generar_informe(contexto)` → Gemma redacta el informe final
   (resumen de mercado + recomendaciones).
6. `agente.flujo_completo(descripcion)` orquesta 2-5 y devuelve el contexto
   completo para el dashboard.

## Módulos
| Archivo | Responsabilidad | Autor |
|---|---|---|
| `src/gemma_agent.py` | Interpretar perfil de negocio con Gemma | Jeremy |
| `src/analytics.py` | Consulta y agregación del dataset | Miguel |
| `src/report_generator.py` | Generación del informe con Gemma | Jeremy |
| `src/agente.py` | Orquestación del flujo completo | Jeremy |
