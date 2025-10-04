# EY AI Credit Risk – MVP

## Summary
- An auditable decisioning MVP that predicts borrower default probability (PD) and maps PD to actions (APPROVE / REVIEW / REJECT).
- Includes: exploratory data analysis (EDA) notebooks, model training artifacts (XGBoost + baseline), a FastAPI backend that applies policy & persists applications, and a Streamlit UI for submission and review.

## Problem framing
- Business objective: given a loan application payload, estimate the probability of default and convert that score into an explicit, auditable decision under a documented policy (dual thresholds and optional top-K).
- Key requirements:
  - Transparent feature set and policy thresholds.
  - Reproducible EDA → model training → artifact export.
  - Lightweight API to score and persist, plus a simple UI for reviewers and demonstration.

## How the work progressed (EDA → Models → API & UI)
1. EDA
   - Notebook-driven exploration to understand feature distributions, missingness, target definition and to produce a stable feature set and engineered variables (emp_length_num, term_num, percent coercion, bands).
   - Location: `eda/accepted_eda.ipynb`, `eda/rejected_eda.ipynb`
   - Outputs: cleaned accepted sample CSV (`eda/lc_accepted_outputs/accepted_subset_clean.csv`) and visualizations under `eda/`.

2. Modeling
   - Baseline: simple DecisionTree pipeline to establish a reference.
     - Notebook: `models/baseline.ipynb`
   - Improved: XGBoost pipeline with ColumnTransformer, imputation, OneHot encoding and targeted metric tracking (PR-AUC / ROC-AUC).
     - Notebook: `models/improved.ipynb`
   - Artifacts and metadata exported to `models/saved_models/` (including `xgb_1.joblib`, `best_model_metadata.json`, `best_model_policy.json`).

3. Policy
   - Policy notebook documented the dual-threshold policy: auto-approve low PD, auto-reject high PD, and flag a gray-zone for manual review.
   - Policy values are stored alongside model metadata for reproducibility: `models/saved_models/best_model_metadata.json`.

4. Backend & API
   - FastAPI service that:
     - Normalizes incoming payloads to the model feature set (`backend/services/policy_core.py`),
     - Loads model artifacts and metadata to compute PD and map to decision,
     - Persists application records (`backend/db/`),
     - Optionally returns concise improvement advice (LLM-backed) for REVIEW cases.
   - Key files:
     - App entry: `backend/main.py`
     - Scoring endpoint: `backend/api/endpoints/scoring.py`
     - Advice / review endpoints: `backend/api/endpoints/advice.py`, `backend/api/endpoints/review.py`
     - DB models & CRUD: `backend/db/models.py`, `backend/db/crud.py`

5. UI
   - Streamlit app for submitting example payloads, viewing PD, decision badges, thresholds, and LLM advice.
   - File: `ui/Home.py`
   - The UI calls the backend endpoints (`/v1/score`, `/v1/applications/{id}`).

## Project layout (important files)
- eda/
  - accepted_eda.ipynb, rejected_eda.ipynb, lc_accepted_outputs/
- models/
  - baseline.ipynb, improved.ipynb, policy.ipynb
  - saved_models/ (model artifacts and metadata)
- backend/
  - main.py, config.py
  - api/endpoints/ (scoring, advice, applications, review)
  - services/policy_core.py, improvement_tips.py
  - db/ (models.py, crud.py, schemas.py, session.py)
- ui/
  - Home.py
- data/
  - accepted_2007_to_2018Q4.csv, rejected_2007_to_2018Q4.csv
- test/
  - api_test.py

## Quick start (Windows)
1. Create and activate virtual environment
   - python -m venv .venv
   - .venv\Scripts\activate

2. Install requirements (add project requirements file if absent)
   - pip install -r requirements.txt

3. Set required environment variables
   - set OPENAI_API_KEY=your_key_here
   - set DATABASE_URL=sqlite:///./app.db   (or your preferred DB)

4. Run backend (development)
   - uvicorn backend.main:app --reload --port 8000

5. Run UI (in a separate terminal)
   - streamlit run ui/Home.py

## Quick start docker
1. Build the image
   - docker compose build
2. Run the containers
   - docker compose up
3. Access the UI at http://localhost:8501 and the API docs at http://localhost:8000/docs


## Model & policy artifacts
- Models and metadata live in `models/saved_models/`.
- Key files:
  - `xgb_1.joblib` — trained XGBoost artifact used by the backend.
  - `best_model_metadata.json` — selected thresholds (thr_reject / thr_review), feature_set and model_version.
  - `best_model_policy.json` — exported policy definition for traceability.

## Testing & validation
- Basic integration tests exist under `test/api_test.py` covering the score flow and expected decisions.
- Recommended additions:
  - Unit tests for `backend/services/policy_core.normalize_payload` (edge cases: missing fields, string percent parsing).
  - Integration test that exercises the UI → API end-to-end (Streamlit calls mocked or endpoint exercised directly).

## Next steps (product / production priorities)
### Short term
- Improve model with more labeled data, stronger feature engineering and robust cross‑validation (time‑aware CV if applicable).
- Replace sqlite with Postgres (or managed DB). Use migrations (Alembic) and connection pooling.
- Move Streamlit demo to a small frontend (React/Vue) for better UX and RBAC.

### Operational & product improvements
- Model lifecycle: model registry (MLflow or similar), versioning and automated retraining pipelines.
- Observability: request / prediction logging, prediction drift monitoring, business metric dashboards, alerting.
- Security & governance: input validation, rate limiting, authentication/authorization (OAuth2/JWT), secrets management (Vault/Azure Key Vault).
- Testing & CI/CD: unit tests, integration tests, docker image scanning, automated deployments and canary releases.
- Data platform: reliable ingestion, feature store for consistent features in training/serving, and lineage tracking.
- Performance & scaling: container orchestration (Kubernetes), autoscaling, caching and model serving (Triton or Seldon for higher QPS).
- Compliance & audit: immutable audit logs, model cards, documented policy changes, retention policies.

### Longer term productization
- A/B testing or online learning to compare models in production.
- Human-in-the-loop workflows for reviewers with annotations that feed back into training data.
