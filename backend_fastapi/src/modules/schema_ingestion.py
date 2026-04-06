"""
Schema Ingestion Pipeline
Extracts schema from SQLite, generates embeddings and relationship graph.
"""
import sqlite3
import json
import os
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from ..config import settings

class SchemaIngestion:
    """Extracts and indexes database schema for retrieval."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DB_PATH
        self.schema_info = {}       # table -> {columns, fks, description}
        self.column_docs = []       # list of semantic column descriptions
        self.column_index = []      # parallel list: (table, column, type, desc)
        self.table_docs = []        # table-level summaries
        self.table_names = []       # parallel list of table names
        self.graph = {}             # adjacency list for FK relationships
        self.vectorizer = None
        self.column_vectors = None
        self.table_vectorizer = None
        self.table_vectors = None

    def extract_schema(self) -> dict:
        """Extract full schema from SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]

        schema = {}
        for table in tables:
            # Column info
            cursor.execute(f"PRAGMA table_info('{table}')")
            columns = []
            for col in cursor.fetchall():
                columns.append({
                    "name": col[1],
                    "type": col[2],
                    "nullable": not col[3],
                    "primary_key": bool(col[5]),
                    "default": col[4]
                })

            # Foreign keys
            cursor.execute(f"PRAGMA foreign_key_list('{table}')")
            fks = []
            for fk in cursor.fetchall():
                fks.append({
                    "from_column": fk[3],
                    "to_table": fk[2],
                    "to_column": fk[4]
                })

            # Row count
            cursor.execute(f"SELECT COUNT(*) FROM '{table}'")
            row_count = cursor.fetchone()[0]

            # Sample data (first 3 rows)
            cursor.execute(f"SELECT * FROM '{table}' LIMIT 3")
            sample_rows = cursor.fetchall()
            col_names = [c["name"] for c in columns]

            schema[table] = {
                "columns": columns,
                "foreign_keys": fks,
                "row_count": row_count,
                "sample_data": [dict(zip(col_names, row)) for row in sample_rows]
            }

        conn.close()
        self.schema_info = schema
        return schema

    def generate_descriptions(self):
        """Generate semantic descriptions for tables and columns."""
        self.column_docs = []
        self.column_index = []
        self.table_docs = []
        self.table_names = []

        for table, info in self.schema_info.items():
            # Table-level summary
            col_names = [c["name"] for c in info["columns"]]
            pk_cols = [c["name"] for c in info["columns"] if c["primary_key"]]
            fk_desc = "; ".join([f"{fk['from_column']} -> {fk['to_table']}.{fk['to_column']}" for fk in info["foreign_keys"]])

            table_summary = (
                f"Table '{table}' stores {info['row_count']} records. "
                f"Columns: {', '.join(col_names)}. "
                f"Primary key: {', '.join(pk_cols) if pk_cols else 'auto'}. "
                f"{'Foreign keys: ' + fk_desc + '.' if fk_desc else 'No foreign keys.'}"
            )
            self.table_docs.append(table_summary)
            self.table_names.append(table)

            # Column-level descriptions
            for col in info["columns"]:
                semantic_desc = (
                    f"Column '{col['name']}' in table '{table}' "
                    f"of type {col['type']}. "
                    f"{'Primary key.' if col['primary_key'] else ''} "
                    f"{'Nullable.' if col['nullable'] else 'Not null.'} "
                    f"{table} {col['name']} {col['type']}"
                )
                self.column_docs.append(semantic_desc)
                self.column_index.append((table, col["name"], col["type"], semantic_desc))

    def build_graph(self):
        """Build a relationship graph from foreign keys."""
        self.graph = {}
        for table, info in self.schema_info.items():
            if table not in self.graph:
                self.graph[table] = []
            for fk in info["foreign_keys"]:
                edge = {
                    "from_table": table,
                    "from_column": fk["from_column"],
                    "to_table": fk["to_table"],
                    "to_column": fk["to_column"],
                    "relationship": "many_to_one"
                }
                self.graph[table].append(edge)
                # Add reverse edge
                if fk["to_table"] not in self.graph:
                    self.graph[fk["to_table"]] = []
                self.graph[fk["to_table"]].append({
                    "from_table": fk["to_table"],
                    "from_column": fk["to_column"],
                    "to_table": table,
                    "to_column": fk["from_column"],
                    "relationship": "one_to_many"
                })

    def build_embeddings(self):
        """Build TF-IDF vector index for schema retrieval."""
        # Column vectors
        if self.column_docs:
            self.vectorizer = TfidfVectorizer(
                stop_words='english',
                max_features=5000,
                ngram_range=(1, 2)
            )
            self.column_vectors = self.vectorizer.fit_transform(self.column_docs)

        # Table vectors
        if self.table_docs:
            self.table_vectorizer = TfidfVectorizer(
                stop_words='english',
                max_features=3000,
                ngram_range=(1, 2)
            )
            self.table_vectors = self.table_vectorizer.fit_transform(self.table_docs)

    def save(self):
        """Persist embeddings and graph to disk."""
        os.makedirs(settings.EMBEDDINGS_DIR, exist_ok=True)
        os.makedirs(settings.GRAPH_DIR, exist_ok=True)

        # Save graph
        with open(os.path.join(settings.GRAPH_DIR, "relationships.json"), "w") as f:
            json.dump(self.graph, f, indent=2)

        # Save schema info
        with open(os.path.join(settings.EMBEDDINGS_DIR, "schema_info.json"), "w") as f:
            # Convert sample_data for JSON serialization
            serializable = {}
            for table, info in self.schema_info.items():
                serializable[table] = {
                    "columns": info["columns"],
                    "foreign_keys": info["foreign_keys"],
                    "row_count": info["row_count"]
                }
            json.dump(serializable, f, indent=2)

        # Save vectorizers and indices
        with open(os.path.join(settings.EMBEDDINGS_DIR, "index.pkl"), "wb") as f:
            pickle.dump({
                "vectorizer": self.vectorizer,
                "column_vectors": self.column_vectors,
                "column_index": self.column_index,
                "column_docs": self.column_docs,
                "table_vectorizer": self.table_vectorizer,
                "table_vectors": self.table_vectors,
                "table_names": self.table_names,
                "table_docs": self.table_docs,
            }, f)

        print(f"✅ Saved embeddings to {settings.EMBEDDINGS_DIR}")
        print(f"✅ Saved graph to {settings.GRAPH_DIR}")

    def load(self):
        """Load persisted embeddings and graph."""
        # Load graph
        graph_path = os.path.join(settings.GRAPH_DIR, "relationships.json")
        if os.path.exists(graph_path):
            with open(graph_path) as f:
                self.graph = json.load(f)

        # Load schema info
        schema_path = os.path.join(settings.EMBEDDINGS_DIR, "schema_info.json")
        if os.path.exists(schema_path):
            with open(schema_path) as f:
                self.schema_info = json.load(f)

        # Load vectorizers
        index_path = os.path.join(settings.EMBEDDINGS_DIR, "index.pkl")
        if os.path.exists(index_path):
            with open(index_path, "rb") as f:
                data = pickle.load(f)
                self.vectorizer = data["vectorizer"]
                self.column_vectors = data["column_vectors"]
                self.column_index = data["column_index"]
                self.column_docs = data["column_docs"]
                self.table_vectorizer = data["table_vectorizer"]
                self.table_vectors = data["table_vectors"]
                self.table_names = data["table_names"]
                self.table_docs = data["table_docs"]
            return True
        return False

    def ingest(self):
        """Full ingestion pipeline."""
        print("📊 Extracting schema...")
        self.extract_schema()
        print("📝 Generating descriptions...")
        self.generate_descriptions()
        print("🔗 Building graph...")
        self.build_graph()
        print("🧮 Building embeddings...")
        self.build_embeddings()
        print("💾 Saving to disk...")
        self.save()
        print("✅ Ingestion complete!")
        return self.schema_info
