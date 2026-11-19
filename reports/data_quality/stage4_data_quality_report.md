# Stage 4 Data Quality & Dataset Audit Report

**Audit Date:** 2026-11-21  
**Auditor:** Automated Ingestion & Data Quality Pipeline (`pipelines.ingest.plantvillage_audit`)  
**Pipeline Version:** `1.0.0`

---

## 1. Executive Summary

This report documents the verification of local dataset assets, pipeline data quality enforcement, and hardware boundaries for Stage 4 (Data Engineering).

Key findings:
1. **PlantVillage Physical Asset Audit:** Verified all 15 classes across `data/raw/PlantVillage` and `data/processed/PlantVillage`. Total raw files count 20,636 (20,635 images), and total processed files count 20,633 (20,632 images), with 3 outlier images removed from `Tomato__Tomato_YellowLeaf__Curl_Virus`.
2. **Severe Class Imbalance:** Verified that `Potato___healthy` has only 152 images, representing less than $0.74\%$ of the total dataset, whereas `Tomato__Tomato_YellowLeaf__Curl_Virus` contains 3,208 raw samples ($15.54\%$).
3. **Outlier Anomaly Detection:** Real audit confirmed 256 images flagged in `suspicious_outliers/outlier_report.csv` ($1.24\%$ overall), with highest outlier proportions in `Potato___Early_blight` ($3.10\%$), `Tomato_Late_blight` ($1.94\%$), and `Potato___Late_blight` ($1.90\%$).
4. **Hardware and Disk Capacity Check:** Available disk space on `C:` is **69.62 GB** free out of 352.77 GB, well above the 24.55 GB safety baseline.
5. **Quality & Lineage Automated Tests:** 100% of pipeline tests passed (35 total project tests passing in `pytest`).

---

## 2. PlantVillage Audit Breakdown

Generated programmatically via [`pipelines/ingest/plantvillage_audit.py`](file:///C:/Users/ACER/Intern21/smart-agriculture-platform/pipelines/ingest/plantvillage_audit.py) and stored at [`reports/data_quality/plantvillage_audit.json`](file:///C:/Users/ACER/Intern21/smart-agriculture-platform/reports/data_quality/plantvillage_audit.json):

| Class Name | Raw Images | Processed Images | Delta (Cleaned) | Flagged Outliers | Outlier % of Class |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `Pepper__bell___Bacterial_spot` | 997 | 997 | 0 | 15 | 1.50% |
| `Pepper__bell___healthy` | 1,476 | 1,476 | 0 | 13 | 0.88% |
| `Potato___Early_blight` | 1,000 | 1,000 | 0 | 31 | **3.10%** |
| `Potato___Late_blight` | 1,000 | 1,000 | 0 | 19 | 1.90% |
| `Potato___healthy` | **152** | **152** | 0 | 2 | 1.32% |
| `Tomato_Bacterial_spot` | 2,127 | 2,127 | 0 | 20 | 0.94% |
| `Tomato_Early_blight` | 1,000 | 1,000 | 0 | 12 | 1.20% |
| `Tomato_Late_blight` | 1,909 | 1,909 | 0 | 37 | 1.94% |
| `Tomato_Leaf_Mold` | 952 | 952 | 0 | 4 | 0.42% |
| `Tomato_Septoria_leaf_spot` | 1,771 | 1,771 | 0 | 25 | 1.41% |
| `Tomato_Spider_mites_Two_spotted_spider_mite` | 1,676 | 1,676 | 0 | 14 | 0.84% |
| `Tomato__Target_Spot` | 1,404 | 1,404 | 0 | 16 | 1.14% |
| `Tomato__Tomato_YellowLeaf__Curl_Virus` | 3,208 | 3,205 | 3 | 35 | 1.09% |
| `Tomato__Tomato_mosaic_virus` | 373 | 373 | 0 | 3 | 0.80% |
| `Tomato_healthy` | 1,590 | 1,590 | 0 | 10 | 0.63% |
| **TOTAL** | **20,635** | **20,632** | **3** | **256** | **1.24%** |

*Note: File count totals on disk include folder metadata and non-image artifacts (20,636 raw / 20,633 processed files).*

---

## 3. Suspicious Outliers Analysis

The audit examined `suspicious_outliers/outlier_report.csv` to determine error modes:
- **Fruit / Non-Leaf Interference:** Images containing ripe bell peppers or tomatoes instead of foliage (e.g. ImageNet zero-shot predictions for `"bell pepper"` at $99.6\%$ probability).
- **Background & Lighting Artifacts:** Images with extreme over-exposure, shadows, human hands holding leaves, or laboratory equipment.
- **Extreme Statistical Distance:** Images exhibiting cosine distance $> 3.0 \sigma$ from nominal class feature centroid.

---

## 4. Verification of Stage 4 Pipelines & Integrity

Stage 4 pipelines were validated via dedicated unit and integration tests:

1. **Schema Integrity (`pipelines/common/schema.py`)**:
   - Explicit `EPISTEMIC_TYPES` verification (`observed`, `external`, `predicted`, `simulated`, `recommended`).
   - Bounds testing for coordinates, physical weather constraints, soil pH/moisture, and yield thresholds.
2. **Lineage Tracking (`pipelines/lineage.py`)**:
   - Automated SHA-256 computation on inputs/outputs.
   - Verified serialization to JSON with timestamps and parameter tracking.
3. **NASA POWER Ingestion (`pipelines/ingest/nasa_power.py`)**:
   - Verified parsing of daily meteorological parameters (`T2M`, `PRECTOTCORR`, `RH2M`, `ALLSKY_SFC_SW_DWN`, `WS2M`).
   - Bounded coordinate ingestion around pilot region (Chitwan Valley, Nepal).
   - Zero-network offline testing verified via simulated payloads.
4. **Data Quality Validators (`pipelines/validate/quality.py`)**:
   - Verified rejection of out-of-bounds coordinates, duplicate observations, unphysical temperatures ($<-50^\circ$C or $>55^\circ$C), and negative yields.
5. **Leakage-Safe Partitioning (`pipelines/validate/splits.py`)**:
   - Temporal ordering: Proved $\max(\text{train date}) \le \min(\text{val date}) \le \min(\text{test date})$.
   - Group disjointness: Proved zero overlap of farm/entity groups across train, val, and test splits.

---

## 5. Hardware & Boundary Enforcement

- **Disk Safety:** SSD capacity monitored. Available free space: **69.62 GB**, exceeding requirements.
- **External Dataset Boundaries:** Heavy multi-spectral satellite rasters (Sentinel-2) and global grids (SoilGrids, AgERA5) are preserved as future pipeline endpoints. Unbounded API downloading is blocked to prevent disk exhaustion.
