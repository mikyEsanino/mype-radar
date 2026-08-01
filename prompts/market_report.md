# Market Report Prompt

## Contexto
Genera un informe de inteligencia de mercado a partir de datos de órdenes de
compra públicas ya filtradas por rubro.

## Reglas
- Usar ÚNICAMENTE los datos entregados en `contexto_datos`, no inventar entidades,
  montos ni oportunidades activas.
- Los datos son órdenes ya ejecutadas por el Estado a otros proveedores — NO son
  historial del negocio del usuario. El usuario es una MYPE evaluando si entrar
  al mercado.
- No prometer contratos ni mencionar licitaciones activas específicas.

## Estructura de salida
1. **Resumen del mercado** (máx. 100 palabras): cantidad de órdenes, entidades que
   más compran, meses con más actividad.
2. **Recomendaciones y ruta de preparación** (máx. 100 palabras): 2-3 pasos
   generales basados solo en los patrones de los datos.