## **Reporte de Avance – Octubre 2025**

- Entrega Parcial II


#### **Contexto general**

Esta actualización representa el desarrollo del primer módulo de código funcional dentro del repositorio. Marca un avance significativo, ya que implementa la primera versión operativa de una aplicación interactiva de visualización de datos geoespaciales desarrollada con Streamlit y Plotly.

El código está estructurado en dos módulos principales:

1. **Módulo de limpieza y normalización de datos.**
2. **Módulo de visualización y lógica interactiva.**

### Consideraciones Generales

#### Recomendaciones y Observaciones Entrega I

- EP1.1 Añadimos una sección de Perfiles en [Establecimiento del Problema](./PROBLEM_STATEMENT.md)
- EP1.2 Agregamos paradigmas adicionales a utilizar en [Paradigmas](./PARADIGM.md)
- EP1.3 El detalle de los datos utilizados fueron entregados en [Fuente de Datos](./DATA_SOURCE.md) desde la primera entrega. Favor revisar la documentación completa.
- EP1.4 Decidimos tomar la recomendación y utilizar solo Streamlit para el desarrollo. Revisar cambio en [Arquitectura](./ARQUITECTURA.png)

#### Paragigmas Utilizados

- Programación Orientada a Objetos: Implementación de `class DataCleaner` y `class DataLoader`
- Programación Funcional (ej.): `df_raw["Coffee type"] = df_raw["Coffee type"].astype(str).apply(lambda x: x.strip() if pd.notna(x) else x)`
- Programación Orientada a Objetos: `event = st.plotly_chart(fig, config=dict(selection_mode=["points","box","lasso"]), on_select="rerun")`


### 1. **Módulo de Limpieza y Preparación de Datos**

Este módulo agrupa las funciones utilitarias responsables de cargar, normalizar y alinear los datos provenientes de distintos archivos CSV y de un archivo GeoJSON.
Incluye las siguientes etapas:

#### **a. Carga y caching**

 - `load_geojson` y `load_csv` usan `@st.cache_data` para evitar recargas innecesarias.
 - Permite trabajar con múltiples fuentes (`Coffee_production.csv`, `Coffee_domestic_consumption.csv`, `Coffee_export.csv`) y con información geográfica (`countries.geo.json`).

#### **b. Limpieza de texto y estandarización**

 - `strip_accents` y `normalize_name_for_match` eliminan acentos, símbolos y palabras comunes (“the”, “of”, “de”, etc.), generando una forma normalizada para comparación.
 - Esto permite resolver discrepancias entre nombres de países en los CSV y en el GeoJSON.

#### **c. Detección de columnas clave**

 - `detect_country_column` identifica automáticamente la columna que contiene nombres de países, incluso si varían los encabezados.
 - `detect_year_columns` localiza columnas de años mediante expresiones regulares.
 - `year_label_to_int` convierte etiquetas de año mixtas (“2005-06”) a enteros.

#### **d. Construcción de correspondencias**

 - `build_country_map` crea un diccionario de mapeo entre los países de los CSV y los del GeoJSON usando coincidencias aproximadas (`get_close_matches`), con un umbral de similitud ajustable.
 - Esto asegura que todos los países puedan representarse en el mapa aun si hay diferencias en ortografía o formato.

**Proceso de Limpieza**

El proceso de limpieza ocurre en tiempo de carga y filtrado, con pasos bien definidos:

1. **Normalización de nombres de países** y tipos de café.
2. **Conversión de tipos de datos** (`pd.to_numeric`) para asegurar coherencia en las columnas de valores.
3. **Reestructuración del dataset** a formato largo (“long”) que facilita el uso de gráficos temporales y comparativos.
4. **Agrupaciones y sumatorias** (`groupby("Country")`) para consolidar datos anuales.
5. **Filtrado de datos inválidos o nulos**, garantizando que solo se grafiquen países con valores válidos.


### 2. **Módulo de Visualización y Lógica Interactiva**

La aplicación implementa una arquitectura interactiva reactiva típica de Streamlit:

#### **a. Backend (Lógica y estado)**

 - La app se inicia con `st.set_page_config`, estableciendo el layout “wide”.
 - Carga dinámica de datasets según la métrica seleccionada (Producción, Consumo, Exportación).
 - Transformación de los datos a formato “long” con `pandas.melt()` para permitir gráficos por año y tipo de café.
 - Filtrado dinámico por:
    - Año (`st.sidebar.selectbox`),
    - Tipo de café (si existe la columna “Coffee type”).

#### **b. Frontend (Interfaz de usuario)**

 - Panel lateral (`st.sidebar`) para los filtros.
 - Gráficos interactivos:
    - **Mapa coroplético** (`px.choropleth`) con selección de países.
    - **Bar chart** con el top 10 de países según la métrica seleccionada.
    - **Gráfico de línea** para la tendencia histórica global.
    - **Gráfico de dona** (solo para exportaciones) que compara proporciones de consumo interno vs exportaciones.
 - El uso de `st.columns` divide el layout en panel de mapa + panel de rankings.

#### **c. Integración interactiva**

 - La función `on_select="rerun"` en el mapa permite seleccionar países y refrescar la vista.
 - Los datos seleccionados se reusan para mostrar detalles específicos sin recargar todo el dataset.


### **Estado actual del desarrollo**

 - Se implementa toda la lógica central de lectura, limpieza y visualización.
 - La app ya puede ejecutarse con datasets reales dentro del directorio `/data`.

**Próximos pasos**

- Modularizar funciones repetidas y aislar `utils.py`.
- Incorporar manejo de errores para archivos faltantes o columnas no estándar.
- Añadir documentación y pruebas unitarias de normalización y detección automática.

