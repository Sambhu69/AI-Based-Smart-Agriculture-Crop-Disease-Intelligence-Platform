# Multi-Domain Agricultural Exploratory Data Analysis & Insights Report

**Stage:** 5 (Multi-Domain Exploratory Data Analysis)  
**Date:** 2026-11-21  
**Lead Authors:** Technical Architecture & ML Engineering Team  
**Pipeline Components:** `pipelines.ingest.plantvillage_audit`, `pipelines.ingest.nasa_power_batch`, `pipelines.ingest.tabular_crops`, `pipelines.eda.run_eda`

---

## 1. Executive Summary

This report synthesizes the multi-domain exploratory analysis across:
1. **PlantVillage Computer Vision Dataset:** Class representation, class imbalance, and feature embedding anomaly detection.
2. **NASA POWER Daily Agroclimatology (2015–2024):** Decadal climate patterns, monsoonal dynamics, temperature regimes, and solar radiation across Nepal's key agricultural pilot zones (Chitwan, Pokhara, Kathmandu).
3. **Tabular Regional Crop Production & Soil Profiles:** Historical harvest baselines (Tomato, Potato, Pepper) and chemical/physical soil parameters.

All exploratory analyses and visualizations were produced programmatically with deterministic pipeline lineage and validated schemas.

---

## 2. Computer Vision Domain: PlantVillage Findings

### 2.1 Extreme Class Imbalance
The audited dataset contains **20,632 processed leaf photographs** across 15 disease/healthy classes. An acute class imbalance ratio of **$21.09\times$** exists between the majority and minority classes:
- **Majority Class:** `Tomato__Tomato_YellowLeaf__Curl_Virus` — **3,205 samples** ($15.54\%$ of total).
- **Minority Class:** `Potato___healthy` — **152 samples** ($0.74\%$ of total).

```text
Class Distribution Extremes:
Tomato__Tomato_YellowLeaf__Curl_Virus:  3,205 [████████████████████████████] (15.5%)
Tomato_Bacterial_spot:                  2,127 [██████████████████]          (10.3%)
Tomato_Late_blight:                     1,909 [████████████████]            (9.3%)
...
Tomato__Tomato_mosaic_virus:              373 [███]                         (1.8%)
Potato___healthy:                         152 [█]                           (0.74%)
```

**Agronomic & Modeling Implications:**
- Naive Cross-Entropy optimization risks suppressing minority class representations (e.g. `Potato___healthy`).
- Stratified sampling, class-weighted cross-entropy loss, or focal loss must be enforced in Stage 6 model training.
- Macro-averaged F1 and per-class recall must serve as the primary evaluation metrics rather than raw top-1 accuracy.

### 2.2 Suspicious Outlier & Noise Analysis
An audit of `suspicious_outliers/outlier_report.csv` identified **256 flagged outlier images** ($1.24\%$ overall anomaly rate).

**Outlier Concentration by Class:**
- `Potato___Early_blight`: **31 outliers** ($3.10\%$) — highest relative anomaly rate.
- `Tomato_Late_blight`: **37 outliers** ($1.94\%$).
- `Potato___Late_blight`: **19 outliers** ($1.90\%$).

**Dominant Error Modes:**
1. **Fruit / Object Intrusion:** Photographs focusing on bell pepper fruits or tomatoes rather than leaves (zero-shot ImageNet predictions for `"bell pepper"` with $>99\%$ probability).
2. **Laboratory & Lighting Artifacts:** Overexposed backgrounds, human hands/fingers holding the leaf, and harsh specular reflections.
3. **Severe Embedding Distance:** Samples exhibiting $>3\sigma$ cosine distance from the nominal class centroid in ResNet feature space.

---

## 3. Meteorological Domain: NASA POWER Agroclimatology (2015–2024)

A total of **10,959 daily weather records** were ingested and validated across three distinct agro-ecological pilot zones:
1. **Chitwan (Terai Lowlands):** Subtropical alluvial plain, intensive cereal and horticulture production.
2. **Pokhara (Mid-Hills Agro-Ecology):** Humid subtropical valley with elevated orographic precipitation.
3. **Kathmandu (Horticulture Basin):** Temperate valley bowl with intensive commercial vegetable cultivation.

