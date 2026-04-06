"""
SQL Execution Module
Safely executes validated SQL queries against SQLite.
"""
import sqlite3
import time
from ..config import settings


class SQLExecutor:
    """Executes SQL queries with safety measures."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DB_PATH
        self.max_rows = 500
        self.timeout_seconds = 10

    def execute(self, sql: str) -> dict:
        """
        Execute a SQL query and return results.
        Returns: {"columns": [...], "rows": [...], "row_count": int, "execution_time_ms": float}
        """
        sql_clean = sql.strip().rstrip(';')

        # Safety: only allow SELECT and WITH (CTE) statements
        first_keyword = sql_clean.split()[0].upper() if sql_clean else ""
        if first_keyword not in ("SELECT", "WITH"):
            return {
                "error": f"Only SELECT queries are allowed. Got: {first_keyword}",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "execution_time_ms": 0
            }

        try:
            conn = sqlite3.connect(self.db_path, timeout=self.timeout_seconds)
            conn.execute("PRAGMA query_only = ON")  # read-only mode
            cursor = conn.cursor()

            start = time.perf_counter()
            cursor.execute(sql_clean)
            rows = cursor.fetchmany(self.max_rows)
            elapsed = (time.perf_counter() - start) * 1000

            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # Check if there are more rows
            has_more = len(rows) == self.max_rows
            total_hint = f"{self.max_rows}+" if has_more else str(len(rows))

            conn.close()

            return {
                "columns": columns,
                "rows": [list(row) for row in rows],
                "row_count": len(rows),
                "total_hint": total_hint,
                "execution_time_ms": round(elapsed, 2),
                "truncated": has_more
            }

        except sqlite3.OperationalError as e:
            return {
                "error": f"SQL execution error: {str(e)}",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "execution_time_ms": 0
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "execution_time_ms": 0
            }
