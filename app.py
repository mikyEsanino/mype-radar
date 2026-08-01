from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_service import analyze_orders, extract_keywords, load_orders


APP_DIR = Path(__file__).resolve().parent
LOGO_FULL = APP_DIR / "assets" / "logo_full.png"
LOGO_ICON = APP_DIR / "assets" / "logo_icon.png"

NAVY = "#12355B"
TEAL = "#00A6A6"
YELLOW = "#F4B942"
LIGHT_BLUE = "#BFD7E2"
PALE = "#F4FAFB"
GRAY = "#5E6B78"

EXAMPLES = {
    "Escribir mi propia descripción": "",
    "Equipos informáticos": (
        "Vendemos laptops, computadoras, impresoras, monitores y brindamos "
        "mantenimiento y soporte técnico."
    ),
    "Limpieza institucional": (
        "Brindamos limpieza integral, desinfección y mantenimiento de oficinas, "
        "hospitales y centros educativos."
    ),
    "Alimentos y catering": (
        "Preparamos alimentos, refrigerios y servicios de catering para "
        "instituciones y eventos."
    ),
    "Mantenimiento de infraestructura": (
        "Realizamos pintura, albañilería, reparaciones menores y mantenimiento "
        "de instalaciones."
    ),
}

TUTORIAL_STEPS = [
    {
        "title": "Describe tu empresa",
        "icon": "🏢",
        "body": (
            "Explica en una o dos frases qué productos vendes o qué servicios "
            "brindas. Incluye especialidad, tipo de cliente o cobertura cuando "
            "sea relevante."
        ),
        "tip": (
            "Ejemplo: Vendemos laptops e impresoras y brindamos mantenimiento "
            "de equipos informáticos."
        ),
    },
    {
        "title": "Revisa las palabras clave",
        "icon": "🔎",
        "body": (
            "La aplicación extrae términos de la descripción. Puedes corregirlos "
            "o agregar palabras utilizadas normalmente en las órdenes públicas."
        ),
        "tip": (
            "Usa términos concretos como laptop, impresora, limpieza, catering "
            "o mantenimiento."
        ),
    },
    {
        "title": "Ejecuta el análisis",
        "icon": "📊",
        "body": (
            "MYPE Radar busca coincidencias en las descripciones de las órdenes, "
            "separa registros anulados y calcula montos, entidades y tendencias."
        ),
        "tip": "El análisis actual es una búsqueda transparente por palabras clave.",
    },
    {
        "title": "Explora el mercado",
        "icon": "📡",
        "body": (
            "Consulta las entidades con mayor actividad, la tendencia mensual, "
            "la distribución departamental y la proporción entre bienes y servicios."
        ),
        "tip": (
            "Los resultados representan actividad histórica; no son una predicción "
            "de compras futuras."
        ),
    },
    {
        "title": "Verifica la evidencia",
        "icon": "✅",
        "body": (
            "Abre la pestaña Evidencia para revisar las órdenes exactas que "
            "sustentan cada métrica y utiliza el resumen para preparar tu empresa."
        ),
        "tip": (
            "Siempre contrasta los hallazgos con las fuentes y plataformas oficiales."
        ),
    },
]


