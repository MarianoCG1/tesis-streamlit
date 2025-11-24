import pandas as pd
import numpy as np
import re
import unicodedata

# =========================
# 1) Cargar datos
# =========================
def cargar_y_procesar_datos_victimizacion(archivo_o_df):
    if isinstance(archivo_o_df, bytes):  # Si es un archivo CSV
        df = pd.read_csv(archivo_o_df, low_memory=False)
    elif isinstance(archivo_o_df, pd.DataFrame):  # Si es un DataFrame
        df = archivo_o_df
    else:
        raise ValueError("El parámetro debe ser un archivo CSV o un DataFrame")

    # -------------------------
    # Utilidades de normalización
    # -------------------------
    def _norm(s):
        if pd.isna(s):
            return s
        s = str(s)
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        return s.strip().upper()

    # Normalizar nombres si existen
    for c in ["NOMBREDD", "NOMBREPP", "NOMBREDI"]:
        if c in df.columns:
            df[c] = df[c].map(_norm)

    # Asegurar códigos con cero a la izquierda si existen
    for c in ["CCDD", "CCPP", "CCDI"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.zfill(2)

    # =========================
    # 2) Filtro Lima Metropolitana (Depto 15, Prov 01)
    # =========================
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

    mask_lima_metro = is_lima_dept & is_lima_prov
    df = df.loc[mask_lima_metro].copy()

    # =========================
    # 3) Variables geográficas y pesos (geografía distrital)
    # =========================
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

    # Peso muestral
    weight_candidates = [c for c in df.columns if re.search(r"(FACTOR|PESO|EXPAN|PONDER)", c, re.IGNORECASE)]
    weight_col = weight_candidates[0] if weight_candidates else None

    # =========================
    # 4) Detectar columnas de victimización
    # =========================
    p615_cols = [c for c in df.columns if re.fullmatch(r"P615_\d+", c)]
    p616_cols = [c for c in df.columns if re.fullmatch(r"P616_\d+", c)]
    victim_ids = sorted(set(int(c.split("_")[1]) for c in (p615_cols + p616_cols)))

    # =========================
    # 5) Recodificar prevalencias (por tipo de delito)
    # =========================
    prev_cols = []
    for i in victim_ids:
        c_count = f"P616_{i}"   # número de veces
        c_flag  = f"P615_{i}"   # si fue víctima (1=Sí, 2=No) según INEI
        colname = f"VIC_{i:02d}"

        # Base NaN
        v = pd.Series(np.nan, index=df.index, dtype=float)

        # Primero intentamos con el conteo P616_i (>=1 => 1; 0 => 0)
        if c_count in df.columns:
            v = np.where(df[c_count] >= 1, 1.0,
                np.where(df[c_count] == 0, 0.0, np.nan))

        # Si hay bandera P615_i, completamos donde todavía hay NaN
        if c_flag in df.columns:
            v = np.where(pd.isna(v) & (df[c_flag] == 1), 1.0, v)
            v = np.where(pd.isna(v) & (df[c_flag] == 2), 0.0, v)

        df[colname] = v
        prev_cols.append(colname)

    # =========================
    # 6) Victimización total (≥1 evento)
    # =========================
    df["VIC_ANY"] = df[prev_cols].max(axis=1, skipna=True)

    def weighted_mean(series, weights):
        mask = series.notna()
        if weights is not None:
            mask = mask & weights.notna()
        if mask.sum() == 0:
            return np.nan
        return np.average(series[mask], weights=weights[mask] if weights is not None else None)

    # Agrupador por distrito
    grouped = df.groupby(geo_col, dropna=False) if geo_col else None

    # =========================
    # 7) Agregación distrital: total y por tipo de delito
    # =========================
    if grouped is not None:
        if weight_col:
            dist_total = grouped.apply(lambda g: weighted_mean(g["VIC_ANY"], g[weight_col]) * 100)
            dist_bytype = pd.DataFrame({
                c: grouped.apply(lambda g, col=c: weighted_mean(g[col], g[weight_col]) * 100)
                for c in prev_cols
            })
        else:
            dist_total = grouped["VIC_ANY"].mean() * 100
            dist_bytype = grouped[prev_cols].mean() * 100

        dist_total = dist_total.rename("Victimizacion_total_%").reset_index()
        dist_bytype = dist_bytype.reset_index()
    else:
        dist_total = pd.DataFrame(columns=["__NO_GEO__", "Victimizacion_total_%"])
        dist_bytype = pd.DataFrame(columns=["__NO_GEO__"] + prev_cols)

    # =========================
    # 8) Grupos (patrimoniales / no patrimoniales / informáticos / vandalismo)
    # =========================
    patrimoniales    = [f"VIC_{i:02d}" for i in range(1, 14)]    # 01–13
    no_patrimoniales = [f"VIC_{i:02d}" for i in range(14, 23)]   # 14–22
    informaticos     = [f"VIC_{i:02d}" for i in range(23, 29)]   # 23–28
    vandalismo       = ["VIC_13"]  # ejemplo: abigeato/daños; muévelo si tu mapeo lo requiere

    df["VIC_PATRIMONIAL"]    = df[patrimoniales].max(axis=1, skipna=True)    if set(patrimoniales)    <= set(df.columns) else np.nan
    df["VIC_NOPATRIMONIAL"]  = df[no_patrimoniales].max(axis=1, skipna=True) if set(no_patrimoniales) <= set(df.columns) else np.nan
    df["VIC_INFORMATICO"]    = df[informaticos].max(axis=1, skipna=True)     if set(informaticos)     <= set(df.columns) else np.nan
    df["VIC_VANDALISMO"]     = df[vandalismo].max(axis=1, skipna=True)       if set(vandalismo)       <= set(df.columns) else np.nan

    if grouped is not None:
        if weight_col:
            dist_segmentado = grouped.apply(lambda g: pd.Series({
                "Victimizacion_patrimonial_%":     weighted_mean(g["VIC_PATRIMONIAL"],   g[weight_col]) * 100,
                "Victimizacion_no_patrimonial_%":  weighted_mean(g["VIC_NOPATRIMONIAL"], g[weight_col]) * 100,
                "Victimizacion_informatico_%":     weighted_mean(g["VIC_INFORMATICO"],   g[weight_col]) * 100,
                "Victimizacion_vandalismo_%":      weighted_mean(g["VIC_VANDALISMO"],    g[weight_col]) * 100
            }))
        else:
            dist_segmentado = grouped[["VIC_PATRIMONIAL", "VIC_NOPATRIMONIAL", "VIC_INFORMATICO", "VIC_VANDALISMO"]].mean() * 100
            dist_segmentado = dist_segmentado.rename(columns={
                "VIC_PATRIMONIAL":    "Victimizacion_patrimonial_%",
                "VIC_NOPATRIMONIAL":  "Victimizacion_no_patrimonial_%",
                "VIC_INFORMATICO":    "Victimizacion_informatico_%",
                "VIC_VANDALISMO":     "Victimizacion_vandalismo_%"
            })
        dist_segmentado = dist_segmentado.reset_index()
    else:
        dist_segmentado = pd.DataFrame(columns=["__NO_GEO__", "Victimizacion_patrimonial_%", "Victimizacion_no_patrimonial_%", "Victimizacion_informatico_%", "Victimizacion_vandalismo_%"])

    # =========================
    # 9) Retornar los resultados
    # =========================
    return dist_total, dist_segmentado