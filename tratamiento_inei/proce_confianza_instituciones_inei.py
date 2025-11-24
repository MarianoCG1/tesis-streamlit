import pandas as pd
import numpy as np
import re
import unicodedata

# =========================
# 1) Cargar datos
# =========================
def cargar_y_procesar_datos_confianza(archivo_o_df):
    # Verificar si el parámetro es un archivo CSV (tipo BytesIO) o ya un DataFrame
    if isinstance(archivo_o_df, bytes):  # Si es un archivo en memoria (Streamlit)
        df = pd.read_csv(archivo_o_df, low_memory=False)
    elif isinstance(archivo_o_df, pd.DataFrame):  # Si ya es un DataFrame
        df = archivo_o_df
    else:
        raise ValueError("El parámetro debe ser un archivo CSV o un DataFrame")

    # =========================
    # Utilidades de normalización
    # =========================
    def _norm(s):
        if pd.isna(s): return s
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

    df = df.loc[is_lima_dept & is_lima_prov].copy()

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

    weight_candidates = [c for c in df.columns if re.search(r"(FACTOR|PESO|EXPAN|PONDER)", c, re.IGNORECASE)]
    weight_col = weight_candidates[0] if weight_candidates else None

    # =========================
    # 4) Función weighted mean
    # =========================
    def wmean(x, w):
        x = pd.to_numeric(x, errors="coerce")
        w = pd.to_numeric(w, errors="coerce")
        m = x.notna() & w.notna()
        if m.sum() == 0: return np.nan
        return np.average(x[m], weights=w[m])

    # =========================
    # 5) Selección de columnas PNP
    # =========================
    p608_cols = [c for c in df.columns if re.fullmatch(r"P608_\d+", c)]
    p612_cols = [c for c in df.columns if re.fullmatch(r"P612_\d+", c)]
    p613_col  = "P613" if "P613" in df.columns else None
    p642_cols = [c for c in df.columns if re.fullmatch(r"P642_\d+", c)]
    p643_cols = [c for c in df.columns if re.fullmatch(r"P643_\d+", c)]
    p644_cols = [c for c in df.columns if re.fullmatch(r"P644_\d+", c)]

    def take(cols, suffix="_1"):
        cands = [c for c in cols if c.endswith(suffix)]
        return cands[0] if cands else (cols[0] if cols else None)

    CONF_PNP = take(p608_cols, "_1")
    PRES_EX  = take(p642_cols, "_1")
    PRES_CAL = take(p643_cols, "_1")
    PRES_MES = take(p644_cols, "_1")
    DESEMP_IT = [c for c in p612_cols if re.fullmatch(r"P612_[1-4]", c)]
    if p613_col: DESEMP_IT += [p613_col]

    # =========================
    # 6) Recodificación binaria
    # =========================
    if CONF_PNP:
        df["CONF_DECL_PNP_BIN"] = df[CONF_PNP].replace({3:1,4:1,1:0,2:0})
        df["CONF_DECL_PNP_BIN"] = df["CONF_DECL_PNP_BIN"].where(df[CONF_PNP].isin([1,2,3,4]), np.nan)

    desemp_bin_cols = []
    for c in DESEMP_IT:
        b = df[c].replace({3:1,4:1,1:0,2:0})
        b = b.where(df[c].isin([1,2,3,4]), np.nan)
        df[c+"_BIN"] = b
        desemp_bin_cols.append(c+"_BIN")

    if PRES_EX:
        df["PRES_EXISTE_PNP_BIN"] = df[PRES_EX].replace({1:1,2:0}).where(df[PRES_EX].isin([1,2]), np.nan)
    if PRES_CAL:
        df["PRES_CAL_POS_BIN"] = df[PRES_CAL].replace({3:1,4:1,1:0,2:0}).where(df[PRES_CAL].isin([1,2,3,4]), np.nan)
    if PRES_MES:
        df["PRES_MES_BIN"] = df[PRES_MES].replace({1:1,2:0}).where(df[PRES_MES].isin([1,2]), np.nan)

    df["PRES_COMPUESTO_ESTRICTO"] = np.nan
    if "PRES_EXISTE_PNP_BIN" in df and "PRES_CAL_POS_BIN" in df:
        both = (df["PRES_EXISTE_PNP_BIN"] == 1) & (df["PRES_CAL_POS_BIN"] == 1)
        zero = (df["PRES_EXISTE_PNP_BIN"] == 0) | (df["PRES_CAL_POS_BIN"] == 0)
        out = pd.Series(np.nan, index=df.index, dtype=float)
        out[both] = 1.0
        out[zero] = 0.0
        df["PRES_COMPUESTO_ESTRICTO"] = out

    # =========================
    # 7) Índice confianza PNP
    # =========================
    comp_series = []
    if "CONF_DECL_PNP_BIN" in df: comp_series.append(df["CONF_DECL_PNP_BIN"].astype(float))
    if len(desemp_bin_cols) > 0:
        desempeno_prom = df[desemp_bin_cols].mean(axis=1, skipna=True)
        desempeno_prom[pd.isna(df[desemp_bin_cols]).all(axis=1)] = np.nan
        comp_series.append(desempeno_prom)
    if "PRES_COMPUESTO_ESTRICTO" in df: comp_series.append(df["PRES_COMPUESTO_ESTRICTO"].astype(float))

    df["INDICE_CONFIANZA_PNP"] = pd.concat(comp_series, axis=1).mean(axis=1, skipna=True)

    # =========================
    # 8) Agregación distrital
    # =========================
    cols_detalle = []
    if "CONF_DECL_PNP_BIN" in df: cols_detalle.append(("CONF_DECL_PNP_%","CONF_DECL_PNP_BIN"))
    for c in desemp_bin_cols:
        cols_detalle.append((f"{c.replace('_BIN','')}_% (positivo)", c))
    if "PRES_EXISTE_PNP_BIN" in df: cols_detalle.append(("PRES_EXISTE_PNP_%","PRES_EXISTE_PNP_BIN"))
    if "PRES_CAL_POS_BIN"   in df: cols_detalle.append(("PRES_CAL_POS_%","PRES_CAL_POS_BIN"))
    if "PRES_MES_BIN"       in df: cols_detalle.append(("PRES_MES_%","PRES_MES_BIN"))

    def agg_weighted(g, cols):
        res = {}
        for outname, col in cols:
            res[outname] = wmean(g[col], g[weight_col]) * 100 if weight_col else g[col].mean() * 100
        res["Indice_confianza_PNP_%"] = wmean(g["INDICE_CONFIANZA_PNP"], g[weight_col]) * 100 if weight_col else g["INDICE_CONFIANZA_PNP"].mean() * 100
        if "PRES_COMPUESTO_ESTRICTO" in g:
            res["Presencia_compuesto_estricto_%"] = wmean(g["PRES_COMPUESTO_ESTRICTO"], g[weight_col]) * 100 if weight_col else g["PRES_COMPUESTO_ESTRICTO"].mean() * 100
        return pd.Series(res)

    if geo_col:
        distritos_confianza = df.groupby(geo_col).apply(lambda g: agg_weighted(g, cols_detalle)).reset_index()
    else:
        distritos_confianza = pd.DataFrame()

    # =========================
    # 9) Exportar resultados
    # =========================
    #distritos_confianza.to_csv("confianza_pnp_distrito_lima.csv", index=False)

    return distritos_confianza
