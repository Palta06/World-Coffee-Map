# World-Coffee-Map

# Plataforma de Análisis del Mercado Global del Café

## Descripción

Este proyecto busca resolver la problemática de la **falta de una plataforma que centralice datos abiertos** sobre la producción, comercialización y distribución del café a nivel mundial.  

Actualmente, la toma de decisiones estratégicas en este mercado se ve limitada por la **escasez de análisis amplios y objetivos** basados en datos disponibles. Nuestro sistema propone una solución que entregue **insights, evaluaciones y métricas financieras** sobre el mercado del café a nivel global, utilizando información de la **International Coffee Organization (ICO)** recopilada y publicada en **Kaggle**.

### Limitaciones
- La solución se restringe al uso de información pública disponible.
- El análisis se realiza a nivel **global y por país**, sin acceso a datos particulares de empresas específicas.
- Los resultados se orientan a **decisiones estratégicas generales** y no a estrategias operativas individuales.

### Objetivo
Proveer una **plataforma completa, intuitiva e interactiva** con información relevante sobre el mercado del café, que permita a los usuarios obtener:
- Evaluaciones comparativas entre países.
- Insights sobre tendencias globales.
- Métricas de producción, consumo, importación, exportación e inventarios de café verde.

---

## Base de Datos Utilizada

**Fuente:** [Coffee Dataset - Michał Sikora (Kaggle)](https://www.kaggle.com/datasets/michals22/coffee-dataset)  
**Origen de los datos:** International Coffee Organization (ICO - [ico.org](https://ico.org/))  
**Cobertura temporal:** 1990 - 2020  
**Cobertura geográfica:** 55 países  
**Licencia:** CC0: Public Domain  

### Tablas principales
- **Consumo Doméstico**: 33 columnas × 55 filas  
- **Exportación**: 32 columnas × 55 filas  
- **Inventario de Café Verde**: 32 columnas × 18 filas  
- **Importación**: 32 columnas × 35 filas  
- **Consumo de Importación**: 32 columnas × 35 filas  
- **Producción**: 33 columnas × 55 filas  
- **Re-Exportación**: 32 columnas × 35 filas  

**Formato general de las tablas:**

| País     | Tipo de Café | 1990     | 1991     | ... | 2019     | 2020     |
|----------|-------------|----------|----------|-----|----------|----------|
| Austria  | Arabica     | 1500000  | 1600000  | ... | 2500000  | 2300000  |

---

## ⚙️ Instrucciones de ejecución

1. **Clonar este repositorio**:
   ```bash
   git clone <url-del-repo>
   cd <nombre-del-proyecto>

2. **Instalar Dependencias (en caso de usar Python)**:
   ```pip install -r requirements.txt (falta ver cuales extensiones ocuparemos)

3. **Ejecutar el proyecto**:
   ```python main.py
