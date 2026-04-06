"""
NL-to-SQL AI Engine — FastAPI Application
Main entry point for the AI backend service.
"""
import os
import shutil
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .models.schemas import (
    QueryRequest, QueryResponse, SchemaResponse,
    IngestRequest, HealthResponse
)
from .modules.orchestrator import QueryOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator = QueryOrchestrator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("🚀 Starting NL-to-SQL AI Engine...")
    try:
        orchestrator.initialize()
        logger.info("✅ Engine initialized with sample database.")
    except Exception as e:
        logger.error(f"⚠️ Initialization error: {e}. Engine will initialize on first query.")
    yield
    logger.info("Shutting down...")
    await orchestrator.cleanup()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health & Schema ─────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        db_loaded=orchestrator._initialized,
        tables_count=len(orchestrator.ingestion.schema_info) if orchestrator._initialized else 0
    )


@app.get("/schema", response_model=SchemaResponse)
async def get_schema():
    """Get current database schema summary."""
    if not orchestrator._initialized:
        raise HTTPException(status_code=503, detail="Engine not initialized. Upload a database first.")
    return SchemaResponse(
        tables=orchestrator.get_schema_summary(),
        db_path=settings.DB_PATH
    )


# ─── Query Endpoint ──────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a natural language query and return SQL + results."""
    if not orchestrator._initialized:
        raise HTTPException(status_code=503, detail="Engine not initialized. Upload a database first.")

    try:
        result = await orchestrator.process_query(
            user_query=request.query,
            chat_history=request.chat_history
        )
        return QueryResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Query processing error")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ─── Database Management ─────────────────────────────────────────

@app.post("/ingest")
async def ingest_schema(request: IngestRequest):
    """Re-ingest schema from current or specified database."""
    try:
        orchestrator.reingest(db_path=request.db_path)
        return {
            "status": "success",
            "tables": list(orchestrator.ingestion.schema_info.keys()),
            "message": "Schema ingested successfully."
        }
    except Exception as e:
        logger.exception("Ingestion error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-db")
async def upload_database(file: UploadFile = File(...)):
    """Upload a SQLite database file."""
    if not file.filename.endswith(('.db', '.sqlite', '.sqlite3')):
        raise HTTPException(status_code=400, detail="Only .db, .sqlite, .sqlite3 files are accepted.")

    # Save uploaded file
    upload_dir = os.path.join(settings.DATA_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    db_path = os.path.join(upload_dir, file.filename)

    try:
        with open(db_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Reingest with new database
        orchestrator.reingest(db_path=db_path)

        return {
            "status": "success",
            "db_path": db_path,
            "tables": list(orchestrator.ingestion.schema_info.keys()),
            "message": f"Database '{file.filename}' uploaded and ingested."
        }
    except Exception as e:
        logger.exception("Upload error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/connect-db")
async def connect_database(request: IngestRequest):
    """Connect to an existing SQLite database by path."""
    if not request.db_path:
        raise HTTPException(status_code=400, detail="db_path is required.")
    if not os.path.exists(request.db_path):
        raise HTTPException(status_code=404, detail=f"Database not found: {request.db_path}")

    try:
        orchestrator.reingest(db_path=request.db_path)
        return {
            "status": "success",
            "tables": list(orchestrator.ingestion.schema_info.keys()),
            "message": f"Connected to {request.db_path}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Run directly ────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
