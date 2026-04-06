"""
Vector Retrieval Module
Converts user query to vector and retrieves relevant tables/columns.
"""
from sklearn.metrics.pairwise import cosine_similarity
from ..config import settings


class VectorRetriever:
    """Retrieves relevant schema elements using TF-IDF similarity."""

    def __init__(self, schema_ingestion):
        self.ingestion = schema_ingestion

    def retrieve_tables(self, query: str, top_k: int = None) -> list[dict]:
        """Retrieve most relevant tables for a natural language query."""
        top_k = top_k or settings.TOP_K_TABLES
        if self.ingestion.table_vectorizer is None:
            return []

        query_vec = self.ingestion.table_vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.ingestion.table_vectors).flatten()

        # Get top-k indices
        top_indices = similarities.argsort()[::-1][:top_k]

        results = []
        for idx in top_indices:
            if similarities[idx] > 0.01:  # minimum relevance threshold
                table_name = self.ingestion.table_names[idx]
                results.append({
                    "table": table_name,
                    "score": float(similarities[idx]),
                    "summary": self.ingestion.table_docs[idx],
                    "schema": self.ingestion.schema_info.get(table_name, {})
                })
        return results

    def retrieve_columns(self, query: str, top_k: int = None) -> list[dict]:
        """Retrieve most relevant columns for a natural language query."""
        top_k = top_k or settings.TOP_K_COLUMNS
        if self.ingestion.vectorizer is None:
            return []

        query_vec = self.ingestion.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.ingestion.column_vectors).flatten()

        top_indices = similarities.argsort()[::-1][:top_k]

        results = []
        for idx in top_indices:
            if similarities[idx] > 0.01:
                table, col, col_type, desc = self.ingestion.column_index[idx]
                results.append({
                    "table": table,
                    "column": col,
                    "type": col_type,
                    "score": float(similarities[idx]),
                })
        return results

    def retrieve(self, query: str) -> dict:
        """Combined retrieval of relevant tables and columns."""
        tables = self.retrieve_tables(query)
        columns = self.retrieve_columns(query)

        # Deduplicate tables from column results
        retrieved_tables = set(t["table"] for t in tables)
        for col in columns:
            if col["table"] not in retrieved_tables:
                retrieved_tables.add(col["table"])
                # Add the table if found through column search
                if col["table"] in self.ingestion.schema_info:
                    idx = self.ingestion.table_names.index(col["table"]) if col["table"] in self.ingestion.table_names else None
                    if idx is not None:
                        tables.append({
                            "table": col["table"],
                            "score": col["score"] * 0.8,  # slightly lower confidence
                            "summary": self.ingestion.table_docs[idx],
                            "schema": self.ingestion.schema_info.get(col["table"], {})
                        })

        return {
            "tables": tables,
            "columns": columns,
            "table_names": list(retrieved_tables)
        }
