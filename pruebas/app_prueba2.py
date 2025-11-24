

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from utils.geo_processing import cargar_y_preparar_datos

# Configuración de la página de Streamlit
st.set_page_config(page_title="Mapa Limeños 2024", layout="wide")

# ------------------------------
# 1. Cargar datos
# ------------------------------
@st.cache_data
def load_gdf(youtube_data):
    # Procesar los datos de YouTube
    return cargar_y_preparar_datos(youtube_data)  # Llamamos la función de geo_processing.py para preparar los datos

# Opción para cargar CSV
youtube_file = st.sidebar.file_uploader("Cargar archivo de YouTube (CSV)", type=["csv"])

if youtube_file is not None:
    # Procesar los datos cargados
    gdfm = load_gdf(youtube_file)

    # ------------------------------
    # 2. Limpiar geometrías nulas
    # ------------------------------
    gdfm_clean = gdfm.dropna(subset=["geometry"]).copy()
    st.dataframe(gdfm_clean.drop(columns=["geometry"]).head())

    if gdfm_clean.empty:
        st.error("❌ Error: No existen geometrías válidas para mostrar.")
        st.stop()

    # ------------------------------
    # 3. Convertir a GeoJSON
    # ------------------------------
    geojson = json.loads(gdfm_clean.to_json())

    # ------------------------------
    # 4. Selector de métrica
    # ------------------------------
    metricas = [
        "Victimizacion_total_%", 
        "Inseguridad_general_%", 
        "Indice_confianza_PNP_%"
    ]

    metric = st.selectbox("📊 Selecciona el indicador:", metricas)

    # ------------------------------
    # 5. Mapa Choropleth 🔥
    # ------------------------------
    fig = px.choropleth_mapbox(
        gdfm_clean,
        geojson=geojson,
        locations=gdfm_clean.index,
        color=metric,
        mapbox_style="carto-positron",
        center={"lat": -12.0464, "lon": -77.0428},
        zoom=10,
        opacity=0.6,
    )

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        height=700,
        margin={"r":0,"t":0,"l":0,"b":0},
        coloraxis_colorbar=dict(title=metric)
    )

    # ------------------------------
    # 6. Mostrar mapa
    # ------------------------------
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------
    # 7. Agregar un gráfico comparativo (Opcional)
    # -----------------------------------
    st.subheader("Gráfico Comparativo de Distritos")

    # Crear gráfico de barras comparando las métricas
    if not gdfm_clean.empty:
        bar_fig = px.bar(
            gdfm_clean,
            x="NOMBDIST",
            y=[metric],
            title="Comparación de distritos según la métrica seleccionada"
        )
        st.plotly_chart(bar_fig)

else:
    st.warning("Por favor, carga el archivo CSV con los datos de YouTube para continuar.")
