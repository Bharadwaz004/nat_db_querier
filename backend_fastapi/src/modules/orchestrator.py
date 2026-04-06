"""
Query Orchestrator
Orchestrates the full NL-to-SQL pipeline: retrieval → graph → context → LLM → validate → execute → respond.
"""
import logging
from .schema_ingestion import SchemaIngestion
from .vector_retrieval import VectorRetriever
from .graph_traversal import GraphTraverser
from .context_builder import ContextBuilder
from .llm_provider import LLMProvider
from .sql_validator import SQLValidator
from .sql_executor import SQLExecutor
from ..config import settings

logger = logging.getLogger(__name__)


class QueryOrchestrator:
    """End-to-end orchestration of NL-to-SQL queries."""

    def __init__(self):
        self.ingestion = SchemaIngestion()
        self.retriever = None
        self.graph = None
        self.context_builder = None
        self.llm = LLMProvider()
        self.validator = None
        self.executor = SQLExecutor()
        self._initialized = False

    def initialize(self, db_path: str = None):
        """Initialize all modules. Call once at startup or when DB changes."""
        if db_path:
            self.ingestion.db_path = db_path
            self.executor.db_path = db_path
            settings.DB_PATH = db_path

        # Try loading from cache first
        if not self.ingestion.load():
            logger.info("No cached embeddings found, running full ingestion...")
            self.ingestion.ingest()
        else:
            logger.info("Loaded cached embeddings.")
            # Still need the full schema if not loaded
            if not self.ingestion.schema_info:
                self.ingestion.extract_schema()

        self.retriever = VectorRetriever(self.ingestion)
        self.graph = GraphTraverser(self.ingestion.graph)
        self.context_builder = ContextBuilder(self.ingestion.schema_info)
        self.validator = SQLValidator(self.ingestion.schema_info, self.ingestion.db_path)
        self._initialized = True
        logger.info("QueryOrchestrator initialized successfully.")

    def reingest(self, db_path: str = None):
        """Re-run ingestion (e.g., when user uploads new DB)."""
        if db_path:
            self.ingestion.db_path = db_path
            self.executor.db_path = db_path
            settings.DB_PATH = db_path
        self.ingestion.ingest()
        self.retriever = VectorRetriever(self.ingestion)
        self.graph = GraphTraverser(self.ingestion.graph)
        self.context_builder = ContextBuilder(self.ingestion.schema_info)
        self.validator = SQLValidator(self.ingestion.schema_info, self.ingestion.db_path)
        self._initialized = True

    async def process_query(self, user_query: str, chat_history: list[dict] = None) -> dict:
        """
        Full pipeline: NL query → SQL → results → NL answer.
        Returns a rich response dict.
        """
        if not self._initialized:
            self.initialize()

        response = {
            "user_query": user_query,
            "sql": "",
            "explanation": "",
            "results": {"columns": [], "rows": [], "row_count": 0},
            "nl_answer": "",
            "tables_used": [],
            "joins_used": [],
            "retrieval_scores": [],
            "retries": 0,
            "error": None
        }

        try:
            # Step 1: Vector retrieval
            logger.info(f"Step 1: Retrieving relevant schema for: {user_query}")
            retrieval = self.retriever.retrieve(user_query)
            response["tables_used"] = retrieval["table_names"]
            response["retrieval_scores"] = [
                {"table": t["table"], "score": round(t["score"], 4)}
                for t in retrieval["tables"]
            ]

            # Step 2: Graph traversal for join paths
            logger.info(f"Step 2: Finding join paths for tables: {retrieval['table_names']}")
            joins = self.graph.find_all_joins(retrieval["table_names"])
            response["joins_used"] = joins

            # Step 3: Build context
            logger.info("Step 3: Building context...")
            schema_context = self.context_builder.build_schema_context(
                retrieval["tables"], retrieval["columns"], joins
            )

            # Step 4: Generate SQL with retry loop
            sql = ""
            explanation = ""
            error_context = None

            for attempt in range(settings.MAX_RETRIES):
                logger.info(f"Step 4: SQL generation attempt {attempt + 1}/{settings.MAX_RETRIES}")

                system_prompt, messages = self.context_builder.build_prompt(
                    user_query, schema_context, chat_history, error_context
                )

                raw_response = await self.llm.generate(system_prompt, messages)
                parsed = self.llm.parse_sql_response(raw_response)
                sql = parsed["sql"]
                explanation = parsed["explanation"]

                if not sql:
                    error_context = "Failed to generate SQL. Please try again with a valid SELECT query."
                    response["retries"] = attempt + 1
                    continue

                # Step 5: Validate
                logger.info("Step 5: Validating SQL...")
                validation = self.validator.validate(sql)

                if validation["valid"]:
                    break
                else:
                    error_context = self.validator.get_error_context(sql, "; ".join(validation["errors"]))
                    response["retries"] = attempt + 1
                    logger.warning(f"Validation failed: {validation['errors']}")

            response["sql"] = sql
            response["explanation"] = explanation

            if not sql:
                response["error"] = "Failed to generate a valid SQL query after retries."
                return response

            # Step 6: Execute SQL
            logger.info("Step 6: Executing SQL...")
            exec_result = self.executor.execute(sql)

            if "error" in exec_result and exec_result["error"]:
                # One more retry after execution error
                error_context = self.validator.get_error_context(sql, exec_result["error"])
                system_prompt, messages = self.context_builder.build_prompt(
                    user_query, schema_context, chat_history, error_context
                )
                raw_response = await self.llm.generate(system_prompt, messages)
                parsed = self.llm.parse_sql_response(raw_response)
                if parsed["sql"]:
                    exec_result = self.executor.execute(parsed["sql"])
                    response["sql"] = parsed["sql"]
                    response["explanation"] = parsed["explanation"]
                    response["retries"] += 1

            if "error" in exec_result and exec_result["error"]:
                response["error"] = exec_result["error"]
                response["results"] = exec_result
                return response

            response["results"] = exec_result

            # Step 7: Generate NL response
            logger.info("Step 7: Generating natural language response...")
            try:
                nl_messages = self.context_builder.build_nl_response_prompt(
                    user_query, sql, exec_result["rows"], exec_result["columns"]
                )
                nl_answer = await self.llm.generate(
                    nl_messages[0]["content"],
                    nl_messages[1:]
                )
                response["nl_answer"] = nl_answer
            except Exception as e:
                logger.error(f"NL generation failed: {e}")
                response["nl_answer"] = f"Query returned {exec_result['row_count']} results."

        except Exception as e:
            logger.exception(f"Pipeline error: {e}")
            response["error"] = str(e)

        return response

    def get_schema_summary(self) -> dict:
        """Return a summary of the current database schema."""
        if not self._initialized:
            self.initialize()

        summary = {}
        for table, info in self.ingestion.schema_info.items():
            summary[table] = {
                "columns": [c["name"] for c in info.get("columns", [])],
                "row_count": info.get("row_count", 0),
                "foreign_keys": info.get("foreign_keys", [])
            }
        return summary

    async def cleanup(self):
        await self.llm.close()
