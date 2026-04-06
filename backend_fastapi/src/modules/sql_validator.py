"""
SQL Validation Module
Validates generated SQL queries against the database schema.
"""
import re
import sqlite3


class SQLValidator:
    """Validates SQL queries for correctness before execution."""

    def __init__(self, schema_info: dict, db_path: str):
        self.schema_info = schema_info
        self.db_path = db_path
        self.all_tables = set(schema_info.keys())
        self.all_columns = {}  # table -> set of columns
        for table, info in schema_info.items():
            cols = info.get("columns", [])
            self.all_columns[table] = set(c["name"] for c in cols)

    def validate(self, sql: str) -> dict:
        """
        Validate SQL query. Returns:
        {"valid": bool, "errors": list[str], "warnings": list[str]}
        """
        errors = []
        warnings = []

        if not sql or not sql.strip():
            return {"valid": False, "errors": ["Empty SQL query"], "warnings": []}

        sql_clean = sql.strip().rstrip(';')

        # 1. Basic syntax check using SQLite EXPLAIN
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(f"EXPLAIN {sql_clean}")
            conn.close()
        except sqlite3.OperationalError as e:
            errors.append(f"SQL syntax error: {str(e)}")
            return {"valid": False, "errors": errors, "warnings": warnings}
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # 2. Check for dangerous operations
        dangerous_patterns = [
            (r'\bDROP\b', "DROP statements are not allowed"),
            (r'\bTRUNCATE\b', "TRUNCATE statements are not allowed"),
            (r'\bALTER\b', "ALTER statements are not allowed"),
            (r'\bDELETE\b', "DELETE statements are not allowed"),
            (r'\bINSERT\b', "INSERT statements are not allowed"),
            (r'\bUPDATE\b', "UPDATE statements are not allowed"),
            (r'\bCREATE\b', "CREATE statements are not allowed"),
        ]
        for pattern, msg in dangerous_patterns:
            if re.search(pattern, sql_clean, re.IGNORECASE):
                errors.append(msg)

        # 3. Check referenced tables exist
        table_pattern = r'\b(?:FROM|JOIN|INTO)\s+(\w+)'
        referenced_tables = set(re.findall(table_pattern, sql_clean, re.IGNORECASE))
        for table in referenced_tables:
            if table.lower() not in {t.lower() for t in self.all_tables}:
                # Could be an alias or subquery
                if not re.search(rf'\bas\s+{table}\b', sql_clean, re.IGNORECASE):
                    warnings.append(f"Table '{table}' not found in schema (might be an alias)")

        # 4. Check for missing LIMIT on SELECT queries
        if re.match(r'\s*SELECT\b', sql_clean, re.IGNORECASE):
            if not re.search(r'\bLIMIT\b', sql_clean, re.IGNORECASE):
                if not re.search(r'\bCOUNT\s*\(', sql_clean, re.IGNORECASE) and \
                   not re.search(r'\bSUM\s*\(', sql_clean, re.IGNORECASE) and \
                   not re.search(r'\bAVG\s*\(', sql_clean, re.IGNORECASE) and \
                   not re.search(r'\bGROUP\s+BY\b', sql_clean, re.IGNORECASE):
                    warnings.append("Query has no LIMIT clause — consider adding one for large tables")

        is_valid = len(errors) == 0
        return {"valid": is_valid, "errors": errors, "warnings": warnings}

    def get_error_context(self, sql: str, error: str) -> str:
        """Build error context string for retry prompt."""
        return (
            f"The following SQL query failed:\n"
            f"```sql\n{sql}\n```\n"
            f"Error: {error}\n"
            f"Available tables: {', '.join(sorted(self.all_tables))}\n"
        )
