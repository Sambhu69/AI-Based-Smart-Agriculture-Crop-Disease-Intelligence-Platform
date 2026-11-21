# AI-Based Autonomous Precision Agriculture Digital Twin & Global Food Security Intelligence Platform

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-v1-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

An end-to-end, provenance-aware agricultural intelligence platform combining deep learning leaf pathology classification, tabular crop yield forecasting, prescriptive agronomy advisories, geospatial vegetation indices, a 5-factor Digital Twin scenario engine, multimodal outbreak risk assessment, and a mobile-first React + TypeScript web application.

---

## System Architecture

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  React + TypeScript + Tailwind UI (frontend/ • http://127.0.0.1:5173)   │
│  Mobile-First Shell • Provenance Badges • Recharts • TanStack Query      │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ HTTP / JSON (/api/v1/*)
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Modular FastAPI Monolith (app/main.py • http://127.0.0.1:8000)         │
│  • Disease CV Service (ResNet-50)     • Digital Twin Simulator           │
│  • Agronomy Rule Engine               • Outbreak Risk & Tool Assistant   │
│  • Yield Baseline Predictor           • Drift & Confidence Monitor       │
│  • Secret-Redacting Logging           • Structured 422 / 500 Handlers    │
└──────────────────┬─────────────────────────────┬─────────────────────────┘
                   │                             │
                   ▼                             ▼
┌──────────────────────────────────┐   ┌───────────────────────────────────┐
│  SQLite / PostgreSQL + Alembic   │   │  Offline & Pipeline Modules       │
│  • farms & plots (observed)      │   │  • pipelines/ingest/ (NASA POWER) │
│  • field_observations (observed/ │   │  • pipelines/gis/ (NDVI/NDWI/EVI) │
│    external)                     │   │  • pipelines/models/ (Grad-CAM)   │
│  • prediction_records (predicted)│   │  • pipelines/monitoring/ (Drift)  │
│  • twin_scenarios (simulated)    │   │  • src/ (Preserved Legacy Core)   │
└──────────────────────────────────┘   └───────────────────────────────────┘
```

### Epistemic Provenance Discipline
Every record, prediction, recommendation, and simulation in the platform is tagged with one of five canonical provenance types so ground-truth measurements are never conflated with model estimates:
- `observed` — Direct field measurements, scout notes, or in-situ sensor readings.
- `external` — External agroclimatology data (e.g., NASA POWER daily records).
- `predicted` — Outputs from trained ML/DL models (ResNet-50 disease CV, Ridge yield baseline, outbreak risk).
- `simulated` — Projections from mathematical scenario engines (5-factor Digital Twin, 14-day RL water balance, NetworkX graph topology).
- `recommended` — Prescriptive advisories from the agronomic suitability, irrigation, and soil pH engine.

---

## Repository Structure

| Directory / File | Purpose |
|---|---|
| `app/` | Primary modular FastAPI backend (`main.py`, `api/v1/routes.py`, `core/`, `db/`, `schemas/`, `services/`). |
| `frontend/` | Mobile-first React + TypeScript + Vite + Tailwind web application (`10` pages, responsive bottom nav + sidebar). |
| `pipelines/` | Data schemas, lineage tracking, PlantVillage audit, NASA POWER ingestion, EDA, GIS indices (`NDVI`, `NDWI`, `EVI`, `SAVI`), Grad-CAM & ML baselines, and drift monitoring. |
| `alembic/` | Database schema migrations (head revision `93b6c2b47e27`). |
| `src/` | **Preserved legacy baseline** (`api.py`, `dashboard.py` Streamlit UI, `model.py`, `train.py`, `evaluate.py`, `dataset.py`). |
| `models/` | `best_model.pth` (preserved ResNet-50 weights) and `stage6/yield_baseline.joblib` (gitignored). |
| `tests/` | Automated backend, pipeline, security hygiene, E2E, and MLOps test suites (`110` tests). |
| `docs/` | `data_dictionary.md` and operational `runbook.md`. |
| `reports/` | Data quality audit, EDA figures & report, model evaluation JSONs, and final delivery report. |
| `Dockerfile` / `docker-compose.yml` | Lean container deployment for FastAPI backend + optional PostgreSQL profile. |

---

## Verified Model & Data Benchmarks

- **PlantVillage Audit (`pipelines/ingest/plantvillage_audit.py`):** `20,636` raw images / `20,633` processed images across `15` Pepper, Potato, and Tomato classes.
- **ResNet-50 Disease Classifier (`models/best_model.pth`):** `98.98%` Top-1 accuracy, `100.00%` Top-3 accuracy, `98.50%` Macro F1 on `2,063` held-out test images (~`6.42 ms` median latency on NVIDIA RTX 4050).
- **NASA POWER Agroclimatology (`pipelines/ingest/nasa_power_batch.py`):** `10,959` real daily records across Chitwan, Pokhara, and Kathmandu (2015–2024).
- **Tabular Yield Baseline (`pipelines/models/yield_baseline.py`):** Ridge Regression (`R² = 0.9827`, `RMSE = 834.94 kg/ha` on held-out test split).
- **Weather Forecast Baseline (`pipelines/models/weather_baseline.py`):** Naive persistence (`RMSE = 0.887 °C`) vs. Ridge (`RMSE = 1.240 °C`) over `547` test days.

---

## Quick Start (Windows PowerShell)

### 1. Backend Setup & Launch
```powershell
cd C:\Users\ACER\Intern21\smart-agriculture-platform
copy .env.example .env
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/api/v1/health`

### 2. Frontend Setup & Launch
```powershell
cd C:\Users\ACER\Intern21\smart-agriculture-platform\frontend
copy .env.example .env
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```
- Web Application: `http://127.0.0.1:5173`

### 3. Legacy Streamlit Dashboard (Preserved)
```powershell
cd C:\Users\ACER\Intern21\smart-agriculture-platform
.\venv\Scripts\python.exe src\api.py
# In a second terminal:
.\venv\Scripts\python.exe -m streamlit run src\dashboard.py
```

### 4. Containerized Deployment (Docker / Compose)
```powershell
# SQLite default:
docker compose up --build api

# Optional PostgreSQL profile (set POSTGRES_PASSWORD in .env first):
docker compose --profile postgres up --build
```

---

## Verification Commands

```powershell
# Backend & MLOps test suite (110 tests)
cd C:\Users\ACER\Intern21\smart-agriculture-platform
.\venv\Scripts\python.exe -m pytest tests -v --tb=short

# Frontend unit tests & production build (15 tests + Vite bundle)
cd C:\Users\ACER\Intern21\smart-agriculture-platform\frontend
npm test
npm run build
```

---

## Limitations & Safety Caveats

- **Laboratory-to-Field Generalization:** The ResNet-50 model was trained on standardized PlantVillage imagery; field lighting, soil backgrounds, and multi-pathogen co-infections require field scouting verification.
- **Simplified Simulations & Rule Engines:** Digital Twin scenarios (`twin_service_v1`), RL irrigation water balance, and agronomy advisories use simplified multiplicative/bucket models and do not account for cultivar-specific genetics, subsurface hydrology, or market economics.
- **Security Hygiene:** Never commit `.env`, `*.db`, `*.pem`, `*.key`, or API credentials. Sensitive keys in logs are automatically scrubbed by `SecretRedactingFilter` in [`app/core/logging.py`](app/core/logging.py).

See [`docs/runbook.md`](docs/runbook.md) for operational procedures and [`reports/final_project_delivery_report.md`](reports/final_project_delivery_report.md) for the complete technical delivery report.
