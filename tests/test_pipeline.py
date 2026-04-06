"""
Unit & integration tests for the NL-to-SQL pipeline.
Run: PYTHONPATH=. python -m pytest tests/ -v
"""
import os
import sys
import json
import pytest

# Ensure project root is on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend_fastapi.src.modules.schema_ingestion import SchemaIngestion
from backend_fastapi.src.modules.vector_retrieval import VectorRetriever
from backend_fastapi.src.modules.graph_traversal import GraphTraverser
from backend_fastapi.src.modules.context_builder import ContextBuilder
from backend_fastapi.src.modules.sql_validator import SQLValidator
from backend_fastapi.src.modules.sql_executor import SQLExecutor

DB_PATH = os.path.join(ROOT, "data", "sample_ecommerce.db")


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def ingestion():
    """Run schema ingestion once for all tests."""
    ing = SchemaIngestion(db_path=DB_PATH)
    ing.extract_schema()
    ing.generate_descriptions()
    ing.build_graph()
    ing.build_embeddings()
    return ing


@pytest.fixture(scope="module")
def retriever(ingestion):
    return VectorRetriever(ingestion)


@pytest.fixture(scope="module")
def graph(ingestion):
    return GraphTraverser(ingestion.graph)


@pytest.fixture(scope="module")
def validator(ingestion):
    return SQLValidator(ingestion.schema_info, DB_PATH)


@pytest.fixture(scope="module")
def executor():
    return SQLExecutor(db_path=DB_PATH)


# ── Schema Ingestion Tests ───────────────────────────────────

class TestSchemaIngestion:
    def test_extracts_all_tables(self, ingestion):
        expected = {"categories", "products", "customers", "orders",
                    "order_items", "reviews", "inventory"}
        assert set(ingestion.schema_info.keys()) == expected

    def test_columns_extracted(self, ingestion):
        products = ingestion.schema_info["products"]
        col_names = {c["name"] for c in products["columns"]}
        assert "product_id" in col_names
        assert "name" in col_names
        assert "price" in col_names
        assert "category_id" in col_names

    def test_foreign_keys_extracted(self, ingestion):
        orders = ingestion.schema_info["orders"]
        fks = orders["foreign_keys"]
        assert len(fks) > 0
        assert any(fk["to_table"] == "customers" for fk in fks)

    def test_row_counts_positive(self, ingestion):
        for table, info in ingestion.schema_info.items():
            assert info["row_count"] > 0, f"{table} has 0 rows"

    def test_descriptions_generated(self, ingestion):
        assert len(ingestion.table_docs) == 7
        assert len(ingestion.column_docs) > 20

    def test_embeddings_built(self, ingestion):
        assert ingestion.vectorizer is not None
        assert ingestion.column_vectors is not None
        assert ingestion.table_vectorizer is not None
        assert ingestion.table_vectors is not None


# ── Vector Retrieval Tests ───────────────────────────────────

class TestVectorRetrieval:
    def test_retrieve_tables_for_product_query(self, retriever):
        results = retriever.retrieve_tables("top selling products")
        tables = [r["table"] for r in results]
        assert "products" in tables

    def test_retrieve_tables_for_order_query(self, retriever):
        results = retriever.retrieve_tables("recent customer orders")
        tables = [r["table"] for r in results]
        assert "orders" in tables or "customers" in tables

    def test_retrieve_columns_returns_relevant(self, retriever):
        results = retriever.retrieve_columns("product price and name")
        cols = [(r["table"], r["column"]) for r in results]
        assert ("products", "price") in cols or ("products", "name") in cols

    def test_combined_retrieve(self, retriever):
        result = retriever.retrieve("average product rating by category")
        assert "table_names" in result
        assert len(result["tables"]) > 0

    def test_scores_are_sorted(self, retriever):
        results = retriever.retrieve_tables("inventory stock levels")
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)


# ── Graph Traversal Tests ────────────────────────────────────