### 3.1 Seasonal & Climate Regimes
- **Temperature Regime:**
  - Chitwan: Hot summers (daily mean exceeding $31^\circ\text{C}$ in May–June) and mild winters (minimum mean $15^\circ\text{C}$).
  - Kathmandu & Pokhara: Moderate thermal regimes ($10^\circ\text{C}$ to $25^\circ\text{C}$), providing suitable microclimates for potato and tomato horticulture.
- **Monsoonal Dynamics (Precipitation & Humidity):**
  - Extreme precipitation concentration: Over $82\%$ of annual rainfall occurs between June and September (South Asian Summer Monsoon).
  - Peak daily rainfall frequently exceeds $50\text{ mm/day}$ in July–August, elevating relative humidity above $85\%$.
  - High humidity ($>80\%$) coupled with temperatures of $20-26^\circ\text{C}$ directly triggers the physical sporulation threshold for Late Blight (`Phytophthora infestans`).

### 3.2 Meteorological Correlations
- Strong positive correlation between Temperature and Precipitation ($r = +0.58$), driven by monsoonal heating.
- Strong negative correlation between Precipitation and Solar Radiation ($r = -0.42$), resulting from extensive cloud cover during the peak monsoon.

---

## 4. Agronomic Domain: Crop Yields & Soil Properties

### 4.1 Historical Yield Baselines (2015–2024)
- **Tomato:** Mean yields ranged from $18,500\text{ kg/ha}$ (2015, Chitwan) to $25,800\text{ kg/ha}$ (2024, Kathmandu greenhouse/commercial peri-urban plots). Shows steady upward trend due to improved hybrid varieties and drip irrigation adoption.
- **Potato:** Terai winter potato yields range from $13,900$ to $17,800\text{ kg/ha}$. Susceptible to sudden dips in unseasonably warm winters or late blight outbreaks.
- **Pepper:** Hill pepper yields range from $8,200$ to $10,600\text{ kg/ha}$.

### 4.2 Soil Chemistry Constraints (SoilGrids Baselines)
- **Chitwan (Terai):** Slightly acidic to neutral alluvium ($\text{pH } 6.2$), moderate organic matter ($2.4\%$), high available potassium ($185\text{ mg/kg}$).
- **Pokhara (Mid-Hills):** Strongly acidic ($\text{pH } 5.6$), high organic matter ($3.1\%$), lower available phosphorus ($18\text{ mg/kg}$), requiring lime application for optimal Solanaceae cultivation.
- **Kathmandu Basin:** Neutral lacustrine loam ($\text{pH } 6.8$), high available nitrogen and potassium from intensive fertilization.

---

## 5. Visual Artifacts Summary (`reports/eda/figures/`)

The following publication-grade charts were generated and verified:
1. `01_plantvillage_class_imbalance.png`: Horizontal ranking illustrating the $21.09\times$ imbalance spread.
2. `02_plantvillage_outliers_by_class.png`: Anomaly frequency per nominal class.
3. `03_outlier_feature_space.png`: Embedding cosine distance vs Isolation Forest decision score.
4. `04_nasa_power_monthly_seasonality.png`: Decadal monthly mean temperatures and monsoonal precipitation profiles.
5. `05_weather_correlation_matrix.png`: Heatmap of inter-variable meteorological correlations.
6. `06_crop_yield_trends.png`: 10-year production trajectory across pilot plots.

---

## 6. Data Biases & Unacquired Sources Status

### 6.1 Identified Biases
1. **PlantVillage Laboratory Bias:** PlantVillage images are captured on uniform gray/black laboratory backdrops with detached leaves. They lack the background complexity (soil, weeds, shadows) of real-world farm conditions.
2. **Spatial Granularity:** NASA POWER provides $0.5^\circ \times 0.625^\circ$ grid cells; micro-topographical variations in hill valleys require downscaling in future digital twin stages.

### 6.2 Unacquired Sources Status (Preserved as Downstream Targets)
- **Sentinel-2 Multispectral Imagery:** Maintained as an on-demand cloud-retrieval pipeline for field-level NDVI; not downloaded locally to respect disk limits.
- **AgERA5 & Full SoilGrids Rasters:** Preserved as remote API endpoints rather than bulk local GeoTIFF downloads.
