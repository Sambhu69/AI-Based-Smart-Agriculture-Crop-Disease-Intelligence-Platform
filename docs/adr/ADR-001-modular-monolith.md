# Architecture Decision Record (ADR) 001: Adoption of Modular Monolith Backend

- **Status:** Accepted
- **Date:** 2026-11-21
- **Deciders:** Technical Architecture & ML Engineering Team
- **Context:** Stage 3 Architectural Refinement

---

## 1. Context and Problem Statement

The platform is designed to provide end-to-end crop disease diagnosis, field monitoring, and digital twin simulation. As the system transitioned from Stage 2 (model training and baseline API) to Stage 3 (backend architecture and database schema), we evaluated the target system architecture.

A common industry temptation in AI-driven distributed platforms is to immediately adopt microservices (e.g., spinning up separate services for Authentication, Disease Inference, Farm Topology, Sensor Ingestion, and Digital Twin Simulation, interconnected via message brokers like Kafka or Redis).

However, introducing distributed microservices prematurely at Stage 3 carries major liabilities:
1. **Operational Overhead:** Distributed networks introduce serialization, network latency, multi-repo or complex monorepo tooling, distributed transactions, and deployment orchestration (e.g. Kubernetes) that distract from core domain logic and model provenance.
2. **Resource Constraints:** Development and deployment occur on resource-constrained environments (e.g., local developer workstations with 16 GB RAM and single-GPU setups). Running multiple containerized microservices and message queues consumes excessive memory and CPU.
3. **Evolving Domain Boundaries:** In early project stages, domain boundaries between farm topology, sensory telemetry, and model inference are still stabilizing. Decomposing across network boundaries prematurely creates high risk of distributed monolith antipatterns.

## 2. Decision

We adopt a **Modular Monolith** architecture pattern located under `app/`.

### Key Architectural Boundaries:
- **`app/core/`**: Centralized configuration management using `pydantic-settings` and structured logging.
- **`app/db/`**: Clean database foundation with SQLAlchemy declarative models, session lifecycle management, Alembic migrations, and repository abstractions (`app/db/repositories.py`).
- **`app/schemas/`**: Strict Pydantic contracts decoupling wire payloads and internal database schemas.
- **`app/services/`**: Business and domain logic encapsulation. Notably, `disease_service.py` encapsulates model loading, inference, preprocessing, and metadata provenance, decoupling model execution from the route handlers.
- **`app/api/v1/`**: Versioned API endpoints providing clean routing for farm topologies, observations, simulations, and disease diagnostics.

### Strict Epistemic Provenance Separation
To avoid data contamination between real physical phenomena and synthetic outputs:
1. **`FieldObservation` (`epistemic_type="observed"` or `"external"`):** Real physical ground truth captured by IoT sensors, field scouts, or weather stations.
2. **`PredictionRecord` (`epistemic_type="predicted"`):** Analytical and ML outputs with explicit model versioning, confidence scores, and timestamps.
3. **`TwinScenario` (`epistemic_type="simulated"`):** Digital twin hypothetical simulations and projection results, strictly demarcated to prevent synthetic data from polluting real-world observation tables.

## 3. Consequences

### Positive:
- **Fast Developer Feedback Loop:** Single codebase, zero distributed debugging, standard in-process testability via `pytest` and `fastapi.testclient.TestClient`.
- **Low Footprint:** Runs comfortably within local workstation memory (no background broker processes, Redis, or PostGIS required).
- **Strong Isolation:** Code is organized by domain modules and layers. Cross-layer calls are strictly in-process and type-checked.
- **Auditability & Provenance:** Full traceability of predictions and twin scenarios in a unified database schema.

### Negative / Trade-offs:
- Requires strict engineering discipline to maintain boundaries and prevent circular dependencies or leaking database models directly into route signatures.
- High-compute workloads (e.g., heavy batch GPU inference) share runtime resources with web API handling unless decoupled in future stages.

## 4. Future Service-Extraction Possibilities

The modular monolith is explicitly organized to allow painless future decomposition into standalone microservices if and when warranted by scaling criteria:
1. **Crop Disease Inference Service:**
   - *Trigger for Extraction:* Inference request volume scales significantly or requires dedicated multi-GPU cluster autoscaling separate from CRUD traffic.
   - *Extraction Mechanism:* `app/services/disease_service.py` and its schema contracts can be cleanly wrapped into a dedicated microservice (or Triton Inference Server container) without changing client contracts.
2. **Digital Twin Simulation Engine:**
   - *Trigger for Extraction:* Compute-intensive numerical simulation (e.g., long-horizon crop growth models) demands asynchronous distributed worker queues (Celery/RabbitMQ).
   - *Extraction Mechanism:* `TwinScenario` domain logic can be shifted to background worker nodes, reading and emitting events via message queues.
3. **Telemetry & Sensor Ingestion Pipeline:**
   - *Trigger for Extraction:* High-frequency IoT streaming telemetry exceeds standard relational write throughput.
   - *Extraction Mechanism:* Dedicated stream ingest worker writing to a time-series optimized store.
