"""Pydantic models for API request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Natural language query")
    chat_history: Optional[list[dict]] = Field(default=None, description="Previous conversation turns")
    session_id: Optional[str] = Field(default=None, description="Session identifier for multi-turn")


class QueryResponse(BaseModel):
    user_query: str
    sql: str
    explanation: str
    results: dict
    nl_answer: str
    tables_used: list[str]
    joins_used: list[dict]
    retrieval_scores: list[dict]
    retries: int
    error: Optional[str] = None


class SchemaResponse(BaseModel):
    tables: dict
    db_path: str


class IngestRequest(BaseModel):
    db_path: Optional[str] = Field(default=None, description="Path to SQLite database file")


class HealthResponse(BaseModel):
    status: str
    version: str
    db_loaded: bool
    tables_count: int
