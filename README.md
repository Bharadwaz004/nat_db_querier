# ⚡ Hybrid Graph + Vector RAG — NL-to-SQL Assistant

A production-grade AI system that converts natural language questions into accurate SQL queries using a **hybrid retrieval architecture** combining Vector RAG (semantic schema search) and Graph-based relationship inference (automatic join generation).

![Architecture: React → Node.js Gateway → FastAPI AI Engine → (Vector DB + Graph Store + SQLite)](https://img.shields.io/badge/Architecture-Hybrid_RAG-blue)
![Tests: 31 passing](https://img.shields.io/badge/Tests-31_passing-green)
![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue)
![Node.js 18+](https://img.shields.io/badge/Node.js-18+-green)

---

## How It Works

```
User Question
     │
     ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  React UI   │────▶│  Node.js     │────▶│  FastAPI         │
│  (Chat)     │◀────│  Gateway     │◀────│  AI Engine       │
└─────────────┘     │  • JWT Auth  │     │                  │
                    │  • Rate Limit│     │  1. Vector Search│
                    │  • Sessions  │     │  2. Graph Joins  │
                    └──────────────┘     │  3. Context Build│
                                        │  4. LLM → SQL    │
                                        │  5. Validate      │
                                        │  6. Execute       │
                                        │  7. NL Response   │
                                        └─────────────────┘
```

**Pipeline steps:**

1. **Vector Retrieval** — TF-IDF embeddings find relevant tables and columns from your query
2. **Graph Traversal** — BFS over FK relationships discovers join paths between tables
3. **Context Building** — Schema + joins assembled into a structured LLM prompt
4. **SQL Generation** — LLM generates SQL with strict schema constraints
5. **Validation + Retry** — SQL validated against schema; auto-retries on errors (up to 3x)
6. **Execution** — Read-only query executed on SQLite with safety guards
7. **NL Response** — Results converted to a human-readable answer

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- An Anthropic API key (or HuggingFace API key)

### 1. Clone & Install

```bash
# Install Python dependencies
cd backend_fastapi
pip install -r requirements.txt

# Install Node.js dependencies
cd ../backend-node
npm install

# Install frontend dependencies
cd ../frontend
npm install
```

### 2. Configure

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your API key:
#   ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Create Sample Database

```bash
python data/create_sample_db.py
```

### 4. Start All Services

```bash
# Option A: Use the startup script
./start.sh

# Option B: Start each service individually
# Terminal 1 — FastAPI AI Engine
PYTHONPATH=. python -m uvicorn backend_fastapi.src.main:app --port 8000 --reload

# Terminal 2 — Node.js Gateway
cd backend-node && PORT=3001 node src/server.js

# Terminal 3 — React Frontend
cd frontend && npx vite
```

### 5. Open the App

Navigate to **http://localhost:5173** and start asking questions!

---

## Docker Deployment

```bash
# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# Build and run
docker-compose up --build
```

Services will be available at:
- Frontend: http://localhost:5173
- API Gateway: http://localhost:3001
- AI Engine: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs

---

## Project Structure

```
nlsql/
├── frontend/                    # React + Vite chat UI
│   └── src/
│       ├── App.jsx              # Main app with chat logic
│       ├── components/
│       │   ├── ChatMessage.jsx  # Message rendering (SQL, results, explanation)
│       │   ├── ConnectionModal.jsx  # DB connection chooser
│       │   └── Sidebar.jsx      # Schema explorer panel
│       ├── hooks/api.js         # API client
│       └── styles/global.css    # Dark theme styles
│
├── backend-node/                # Node.js API Gateway
│   └── src/server.js            # Express + JWT + rate limiting + proxy
│
├── backend_fastapi/             # Python AI Engine
│   └── src/
│       ├── main.py              # FastAPI app with endpoints
│       ├── config.py            # Environment configuration
│       ├── modules/
│       │   ├── schema_ingestion.py   # Extract schema → embeddings + graph
│       │   ├── vector_retrieval.py   # TF-IDF similarity search
│       │   ├── graph_traversal.py    # BFS join path discovery
│       │   ├── context_builder.py    # Prompt construction
│       │   ├── llm_provider.py       # Anthropic / HuggingFace API
│       │   ├── sql_validator.py      # Schema validation + safety
│       │   ├── sql_executor.py       # Read-only SQL execution
│       │   └── orchestrator.py       # Full pipeline orchestration
│       └── models/schemas.py    # Pydantic request/response models
│
├── data/
│   ├── create_sample_db.py      # Sample e-commerce DB generator
│   └── sample_ecommerce.db      # Generated SQLite database
│
├── embeddings/                  # Cached TF-IDF vectors
├── graph/                       # FK relationship graph (JSON)
├── tests/test_pipeline.py       # 31 unit + integration tests
├── docker/                      # Dockerfiles for each service
├── docker-compose.yml
├── start.sh                     # One-command startup script
└── .env.example                 # Environment template
```

---

## API Endpoints

### Node.js Gateway (port 3001)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/guest` | No | Get a guest JWT token |
| POST | `/api/auth/register` | No | Register with username/password |
| POST | `/api/auth/login` | No | Login and get JWT token |
| POST | `/api/sessions` | JWT | Create a new chat session |
| POST | `/api/query` | JWT | Send NL query (proxied to FastAPI) |
| GET | `/api/schema` | JWT | Get database schema |
| POST | `/api/upload-db` | JWT | Upload a SQLite database |
| POST | `/api/connect-db` | JWT | Connect to existing DB by path |
| GET | `/api/health` | No | Health check |

### FastAPI AI Engine (port 8000)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/query` | Process NL query → SQL → results |
| GET | `/schema` | Get current schema summary |
| POST | `/ingest` | Re-run schema ingestion |
| POST | `/upload-db` | Upload SQLite file |
| POST | `/connect-db` | Connect to DB by path |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger API documentation |

---

## Sample Queries

The included e-commerce database supports queries like:

- "What are the top 5 best-selling products?"
- "Show me customers who spent more than $500"
- "Which product category has the highest average rating?"
- "List orders from last month with their items"
- "What is the total revenue by payment method?"
- "Which products are running low on inventory?"
- "How many customers are in each state?"
- "What's the average order value for credit card payments?"

---

## Configuration

### LLM Provider

Set `LLM_PROVIDER` in `.env`:

- **`anthropic`** (default) — Uses Claude API. Set `ANTHROPIC_API_KEY`.
- **`huggingface`** — Uses HF Inference API. Set `HF_API_KEY`, `HF_API_URL`, and `HF_MODEL`.

| Variable | Default | Description |
|----------|---------|-------------|
| `HF_API_URL` | `https://router.huggingface.co/v1` | HF Router API base URL (OpenAI-compatible; change for dedicated endpoints or local TGI) |

### Retrieval Tuning

| Variable | Default | Description |
|----------|---------|-------------|
| `TOP_K_TABLES` | 5 | Max tables retrieved per query |
| `TOP_K_COLUMNS` | 15 | Max columns retrieved per query |
| `MAX_RETRIES` | 3 | SQL generation retry attempts |

---

## Running Tests

```bash
cd nlsql
PYTHONPATH=. python -m pytest tests/ -v
```

All 31 tests cover: schema ingestion, vector retrieval, graph traversal, SQL validation, SQL execution, context building, and end-to-end integration.

---

## Security

- **JWT authentication** on all API endpoints
- **Rate limiting** (100 requests per 15 minutes)
- **SQL injection prevention** — only SELECT/WITH queries allowed; EXPLAIN-based validation
- **Read-only database access** via `PRAGMA query_only = ON`
- **Input validation** with Pydantic models
- **DML blocking** — DROP, DELETE, INSERT, UPDATE, ALTER, CREATE all rejected

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, CSS |
| API Gateway | Node.js, Express, JWT, bcrypt |
| AI Engine | Python, FastAPI, scikit-learn |
| Vector Search | TF-IDF + Cosine Similarity |
| Graph Store | JSON adjacency list |
| LLM | Anthropic Claude / HuggingFace |
| Database | SQLite |
| Containerization | Docker, Docker Compose |

---

## License

MIT
