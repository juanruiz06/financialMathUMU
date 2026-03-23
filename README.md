# Quantitative Finance Engineering Platform (WIP)

**Tech Stack:** Python (NumPy/SciPy), Node.js, TypeScript, Docker, Streamlit.

## Live Endpoints

- Frontend: [https://financialmathumu.streamlit.app]
- API Health Check: [https://financialmathumu-production.up.railway.app/health]

---

## 1) Academic Context (Work in Progress)

This repository is a **work in progress (WIP)** developed in the context of a **Student Intern / Undergraduate Research Assistant** role at the **University of Murcia (UMU)**.

The project objective is explicit: to connect **Quantitative Finance theory** with **Modern Software Engineering practices** in a production-minded architecture.  
In practical terms, this means building mathematically coherent pricing and hedging workflows while enforcing engineering discipline in validation, deployment, observability, and resilience.

---

## 2) Mathematical Rigor (The Engine)

The computational core is implemented in **Python** with **NumPy/SciPy**.

### Core Models

- **Geometric Brownian Motion (GBM)** simulation for path generation.
- **Black-Scholes** pricing for analytical benchmark and theoretical valuation.

### Discrete Delta Hedging

The platform implements a discrete-time delta hedging loop with:

- Stepwise rebalancing under configurable frequency.
- **Cash account adjustments** with interest accrual through time.
- Path-by-path comparison of replication portfolio value against theoretical option value.

### Pathological Cases Handling

Special handling is included for numerically unstable regimes, especially:

- **Binary options near maturity**, where delta can become extremely unstable.
- Stability logic in the engine to avoid explosive hedge behavior close to expiry.

---

## 3) Backend & Architecture Craftsmanship

The system uses a lightweight distributed architecture:

- **API Gateway** in **Node.js + TypeScript**.
- **Python compute engine** invoked through a CLI bridge (`cli_bridge.py`).

### Security and Resilience by Design

- Strict request validation with **Zod** (numeric typing + safe ranges).
- Runtime guards for high-cost workloads (bounded simulation parameters).
- Controlled subprocess execution with explicit buffering and execution timeouts.
- Health endpoint support for deployment probes.

### Network Payload Slicing (Latency Optimization)

To preserve statistical quality without overloading the network:

- Python computes the full Monte Carlo sample (e.g., **10,000 paths**) for robust final metrics.
- The backend returns only a lightweight subset of trajectories for line plotting (e.g., **50 paths**).
- Final-price vectors are sent separately for histogram and probability metrics.

This sharply reduces transfer size and frontend parsing overhead while maintaining quantitative fidelity.

### Immutable Delivery with Docker

Deployment is containerized via a **multi-stage Docker build**:

- Build stage compiles TypeScript artifacts.
- Runtime stage includes only required execution assets (Node runtime + Python engine + dependencies).

This approach improves reproducibility and keeps runtime images deterministic and auditable.

---

## Local Run (Docker Compose)

From the repository root:

```bash
docker compose up --build
```

Default API port:

- `http://localhost:3000`

---

## Repository Snapshot

- `backend/server.ts`: API Gateway, request schemas, process orchestration.
- `cli_bridge.py`: Python bridge for pricing and hedging actions.
- `engine/`: quantitative models and numerical finance primitives.
- `pages/`: Streamlit UI pages for pricing and hedging analysis.
