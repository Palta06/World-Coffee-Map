import streamlit as st
import pandas as pd
import plotly.express as px
import json
from pathlib import Path
from difflib import get_close_matches
import re
import utils

st.set_page_config(page_title="Coffee World Map", layout="wide")

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"

@st.cache_data
def load_geojson(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def load_csv(path: Path):
    return pd.read_csv(path)


def build_country_map(csv_countries, geo_countries, cutoff=0.7):
    """
    Crea un mapping csv_name -> geo_name intentando:
    1) match exacto
    2) match por normalized name exacto
    3) fuzzy match sobre normalized names
    """
    geo_norm = {n: utils.normalize_name_for_match(n) for n in geo_countries}
    norm_to_geo = {}
    for geo, n in geo_norm.items():
        if n:
            norm_to_geo.setdefault(n, []).append(geo)

    mapping = {}
    for c in csv_countries:
        if c in geo_countries:
            mapping[c] = c
            continue
        c_norm = utils.normalize_name_for_match(c)
       
        if c_norm in norm_to_geo:
           
            mapping[c] = norm_to_geo[c_norm][0]
            continue

        choices = list(norm_to_geo.keys())
        best = get_close_matches(c_norm, choices, n=1, cutoff=cutoff)
        if best:
            mapping[c] = norm_to_geo[best[0]][0]
        else:
            mapping[c] = None
    return mapping


geojson_path = DATA_DIR / "countries.geo.json"
countries_geo = load_geojson(geojson_path)

geo_names = []
for feat in countries_geo.get("features", []):
    prop = feat.get("properties", {})
    name = prop.get("name") or prop.get("NAME") or prop.get("ADMIN") or prop.get("ADMIN_NAME") or prop.get("Country")
    if name:
        geo_names.append(name)

FILES = {
    "Producción": DATA_DIR / "Coffee_production.csv",
    "Consumo": DATA_DIR / "Coffee_domestic_consumption.csv",
    "Exportación": DATA_DIR / "Coffee_export.csv",
}

st.sidebar.title("Coffee World Map")
st.sidebar.markdown("### Filtros")

metric = st.sidebar.selectbox("Seleccionar Métrica:", list(FILES.keys()))

csv_path = FILES[metric]
df_raw = load_csv(csv_path)

country_col = 'Country'
id_vars = [ country_col ]

if "Coffee type" in df_raw.columns:
    df_raw["Coffee type"] = df_raw["Coffee type"].astype(str).apply(lambda x: x.strip() if pd.notna(x) else x)
    df_raw["Coffee type"] = df_raw["Coffee type"].replace({
        "Arabica/Robusta": "Robusta/Arabica",
        "Arabica / Robusta": "Robusta/Arabica",
        "Robusta / Arabica": "Robusta/Arabica",
    })
    id_vars.append("Coffee type")


year_cols = utils.detect_year_columns(df_raw.columns)
if not year_cols:
    st.error("No se detectaron columnas de año en el CSV seleccionado.")
    st.stop()

df_long = df_raw.melt(id_vars=id_vars, value_vars=year_cols, var_name="year_label", value_name="value")

df_long["value"] = pd.to_numeric(df_long["value"], errors="coerce")
df_long["year_int"] = df_long["year_label"].apply(utils.year_label_to_int)
df_long["Country"] = df_long["Country"].astype(str).str.strip()


years_ordered = (df_long[["year_label","year_int"]].drop_duplicates().sort_values("year_int")["year_label"].tolist())
selected_year = st.sidebar.selectbox("Seleccionar Año:", years_ordered, index=len(years_ordered)-1, disabled=True)


if "Coffee type" in df_long.columns:
    types_present = sorted(df_long["Coffee type"].dropna().unique().tolist())
    preferred = [t for t in ["Arabica","Robusta","Robusta/Arabica"] if t in types_present]
    for t in types_present:
        if t not in preferred:
            preferred.append(t)
    selected_type = st.sidebar.selectbox("Seleccionar Tipo de Café:", preferred, index=0)
else:
    selected_type = "Todos"


mask = df_long["year_label"] == selected_year
if selected_type != "Todos" and "Coffee type" in df_long.columns:
    mask = mask & (df_long["Coffee type"].fillna("").str.strip().str.lower() == selected_type.strip().lower())

df_filtered = df_long[mask].copy()
map_df = df_filtered.groupby("Country", as_index=False)["value"].sum()

csv_countries = map_df["Country"].dropna().unique().tolist()
country_map = build_country_map(csv_countries, geo_names, cutoff=0.7)
map_df["geo_name"] = map_df["Country"].map(country_map)


map_df["plot_location"] = map_df["geo_name"].where(map_df["geo_name"].notna(), map_df["Country"])


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

st.markdown("## ☕ Coffee World Map")
st.write(f"**Métrica:** {metric}    •    **Año:** {selected_year}" + (f"    •    **Tipo:** {selected_type}" if selected_type != "Todos" else ""))

event = st.plotly_chart(fig, config=dict(selection_mode=["points","box","lasso"]), on_select="rerun")
if len(event.selection.points):
    selected_point = event.selection.points[0]
    selected_country = selected_point['properties']['name']
    st.markdown(f'**Pais seleccionado: {selected_country}**')
