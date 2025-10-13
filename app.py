import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_plotly_events import plotly_events
from urllib.request import urlopen
import json

with open('data/countries.geo.json') as f:
    countries = json.load(f)

FILE_METRICS = {
    "Consumo Doméstico": "data\Coffee_domestic_consumption.csv",
    "Exportación": "data\Coffee_export.csv",
    "Inventario de Café Verde": "data\Coffee_green_coffee_inventorie.csv",
    "Importación": "data\Coffee_import.csv",
    "Consumo de Importadores": "data\Coffee_importers:consumption.csv",
    "Producción": "data\Coffee_production.csv",
    "Re Exportación": "data\Coffee_re_export.csv",
}

METRIC = "Producción"
YEAR = "1990/91"

df = pd.read_csv(FILE_METRICS[METRIC])

fig = px.choropleth(
    df,
    geojson=countries,
    locations='Country',
    color=YEAR,
    featureidkey='properties.name',  # coincide con tu geojson
    # color_continuous_scale='blues',
    scope="world",
    labels={YEAR: 'Producción'}
)

fig.update_geos(
    visible=False,              
    showcountries=True,         
    projection_type="natural earth"
)

fig.update_layout(
    margin={"r":0,"t":0,"l":0,"b":0},
    geo=dict(bgcolor='white'),
    dragmode=False,             
)

st.markdown("Seleccione un pais")

event = st.plotly_chart(fig, on_select="rerun", selection_mode=["points","box","lasso"])
if len(event.selection.points):
    selected_point = event.selection.points[0]
    selected_country = selected_point['properties']['name']
    st.markdown(f'**Pais seleccionado: {selected_country}**')