class TestGraphTraversal:
    def test_direct_join_path(self, graph):
        path = graph.find_join_path("orders", "customers")
        assert path is not None
        assert len(path) >= 1
        assert path[0]["from_table"] == "orders" or path[0]["to_table"] == "customers"

    def test_multi_hop_join(self, graph):
        path = graph.find_join_path("products", "customers")
        # products -> order_items -> orders -> customers
        assert path is not None
        assert len(path) >= 2

    def test_no_path_to_self(self, graph):
        path = graph.find_join_path("products", "products")
        assert path == []

    def test_find_all_joins_multiple_tables(self, graph):
        joins = graph.find_all_joins(["products", "orders", "customers"])
        assert len(joins) >= 2

    def test_related_tables(self, graph):
        related = graph.get_related_tables("orders")
        assert "customers" in related or "order_items" in related


# ── SQL Validator Tests ──────────────────────────────────────

class TestSQLValidator:
    def test_valid_select(self, validator):
        result = validator.validate("SELECT * FROM products LIMIT 10")
        assert result["valid"] is True

    def test_invalid_syntax(self, validator):
        result = validator.validate("SELEC * FORM products")
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_blocks_drop(self, validator):
        result = validator.validate("DROP TABLE products")
        assert result["valid"] is False

    def test_blocks_delete(self, validator):
        result = validator.validate("DELETE FROM products WHERE product_id = 1")
        assert result["valid"] is False

    def test_blocks_insert(self, validator):
        result = validator.validate("INSERT INTO products (name) VALUES ('test')")
        assert result["valid"] is False

    def test_empty_query(self, validator):
        result = validator.validate("")
        assert result["valid"] is False

    def test_warns_no_limit(self, validator):
        result = validator.validate("SELECT * FROM products")
        assert any("LIMIT" in w for w in result["warnings"])


# ── SQL Executor Tests ───────────────────────────────────────

class TestSQLExecutor:
    def test_basic_select(self, executor):
        result = executor.execute("SELECT * FROM products LIMIT 5")
        assert "error" not in result or not result.get("error")
        assert result["row_count"] == 5
        assert "name" in result["columns"]

    def test_aggregate_query(self, executor):
        result = executor.execute("SELECT COUNT(*) as cnt FROM customers")
        assert result["rows"][0][0] > 0

    def test_join_query(self, executor):
        sql = """
        SELECT o.order_id, c.first_name, o.total_amount
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        LIMIT 5
        """
        result = executor.execute(sql)
        assert result["row_count"] == 5
        assert "first_name" in result["columns"]

    def test_blocks_non_select(self, executor):
        result = executor.execute("DROP TABLE products")
        assert "error" in result and result["error"]

    def test_returns_execution_time(self, executor):
        result = executor.execute("SELECT 1")
        assert result["execution_time_ms"] >= 0


# ── Context Builder Tests ────────────────────────────────────

class TestContextBuilder:
    def test_builds_schema_context(self, ingestion):
        builder = ContextBuilder(ingestion.schema_info)
        tables = [{"table": "products", "score": 0.9, "summary": "test", "schema": {}}]
        columns = [{"table": "products", "column": "name", "type": "TEXT", "score": 0.8}]
        joins = []
        context = builder.build_schema_context(tables, columns, joins)
        assert "products" in context
        assert "TABLE:" in context

    def test_builds_prompt_with_history(self, ingestion):
        builder = ContextBuilder(ingestion.schema_info)
        history = [
            {"role": "user", "content": "Show me products"},
            {"role": "assistant", "content": "Here are the products..."}
        ]
        system, messages = builder.build_prompt(
            "Now filter by price > 100", "schema context here", history
        )
        assert len(messages) > 1
        assert "STRICT RULES" in system


# ── Integration Test ─────────────────────────────────────────

class TestIntegration:
    def test_full_retrieval_to_execution(self, retriever, graph, ingestion):
        """End-to-end: retrieve → graph → build context → execute hardcoded SQL."""
        query = "top 5 products by price"
        retrieval = retriever.retrieve(query)
        assert len(retrieval["tables"]) > 0

        joins = graph.find_all_joins(retrieval["table_names"])

        builder = ContextBuilder(ingestion.schema_info)
        context = builder.build_schema_context(
            retrieval["tables"], retrieval["columns"], joins
        )
        assert "products" in context.lower()

        # Execute a known-good query
        executor = SQLExecutor(db_path=DB_PATH)
        result = executor.execute(
            "SELECT name, price FROM products ORDER BY price DESC LIMIT 5"
        )
        assert result["row_count"] == 5
        assert result["rows"][0][1] >= result["rows"][1][1]  # sorted desc


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
