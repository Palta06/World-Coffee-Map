import streamlit as st
import pandas as pd
import plotly.express as px
import json
from pathlib import Path
from difflib import get_close_matches
import re
import utils
import unicodedata

st.set_page_config(page_title="Coffee World Map", layout="wide")

@st.cache_data
def load_geojson(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def load_csv(path: Path):
    return pd.read_csv(path)

if not 'selected_country' in st.session_state:  
    st.session_state['selected_country'] = None

class DataCleaner:

    def strip_accents(self, s: str) -> str:
        if not isinstance(s, str):
            return s
        nfkd = unicodedata.normalize('NFKD', s)
        return ''.join([c for c in nfkd if not unicodedata.combining(c)])

    def normalize_name_for_match(self, s: str) -> str:
        if not isinstance(s, str):
            return ""
        s = s.strip()
        s = re.sub(r'\(.*?\)', '', s)
        s = self.strip_accents(s)
        s = s.replace('&', 'and')
        s = s.replace('-', ' ')
        s = s.replace('/', ' ')
        s = re.sub(r'[^0-9A-Za-z\s]', '', s)
        s = re.sub(r'\s+', ' ', s)
        return s.strip().lower()
    
    
class DataLoader:

    def __init__(self, base):
        self.data_dir = base / "data"

        self.geojson_path = self.data_dir / "countries.geo.json"
        self.countries_geo = load_geojson(self.geojson_path)
        self.geo_names = self.get_geo_names()

        self.files = {
                "Producción": self.data_dir / "Coffee_production.csv",
                "Consumo": self.data_dir / "Coffee_domestic_consumption.csv",
                "Exportación": self.data_dir / "Coffee_export.csv",
            }

    def get_geo_names(self):
        geo_names = []
        for feat in self.countries_geo.get("features", []):
            prop = feat.get("properties", {})
            name = prop.get("name") or prop.get("NAME") or prop.get("ADMIN") or prop.get("ADMIN_NAME") or prop.get("Country")
            if name:
                geo_names.append(name)
        return geo_names

    
cleaner = DataCleaner()
loader = DataLoader(Path(__file__).parent)

def detect_country_column(df: pd.DataFrame) -> str:
    candidates = ["Country", "country", "Country or Area", "Country or area", "Country/Area", "country/area",
                  "Country or Area", "Country name"]
    for c in candidates:
        if c in df.columns:
            return c
    
    for c in df.columns:
        if df[c].dtype == object:
            sample = df[c].dropna().astype(str).head(20).tolist()
            alpha_ratio = sum(1 for v in sample if re.search(r'[A-Za-z]', v)) / max(1, len(sample))
            if alpha_ratio > 0.6:
                return c
    return None

def detect_year_columns(columns) -> list:
    year_regex = re.compile(r'^\s*\d{4}(\s*[-/]\s*\d{2,4})?\s*$')
    return [c for c in columns if isinstance(c, str) and year_regex.match(c.strip())]

def year_label_to_int(label: str) -> int:
    if not isinstance(label, str):
        return 9999
    m = re.match(r'^\s*(\d{4})', label)
    return int(m.group(1)) if m else 9999

def build_country_map(csv_countries, geo_countries, cutoff=0.7):
    geo_norm = {n: cleaner.normalize_name_for_match(n) for n in geo_countries}
    norm_to_geo = {}
    for geo, n in geo_norm.items():
        if n:
            norm_to_geo.setdefault(n, []).append(geo)

    mapping = {}
    for c in csv_countries:
        if c in geo_countries:
            mapping[c] = c
            continue
        c_norm = cleaner.normalize_name_for_match(c)
        
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

st.sidebar.title("Coffee World Map")

metric = st.sidebar.selectbox("Seleccionar Métrica:", list(loader.files.keys()))

csv_path = loader.files[metric]
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
df_long["year"] = df_long["year_label"].apply(utils.year_label_to_int)
df_long = df_long.drop('year_label', axis=1)

df_long["Country"] = df_long["Country"].astype(str).str.strip()
years_ordered = (df_long["year"].drop_duplicates().sort_values().tolist())
selected_year = st.sidebar.selectbox("Seleccionar Año:", years_ordered, index=len(years_ordered)-1)

if "Coffee type" in df_long.columns:
    types_present = sorted(df_long["Coffee type"].dropna().unique().tolist())
    preferred = [t for t in ["Arabica","Robusta","Robusta/Arabica"] if t in types_present]
    for t in types_present:
        if t not in preferred:
            preferred.append(t)
    selected_type = st.sidebar.selectbox("Seleccionar Tipo de Café:", preferred, index=0)
else:
    selected_type = "Todos"


mask = df_long["year"] == selected_year
if selected_type != "Todos" and "Coffee type" in df_long.columns:
    mask = mask & (df_long["Coffee type"].fillna("").str.strip().str.lower() == selected_type.strip().lower())

df_filtered = df_long[mask].copy()
map_df = df_filtered.groupby("Country", as_index=False)["value"].sum()

csv_countries = map_df["Country"].dropna().unique().tolist()
country_map = build_country_map(csv_countries, loader.geo_names, cutoff=0.7)
map_df["geo_name"] = map_df["Country"].map(country_map)
 

map_df["plot_location"] = map_df["geo_name"].where(map_df["geo_name"].notna(), map_df["Country"])

left_column, center_column, right_column = st.columns([2, 4, 3])

with center_column:
    fig = px.choropleth(
        map_df,
        geojson=loader.countries_geo,
        locations="plot_location",
        featureidkey="properties.name",
        color="value",
        hover_name="Country",
        projection="natural earth",
        title=f"{metric} - {selected_year}" + (f" ({selected_type})" if selected_type != "Todos" else "")
    )

    fig.update_geos(showcountries=False, showcoastlines=False, showland=True, bgcolor="#2c2f33")
    fig.update_layout(
        margin={"r":0,"t":60,"l":0,"b":0},
        coloraxis_colorbar=dict(title="Valor")
    )
    fig.update_coloraxes(showscale=False)

    event = st.plotly_chart(fig, config=dict(selection_mode=["points","box","lasso"]), on_select="rerun")
    if len(event.selection.points):
        selected_point = event.selection.points[0]
        selected_country = selected_point['properties']['name']
        st.session_state['selected_country'] = selected_country
    else:
        st.session_state['selected_country'] = None

with left_column.container(border=True):

    selected_country = st.session_state['selected_country']
    if selected_country:
        st.write(f"### {selected_country}")

        bags = map_df.loc[map_df['plot_location'] == selected_country, 'value'].values[0]
        st.metric(label=metric, value=f"{bags/1_000_000:,.2f} M bolsas")

        # Filtrar la data completa solo para ese país
        df_country = df_long[df_long["Country"] == selected_country]

        # Agrupar por año
        hist_country = df_country.groupby("year")["value"].sum().reset_index()
        hist_country["value_m"] = hist_country["value"] / 1_000_000

        # Evitar gráfico vacío
        if not hist_country.empty:
            hist_fig = px.line(
                hist_country,
                x="year",
                y="value_m",
                labels={"year": "Año", "value_m": "Millones de bolsas"},
                markers=True
            )

            hist_fig.update_traces(
                line_color='#1f77b4',
                marker=dict(size=8),
                hovertemplate=f'Año: %{{x}}<br>{metric}: %{{y:.2f}}M bolsas<extra></extra>'
            )

            hist_fig.update_layout(
                height=260,
                margin=dict(l=0, r=0, t=40, b=0),
                showlegend=False
            )

            st.plotly_chart(hist_fig, use_container_width=True)
        else:
            st.info("No hay datos históricos disponibles para este país.")


    else:
        st.write(f"### {metric} Mundial")
        bags = map_df['value'].sum()
        st.metric(label=metric, value=f"{bags/1_000_000:,.2f} M bolsas")

with right_column:

    label_dict = { 'Producción': 'Productores', 'Consumo': 'en Consumo', 'Exportación': 'Exportadores' } 
    st.markdown(f"## Top 10 Países {label_dict.get(metric, '')}")

    chart_data = map_df.sort_values("value", ascending=True).tail(10)

    chart_data = chart_data.copy()
    chart_data['value_m'] = chart_data['value'] / 1_000_000

    bar_fig = px.bar(
        chart_data,
        y="Country",
        x="value_m",
        orientation='h',
        labels={"Country": "País", "value_m": f"Millones de bolsas"},
        text="value_m"
    )

    bar_fig.update_traces(
        texttemplate='%{text:.1f}M',
        textposition='auto',
        marker_color='#1f77b4'
    )

    bar_fig.update_layout(
        showlegend=False,
        margin=dict(l=200, r=20, t=50, b=20),
        height=400
    )

    st.plotly_chart(bar_fig, use_container_width=True)

if selected_type != "Todos" and "Coffee type" in df_long.columns:
    title_suffix = f" ({selected_type})"
    df_trend = df_long[df_long["Coffee type"].fillna("").str.strip().str.lower() == selected_type.strip().lower()]
else:
    title_suffix = ""
    df_trend = df_long

historical_data = df_trend.groupby('year')['value'].sum().reset_index()
historical_data['value_m'] = historical_data['value'] / 1_000_000

trend_fig = px.line(
    historical_data,
    x='year',
    y='value_m',
    title=f'Tendencia Histórica de {metric} Mundial{title_suffix}',
    labels={'year': 'Año', 'value_m': 'Millones de bolsas'},
    markers=True
)

trend_fig.update_traces(
    line_color='#1f77b4',
    marker=dict(size=8),
    hovertemplate=f'Año: %{{x}}<br>{metric}: %{{y:.1f}}M bolsas<extra></extra>'
)

trend_fig.update_layout(
    xaxis_title='Año',
    yaxis_title='Millones de bolsas',
    showlegend=False,
    hovermode='x unified'
)

trend_col, pie_col = st.columns([3, 2])
trend_col.plotly_chart(trend_fig, use_container_width=True)

if metric == "Exportación":
    def compute_total_from_file(path, year_label, coffee_type=None):
        df_local = load_csv(path)
        country_col_local = detect_country_column(df_local)
        if country_col_local and country_col_local != "Country":
            df_local = df_local.rename(columns={country_col_local: "Country"})
        if "Coffee Type" in df_local.columns and "Coffee type" not in df_local.columns:
            df_local = df_local.rename(columns={"Coffee Type": "Coffee type"})
        if "Coffee type" in df_local.columns:
            df_local["Coffee type"] = df_local["Coffee type"].astype(str).apply(lambda x: x.strip() if pd.notna(x) else x)
        year_cols_local = detect_year_columns(df_local.columns)
        if not year_cols_local:
            return 0.0
        if year_label not in year_cols_local:
            matches = [c for c in year_cols_local if c.strip().startswith(str(year_label).strip())]
            if matches:
                year_label_use = matches[0]
            else:
                return 0.0
        else:
            year_label_use = year_label
        id_vars_local = ["Country"]
        if "Coffee type" in df_local.columns:
            id_vars_local.append("Coffee type")
        df_long_local = df_local.melt(id_vars=id_vars_local, value_vars=year_cols_local, var_name="year_label", value_name="value")
        df_long_local["value"] = pd.to_numeric(df_long_local["value"], errors="coerce")
        mask_local = df_long_local["year_label"] == year_label_use
        if coffee_type:
            mask_local = mask_local & (df_long_local["Coffee type"].fillna("").str.strip().str.lower() == coffee_type.strip().lower())
        return df_long_local.loc[mask_local, "value"].sum()

    coffee_type_arg = selected_type if selected_type != "Todos" else None
    prod_total = compute_total_from_file(loader.data_dir / "Coffee_production.csv", selected_year, coffee_type_arg)
    export_total = compute_total_from_file(loader.data_dir / "Coffee_export.csv", selected_year, coffee_type_arg)
    domestic_total = max(0.0, prod_total - export_total)

    donut_df = pd.DataFrame({
        "category": ["Consumo Interno", "Exportado"],
        "value": [domestic_total, export_total]
    })
    donut_df["value_m"] = donut_df["value"] / 1_000_000

    donut_fig = px.pie(
        donut_df,
        names="category",
        values="value_m",
        hole=0.5,
        title=f"Proporción: Consumo Interno vs Exportaciones ({selected_year})" + (f" - {selected_type}" if selected_type != "Todos" else "")
    )
    donut_fig.update_traces(textinfo="label+percent", hovertemplate='%{label}: %{value:.1f}M bolsas (%{percent})')
    donut_fig.update_layout(margin=dict(t=50, b=20), showlegend=True)
    pie_col.plotly_chart(donut_fig, use_container_width=True)