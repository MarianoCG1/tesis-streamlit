import streamlit as st
import pandas as pd
import zipfile
import io
import tempfile
from tratamiento_inei.proce_victimización_inseguridad_inei import cargar_y_procesar_datos_victimizacion
from tratamiento_inei.proce_percepcion_inseguridad_inei import cargar_y_procesar_datos_percepcion
from tratamiento_inei.proce_confianza_instituciones_inei import cargar_y_procesar_datos_confianza  # Importar función para confian

def page_1():
        # Título de la página principal
    st.title("Carga de Datos y Procesamiento")

    # Subir archivo ZIP
    uploaded_file = st.file_uploader("Cargar archivo ZIP", type=["zip"])

    # Verificar si se ha cargado un archivo
    if uploaded_file is not None:
        # Crear una instancia de ZipFile para leer el archivo cargado
        with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
            # Listar todos los archivos dentro del zip
            file_list = zip_ref.namelist()
            st.write("Archivos dentro del ZIP:", file_list)

            # Buscar la carpeta dentro del ZIP (en este caso, cualquier carpeta dentro)
            folder_name = None
            for file in file_list:
                if file.endswith("/"):  # Carpeta
                    folder_name = file
                    break

            if folder_name:
                # Ahora, buscar el archivo CSV dentro de esa carpeta
                csv_file = None
                for file in file_list:
                    if file.startswith(folder_name) and file.endswith(".csv"):
                        csv_file = file
                        break

                if csv_file:
                     
                    # Extraer el archivo CSV desde el ZIP y leerlo en un DataFrame
                    with zip_ref.open(csv_file) as f:
                        columnas_geografia = [
                            "NOMBREDD", "NOMBREPP", "NOMBREDI",
                            "CCDD", "CCPP", "CCDI"
                        ]

                        columnas_peso = [
                            "FACTOR"
                        ]

                        columnas_confianza_declarada = [
                            "P608_1", "P608_2", "P608_3", "P608_4"
                        ]

                        columnas_desempeno = [
                            "P612_1", "P612_2", "P612_3", "P612_4", "P613"
                        ]

                        columnas_presencia_existencia = [
                            "P642_1", "P642_2", "P642_3"
                        ]

                        columnas_presencia_calidad = [
                            "P643_1", "P643_2", "P643_3"
                        ]

                        columnas_presencia_meses = [
                            "P644_1", "P644_2", "P644_3"
                        ]

                        columnas_expectativa = [
                            f"P601_{i}" for i in range(1, 17)  # por seguridad, capturamos P601_1 hasta P601_19
                        ]

                        columnas_inseguridad_directa = [
                            "P602",  # inseguridad en barrio
                            "P604",  # inseguridad de noche
                            "P605"   # inseguridad de día
                        ]	

                        columnas_lugares = [
                            f"P606_{i}" for i in range(1, 11)   # por seguridad, P606_1 a P606_39
                        ]


                        # 3) Columnas P615 (bandera: fue víctima 1=Sí 2=No)
                        # (capturamos un rango amplio para seguridad)
                        # --------------------------
                        columnas_p615 = ['P615_1', 'P615_2', 'P615_3', 'P615_4', 'P615_5', 
                        'P615_6', 'P615_7', 'P615_8', 'P615_9', 'P615_10', 'P615_11', 'P615_12', 
                        'P615_13', 'P615_14', 'P615_15', 'P615_16', 'P615_17', 'P615_18', 'P615_19', 
                        'P615_20', 'P615_21', 'P615_22', 'P615_23', 'P615_24', 'P615_25', 'P615_26', 'P615_27', 'P615_28']


                        # --------------------------
                        # 4) Columnas P616 (conteo: nº de veces)
                        # (mismo rango amplio)
                        # --------------------------
                        columnas_p616 = ['P616_1', 'P616_2', 'P616_3', 'P616_4', 'P616_5', 
                        'P616_6', 'P616_7', 'P616_8', 'P616_9', 'P616_10', 'P616_11', 'P616_12', 
                        'P616_13', 'P616_14', 'P616_15', 'P616_16', 'P616_17', 'P616_18', 
                        'P616_19', 'P616_20', 'P616_21', 'P616_22', 'P616_23', 'P616_24', 
                        'P616_25', 'P616_26', 'P616_27', 'P616_28']


                        columnas_requeridas = (
                            columnas_geografia
                            + columnas_peso
                            + columnas_confianza_declarada
                            + columnas_desempeno
                            + columnas_presencia_existencia
                            + columnas_presencia_calidad
                            + columnas_presencia_meses
                            + columnas_expectativa
                            + columnas_inseguridad_directa
                            + columnas_lugares
                            +columnas_p615
                            +columnas_p616)


                        df = pd.read_csv(
                            f,
                            usecols=columnas_requeridas,   # SOLO las que necesitas
                            low_memory=False
                        )

                    
                    # Mostrar los primeros registros del archivo cargado solo si no se ha procesado
                    if 'df_processed' not in st.session_state:
                        st.write(f"Datos cargados desde: {csv_file}")
                        #st.dataframe(df.head())

                    # Botón para procesar el CSV
                    if st.button("Procesar Datos"):
                        # Llamar a las funciones de procesamiento para las tres dimensiones, pasando el DataFrame directamente
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

                        # Crear df_completo con todos los datos procesados
                        df_completo = pd.merge(dist_segmentado_victimizacion, dist_segmentado_percepcion, on="NOMBREDI", how="left")
                        df_completo = pd.merge(df_completo, distritos_confianza, on="NOMBREDI", how="left")

                        # Exportar los DataFrames procesados a CSV
                        with tempfile.NamedTemporaryFile(delete=False, mode="w", newline="") as temp_file:
                            df_final.to_csv(temp_file.name, index=False)
                            st.session_state.df_final_path = temp_file.name  # Guardamos el path temporal en session_state

                        with tempfile.NamedTemporaryFile(delete=False, mode="w", newline="") as temp_file:
                            df_completo.to_csv(temp_file.name, index=False)
                            st.session_state.df_completo_path = temp_file.name  # Guardamos el path temporal en session_state

                        # Liberar la memoria del DataFrame original
                        del df

                        # Guardar los datos procesados en el session state para que se usen en la página de visualización
                        st.session_state.df_final = df_final
                        st.session_state.df_completo = df_completo

                        # Mostrar el DataFrame final con las tres métricas
                        st.write("Datos finales procesados (principal):")
                        st.dataframe(df_final)

                        # Mostrar el DataFrame completo con todas las métricas
                        st.write("Datos completos procesados:")
                        st.dataframe(df_completo)

                        st.success("Datos procesados exitosamente. Puedes ir a la página de visualización para ver los resultados.")
                        
                        # Botón para descargar los archivos CSV
                        st.download_button(
                            label="Descargar CSV de Datos Finales",
                            data=open(st.session_state.df_final_path, 'rb').read(),
                            file_name="df_final.csv",
                            mime="text/csv"
                        )

                        st.download_button(
                            label="Descargar CSV de Datos Completos",
                            data=open(st.session_state.df_completo_path, 'rb').read(),
                            file_name="df_completo.csv",
                            mime="text/csv"
                        )

                        # Botón para redirigir a la página de visualización (usando `st.session_state`)
                        if st.button("Ir a la página de visualización"):
                            st.session_state.step = 2
                            st.experimental_rerun()  # Esto recarga la página y muestra los datos procesados en la visualización
                                

