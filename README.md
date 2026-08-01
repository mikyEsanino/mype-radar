# MYPE Radar

Agente inteligente con Gemma para analizar oportunidades y tendencias del mercado de compras públicas del Perú.

## Problema

Las micro y pequeñas empresas peruanas tienen dificultades para comprender qué bienes y servicios compra el Estado, qué entidades los requieren, qué montos se manejan y en qué periodos existe mayor actividad.

Aunque esta información está disponible en la Plataforma Nacional de Datos Abiertos del Perú, se presenta mediante archivos extensos, códigos y descripciones técnicas que requieren conocimientos especializados para ser analizados.

## Solución

MYPE Radar permitirá que una MYPE describa en lenguaje natural los productos o servicios que ofrece.

Gemma interpretará el perfil empresarial, identificará términos relacionados y coordinará el análisis de las órdenes históricas de compra y servicios registradas por las entidades públicas.

La plataforma mostrará:

- Entidades públicas que demandan los bienes o servicios.
- Cantidad de órdenes registradas.
- Rangos históricos de montos.
- Periodos con mayor actividad.
- Productos o servicios relacionados.
- Una explicación generada por Gemma.
- Un informe de inteligencia de mercado para la MYPE.

## Funcionamiento

1. La empresa describe sus productos o servicios.
2. Gemma identifica categorías y palabras relacionadas.
3. El usuario confirma las categorías.
4. Python analiza las órdenes históricas.
5. La plataforma muestra métricas y visualizaciones.
6. Gemma interpreta los resultados.
7. Se genera un informe de inteligencia de mercado.

## Fuente de datos

Plataforma Nacional de Datos Abiertos del Perú.

Dataset principal:

**Órdenes de Compra y/o Servicios de las entidades**, publicado por el Organismo Especializado para las Contrataciones Públicas Eficientes — OECE.

La información utilizada es histórica y no representa necesariamente licitaciones activas.

## Tecnologías previstas

- Gemma
- Google AI Studio
- Python
- Pandas
- Streamlit
- Plotly o Matplotlib
- Kaggle
- GitHub

## Tracks

- AI for Social Impact
- AI Agents & Automation
- Developer Tools & Productivity

## Objetivos de Desarrollo Sostenible

- ODS 8: Trabajo decente y crecimiento económico.
- ODS 16: Paz, justicia e instituciones sólidas.

## Equipo

- **Miguel:** líder, datos y analítica.
- **Jeremy:** integración de Gemma y agente.
- **Kheyla:** interfaz, documentación y presentación.

## Estado

Proyecto aceptado para participar en la hackatón Build with Gemma.

Actualmente se encuentra en etapa de preparación y validación técnica.

## Limitaciones

MYPE Radar no garantiza que una empresa obtendrá contratos con el Estado y no será presentado como un buscador de licitaciones activas. Su objetivo es facilitar el análisis de información histórica y ayudar a las MYPE a comprender el mercado estatal.
