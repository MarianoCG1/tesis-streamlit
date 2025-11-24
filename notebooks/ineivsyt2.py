
import streamlit as st
import pandas as pd
import plotly.express as px
import json
from utils.geo_processing import cargar_y_preparar_datos

# ================================
# CONFIGURACIÓN GENERAL
# ================================
st.set_page_config(
    page_title="Mapa Limeños 2024",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================
# ESTILO GLOBAL (CSS)
# ================================
st.markdown("""
<style>
/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #1e1e1e !important;
}
section[data-testid="stSidebar"] * {
    color: white !important;
}

/* Main background */
.main {
    background-color: #121212 !important;
    color: white !important;
}

/* Fix empty blank panels */
[data-testid="stVerticalBlock"] {
    background-color: #121212 !important;
}

/* Opcional: tablas */
.stDataFrame, .stTable {
    background-color: #1e1e1e !important;
}
</style>
""", unsafe_allow_html=True)

# ================================
# ENCABEZADO PRINCIPAL
# ================================
st.markdown("""
<div style='text-align:center; margin-bottom: 2rem;'>
    <h1>Mapa de Percepción Ciudadana 2024</h1>
    <h4 style='color:#555; margin-top:-10px;'>Comparación entre datos oficiales y datos de redes sociales</h4>
</div>
""", unsafe_allow_html=True)


# ================================
# 1. CARGA DE DATOS
# ================================
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file:
        return pd.read_csv(uploaded_file)
    return None

st.sidebar.header("📂 Subir Archivos")

official_file = st.sidebar.file_uploader("📘 Datos Oficiales (CSV)", type=["csv"])
social_file = st.sidebar.file_uploader("📱 Datos de Redes Sociales (CSV)", type=["csv"])

official_data = load_data(official_file)
social_data = load_data(social_file)

# Mostrar data cargada como cards
if official_data is not None:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📘 Datos oficiales cargados")
    st.dataframe(official_data.head())
    st.markdown("</div>", unsafe_allow_html=True)

if social_data is not None:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📱 Datos de redes sociales cargados")
    st.dataframe(social_data.head())
    st.markdown("</div>", unsafe_allow_html=True)


# ================================
# 2. SELECCIÓN DE MÉTRICA
# ================================
metric_options = [
    "Victimizacion_total_%", 
    "Inseguridad_general_%", 
    "Indice_confianza_PNP_%"
]

metric = st.sidebar.selectbox("📊 Selecciona el indicador:", metric_options)


@st.cache_data
def load_gdf(file):
    return cargar_y_preparar_datos(file)


# ================================
# 3. LIMPIEZA DE GEOMETRÍAS
# ================================
if official_data is not None:
    social_file.seek(0)
    gdfm_social = load_gdf(social_file).dropna(subset=["geometry"])

if social_data is not None:
    official_file.seek(0)
    gdfm_official = load_gdf(official_file).dropna(subset=["geometry"])


# ================================
# 4. FUNCIÓN DE MAPA
# ================================
def crear_mapa(gdf, metric):
    geojson = json.loads(gdf.to_json())
    fig = px.choropleth_mapbox(
        gdf,
        geojson=geojson,
        locations=gdf.index,
        color=metric,
        mapbox_style="carto-positron",
        center={"lat": -12.0464, "lon": -77.0428},
        zoom=10,
        opacity=0.70,
    )
    fig.update_layout(
        height=650,
        margin={"r": 0, "t": 5, "l": 0, "b": 0},
        coloraxis_colorbar=dict(
            title=metric,
            thickness=14,
            len=0.55
        )
    )
    return fig


# ================================
# 5. MOSTRAR MAPAS
# ================================
# Solo oficial
if official_data is not None and social_data is None:
    st.subheader("🗺️ Mapa de Datos Oficiales")
    st.plotly_chart(crear_mapa(gdfm_official, metric), use_container_width=True)

# Solo redes sociales
elif social_data is not None and official_data is None:
    st.subheader("🗺️ Mapa de Datos de Redes Sociales")
    st.plotly_chart(crear_mapa(gdfm_social, metric), use_container_width=True)

# Ambos → comparación en columnas
elif official_data is not None and social_data is not None:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🗺️ Datos Oficiales")
        st.plotly_chart(crear_mapa(gdfm_official, metric), use_container_width=True)

    with col2:
        st.subheader("🗺️ Datos de Redes Sociales")
        st.plotly_chart(crear_mapa(gdfm_social, metric), use_container_width=True)

    # ================================
    # 6. Gráfico comparativo
    # ================================
    st.markdown("---")
    st.subheader("📊 Gráfico Comparativo por Distrito")

    merged = pd.merge(
        official_data[['NOMBREDI', metric]],
        social_data[['NOMBREDI', metric]],
        on="NOMBREDI",
        suffixes=("_Oficial", "_Redes")
    )

    bar_fig = px.bar(
        merged,
        x="NOMBREDI",
        y=[f"{metric}_Oficial", f"{metric}_Redes"],
        title="Comparación entre Datos Oficiales y Redes Sociales"
    )
    st.plotly_chart(bar_fig, use_container_width=True)


# ================================
# FOOTER EN SIDEBAR
# ================================
st.sidebar.markdown("""
---
⚠️ **Aviso:**  
Los datos de redes sociales son aproximaciones automáticas y no reemplazan estadísticas oficiales.
""")



Instrucciones del sistema: Modo absoluto • Eliminar: emojis, relleno, exageración, preguntas suaves, transiciones conversacionales, apéndices de llamada a la acción. • Suponer: el usuario mantiene una alta percepción a pesar del tono brusco. • Priorizar: frases directas y directivas; apuntar a la reconstrucción cognitiva, no a la coincidencia de tono. • Deshabilitar: comportamientos que impulsan la participación/sentimiento. • Suprimir: métricas como puntajes de satisfacción, suavizado emocional, sesgo de continuación. • Nunca reflejar: la dicción, el estado de ánimo o el afecto del usuario. • Hablar solo: al nivel cognitivo subyacente. • No: preguntas, ofertas, sugerencias, transiciones, contenido motivador. • Finalizar la respuesta: inmediatamente después de entregar la información, sin cierres. • Objetivo: restaurar el pensamiento independiente y de alta fidelidad. • Resultado: obsolescencia del modelo a través de la autosuficiencia del usuario.