# NeuralPulse - AI News Intelligence Platform

NeuralPulse is a production-grade, end-to-end automated news monitoring and analytics platform. It orchestrates a multi-agent AI system that crawls raw web content, evaluates credibility, calculates sentiment, extracts key entities, indexes embeddings into a vector store, and hosts a RAG (Retrieval-Augmented Generation) chat assistant to query news archives in real-time.

---

## Technical Stack & Architecture

NeuralPulse is built using a decoupled, multi-tier microservice architecture:

```
                      [ Next.js 15 Client App ]
                                 |
                                 | (HTTP API & WebSockets)
                                 v
                     [ FastAPI Router Backend ]
                       |         |         |
                       |         |         |
          +------------+         |         +------------+
          |                      |                      |
          v                      v                      v
    [ PostgreSQL ]           [ Redis ]             [ ChromaDB ]
  (Relational Data)    (Pub/Sub & Caching)       (Vector Indexes)
                                 ^
                                 |
                        [ Celery Workers ]
                    (Multi-Agent AI Pipelines)
```

- **Frontend**: Next.js 15 (App Router), TypeScript, TailwindCSS, Lucide Icons, and Axios client with concurrent-safe automatic token refresh interceptors.
- **Backend Core**: FastAPI (Python 3.11), SQLAlchemy 2.0 Async engine (PostgreSQL), and async `redis-py` database sessions.
- **Background workers**: Celery backed by Redis brokers executing ingestion pipelines and multi-agent AI tasks.
- **Vector Database**: ChromaDB storing contextual document indexes for semantic search and RAG completions.
- **Authentication**: JWT access and refresh token rotation with secure, HTTP-only SameSite cookies and session database revocation.

---

## Directory Structure

```
├── backend/app/                 # FastAPI core application files (flat structure)
│   ├── auth/                    # JWT token creation and encryption utilities
│   ├── middleware/              # Audit logging request tracking
│   ├── routers/                 # REST API endpoints (Auth, News, WebSockets)
│   ├── database.py              # Async SQLAlchemy engine
│   ├── main.py                  # API gateway entrypoint
│   ├── models.py                # Database entity mappings
│   ├── schemas.py               # Pydantic validation models
│   └── services.py              # Business logic controllers
│
├── frontend/src/                # Next.js 15 App Router client app
│   ├── app/                     # Layouts, login screens, dashboard views, live feed
│   ├── components/              # Sidebar wrappers and ProtectedRoute guards
│   ├── context/                 # Global AuthContext providers
│   ├── hooks/                   # useWebSocket connections
│   └── lib/                     # Axios API clients
│
├── ingestion/                   # RSS & crawler news fetch pipelines
├── ai_agents/                   # Multi-Agent credibility and analysis models
├── vector_store/                # ChromaDB vector store clients
├── workers/                     # Celery background tasks
├── shared/                      # Shared TypeScript models
└── infrastructure/              # Multi-container Docker configurations
```

---

## Key Features Implemented

1. **Multi-Agent Analysis Pipeline**:
   - **Fact-Checker Agent**: Evaluates article titles and bodies to calculate a source credibility score (0.0 to 1.0).
   - **Sentiment & Entity Agent**: Extracted key named organizations, places, or technologies, and scores positive/negative sentiment.
   - **Synthesis Agent**: Creates concise executive summaries.
2. **AI RAG Chat Assistant**:
   - Retrieval-Augmented Generation chat console that fetches the top 4 matched documents from ChromaDB, constructs a system prompt, queries the LLM, and streams references back to the client interface with collapsible citations.
3. **Double-Token Auth Rotation**:
   - Encrypts passwords using `bcrypt`. Generates short-lived access keys and rotated refresh keys. Refresh keys are stored in database sessions and delivered in HTTP-only cookies to secure sessions against XSS and replay attacks.
4. **WebSocket Live Feed**:
   - Establishes persistent socket channels from Next.js. Listens to Redis pub/sub channels to deliver real-time news crawler logs to screens without forcing page refreshes.

---

## Installation & Setup

### Option 1: Docker Compose (Recommended)

To run the entire NeuralPulse infrastructure (6 containers) out-of-the-box:

1. Clone this repository.
2. Copy the `.env.example` template:
   ```bash
   cp .env.example .env
   ```
3. Run the container cluster:
   ```bash
   docker compose up --build -d
   ```
4. Access the client app at `http://localhost:3000` and the API documentation at `http://localhost:8000/docs`.

### Option 2: Local Development Setup

#### 1. Backend and Workers
1. Navigate to the root directory and install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. Make sure PostgreSQL, Redis, and ChromaDB instances are running.
3. Start the FastAPI API server:
   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```
4. Start the Celery task worker:
   ```bash
   celery -A workers.celery_app worker --loglevel=info
   ```

#### 2. Frontend
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install node dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
4. Visit `http://localhost:3000` in your web browser.

---

## Environment Configuration

A complete list of configurations is supplied in [env.example](file:///d:/coding/news/.env.example):
- `OPENAI_API_KEY`: Supply this key to run the multi-agent LLM analyzer and RAG chat. If empty, the platform falls back gracefully to a rules-based local semantic analyzer.
- `POSTGRES_USER` / `POSTGRES_PASSWORD` / `DATABASE_URL`: Relational DB credentials.
- `REDIS_URL` / `CELERY_BROKER_URL`: Cache and message broker configurations.
- `JWT_SECRET`: Hexadecimal key for securing token encryptions.
