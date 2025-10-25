# app.py
# Versión final para usar los CSVs correctamente, melt por años, y matching de países robusto.
import streamlit as st
import pandas as pd
import plotly.express as px
import json
from pathlib import Path
from difflib import get_close_matches
import re
import unicodedata

# -------------------------
# Config
# -------------------------
BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
st.set_page_config(page_title="Coffee World Map", layout="wide")

# -------------------------
# Utilidades
# -------------------------
@st.cache_data
def load_geojson(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def load_csv(path: Path):
    return pd.read_csv(path)

def strip_accents(s: str) -> str:
    if not isinstance(s, str):
        return s
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join([c for c in nfkd if not unicodedata.combining(c)])

def normalize_name_for_match(s: str) -> str:
    """Normaliza un nombre quitando acentos, paréntesis, artículos comunes, puntuación y lowercasing."""
    if not isinstance(s, str):
        return ""
    s = s.strip()
    s = re.sub(r'\(.*?\)', '', s)                # quitar paréntesis y su contenido
    s = strip_accents(s)                         # quitar acentos
    s = s.replace('&', 'and')
    s = s.replace('-', ' ')
    s = s.replace('/', ' ')
    s = re.sub(r'[^0-9A-Za-z\s]', '', s)         # dejar solo alfanumérico y espacios
    s = re.sub(r'\b(the|of|and|de|del|la|el|plurinational|state)\b', '', s, flags=re.I)
    s = re.sub(r'\s+', ' ', s)                   # compactar espacios
    return s.strip().lower()

def detect_country_column(df: pd.DataFrame) -> str:
    candidates = ["Country", "country", "Country or Area", "Country or area", "Country/Area", "country/area",
                  "Country or Area", "Country name"]
    for c in candidates:
        if c in df.columns:
            return c
    # fallback heurístico: columna object con muchos valores alfabéticos
    for c in df.columns:
        if df[c].dtype == object:
            sample = df[c].dropna().astype(str).head(20).tolist()
            alpha_ratio = sum(1 for v in sample if re.search(r'[A-Za-z]', v)) / max(1, len(sample))
            if alpha_ratio > 0.6:
                return c
    return None

def detect_year_columns(columns) -> list:
    """Detecta columnas que parezcan años (1990, 1990/91, 1990-91, etc.)"""
    year_regex = re.compile(r'^\s*\d{4}(\s*[-/]\s*\d{2,4})?\s*$')
    return [c for c in columns if isinstance(c, str) and year_regex.match(c.strip())]

def year_label_to_int(label: str) -> int:
    """Extrae el año inicial como entero para ordenar: '1990/91'->1990, '1990'->1990"""
    if not isinstance(label, str):
        return 9999
    m = re.match(r'^\s*(\d{4})', label)
    return int(m.group(1)) if m else 9999

def build_country_map(csv_countries, geo_countries, cutoff=0.7):
    """
    Crea un mapping csv_name -> geo_name intentando:
    1) match exacto
    2) match por normalized name exacto
    3) fuzzy match sobre normalized names
    """
    geo_norm = {n: normalize_name_for_match(n) for n in geo_countries}
    norm_to_geo = {}
    for geo, n in geo_norm.items():
        if n:
            norm_to_geo.setdefault(n, []).append(geo)

    mapping = {}
    for c in csv_countries:
        if c in geo_countries:
            mapping[c] = c
            continue
        c_norm = normalize_name_for_match(c)
        # try normalized exact
        if c_norm in norm_to_geo:
            # si hay múltiples geo con mismo normalized, elegimos el primero (mejorar manualmente si falla)
            mapping[c] = norm_to_geo[c_norm][0]
            continue
        # fuzzy match on normalized
        choices = list(norm_to_geo.keys())
        best = get_close_matches(c_norm, choices, n=1, cutoff=cutoff)
        if best:
            mapping[c] = norm_to_geo[best[0]][0]
        else:
            mapping[c] = None
    return mapping

# -------------------------
# Cargar geojson y nombres
# -------------------------
geojson_path = DATA_DIR / "countries.geo.json"
countries_geo = load_geojson(geojson_path)

# extraer nombres desde properties (varias claves posibles)
geo_names = []
for feat in countries_geo.get("features", []):
    prop = feat.get("properties", {})
    name = prop.get("name") or prop.get("NAME") or prop.get("ADMIN") or prop.get("ADMIN_NAME") or prop.get("Country")
    if name:
        geo_names.append(name)

# -------------------------
# Archivos (solo 3 métricas)
# -------------------------
FILES = {
    "Producción": DATA_DIR / "Coffee_production.csv",
    "Consumo": DATA_DIR / "Coffee_domestic_consumption.csv",
    "Exportación": DATA_DIR / "Coffee_export.csv",
}

# -------------------------
# Sidebar (UI)
# -------------------------
st.sidebar.title("Coffee World Map")
st.sidebar.markdown("### Filtros")

metric = st.sidebar.selectbox("Seleccionar Métrica:", list(FILES.keys()))

# Cargar CSV de la métrica seleccionada
csv_path = FILES[metric]
df_raw = load_csv(csv_path)

# detectar y renombrar columna Country a 'Country' si necesario
country_col = detect_country_column(df_raw)
if not country_col:
    st.error("No fue posible detectar la columna de país en el CSV. Revisa el archivo.")
    st.stop()
if country_col != "Country":
    df_raw = df_raw.rename(columns={country_col: "Country"})

# uniformizar 'Coffee Type' columna
if "Coffee Type" in df_raw.columns and "Coffee type" not in df_raw.columns:
    df_raw = df_raw.rename(columns={"Coffee Type": "Coffee type"})
if "Coffee type" in df_raw.columns:
    df_raw["Coffee type"] = df_raw["Coffee type"].astype(str).apply(lambda x: x.strip() if pd.notna(x) else x)
    df_raw["Coffee type"] = df_raw["Coffee type"].replace({
        "Arabica/Robusta": "Robusta/Arabica",
        "Arabica / Robusta": "Robusta/Arabica",
        "Robusta / Arabica": "Robusta/Arabica",
    })

# detectar columnas de años robustamente
year_cols = detect_year_columns(df_raw.columns)
if not year_cols:
    st.error("No se detectaron columnas de año en el CSV seleccionado.")
    st.stop()

# Hacer melt (wide -> long) para asegurar que cada fila sea Country | Coffee type? | year_label | value
id_vars = ["Country"]
if "Coffee type" in df_raw.columns:
    id_vars.append("Coffee type")

df_long = df_raw.melt(id_vars=id_vars, value_vars=year_cols, var_name="year_label", value_name="value")

# convertir numeric
df_long["value"] = pd.to_numeric(df_long["value"], errors="coerce")
df_long["year_int"] = df_long["year_label"].apply(year_label_to_int)
df_long["Country"] = df_long["Country"].astype(str).str.strip()

# orden de años para selector
years_ordered = (df_long[["year_label","year_int"]].drop_duplicates().sort_values("year_int")["year_label"].tolist())
selected_year = st.sidebar.selectbox("Seleccionar Año:", years_ordered, index=len(years_ordered)-1)

# tipos de café para selector (forzar orden preferido)
if "Coffee type" in df_long.columns:
    types_present = sorted(df_long["Coffee type"].dropna().unique().tolist())
    preferred = ["Todos"] + [t for t in ["Arabica","Robusta","Robusta/Arabica"] if t in types_present]
    for t in types_present:
        if t not in preferred:
            preferred.append(t)
    selected_type = st.sidebar.selectbox("Seleccionar Tipo de Café:", preferred, index=0)
else:
    selected_type = "Todos"

# -------------------------
# Filtrar por año y tipo
# -------------------------
mask = df_long["year_label"] == selected_year
if selected_type != "Todos" and "Coffee type" in df_long.columns:
    mask = mask & (df_long["Coffee type"].fillna("").str.strip().str.lower() == selected_type.strip().lower())

df_filtered = df_long[mask].copy()

# agrupar por país
map_df = df_filtered.groupby("Country", as_index=False)["value"].sum()
# si un país no aparece en df_filtered, no estará en map_df -> eso es correcto (no hay dato)

# -------------------------
# Emparejar nombres de países de forma robusta y silenciosa
# -------------------------
csv_countries = map_df["Country"].dropna().unique().tolist()
country_map = build_country_map(csv_countries, geo_names, cutoff=0.7)
map_df["geo_name"] = map_df["Country"].map(country_map)

# usar geo_name si existe, si no dejar el Country (Plotly no encontrará la geo feature y quedará gris)
map_df["plot_location"] = map_df["geo_name"].where(map_df["geo_name"].notna(), map_df["Country"])

# -------------------------
# Construir mapa
# -------------------------
fig = px.choropleth(
    map_df,
    geojson=countries_geo,
    locations="plot_location",
    featureidkey="properties.name",
    color="value",
    hover_name="Country",
    projection="natural earth",
    title=f"{metric} - {selected_year}" + (f" ({selected_type})" if selected_type != "Todos" else "")
)

fig.update_geos(showcountries=True, showcoastlines=True, showland=True)
fig.update_layout(margin={"r":0,"t":60,"l":0,"b":0}, coloraxis_colorbar=dict(title="Valor"))

# -------------------------
# Interfaz final (sin tablas extras)
# -------------------------
st.markdown("## ☕ Coffee World Map")
st.write(f"**Métrica:** {metric}    •    **Año:** {selected_year}" + (f"    •    **Tipo:** {selected_type}" if selected_type != "Todos" else ""))
st.plotly_chart(fig, use_container_width=True)
