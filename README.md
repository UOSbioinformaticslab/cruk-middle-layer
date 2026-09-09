# CRUK Middle Layer Proxy

The **CRUK Middle Layer Proxy** is an administrative FastAPI microservice running on `http://localhost:8002`. It handles CRUK-specific administrative operations, Data Custodian onboarding team applications (`TeamRequest`), and centralized system error logging (`ErrorLog`).

---

## 🚀 System Setup & Quick Start

### System Architecture Overview

The CRUK Metadata Catalogue consists of five inter-connected repositories:

1. **Frontend Landing Page** (`CRUK_datahub_landing_page`) — [`git@github.com:UOSbioinformaticslab/CRUK_datahub_landing_page.git`](https://github.com/UOSbioinformaticslab/CRUK_datahub_landing_page)
   * **Role**: React/Vite user interface running on `http://localhost:5173`. Provides dataset browsing, search, metadata upload forms, custodian management, and live schema documentation views.
2. **Basic Backend** (`basic/basic_backend`) — [`git@github.com:UOSbioinformaticslab/basic_backend.git`](https://github.com/UOSbioinformaticslab/basic_backend)
   * **Role**: Core FastAPI database backend running on `http://localhost:8000`. Manages Users, Teams, Datasets (JSON metadata blobs & draft states), Projects, Publications, Tools, and Team Invitations.
3. **Middle Layer Proxy** (`middle`) — [`git@github.com:UOSbioinformaticslab/cruk-middle-layer.git`](https://github.com/UOSbioinformaticslab/cruk-middle-layer) — *(You are here)*
   * **Role**: Administrative FastAPI service running on `http://localhost:8002`. Manages new Data Custodian team request applications (`TeamRequest`) and centralized system error logging (`ErrorLog`).
4. **CRUK Semantic Schema Viewer & Package** (`semantic-schema/cruk-semantic-schema`) — [`git@github.com:UOSbioinformaticslab/cruk-semantic-schema.git`](https://github.com/UOSbioinformaticslab/cruk-semantic-schema)
   * **Role**: React component library & standalone interactive UI for rendering the CRUK 1.0.0 semantic schema overlay dynamically fetched from HDRUK schemata.
5. **AI Microservices** (`ai/ai-microservices`) — *Optional / Private Repository* — [`git@github.com:UOSbioinformaticslab/ai-microservices.git`](https://github.com/UOSbioinformaticslab/ai-microservices)
   * **Role**: FastAPI AI microservice running on `http://localhost:8001`. Powered by Google Gemini API for intelligent metadata extraction, automated tagging, and semantic search assistance. Note: This repository is private. If you do not have access to it or do not have a Gemini API key, the rest of the CRUK catalogue will run fully and seamlessly without it.

---

### Environment Setup (`.env` Configuration)

Before running the middle layer proxy, a `.env` file must be present in this folder:

1. **Automatic Setup**: Running `./start_all.sh` will automatically create `.env` from `.env.example` if missing.
2. **Manual Setup**: Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. **Variable Breakdown**:
   * `DATABASE_URL`: Connection string for the middle layer database storing team onboarding requests and error logs (defaults to local SQLite `sqlite:///./middlelayer.db`).

Example `.env` configuration:

```env
DATABASE_URL="sqlite:///./middlelayer.db"
```

---

### Running Locally

To spin up the service locally on port 8002:

```bash
uvicorn main:app --reload --port 8002
```

To start the complete system:

```bash
# From workspace root or CRUK_datahub_landing_page
./start_all.sh
```

View interactive Swagger API documentation at `http://localhost:8002/docs`.