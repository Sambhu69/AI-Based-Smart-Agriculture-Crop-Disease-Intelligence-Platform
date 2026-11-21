# Operational Runbook — Smart Agriculture Platform

## 1. Environment Configuration
Copy `.env.example` to `.env` in the repository root and `frontend/.env.example` to `frontend/.env` before running locally:

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `"Smart Agriculture Platform"` | FastAPI application title |
| `APP_ENV` | `development` | Runtime mode (`development` \| `production`) |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`INFO`, `WARNING`, `ERROR`) |
| `DATABASE_URL` | `sqlite:///./smart_ag.db` | SQLAlchemy connection string (SQLite default or PostgreSQL URL) |
| `MODEL_CHECKPOINT_PATH` | `models/best_model.pth` | Path to ResNet-50 checkpoint |
| `DEFAULT_DEVICE` | `cuda` | Torch inference device (`cuda` falls back to `cpu` if unavailable) |
| `NASA_POWER_API_KEY` | `None` | Optional external key (loaded strictly from env / `.env`) |
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | Frontend API target (`frontend/.env`) |

> **Secret Safety:** Never commit `.env`, `*.pem`, `*.key`, or credential JSON files. All application logs pass through `SecretRedactingFilter` in `app/core/logging.py` to mask tokens, passwords, and Bearer headers.

---

## 2. Database & Alembic Migrations

Check current schema head and apply migrations:
```powershell
cd C:\Users\ACER\Intern21\smart-agriculture-platform
.\venv\Scripts\python.exe -m alembic heads
.\venv\Scripts\python.exe -m alembic current
.\venv\Scripts\python.exe -m alembic upgrade head
```

### Backup Procedure (SQLite)
```powershell
# Safe file-level backup while server is idle or via sqlite3 .backup
Copy-Item smart_ag.db "smart_ag_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
```

---

## 3. Service Startup

### Local Development
1. **Start Backend:**
   ```powershell
   .\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. **Start Frontend:**
   ```powershell
   cd frontend
   npm run dev -- --host 127.0.0.1 --port 5173
   ```

### Docker Compose
```powershell
docker compose up --build api
# With PostgreSQL:
docker compose --profile postgres up --build
```

---

## 4. Monitoring & Drift Checks

### Live API Drift Status
Poll `GET /api/v1/monitoring/status` (or open Swagger at `/docs`) to inspect recent persisted prediction confidences against the `0.85` reference baseline:
- `normal`: Confidence within expected operating range.
- `watch`: Mean confidence dropped by `>= 0.08`.
- `drift_alert`: Mean confidence dropped by `>= 0.15`.

### Offline Batch Drift Check
Use `pipelines/monitoring/drift_monitor.py` (`evaluate_monitoring_status`) to compare new tabular weather/soil batches against reference `(mean, std)` baselines.

---

## 5. Troubleshooting

| Symptom | Likely Cause | Resolution |
|---|---|---|
| Frontend shows `API Offline` | Backend not running or wrong port | Start `uvicorn app.main:app --port 8000`; check `VITE_API_BASE_URL` or Settings page |
| `alembic` command not found | Global PATH lacks venv Scripts | Run `.\venv\Scripts\python.exe -m alembic ...` |
| CUDA unavailable in `/api/v1/health` | CPU-only PyTorch or no GPU | Backend automatically falls back to CPU; verify `torch.cuda.is_available()` |
| `422 Unprocessable Entity` on observation | Invalid `epistemic_type` | Observations accept only `"observed"` or `"external"` |
| `404 Not Found` on `/twin/simulate` | Nonexistent `plot_id` | Omit `plot_id` for ephemeral runs or pass a valid Plot ID |
