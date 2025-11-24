import pandas as pd
import numpy as np
import re
import unicodedata

# -------------------------
# Utilidades
# -------------------------
def _norm(s):
    if pd.isna(s): return s
    s = str(s)
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")
    return s.strip().upper()

def weighted_mean(series, weights):
    """Promedio ponderado ignorando NAs."""
    s = pd.to_numeric(series, errors="coerce")
    if weights is None:
        return s.mean()
    w = pd.to_numeric(weights, errors="coerce")
    m = s.notna() & w.notna()
    if m.sum() == 0:
        return np.nan
    return np.average(s[m], weights=w[m])

def row_or(a, b):
    # OR con soporte a NAs
    x = pd.concat([a, b], axis=1)
    one = (x == 1).any(axis=1)
    zero = (x == 0).all(axis=1)
    out = pd.Series(np.nan, index=a.index, dtype=float)
    out[one] = 1.0
    out[zero] = 0.0
    return out

# -------------------------
# Función de Procesamiento: Cargar y procesar datos
# -------------------------
def cargar_y_procesar_datos_percepcion(archivo_o_df):
    # Verificar si el parámetro es un archivo CSV (tipo BytesIO) o ya un DataFrame
    if isinstance(archivo_o_df, bytes):  # Si es un archivo en memoria (Streamlit)
        df = pd.read_csv(archivo_o_df, low_memory=False)
    elif isinstance(archivo_o_df, pd.DataFrame):  # Si ya es un DataFrame
        df = archivo_o_df
    else:
        raise ValueError("El parámetro debe ser un archivo CSV o un DataFrame")

    # Normalizar nombres y códigos geográficos
    for c in ["NOMBREDD", "NOMBREPP", "NOMBREDI"]:
        if c in df.columns:
            df[c] = df[c].map(_norm)

    for c in ["CCDD", "CCPP", "CCDI"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.zfill(2)

    # -------------------------
    # 2) Filtro Lima Metropolitana (Depto 15, Prov 01)
    # -------------------------
    is_lima_dept = False
    if "CCDD" in df.columns:
        is_lima_dept = df["CCDD"].eq("15")
    if "NOMBREDD" in df.columns:
        is_lima_dept = is_lima_dept | df["NOMBREDD"].eq("LIMA")

    is_lima_prov = False
    if "CCPP" in df.columns:
        is_lima_prov = df["CCPP"].eq("01")
    if "NOMBREPP" in df.columns:
        is_lima_prov = is_lima_prov | df["NOMBREPP"].eq("LIMA")

    df = df.loc[is_lima_dept & is_lima_prov].copy()

    # -------------------------
    # 3) Variables geográficas y pesos
    # -------------------------
    if "NOMBREDI" in df.columns and df["NOMBREDI"].notna().any():
        geo_col = "NOMBREDI"
    elif "CCDI" in df.columns:
        geo_col = "CCDI"
    else:
        if all(c in df.columns for c in ["CCDD", "CCPP", "CCDI"]):
            df["ID_DISTRITO"] = df["CCDD"] + df["CCPP"] + df["CCDI"]
            geo_col = "ID_DISTRITO"
        else:
            geo_col = None  

    weight_candidates = [c for c in df.columns if re.search(r"(FACTOR|PESO|EXPAN|PONDER)", c, re.IGNORECASE)]
    weight_col = weight_candidates[0] if weight_candidates else None

    # ----------------------------------------------------
    # 4) Recodificaciones – Percepción
    # ----------------------------------------------------
    # A) Expectativa de ser víctima (P601_*)
    p601_cols = [c for c in df.columns if re.fullmatch(r"P601_\d+", c)]
    for c in p601_cols:
        df[c] = df[c].replace({1:1, 2:0})
        df[c] = df[c].where(df[c].isin([0,1]), np.nan)

    # Usamos el promedio (no el max)
    df["PERCEPCION_EXPECTATIVA"] = df[p601_cols].mean(axis=1, skipna=True) if p601_cols else np.nan

    # B) Barrio / Día / Noche
    MAP_INSEG = {1:1, 2:1, 3:0, 4:0}
    for c in ["P602", "P604", "P605"]:
        if c in df.columns:
            df[c+"_BIN"] = df[c].map(MAP_INSEG)
            df[c+"_BIN"] = df[c+"_BIN"].where(df[c].isin([1,2,3,4]), np.nan)

    df["PERCEPCION_BARRIO"] = df["P602_BIN"] if "P602_BIN" in df.columns else np.nan
    df["PERCEPCION_NOCHE"]  = df["P604_BIN"] if "P604_BIN" in df.columns else np.nan
    df["PERCEPCION_DIA"]    = df["P605_BIN"] if "P605_BIN" in df.columns else np.nan

    # C) Lugares/actividades (MEDIA por persona)
    p606_cols = [c for c in df.columns if re.fullmatch(r"P606_\d+", c)]
    p606_bin_cols = []
    for c in p606_cols:
        b = df[c].map(MAP_INSEG)
        b = b.where(df[c].isin([1,2,3,4]), np.nan)
        df[c+"_BIN"] = b
        p606_bin_cols.append(c+"_BIN")

    if p606_bin_cols:
        df["PERCEPCION_LUGARES"] = df[p606_bin_cols].mean(axis=1, skipna=True)
    else:
        df["PERCEPCION_LUGARES"] = np.nan

    # ----------------------------------------------------
    # 5) Agregación distrital (5 métricas “full”)
    # ----------------------------------------------------
    grouped = df.groupby(geo_col, dropna=False)

    if weight_col:
        dist_percepcion = grouped.apply(lambda g: pd.Series({
            "Expectativa_victimizacion_%": weighted_mean(g["PERCEPCION_EXPECTATIVA"], g[weight_col]) * 100,
            "Barrio_inseguro_%":          weighted_mean(g["PERCEPCION_BARRIO"],      g[weight_col]) * 100,
            "Dia_inseguro_%":             weighted_mean(g["PERCEPCION_DIA"],         g[weight_col]) * 100,
            "Noche_inseguro_%":           weighted_mean(g["PERCEPCION_NOCHE"],       g[weight_col]) * 100,
            "Lugares_inseguros_%":        weighted_mean(g["PERCEPCION_LUGARES"],     g[weight_col]) * 100,
        }))
    else:
        dist_percepcion = grouped[[
            "PERCEPCION_EXPECTATIVA","PERCEPCION_BARRIO","PERCEPCION_DIA",
            "PERCEPCION_NOCHE","PERCEPCION_LUGARES"
        ]].mean() * 100

    dist_percepcion = dist_percepcion.reset_index().rename(columns={geo_col:"NOMBREDI"})

    # ----------------------------------------------------
    # 6) Versión segmentada (3 compactos)
    # ----------------------------------------------------
    df["LUGARES_UMBRAL50"] = np.where(df["PERCEPCION_LUGARES"]>=0.5, 1.0,
                               np.where(df["PERCEPCION_LUGARES"]<0.5, 0.0, np.nan))
    df["PERCEPCION_INSEG_GENERAL"] = row_or(df["PERCEPCION_BARRIO"], df["LUGARES_UMBRAL50"])

    if weight_col:
        dist_segmentado = grouped.apply(lambda g: pd.Series({
            "Expectativa_victimizacion_%": weighted_mean(g["PERCEPCION_EXPECTATIVA"],   g[weight_col]) * 100,
            "Inseguridad_general_%":       weighted_mean(g["PERCEPCION_INSEG_GENERAL"], g[weight_col]) * 100,
            "Inseguridad_nocturna_%":      weighted_mean(g["PERCEPCION_NOCHE"],         g[weight_col]) * 100,
        }))
    else:
        dist_segmentado = grouped[[
            "PERCEPCION_EXPECTATIVA","PERCEPCION_INSEG_GENERAL","PERCEPCION_NOCHE"
        ]].mean() * 100

    dist_segmentado = dist_segmentado.reset_index().rename(columns={geo_col:"NOMBREDI"})

    # -------------------------
    # 7) Retornar los resultados
    # -------------------------
    return dist_percepcion, dist_segmentado