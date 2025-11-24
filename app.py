import streamlit as st
import pandas as pd
import zipfile
import tempfile
from tratamiento_inei.proce_victimización_inseguridad_inei import cargar_y_procesar_datos_victimizacion
from tratamiento_inei.proce_percepcion_inseguridad_inei import cargar_y_procesar_datos_percepcion
from tratamiento_inei.proce_confianza_instituciones_inei import cargar_y_procesar_datos_confianza
import plotly.express as px
import json
from utils.geo_processing import cargar_y_preparar_datos
from st_aggrid import AgGrid

def page_2():
        # Recuperar los datos desde el session_state
    df_final = st.session_state.get("df_final", None)
    df_completo = st.session_state.get("df_completo", None)

    if df_final is not None:
        st.write("Datos finales procesados (principal):")
        st.dataframe(df_final)

    if df_completo is not None:
        st.write("Datos completos procesados:")
        st.dataframe(df_completo)


    # ================================
    # CONFIGURACIÓN GENERAL
    # ================================

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

    st.markdown("""
    <style>
    .df-card {
        background-color: #1e1e1e;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #333;
        height: 330px; /* Ajusta altura */
        overflow-y: scroll;
    }
    .df-title {
        font-size: 18px;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <style>
    .df-card {
        background: linear-gradient(135deg, #1c1c1c 0%, #232323 100%);
        padding: 12px;
        border-radius: 14px;
        border: 1px solid #333;
        height: 350px; /* Ajustar si quieres más/menos */
        overflow-y: auto;
        box-shadow: 0px 0px 12px rgba(0,0,0,0.35);
        transition: all 0.25s ease-in-out;
    }

    .df-card:hover {
        transform: translateY(-5px) scale(1.01);
        box-shadow: 0px 0px 22px rgba(255,255,255,0.07);
        border-color: #555;
    }

    .df-title {
        font-size: 18px;
        font-weight: 600;
        color: #eaeaea;
        margin-bottom: 8px;
        text-align: center;
        letter-spacing: 0.4px;
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
            # 1. Cargar el DataFrame
            df = pd.read_csv(uploaded_file)
            
            # 2. Definir las columnas a redondear (las métricas de interés)
            metric_columns = [
                "Victimizacion_total_%", 
                "Inseguridad_general_%", 
                "Indice_confianza_PNP_%"
            ]
            
            # 3. Aplicar redondeo a 1 decimal (para porcentajes) si la columna existe
            for col in metric_columns:
                if col in df.columns:
                    try:
                        # Aplicar .round(1)
                        df[col] = df[col].round(1) 
                    except TypeError:
                        # En caso de que la columna no sea numérica (debería manejarse con cargar_y_preparar_datos)
                        # Pero es un buen control de errores.
                        print(f"Advertencia: La columna {col} no es numérica y no se redondeó.")
                    
            return df
        return None
    st.sidebar.header("📂 Subir Archivos)")

    official_file = st.sidebar.file_uploader("📘 Datos Oficiales (CSV)", type=["csv"])
    youtube_file  = st.sidebar.file_uploader("📺 Datos de YouTube (CSV)", type=["csv"])
    twitter_file  = st.sidebar.file_uploader("🐦 Datos de Twitter (CSV)", type=["csv"])

    official_data = load_data(official_file)
    youtube_data = load_data(youtube_file)
    twitter_data = load_data(twitter_file)

    # ================================
    # MOSTRAR DATAFRAMES EN COLUMNAS
    # ================================
    # ================================
    # MOSTRAR DATAFRAMES EN COLUMNAS
    # ================================
    dfs_to_show = []

    if official_data is not None:
        dfs_to_show.append(("📘 Datos oficiales", official_data))

    if youtube_data is not None:
        dfs_to_show.append(("📺 YouTube", youtube_data))

    if twitter_data is not None:
        dfs_to_show.append(("🐦 Twitter", twitter_data))

    if len(dfs_to_show) > 0:
        st.markdown("## 📊 Vista previa de datos cargados")

        # Crear columnas de manera dinámica
        cols = st.columns(len(dfs_to_show))

        for idx, (title, df) in enumerate(dfs_to_show):
            with cols[idx]:
                # Título de la tabla
                st.markdown(f"### {title}", unsafe_allow_html=True)  
                
                # Mostrar la tabla con un tamaño fijo y barras de desplazamiento si es necesario
                AgGrid(df, height=300, fit_columns_on_grid_load=True, enable_enterprise_modules=True)
                
                # Ajustar el diseño de la tabla
                st.markdown("<br>", unsafe_allow_html=True)


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
    # Verificar que el archivo de datos oficiales y de redes sociales esté cargado correctamente
    if official_data is not None:
        official_file.seek(0)
        gdfm_official = load_gdf(official_file).dropna(subset=["geometry"])

    if youtube_data is not None:
        youtube_file.seek(0)
        gdfm_youtube = load_gdf(youtube_file).dropna(subset=["geometry"])

    if twitter_data is not None:
        twitter_file.seek(0)
        gdfm_twitter = load_gdf(twitter_file).dropna(subset=["geometry"])
    # ================================
    # 4. FUNCIONES DE MAPAS Y GRAFICOS
    # ================================
    def crear_mapa(gdf, metric, data_source):
        geojson = json.loads(gdf.to_json())
        
        # Colores específicos según la fuente de datos
        if data_source == "youtube":
            color_scale = "reds"  # Color rojo para YouTube
        elif data_source == "twitter":
            color_scale = "blues"  # Color azul para Twitter
        else:  # INEI
            color_scale = "Viridis"  # Color por defecto para INEI
        
        fig = px.choropleth_mapbox(
            gdf,
            geojson=geojson,
            locations=gdf.index,
            color=metric,
            color_continuous_scale=color_scale,  # Asignar color específico
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
    # 5. LÓGICA GENERAL DE ANÁLISIS
    # ================================

    # Diccionario de datos cargados
    fuentes = {
        "INEI": {
            "data": official_data,
            "file": official_file,
            "color": "Viridis",
            "tag": "inei"
        },
        "YouTube": {
            "data": youtube_data,
            "file": youtube_file,
            "color": "Reds",
            "tag": "youtube"
        },
        "Twitter": {
            "data": twitter_data,
            "file": twitter_file,
            "color": "Blues",
            "tag": "twitter"
        }
    }

    # Contar cuántas fuentes se subieron
    fuentes_cargadas = {k:v for k,v in fuentes.items() if v["data"] is not None}
    n = len(fuentes_cargadas)


    # ================================
    # CASO 0 → Nada cargado
    # ================================
    if n == 0:
        st.warning("📂 Sube al menos un archivo para comenzar el análisis.")
        st.stop()


    # ================================
    # CASO 1 → Análisis individual
    # ================================
    if n == 1:

        nombre, f = list(fuentes_cargadas.items())[0]

        st.info(f"🔍 Solo se cargó **{nombre}**.")
        continuar = st.sidebar.radio(
            f"¿Deseas analizar únicamente la fuente **{nombre}**?",
            ["Sí", "No"], index=0
        )

        if continuar == "No":
            st.stop()

        f["file"].seek(0)
        gdf = load_gdf(f["file"]).dropna(subset=["geometry"])

        st.subheader(f"🗺️ Mapa – {nombre}")
        st.plotly_chart(crear_mapa(gdf, metric, f["tag"]), use_container_width=True)

        # Seleccionar los datos del dataframe
        df = f["data"]
        # Filtrar el indicador seleccionado
        selected_data = df[["NOMBREDI", metric]].sort_values(by=metric, ascending=False)

        # Mostrar las primeras 10 filas
        top_distritos = selected_data.head(10)

        # Crear gráfico de barras
        fig_barras = px.bar(
            top_distritos, 
            x="NOMBREDI", 
            y=metric, 
            title=f"Top 10 distritos con mayor {metric}",
            labels={metric: f"{metric} (%)", "NOMBREDI": "Distrito"},
            color=metric, 
            color_continuous_scale="Viridis"
        )

        # Mostrar el gráfico de barras
        st.plotly_chart(fig_barras, use_container_width=True)

        # Agrupar por distrito y obtener la suma del indicador seleccionado
        pie_data = df.groupby("NOMBREDI")[metric].sum().reset_index()

        # Crear gráfico de pie
        fig_pie = px.pie(
            pie_data, 
            names="NOMBREDI", 
            values=metric, 
            title=f"Distribución de {metric} por distrito",
            color="NOMBREDI",
            color_discrete_sequence=px.colors.qualitative.Set3
        )

        # Mostrar el gráfico de pie
        st.plotly_chart(fig_pie, use_container_width=True)

        st.stop()


    # ================================
    # CASO 2 O 3 → Comparaciones
    # ================================
    st.success("📊 Archivos cargados correctamente. Análisis comparativo activado.")

    # Convertir todos los archivos subidos en geodataframes
    gdfs = {}
    for nombre, f in fuentes_cargadas.items():
        f["file"].seek(0)
        gdfs[nombre] = load_gdf(f["file"]).dropna(subset=["geometry"])


    # ================================
    # 1. MAPAS EN COLUMNAS (dinámico)
    # ================================
    st.markdown("## 🗺️ Comparación de Mapas por Fuente")

    cols = st.columns(n)

    for idx, (nombre, f) in enumerate(fuentes_cargadas.items()):
        with cols[idx]:
            st.subheader(f"Mapa – {nombre}")
            st.plotly_chart(
                crear_mapa(gdfs[nombre], metric, f["tag"]),
                use_container_width=True
            )


    # ================================
    # 2. GRÁFICO COMPARATIVO (si >= 2 fuentes)
    # ================================
    if n >= 2:
        st.markdown("---")
        st.markdown("## 📈 Comparación de Valores por Distrito")

        # Unir todas las fuentes por distrito
        merged = None

        for nombre, f in fuentes_cargadas.items():
            df = f["data"][["NOMBREDI", metric]].rename(
                columns={metric: f"{metric}_{nombre}"}
            )
            if merged is None:
                merged = df
            else:
                merged = pd.merge(merged, df, on="NOMBREDI")

        fig = px.bar(
            merged,
            x="NOMBREDI",
            y=[col for col in merged.columns if col != "NOMBREDI"],
            title="Comparación entre fuentes de datos"
        )
        st.plotly_chart(fig, use_container_width=True)

    # ================================
    # FOOTER EN SIDEBAR
    # ================================
    st.sidebar.markdown("""
    ---
    ⚠️ **Aviso:**  
    Los datos de redes sociales son aproximaciones automáticas y no reemplazan estadísticas oficiales.
    """)







# Inicializa el estado para controlar el paso entre las etapas
if "step" not in st.session_state:
    st.session_state.step = 1  # 1 = carga, 2 = visualización

# Flujo guiado
if st.session_state.step == 1:
    # Título de la página de carga
    st.set_page_config(
    page_title="Carga de Datos y Procesamiento",
    layout="wide",
    initial_sidebar_state="expanded"
    )

    # Subir archivo ZIP
    uploaded_file = st.file_uploader("Cargar archivo ZIP", type=["zip"])

    # Verificar si se ha cargado un archivo
    if uploaded_file is not None:
        with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
            # Listar los archivos dentro del ZIP
            file_list = zip_ref.namelist()
            st.write("Archivos dentro del ZIP:", file_list)

            # Buscar la carpeta dentro del ZIP (en este caso, cualquier carpeta dentro)
            folder_name = None
            for file in file_list:
                if file.endswith("/"):  # Carpeta
                    folder_name = file
                    break

            if folder_name:
                # Buscar el archivo CSV dentro de esa carpeta
                csv_file = None
                for file in file_list:
                    if file.startswith(folder_name) and file.endswith(".csv"):
                        csv_file = file
                        break

                if csv_file:
                    # Extraer el archivo CSV desde el ZIP y leerlo en un DataFrame
                    with zip_ref.open(csv_file) as f:
                        df = pd.read_csv(f)

                    # Botón para procesar el CSV
                    if st.button("Procesar Datos"):
                        # Procesar los datos
                        dist_total_victimizacion, dist_segmentado_victimizacion = cargar_y_procesar_datos_victimizacion(df)
                        dist_percepcion, dist_segmentado_percepcion = cargar_y_procesar_datos_percepcion(df)
                        distritos_confianza = cargar_y_procesar_datos_confianza(df)

                        # Extraer solo las columnas necesarias de cada DataFrame
                        vict_total_df = dist_total_victimizacion[["NOMBREDI", "Victimizacion_total_%"]]
                        inseguridad_general_df = dist_segmentado_percepcion[["NOMBREDI", "Inseguridad_general_%"]]
                        confianza_df = distritos_confianza[["NOMBREDI", "Indice_confianza_PNP_%"]]

                        # Crear un DataFrame final con las tres métricas clave
                        df_final = pd.merge(vict_total_df, inseguridad_general_df, on="NOMBREDI", how="left")
                        df_final = pd.merge(df_final, confianza_df, on="NOMBREDI", how="left")
                        st.success("Datos procesados exitosamente. Puedes ir a la página de visualización para ver los resultados.")

                        # Crear df_completo con todos los datos procesados
                        df_completo = pd.merge(dist_segmentado_victimizacion, dist_segmentado_percepcion, on="NOMBREDI", how="left")
                        df_completo = pd.merge(df_completo, distritos_confianza, on="NOMBREDI", how="left")

                        # Guardar los datos procesados en session_state
                        st.session_state.df_final = df_final
                        st.session_state.df_completo = df_completo

                        # Botón para redirigir a la página de visualización (usando `st.session_state`)
                        st.button("Ir a la página de visualización", on_click=lambda: st.session_state.update({'step': 2}))
                        
else:
    # Página de visualización
    page_2()