def configure_page() -> None:
    st.set_page_config(
        page_title="MYPE Radar",
        page_icon= LOGO_ICON if LOGO_ICON.exists() else "📡",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        f"""
        <style>
            :root {{
                --navy: {NAVY};
                --teal: {TEAL};
                --yellow: {YELLOW};
                --light-blue: {LIGHT_BLUE};
                --pale: {PALE};
                --gray: {GRAY};
            }}

            .stApp {{
                background:
                    radial-gradient(circle at 92% 4%, rgba(0,166,166,.08), transparent 24rem),
                    #ffffff;
            }}

            .block-container {{
                max-width: 1240px;
                padding-top: 1.15rem;
                padding-bottom: 3rem;
            }}

            header[data-testid="stHeader"] {{
                background: transparent;
            }}

            #MainMenu, footer {{
                visibility: hidden;
            }}

            .brand-nav {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                min-height: 64px;
                margin-bottom: 1rem;
                border-bottom: 1px solid #e4ecef;
                padding-bottom: .85rem;
            }}

            .brand-name {{
                color: var(--navy);
                font-weight: 800;
                font-size: 1.2rem;
            }}

            .hero {{
                position: relative;
                overflow: hidden;
                border-radius: 28px;
                padding: 3.2rem 3rem;
                background:
                    radial-gradient(circle at 91% 10%, rgba(244,185,66,.20), transparent 15rem),
                    linear-gradient(135deg, #12355b 0%, #0e4f6c 58%, #007f83 100%);
                color: #ffffff;
                box-shadow: 0 22px 55px rgba(18,53,91,.18);
            }}

            .hero::after {{
                content: "";
                position: absolute;
                width: 320px;
                height: 320px;
                border: 2px solid rgba(255,255,255,.14);
                border-radius: 50%;
                right: -95px;
                bottom: -165px;
            }}

            .eyebrow {{
                display: inline-block;
                padding: .35rem .72rem;
                border-radius: 999px;
                background: rgba(255,255,255,.12);
                border: 1px solid rgba(255,255,255,.22);
                color: #ffffff;
                font-size: .78rem;
                letter-spacing: .08em;
                font-weight: 750;
            }}

            .hero h1 {{
                color: #ffffff;
                font-size: clamp(2.35rem, 5vw, 4.4rem);
                line-height: 1.03;
                letter-spacing: -.045em;
                max-width: 900px;
                margin: 1rem 0 .9rem;
            }}

            .hero p {{
                color: rgba(255,255,255,.82);
                max-width: 780px;
                font-size: 1.12rem;
                line-height: 1.7;
                margin-bottom: 0;
            }}

            .section-title {{
                color: var(--navy);
                font-size: 2rem;
                line-height: 1.15;
                margin: 3.2rem 0 .6rem;
            }}

            .section-lead {{
                color: var(--gray);
                max-width: 800px;
                margin-bottom: 1.25rem;
            }}

            .feature-card {{
                height: 100%;
                padding: 1.25rem;
                border-radius: 18px;
                background: #ffffff;
                border: 1px solid #e1ebef;
                box-shadow: 0 9px 28px rgba(18,53,91,.055);
            }}

            .feature-card h3 {{
                color: var(--navy);
                font-size: 1.06rem;
                margin: .7rem 0 .45rem;
            }}

            .feature-card p {{
                color: var(--gray);
                line-height: 1.55;
                margin: 0;
            }}

            .feature-icon {{
                display: grid;
                place-items: center;
                width: 46px;
                height: 46px;
                border-radius: 14px;
                background: rgba(0,166,166,.10);
                color: var(--teal);
                font-size: 1.35rem;
            }}

            .process-card {{
                padding: 1.2rem;
                border-left: 4px solid var(--teal);
                background: var(--pale);
                border-radius: 0 16px 16px 0;
                min-height: 132px;
            }}

            .process-number {{
                color: var(--yellow);
                font-size: 1.6rem;
                font-weight: 850;
            }}

            .process-card strong {{
                color: var(--navy);
            }}

            .workspace-header {{
                padding: 1.1rem 1.25rem;
                border: 1px solid #dce8ee;
                border-radius: 20px;
                background: linear-gradient(135deg, #f8fbfd 0%, #eef9f8 100%);
                margin-bottom: 1rem;
            }}

            .workspace-header h1 {{
                color: var(--navy);
                margin: 0;
                font-size: 2rem;
            }}

            .workspace-header p {{
                color: var(--gray);
                margin: .35rem 0 0;
            }}

            .source-banner {{
                padding: .82rem 1rem;
                border-radius: 12px;
                background: #fff8e8;
                border: 1px solid #f6d486;
                color: #6a510b;
                margin-bottom: 1rem;
            }}

            .tip-card {{
                padding: .95rem 1rem;
                border-radius: 14px;
                background: #f2fbfb;
                border: 1px solid #c9eaea;
                color: #22565a;
                margin: .5rem 0 1rem;
            }}

            .tutorial-hero {{
                border-radius: 24px;
                padding: 2.2rem;
                background: linear-gradient(135deg, #f3fbfb 0%, #f9fbfd 100%);
                border: 1px solid #dce8ee;
            }}

            .tutorial-step {{
                height: 100%;
                padding: 1.25rem;
                border-radius: 18px;
                border: 1px solid #e1ebef;
                background: #ffffff;
            }}

            .tutorial-step h3 {{
                color: var(--navy);
                margin: .45rem 0;
            }}

            .tutorial-step p {{
                color: var(--gray);
                line-height: 1.55;
            }}

            .metric-note {{
                color: var(--gray);
                font-size: .82rem;
            }}

            .footer-band {{
                margin-top: 3rem;
                padding: 1.35rem 1.5rem;
                border-radius: 18px;
                background: var(--navy);
                color: rgba(255,255,255,.75);
                text-align: center;
            }}

            .footer-band strong {{
                color: #ffffff;
            }}

            div[data-testid="stMetric"] {{
                border: 1px solid #e1ebef;
                border-radius: 16px;
                background: #ffffff;
                padding: .75rem;
                box-shadow: 0 6px 20px rgba(18,53,91,.045);
            }}

            div[data-testid="stMetricLabel"] {{
                color: var(--gray);
            }}

            div[data-testid="stMetricValue"] {{
                color: var(--navy);
            }}

            div[data-testid="stButton"] > button {{
                border-radius: 12px;
                min-height: 44px;
                font-weight: 700;
            }}

            div[data-testid="stButton"] > button[kind="primary"] {{
                background: var(--teal);
                border-color: var(--teal);
                color: #ffffff;
            }}

            div[data-testid="stButton"] > button[kind="primary"]:hover {{
                background: #008f91;
                border-color: #008f91;
            }}

            div[data-baseweb="tab-list"] {{
                gap: .45rem;
            }}

            button[data-baseweb="tab"] {{
                border-radius: 10px;
                padding-left: 1.1rem;
                padding-right: 1.1rem;
            }}

            @media (max-width: 760px) {{
                .hero {{
                    padding: 2rem 1.35rem;
                }}

                .hero h1 {{
                    font-size: 2.4rem;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_state() -> None:
    defaults = {
        "page": "landing",
        "tutorial_seen": False,
        "show_tutorial": False,
        "tutorial_step": 0,
        "analysis": None,
        "profile_text": "",
        "keywords_text": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def navigate(page: str, *, show_tutorial: bool = False) -> None:
    st.session_state.page = page
    if show_tutorial:
        st.session_state.show_tutorial = True
        st.session_state.tutorial_step = 0
    st.rerun()


def close_tutorial() -> None:
    st.session_state.show_tutorial = False
    st.session_state.tutorial_seen = True


@st.dialog(
    "Tutorial rápido de MYPE Radar",
    width="medium",
    icon="🎓",
    on_dismiss=close_tutorial,
)
def tutorial_dialog() -> None:
    step_index = int(st.session_state.get("tutorial_step", 0))
    step_index = max(0, min(step_index, len(TUTORIAL_STEPS) - 1))
    step = TUTORIAL_STEPS[step_index]

    st.progress((step_index + 1) / len(TUTORIAL_STEPS))
    st.caption(f"Paso {step_index + 1} de {len(TUTORIAL_STEPS)}")
    st.markdown(f"## {step['icon']} {step['title']}")
    st.write(step["body"])
    st.info(step["tip"], icon="💡")

    previous_col, next_col = st.columns(2)
    with previous_col:
        if step_index > 0 and st.button(
            "← Anterior",
            use_container_width=True,
            key=f"tutorial_previous_{step_index}",
        ):
            st.session_state.tutorial_step = step_index - 1
            st.rerun()

    with next_col:
        if step_index < len(TUTORIAL_STEPS) - 1:
            if st.button(
                "Siguiente →",
                type="primary",
                use_container_width=True,
                key=f"tutorial_next_{step_index}",
            ):
                st.session_state.tutorial_step = step_index + 1
                st.rerun()
        else:
            if st.button(
                "Comenzar a usar MYPE Radar",
                type="primary",
                use_container_width=True,
                key="tutorial_finish",
            ):
                st.session_state.show_tutorial = False
                st.session_state.tutorial_seen = True
                st.rerun()


def render_top_navigation(active: str) -> None:
    logo_col, spacer_col, home_col, tutorial_col, app_col = st.columns(
        [2.6, 3.5, 1, 1.2, 1.2]
    )

    with logo_col:
        if LOGO_FULL.exists():
            st.image(str(LOGO_FULL), width=270)
        else:
            st.markdown('<span class="brand-name">MYPE Radar</span>', unsafe_allow_html=True)

    with home_col:
        if st.button(
            "Inicio",
            use_container_width=True,
            type="primary" if active == "landing" else "secondary",
            key=f"nav_home_{active}",
        ):
            navigate("landing")

    with tutorial_col:
        if st.button(
            "Tutorial",
            use_container_width=True,
            type="primary" if active == "tutorial" else "secondary",
            key=f"nav_tutorial_{active}",
        ):
            navigate("tutorial")

    with app_col:
        if st.button(
            "Aplicación",
            use_container_width=True,
            type="primary" if active == "workspace" else "secondary",
            key=f"nav_app_{active}",
        ):
            open_tutorial = not st.session_state.tutorial_seen
            navigate("workspace", show_tutorial=open_tutorial)


def render_landing() -> None:
    render_top_navigation("landing")

    st.markdown(
        """
        <section class="hero">
            <span class="eyebrow">INTELIGENCIA DE MERCADO PARA MYPE</span>
            <h1>Comprende el mercado público antes de tomar decisiones.</h1>
            <p>
                MYPE Radar transforma registros históricos de compras públicas en
                una lectura empresarial sencilla: entidades, montos, tendencias y
                evidencia verificable para preparar mejor tu oferta.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    start_col, tutorial_col, spacer_col = st.columns([1.45, 1.25, 3.8])
    with start_col:
        if st.button(
            "Iniciar análisis →",
            type="primary",
            use_container_width=True,
            key="landing_start",
        ):
            navigate(
                "workspace",
                show_tutorial=not st.session_state.tutorial_seen,
            )
    with tutorial_col:
        if st.button(
            "Ver cómo funciona",
            use_container_width=True,
            key="landing_tutorial",
        ):
            navigate("tutorial")

    st.markdown(
        """
        <h2 class="section-title">Información útil, comprensible y verificable</h2>
        <p class="section-lead">
            La experiencia está diseñada para usuarios empresariales que no
            necesitan conocer códigos técnicos ni manipular archivos extensos.
        </p>
        """,
        unsafe_allow_html=True,
    )

    cards = st.columns(3)
    features = [
        (
            "📈",
            "Lectura ejecutiva",
            "Resume demanda histórica, montos, entidades y periodos con mayor actividad.",
        ),
        (
            "🔍",
            "Evidencia visible",
            "Cada indicador puede contrastarse con las órdenes que sustentan el resultado.",
        ),
        (
            "🧭",
            "Preparación empresarial",
            "Convierte los hallazgos en una ruta práctica de revisión y preparación.",
        ),
    ]
    for column, (icon, title, text) in zip(cards, features):
        with column:
            st.markdown(
                f"""
                <article class="feature-card">
                    <div class="feature-icon">{icon}</div>
                    <h3>{title}</h3>
                    <p>{text}</p>
                </article>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <h2 class="section-title">Así funciona MYPE Radar</h2>
        <p class="section-lead">
            Un recorrido corto que mantiene separados el cálculo de datos y la
            interpretación empresarial.
        </p>
        """,
        unsafe_allow_html=True,
    )

    process_columns = st.columns(4)
    process = [
        ("01", "Describe tu empresa", "Indica qué vendes o qué servicio brindas."),
        ("02", "Define términos", "Revisa las palabras utilizadas para buscar órdenes."),
        ("03", "Analiza el mercado", "Consulta montos, entidades, fechas y distribución."),
        ("04", "Verifica y prepara", "Revisa los registros y genera una lectura ejecutiva."),
    ]
    for column, (number, title, text) in zip(process_columns, process):
        with column:
            st.markdown(
                f"""
                <div class="process-card">
                    <div class="process-number">{number}</div>
                    <strong>{title}</strong>
                    <p>{text}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <h2 class="section-title">Diseñada para generar confianza</h2>
        <p class="section-lead">
            MYPE Radar no presenta los datos históricos como predicciones ni
            garantiza contratos. Su valor está en reducir la barrera de análisis
            y facilitar una preparación empresarial basada en evidencia.
        </p>
        """,
        unsafe_allow_html=True,
    )

    final_col, _ = st.columns([1.4, 4])
    with final_col:
        if st.button(
            "Explorar la aplicación",
            type="primary",
            use_container_width=True,
            key="landing_final_cta",
        ):
            navigate(
                "workspace",
                show_tutorial=not st.session_state.tutorial_seen,
            )

    st.markdown(
        """
        <div class="footer-band">
            <strong>MYPE Radar</strong> · Inteligencia de mercado para compras públicas
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_report(analysis: dict[str, Any]) -> str:
    summary = analysis["summary"]
    entities = analysis["entities"]
    departments = analysis["departments"]

    top_entities = entities.head(3)["ENTIDAD"].tolist()
    entity_text = ", ".join(top_entities) if top_entities else "sin entidades destacadas"

    top_department = (
        str(departments.iloc[0]["DEPARTAMENTO"])
        if not departments.empty
        else "sin información"
    )

    keywords = ", ".join(analysis["keywords"])

    return f"""
### Lectura ejecutiva

La búsqueda utilizó los términos **{keywords}** y encontró
**{summary['total_orders']:,} órdenes válidas**, por un monto original acumulado
de **S/ {summary['total_amount']:,.0f}**.

El periodo con mayor número de registros es **{summary['peak_month']}**. Las
entidades con mayor actividad son **{entity_text}**, mientras que
**{top_department}** concentra el mayor monto agregado por departamento de la
entidad.

### Recomendaciones iniciales

1. Revisar las entidades que presentan recurrencia y no solamente los montos más altos.
2. Comparar las descripciones de las órdenes para adaptar el catálogo empresarial.
3. Preparar fichas técnicas, capacidad operativa y cotizaciones antes de los periodos de mayor actividad.
4. Separar bienes y servicios cuando requieran propuestas comerciales distintas.
5. Contrastar cada conclusión con la pestaña **Evidencia** y con las fuentes oficiales.

### Alcance

Este resumen se genera a partir de cálculos determinísticos sobre registros
históricos. No constituye una predicción, una garantía de contratación ni un
buscador de procesos activos.
""".strip()


def inject_workspace_styles() -> None:
    """Estilos exclusivos del panel; no se cargan en la página de inicio."""
    st.markdown(
        f"""
        <style>
            .workspace-kicker {{
                display: inline-flex;
                align-items: center;
                gap: .4rem;
                margin-bottom: .45rem;
                color: {TEAL};
                font-size: .74rem;
                font-weight: 800;
                letter-spacing: .09em;
                text-transform: uppercase;
            }}

            .workspace-header {{
                padding: 1.4rem 1.5rem;
                border: 1px solid #dce8ee;
                border-radius: 22px;
                background:
                    radial-gradient(circle at 94% 5%, rgba(0,166,166,.12), transparent 12rem),
                    linear-gradient(135deg, #f8fbfd 0%, #eef9f8 100%);
                margin-bottom: .15rem;
            }}

            .workspace-header h1 {{
                color: {NAVY};
                margin: 0;
                font-size: clamp(1.65rem, 3vw, 2.25rem);
                letter-spacing: -.025em;
            }}

            .workspace-header p {{
                color: {GRAY};
                margin: .45rem 0 0;
                max-width: 760px;
                line-height: 1.55;
            }}

            .workspace-source-card {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                padding: .78rem 1rem;
                margin: .75rem 0 1.1rem;
                border: 1px solid #dfeaec;
                border-radius: 14px;
                background: #ffffff;
                color: {GRAY};
                font-size: .9rem;
            }}

            .workspace-source-card strong {{
                color: {NAVY};
            }}

            .source-status {{
                display: inline-flex;
                align-items: center;
                white-space: nowrap;
                padding: .3rem .62rem;
                border-radius: 999px;
                background: rgba(0,166,166,.09);
                color: #08777a;
                font-size: .76rem;
                font-weight: 800;
            }}

            .source-status.demo {{
                background: #fff4d8;
                color: #7a5900;
            }}

            .workflow-strip {{
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: .65rem;
                margin: 0 0 1.1rem;
            }}

            .workflow-step {{
                display: flex;
                gap: .68rem;
                align-items: center;
                padding: .78rem .85rem;
                border: 1px solid #e1ebef;
                border-radius: 14px;
                background: #ffffff;
                color: {GRAY};
                font-size: .82rem;
                line-height: 1.25;
            }}

            .workflow-step span {{
                display: grid;
                place-items: center;
                flex: 0 0 30px;
                width: 30px;
                height: 30px;
                border-radius: 9px;
                background: rgba(0,166,166,.10);
                color: {TEAL};
                font-weight: 850;
            }}

            .workflow-step strong {{
                display: block;
                color: {NAVY};
                font-size: .86rem;
            }}

            .section-heading {{
                display: flex;
                align-items: flex-start;
                gap: .8rem;
                margin: .2rem 0 1rem;
            }}

            .section-number {{
                display: grid;
                place-items: center;
                flex: 0 0 38px;
                width: 38px;
                height: 38px;
                border-radius: 12px;
                background: {NAVY};
                color: #ffffff;
                font-weight: 850;
            }}

            .section-heading h2 {{
                color: {NAVY};
                margin: 0;
                font-size: 1.35rem;
            }}

            .section-heading p {{
                color: {GRAY};
                margin: .18rem 0 0;
                line-height: 1.45;
            }}

            .panel-label {{
                margin: 0 0 .25rem;
                color: {NAVY};
                font-size: .88rem;
                font-weight: 800;
            }}

            .panel-caption {{
                margin: 0 0 .85rem;
                color: {GRAY};
                font-size: .82rem;
                line-height: 1.45;
            }}

            .analysis-ready {{
                margin-top: .8rem;
                padding: .85rem 1rem;
                border-left: 4px solid {TEAL};
                border-radius: 0 12px 12px 0;
                background: #f1fbfa;
                color: #245b5e;
            }}

            .insight-strip {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                margin: .75rem 0 1rem;
                padding: .8rem 1rem;
                border-radius: 14px;
                background: #f7fafc;
                border: 1px solid #e1ebef;
                color: {GRAY};
                font-size: .88rem;
            }}

            .insight-strip strong {{
                color: {NAVY};
            }}

            .empty-state {{
                padding: 2.3rem 1.4rem;
                border: 1px dashed #bfd2da;
                border-radius: 18px;
                background: linear-gradient(135deg, #fbfdfe 0%, #f2fbfa 100%);
                text-align: center;
            }}

            .empty-state .empty-icon {{
                font-size: 2rem;
                margin-bottom: .45rem;
            }}

            .empty-state h3 {{
                color: {NAVY};
                margin: 0 0 .35rem;
                font-size: 1.08rem;
            }}

            .empty-state p {{
                color: {GRAY};
                margin: 0 auto;
                max-width: 540px;
                line-height: 1.5;
            }}

            .record-summary {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: .8rem;
                margin: .7rem 0 .45rem;
                color: {GRAY};
                font-size: .86rem;
            }}

            .record-count {{
                padding: .28rem .58rem;
                border-radius: 999px;
                background: rgba(18,53,91,.08);
                color: {NAVY};
                font-weight: 800;
            }}

            .detail-title {{
                color: {NAVY};
                margin: 0 0 .35rem;
                font-size: 1rem;
            }}

            .report-intro {{
                padding: .9rem 1rem;
                margin-bottom: 1rem;
                border-radius: 14px;
                background: #f7fafc;
                border: 1px solid #e1ebef;
                color: {GRAY};
                line-height: 1.5;
            }}

            div[data-testid="stTabs"] {{
                margin-top: .25rem;
            }}

            div[data-testid="stTabs"] div[data-baseweb="tab-list"] {{
                gap: .35rem;
                padding: .35rem;
                border: 1px solid #e1ebef;
                border-radius: 14px;
                background: #f6f9fa;
            }}

            div[data-testid="stTabs"] button[data-baseweb="tab"] {{
                min-height: 42px;
                border-radius: 10px;
                color: {GRAY};
                font-weight: 750;
            }}

            div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {{
                background: #ffffff;
                color: {NAVY};
                box-shadow: 0 4px 14px rgba(18,53,91,.08);
            }}

            div[data-testid="stTabs"] div[data-baseweb="tab-highlight"] {{
                display: none;
            }}

            div[data-testid="stTabs"] div[role="tabpanel"] {{
                padding-top: 1.15rem;
            }}

            div[data-testid="stVerticalBlockBorderWrapper"] {{
                border-color: #e1ebef;
                border-radius: 18px;
                box-shadow: 0 7px 24px rgba(18,53,91,.035);
            }}

            div[data-testid="stDataFrame"] {{
                border: 1px solid #e1ebef;
                border-radius: 14px;
                overflow: hidden;
            }}

            @media (max-width: 800px) {{
                .workflow-strip {{
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }}

                .workspace-source-card,
                .insight-strip {{
                    align-items: flex-start;
                    flex-direction: column;
                }}
            }}

            @media (max-width: 520px) {{
                .workflow-strip {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_section_heading(number: int, title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="section-heading">
            <div class="section-number">{number}</div>
            <div>
                <h2>{title}</h2>
                <p>{description}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(icon: str, title: str, message: str) -> None:
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-icon">{icon}</div>
            <h3>{title}</h3>
            <p>{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workspace_header(is_demo: bool, source_label: str) -> None:
    title_col, action_col = st.columns([5.7, 2.1])

    with title_col:
        st.markdown(
            """
            <section class="workspace-header">
                <div class="workspace-kicker">📡 ESPACIO DE ANÁLISIS</div>
                <h1>Panel de inteligencia de mercado</h1>
                <p>
                    Describe tu empresa, analiza señales históricas y verifica
                    cada resultado con las órdenes que lo sustentan.
                </p>
            </section>
            """,
            unsafe_allow_html=True,
        )

    with action_col:
        home_col, tutorial_col = st.columns(2)
        with home_col:
            if st.button(
                "← Inicio",
                use_container_width=True,
                key="workspace_home",
            ):
                navigate("landing")

        with tutorial_col:
            if st.button(
                "🎓 Tutorial",
                type="primary",
                use_container_width=True,
                key="workspace_tutorial",
            ):
                st.session_state.show_tutorial = True
                st.session_state.tutorial_step = 0
                st.rerun()

    status_class = "source-status demo" if is_demo else "source-status"
    status_text = "MODO DEMO" if is_demo else "DATOS DISPONIBLES"
    source_detail = (
        "Se emplean registros de demostración. El Parquet procesado se cargará "
        "automáticamente cuando esté disponible."
        if is_demo
        else "El panel está trabajando con la fuente procesada configurada en el proyecto."
    )
    st.markdown(
        f"""
        <div class="workspace-source-card">
            <div>
                <strong>Fuente activa:</strong> {source_label}<br>
                <span>{source_detail}</span>
            </div>
            <span class="{status_class}">{status_text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="workflow-strip">
            <div class="workflow-step"><span>1</span><div><strong>Describe</strong>tu oferta</div></div>
            <div class="workflow-step"><span>2</span><div><strong>Analiza</strong>el mercado</div></div>
            <div class="workflow-step"><span>3</span><div><strong>Verifica</strong>la evidencia</div></div>
            <div class="workflow-step"><span>4</span><div><strong>Prepara</strong>tu informe</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_business_tab(
    orders: pd.DataFrame,
    departments: list[str],
    object_types: list[str],
) -> None:
    render_section_heading(
        1,
        "Describe tu empresa",
        "Define qué ofreces y ajusta los términos que se buscarán en las órdenes públicas.",
    )

    content_col, settings_col = st.columns([1.45, 0.85], gap="large")

    with content_col:
        with st.container(border=True):
            st.markdown('<p class="panel-label">Perfil empresarial</p>', unsafe_allow_html=True)
            st.markdown(
                '<p class="panel-caption">Puedes partir de un ejemplo o escribir una descripción propia.</p>',
                unsafe_allow_html=True,
            )

            example = st.selectbox(
                "Comienza con un ejemplo",
                options=list(EXAMPLES),
                index=0,
            )
            if example != "Escribir mi propia descripción":
                current = st.session_state.get("profile_text", "")
                if current != EXAMPLES[example]:
                    st.session_state.profile_text = EXAMPLES[example]

            label_col, help_col = st.columns([4, 1.25])
            with label_col:
                st.markdown("**¿Qué productos o servicios ofrece tu empresa?**")
            with help_col:
                with st.popover("💡 Guía", use_container_width=True):
                    st.markdown(
                        """
                        Incluye:
                        - producto o servicio principal;
                        - especialidad;
                        - tipo de instalación o cliente;
                        - cobertura, cuando sea relevante.

                        **Ejemplo:** “Brindamos limpieza y desinfección de oficinas y
                        establecimientos de salud”.
                        """
                    )

            profile = st.text_area(
                "Descripción empresarial",
                key="profile_text",
                height=150,
                label_visibility="collapsed",
                placeholder=(
                    "Ejemplo: Vendemos laptops, impresoras y brindamos mantenimiento "
                    "de equipos informáticos."
                ),
            )

            extracted = extract_keywords(profile, "")
            suggested = ", ".join(extracted)

            keyword_col, keyword_help = st.columns([4, 1.25])
            with keyword_col:
                st.markdown("**Palabras clave para la búsqueda**")
            with keyword_help:
                with st.popover("Ayuda", use_container_width=True):
                    st.write(
                        "La versión actual busca estas palabras dentro de "
                        "`DESCRIPCION_ORDEN`. Puedes eliminarlas, corregirlas o agregar "
                        "sinónimos. No se está simulando una respuesta de Gemma."
                    )

            if suggested and not st.session_state.get("keywords_text"):
                st.session_state.keywords_text = suggested

            keywords_text = st.text_input(
                "Palabras clave",
                key="keywords_text",
                label_visibility="collapsed",
                placeholder="laptop, impresora, soporte técnico",
            )

    with settings_col:
        with st.container(border=True):
            st.markdown('<p class="panel-label">Alcance del análisis</p>', unsafe_allow_html=True)
            st.markdown(
                '<p class="panel-caption">Los filtros son opcionales. Déjalos vacíos para revisar todo el conjunto de datos.</p>',
                unsafe_allow_html=True,
            )

            selected_departments = st.multiselect(
                "Departamento de la entidad",
                options=departments,
                default=[],
                placeholder="Todos los departamentos",
            )
            selected_objects = st.multiselect(
                "Objeto contractual",
                options=object_types,
                default=[],
                placeholder="Todos los objetos",
            )

            st.divider()
            st.caption(f"Registros disponibles en la fuente: {len(orders):,}")
            st.caption(
                "Las órdenes anuladas se separan automáticamente del resultado principal."
            )

        st.markdown(
            """
            <div class="tip-card">
                <strong>Consejo de búsqueda</strong><br>
                Empieza con términos específicos. Amplía con sinónimos solo cuando
                encuentres pocos resultados.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.button(
        "Analizar oportunidades  →",
        type="primary",
        use_container_width=True,
        key="run_analysis",
    ):
        keywords = extract_keywords(profile, keywords_text)
        if not keywords:
            st.warning(
                "Agrega una descripción o al menos una palabra clave para iniciar."
            )
            return

        result = analyze_orders(
            orders,
            keywords=keywords,
            departments=selected_departments,
            object_types=selected_objects,
        )

        if result["summary"]["total_orders"] == 0:
            st.session_state.analysis = None
            st.warning(
                "No se encontraron coincidencias. Prueba términos más generales "
                "o elimina algunos filtros."
            )
        else:
            result["report"] = build_report(result)
            st.session_state.analysis = result
            st.toast("Análisis completado", icon="✅")
            st.markdown(
                """
                <div class="analysis-ready">
                    <strong>El análisis está listo.</strong> Continúa en Mercado para
                    interpretar los resultados, luego revisa Evidencia e Informe.
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_metrics(analysis: dict[str, Any]) -> None:
    summary = analysis["summary"]
    metric_columns = st.columns(4)
    metric_columns[0].metric(
        "Órdenes válidas",
        f"{summary['total_orders']:,}",
        help="Órdenes coincidentes que no están anuladas.",
    )
    metric_columns[1].metric(
        "Monto original",
        f"S/ {summary['total_amount']:,.0f}",
        help="Suma de los montos originales de las órdenes válidas.",
    )
    metric_columns[2].metric(
        "Entidades",
        f"{summary['entity_count']:,}",
        help="Cantidad de entidades distintas presentes en el resultado.",
    )
    metric_columns[3].metric(
        "Mes con mayor actividad",
        summary["peak_month"],
        help="Periodo con mayor cantidad de órdenes coincidentes.",
    )


def render_market_tab(analysis: dict[str, Any] | None) -> None:
    if not analysis:
        render_empty_state(
            "📊",
            "Aún no hay resultados para mostrar",
            "Completa la descripción de tu empresa y ejecuta el análisis desde la pestaña Mi empresa.",
        )
        return

    render_section_heading(
        2,
        "Lectura del mercado",
        "Explora volumen, montos, entidades, evolución temporal y distribución del resultado.",
    )

    help_col, spacer_col = st.columns([1.25, 4.75])
    with help_col:
        with st.popover("Cómo interpretar", use_container_width=True):
            st.write(
                "Las métricas se calculan sobre órdenes históricas coincidentes. "
                "Las órdenes anuladas se muestran por separado y no se incluyen "
                "en el total principal."
            )

    render_metrics(analysis)

    summary = analysis["summary"]
    st.markdown(
        f"""
        <div class="insight-strip">
            <span><strong>Lectura rápida:</strong> los indicadores muestran actividad histórica relacionada con tus términos.</span>
            <span>Órdenes anuladas separadas: <strong>{summary['cancelled_orders']:,}</strong></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left_chart, right_chart = st.columns([1.15, 1], gap="large")
    with left_chart:
        with st.container(border=True):
            entities = analysis["entities"].head(10).copy()
            figure = px.bar(
                entities.sort_values("ordenes"),
                x="ordenes",
                y="ENTIDAD",
                orientation="h",
                text="ordenes",
                labels={"ordenes": "Cantidad de órdenes", "ENTIDAD": "Entidad"},
                title="Entidades con mayor actividad relacionada",
                color_discrete_sequence=[TEAL],
            )
            figure.update_traces(
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Órdenes: %{x:,}<extra></extra>",
            )
            figure.update_layout(
                height=430,
                margin=dict(l=10, r=24, t=58, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=GRAY),
                title_font=dict(color=NAVY, size=16),
                xaxis=dict(showgrid=True, gridcolor="#edf2f4"),
                yaxis=dict(title=None),
            )
            st.plotly_chart(figure, use_container_width=True)

    with right_chart:
        with st.container(border=True):
            monthly = analysis["monthly"].copy()
            figure = px.line(
                monthly,
                x="MES",
                y="ordenes",
                markers=True,
                labels={"MES": "Mes", "ordenes": "Órdenes"},
                title="Tendencia mensual",
                color_discrete_sequence=[NAVY],
            )
            figure.update_traces(
                marker=dict(size=9, color=YELLOW),
                line=dict(width=3),
                hovertemplate="<b>%{x}</b><br>Órdenes: %{y:,}<extra></extra>",
            )
            figure.update_layout(
                height=430,
                margin=dict(l=10, r=10, t=58, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=GRAY),
                title_font=dict(color=NAVY, size=16),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#edf2f4"),
            )
            st.plotly_chart(figure, use_container_width=True)

    department_col, object_col = st.columns(2, gap="large")
    with department_col:
        with st.container(border=True):
            departments = analysis["departments"].copy()
            figure = px.bar(
                departments,
                x="DEPARTAMENTO",
                y="monto_total",
                labels={
                    "DEPARTAMENTO": "Departamento",
                    "monto_total": "Monto original",
                },
                title="Monto por departamento de la entidad",
                color_discrete_sequence=[TEAL],
            )
            figure.update_traces(
                hovertemplate="<b>%{x}</b><br>Monto: S/ %{y:,.2f}<extra></extra>"
            )
            figure.update_layout(
                height=410,
                margin=dict(l=10, r=10, t=58, b=30),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=GRAY),
                title_font=dict(color=NAVY, size=16),
                xaxis=dict(tickangle=-30, title=None),
                yaxis=dict(showgrid=True, gridcolor="#edf2f4"),
            )
            st.plotly_chart(figure, use_container_width=True)

    with object_col:
        with st.container(border=True):
            objects = analysis["objects"].copy()
            figure = px.pie(
                objects,
                names="OBJETOCONTRACTUAL",
                values="ordenes",
                hole=.48,
                title="Distribución entre bienes y servicios",
                color_discrete_sequence=[NAVY, TEAL, YELLOW, LIGHT_BLUE],
            )
            figure.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate="<b>%{label}</b><br>Órdenes: %{value:,}<br>Participación: %{percent}<extra></extra>",
            )
            figure.update_layout(
                height=410,
                margin=dict(l=10, r=10, t=58, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color=GRAY),
                title_font=dict(color=NAVY, size=16),
                showlegend=False,
            )
            st.plotly_chart(figure, use_container_width=True)


def render_evidence_tab(analysis: dict[str, Any] | None) -> None:
    if not analysis:
        render_empty_state(
            "🔍",
            "La evidencia aparecerá después del análisis",
            "Ejecuta una búsqueda desde Mi empresa para consultar las órdenes exactas utilizadas en los indicadores.",
        )
        return

    render_section_heading(
        3,
        "Evidencia del análisis",
        "Filtra, revisa y abre los registros exactos que sustentan las métricas del mercado.",
    )

    evidence = analysis["evidence"].copy()

    with st.container(border=True):
        st.markdown('<p class="panel-label">Filtrar registros</p>', unsafe_allow_html=True)
        filter_col_1, filter_col_2, filter_col_3 = st.columns(3)
        with filter_col_1:
            evidence_departments = st.multiselect(
                "Departamento",
                sorted(evidence["DEPARTAMENTO"].dropna().astype(str).unique()),
                key="evidence_departments",
                placeholder="Todos",
            )
        with filter_col_2:
            evidence_states = st.multiselect(
                "Estado",
                sorted(evidence["ESTADOCONTRATACION"].dropna().astype(str).unique()),
                key="evidence_states",
                placeholder="Todos",
            )
        with filter_col_3:
            evidence_objects = st.multiselect(
                "Objeto contractual",
                sorted(evidence["OBJETOCONTRACTUAL"].dropna().astype(str).unique()),
                key="evidence_objects",
                placeholder="Todos",
            )

    filtered = evidence.copy()
    if evidence_departments:
        filtered = filtered[
            filtered["DEPARTAMENTO"].astype(str).isin(evidence_departments)
        ]
    if evidence_states:
        filtered = filtered[
            filtered["ESTADOCONTRATACION"].astype(str).isin(evidence_states)
        ]
    if evidence_objects:
        filtered = filtered[
            filtered["OBJETOCONTRACTUAL"].astype(str).isin(evidence_objects)
        ]

    st.markdown(
        f"""
        <div class="record-summary">
            <span>Resultados después de aplicar los filtros</span>
            <span class="record-count">{len(filtered):,} de {len(evidence):,} órdenes</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if filtered.empty:
        render_empty_state(
            "🧹",
            "No hay registros con estos filtros",
            "Retira uno o más filtros para ampliar el conjunto de evidencia.",
        )
        return

    table_columns = [
        "ORDEN",
        "FECHA_DE_EMISION",
        "ENTIDAD",
        "DESCRIPCION_ORDEN",
        "MONTO_TOTAL_ORDEN_ORIGINAL",
        "ESTADOCONTRATACION",
        "DEPARTAMENTO",
        "NOMBRE_RAZON_CONTRATISTA",
    ]

    st.dataframe(
        filtered[table_columns].sort_values(
            "FECHA_DE_EMISION",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
        height=440,
        column_config={
            "ORDEN": st.column_config.TextColumn("Orden", width="small"),
            "ENTIDAD": st.column_config.TextColumn("Entidad", width="medium"),
            "DESCRIPCION_ORDEN": st.column_config.TextColumn(
                "Descripción", width="large"
            ),
            "MONTO_TOTAL_ORDEN_ORIGINAL": st.column_config.NumberColumn(
                "Monto original",
                format="S/ %.2f",
            ),
            "FECHA_DE_EMISION": st.column_config.DateColumn(
                "Fecha de emisión",
                format="DD/MM/YYYY",
            ),
        },
    )

    st.write("")
    with st.container(border=True):
        detail_head_col, selector_col = st.columns([1.1, 1.4])
        with detail_head_col:
            st.markdown('<p class="detail-title"><strong>Ficha de la orden</strong></p>', unsafe_allow_html=True)
            st.caption("Selecciona un registro para revisar sus datos completos.")
        with selector_col:
            selected_order = st.selectbox(
                "Abrir ficha de una orden",
                filtered["ORDEN"].astype(str).tolist(),
                label_visibility="collapsed",
            )

        row = filtered[
            filtered["ORDEN"].astype(str) == selected_order
        ].iloc[0]

        st.divider()
        principal_col, timeline_col = st.columns(2, gap="large")
        with principal_col:
            st.markdown("#### Datos principales")
            st.write(f"**Entidad:** {row['ENTIDAD']}")
            st.write(f"**Descripción:** {row['DESCRIPCION_ORDEN']}")
            st.write(
                "**Monto original:** "
                f"S/ {float(row['MONTO_TOTAL_ORDEN_ORIGINAL']):,.2f}"
            )
            st.write(f"**Tipo:** {row['TIPOORDEN']}")
            st.write(f"**Estado:** {row['ESTADOCONTRATACION']}")
            st.write(f"**Proveedor:** {row['NOMBRE_RAZON_CONTRATISTA']}")

        with timeline_col:
            st.markdown("#### Línea de tiempo")
            st.write(f"**Registro:** {row['FECHA_REGISTRO']}")
            st.write(f"**Emisión:** {row['FECHA_DE_EMISION']}")
            st.write(
                "**Compromiso presupuestal:** "
                f"{row['FECHA_COMPROMISO_PRESUPUESTAL']}"
            )
            st.write(f"**Notificación:** {row['FECHA_DE_NOTIFICACION']}")


def render_report_tab(analysis: dict[str, Any] | None) -> None:
    if not analysis:
        render_empty_state(
            "📄",
            "El informe todavía no está disponible",
            "Primero ejecuta el análisis. El resumen se construirá con las métricas y la evidencia obtenidas.",
        )
        return

    report_file = (
        "# Informe MYPE Radar\n\n"
        f"**Descripción empresarial:** {st.session_state.profile_text}\n\n"
        f"**Palabras clave:** {', '.join(analysis['keywords'])}\n\n"
        f"{analysis['report']}\n\n"
        f"_Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}_"
    )

    heading_col, download_col = st.columns([4.4, 1.6])
    with heading_col:
        render_section_heading(
            4,
            "Resumen para la empresa",
            "Convierte los resultados en una lectura ejecutiva que puedes descargar y compartir.",
        )
    with download_col:
        st.download_button(
            "⬇ Descargar informe",
            data=report_file.encode("utf-8"),
            file_name="informe_mype_radar.md",
            mime="text/markdown",
            type="primary",
            use_container_width=True,
        )

    st.markdown(
        """
        <div class="report-intro">
            El informe resume los cálculos del análisis actual. Antes de tomar una
            decisión comercial, contrasta las conclusiones con la pestaña
            <strong>Evidencia</strong> y con las fuentes oficiales.
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown(analysis["report"])


def render_workspace() -> None:
    orders, source_label, is_demo = load_orders(APP_DIR)
    departments = sorted(
        orders["DEPARTAMENTO"].dropna().astype(str).unique().tolist()
    )
    object_types = sorted(
        orders["OBJETOCONTRACTUAL"].dropna().astype(str).unique().tolist()
    )

    inject_workspace_styles()
    render_workspace_header(is_demo, source_label)

    if st.session_state.show_tutorial:
        tutorial_dialog()

    business_tab, market_tab, evidence_tab, report_tab = st.tabs(
        ["Mi empresa", "Mercado", "Evidencia", "Informe"]
    )

    with business_tab:
        render_business_tab(orders, departments, object_types)

    analysis = st.session_state.get("analysis")

    with market_tab:
        render_market_tab(analysis)

    with evidence_tab:
        render_evidence_tab(analysis)

    with report_tab:
        render_report_tab(analysis)

    st.markdown(
        """
        <div class="footer-band">
            <strong>MYPE Radar</strong> analiza información histórica y no
            garantiza contratos ni adjudicaciones.
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_tutorial_page() -> None:
    render_top_navigation("tutorial")

    st.markdown(
        """
        <section class="tutorial-hero">
            <span class="eyebrow" style="background:#12355b;">CENTRO DE AYUDA</span>
            <h1 style="color:#12355b; margin:.8rem 0 .45rem;">
                Aprende a utilizar MYPE Radar
            </h1>
            <p style="color:#5e6b78; max-width:820px; line-height:1.65;">
                Este tutorial permanece disponible durante toda la experiencia.
                También puedes abrir la guía emergente desde el panel principal.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <h2 class="section-title">Recorrido completo</h2>
        <p class="section-lead">
            Sigue estos pasos para obtener resultados claros y verificables.
        </p>
        """,
        unsafe_allow_html=True,
    )

    first_row = st.columns(3)
    second_row = st.columns(2)
    tutorial_columns = first_row + second_row

    for column, step in zip(tutorial_columns, TUTORIAL_STEPS):
        with column:
            st.markdown(
                f"""
                <article class="tutorial-step">
                    <div class="feature-icon">{step['icon']}</div>
                    <h3>{step['title']}</h3>
                    <p>{step['body']}</p>
                    <p><strong>Consejo:</strong> {step['tip']}</p>
                </article>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <h2 class="section-title">Buenas prácticas</h2>
        """,
        unsafe_allow_html=True,
    )

    practice_columns = st.columns(3)
    practices = [
        (
            "Usa descripciones concretas",
            "Evita frases como “vendemos de todo”. Menciona productos, servicios y especialidad.",
        ),
        (
            "Revisa la evidencia",
            "No tomes una recomendación sin consultar las órdenes que sustentan el resultado.",
        ),
        (
            "Interpreta con cautela",
            "La actividad histórica ayuda a prepararse, pero no predice compras ni adjudicaciones.",
        ),
    ]
    for column, (title, text) in zip(practice_columns, practices):
        with column:
            st.markdown(
                f"""
                <article class="feature-card">
                    <h3>{title}</h3>
                    <p>{text}</p>
                </article>
                """,
                unsafe_allow_html=True,
            )

    st.write("")
    start_col, popup_col, spacer_col = st.columns([1.4, 1.55, 3.4])
    with start_col:
        if st.button(
            "Ir a la aplicación",
            type="primary",
            use_container_width=True,
            key="tutorial_go_app",
        ):
            navigate("workspace")

    with popup_col:
        if st.button(
            "Abrir tutorial emergente",
            use_container_width=True,
            key="tutorial_open_popup",
        ):
            navigate("workspace", show_tutorial=True)


def main() -> None:
    configure_page()
    initialize_state()

    page = st.session_state.page

    if page == "landing":
        render_landing()
    elif page == "tutorial":
        render_tutorial_page()
    else:
        render_workspace()


if __name__ == "__main__":
    main()