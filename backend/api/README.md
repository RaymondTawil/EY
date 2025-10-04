# backend/api — API overview

This folder contains the FastAPI route wiring for the AI Credit Risk backend. The routes implement scoring, retrieval, LLM advice generation, and manual review actions.

What the API does (quick)
- POST /v1/score
  - Invokes the scorer to compute PD, decision (APPROVE/REVIEW/REJECT) and persists a record.
  - Implemented by [`backend.api.endpoints.scoring.score_and_store`](backend/api/endpoints/scoring.py).
  - If the system decision is REJECT, a client-facing message is generated via the improvement tips helpers before storing (uses [`backend.services.improvement_tips.recommend_improvements`](backend/services/improvement_tips.py) and [`backend.services.improvement_tips.format_client_message_llm`](backend/services/improvement_tips.py)).

- GET /v1/applications/{app_id}
  - Returns stored application summary (probability, decisions, thresholds, status).
  - Implemented by [`backend.api.endpoints.applications.get_application`](backend/api/endpoints/applications.py).

- POST /v1/applications/{app_id}/advice
  - Generates LLM advice for manual-review cases only (system_decision == REVIEW).
  - Implemented by [`backend.api.endpoints.advice.request_advice`](backend/api/endpoints/advice.py).
  - Uses OpenAI (if configured via settings) to produce concise recommendations.

- POST /v1/applications/{app_id}/review
  - Officer action to APPROVE or REJECT a REVIEW case; finalizes and closes the record.
  - Implemented by [`backend.api.endpoints.review.officer_decision`](backend/api/endpoints/review.py).
  - On officer REJECT, a client message is generated (uses improvement tips helpers).

Dependencies & internals
- DB access is supplied by the dependency in [`backend.api.deps.get_db`](backend/api/deps.py) and records are created/updated via [`backend.db.crud.create_application`](backend/db/crud.py) and [`backend.db.crud.get_application`](backend/db/crud.py).
- The API is mounted under the app created in [`backend.main.create_app`](backend/main.py) which sets the prefix (typically `/v1`).
- LLM behavior and prompts are controlled by settings in [`backend.config.settings`](backend/config.py) and the OpenAI client usage is in [backend/api/endpoints/advice.py](backend/api/endpoints/advice.py).

Testing
- Basic integration-style smoke tests and usage examples are in [test/api_test.py](test/api_test.py).

Notes
- Advice endpoint and LLM features require OPENAI credentials (see config).
- Business logic (scoring, policy thresholds, improvement tips) is implemented in the services layer (see [`backend.services.improvement_tips`](backend/services/improvement_tips.py) and [`backend.services.policy_core`](backend/services/policy_core.py)).

For quick usage examples, see [test/api_test.py](test/api_test.py).