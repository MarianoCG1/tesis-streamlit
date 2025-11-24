# utils/geo_processing.py
import pandas as pd
import geopandas as gpd
from unidecode import unidecode
import io

def cargar_y_preparar_datos(csv_input):
    """
    Carga el GeoJSON de Lima, normaliza nombres y hace merge con el CSV.
    
    Parámetro csv_input puede ser:
        - str: ruta al archivo CSV
        - pd.DataFrame
        - UploadedFile (Streamlit)
    """

    # ---------- 1) Cargar GeoJSON ----------
    url = "https://raw.githubusercontent.com/juaneladio/peru-geojson/master/peru_distrital_simple.geojson"
    gdf = gpd.read_file(url)

    gdf_lima_metro = gdf[
        (gdf["NOMBDEP"].str.upper() == "LIMA") &
        (gdf["NOMBPROV"].str.upper() == "LIMA")
    ][["NOMBDIST", "geometry"]].copy()

    # ---------- 2) Interpretar el CSV según el tipo recibido ----------
    if isinstance(csv_input, str):
        # Ruta al archivo
        df_raw = pd.read_csv(csv_input).copy()

    elif isinstance(csv_input, pd.DataFrame):
        # Ya es un DataFrame
        df_raw = csv_input.copy()

    elif hasattr(csv_input, "read"):
        # Caso Streamlit UploadedFile: leer el buffer
        df_raw = pd.read_csv(io.BytesIO(csv_input.read())).copy()

    else:
        raise ValueError(
            "csv_input debe ser: ruta (str), DataFrame o UploadedFile de Streamlit."
        )

    # ---------- 3) Verificar la columna de distrito ----------
    if "NOMBREDI" in df_raw.columns:
        name_col = "NOMBREDI"
    elif "NOMBDIST" in df_raw.columns:
        name_col = "NOMBDIST"
    else:
        raise ValueError("El CSV debe contener 'NOMBREDI' o 'NOMBDIST'.")

    # ---------- 4) Verificar métricas ----------
    metric_cols = [
        "Victimizacion_total_%",
        "Inseguridad_general_%",
        "Indice_confianza_PNP_%"
    ]

    missing = [c for c in metric_cols if c not in df_raw.columns]
    if missing:
        raise ValueError(f"Faltan columnas métricas en el CSV: {missing}")

    # ---------- 5) Normalizar nombres ----------
    def norm(s):
        return unidecode(str(s).strip().upper())

    gdf_lima_metro["_MERGE_KEY"] = gdf_lima_metro["NOMBDIST"].map(norm)
    df_raw["_MERGE_KEY"] = df_raw[name_col].map(norm)

    alias = {
        "MAGDALENA VIEJA": "PUEBLO LIBRE",
        "BREÑA": "BRENA",
        "RÍMAC": "RIMAC",
        "JESÚS MARÍA": "JESUS MARIA",
        "SAN MARTÍN DE PORRES": "SAN MARTIN DE PORRES",
        "SANTIAGO DE SURCO": "SANTIAGO DE SURCO"
    }
    alias_norm = {norm(k): norm(v) for k, v in alias.items()}
    gdf_lima_metro["_MERGE_KEY"] = gdf_lima_metro["_MERGE_KEY"].replace(alias_norm)

    # ---------- 6) Merge ----------
    df_to_merge = df_raw[["_MERGE_KEY"] + metric_cols].copy()
    gdfm = gdf_lima_metro.merge(
        df_to_merge,
        on="_MERGE_KEY",
        how="left",
        validate="1:1"
    )

    # ---------- 7) Mantener columnas finales ----------
    gdfm = gdfm[["NOMBDIST", "geometry"] + metric_cols].copy()

    # Asegurar métricas numéricas
    for c in metric_cols:
        gdfm[c] = pd.to_numeric(gdfm[c], errors="coerce")

    return gdfm
