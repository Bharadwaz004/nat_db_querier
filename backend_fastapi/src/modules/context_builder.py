"""
Context Builder
Combines retrieved tables, columns, and join paths into a structured prompt.
"""


class ContextBuilder:
    """Builds structured context for LLM from retrieval results."""

    def __init__(self, schema_info: dict):
        self.schema_info = schema_info

    def build_schema_context(self, tables: list[dict], columns: list[dict], joins: list[dict]) -> str:
        """Build a concise schema description for the LLM prompt."""
        lines = ["=== DATABASE SCHEMA ===\n"]

        # Collect relevant tables
        table_names = set()
        for t in tables:
            table_names.add(t["table"])
        for c in columns:
            table_names.add(c["table"])
        for j in joins:
            table_names.add(j["from_table"])
            table_names.add(j["to_table"])

        for table_name in sorted(table_names):
            info = self.schema_info.get(table_name, {})
            if not info:
                continue

            cols = info.get("columns", [])
            lines.append(f"TABLE: {table_name}")
            lines.append(f"  Rows: {info.get('row_count', '?')}")
            lines.append("  Columns:")
            for col in cols:
                pk = " [PK]" if col.get("primary_key") else ""
                nullable = " NULL" if col.get("nullable") else " NOT NULL"
                lines.append(f"    - {col['name']} ({col['type']}{pk}{nullable})")

            # Foreign keys
            fks = info.get("foreign_keys", [])
            if fks:
                lines.append("  Foreign Keys:")
                for fk in fks:
                    lines.append(f"    - {fk['from_column']} → {fk['to_table']}.{fk['to_column']}")
            lines.append("")

        # Join paths
        if joins:
            lines.append("=== JOIN RELATIONSHIPS ===")
            for j in joins:
                lines.append(
                    f"  {j['from_table']}.{j['from_column']} → "
                    f"{j['to_table']}.{j['to_column']}"
                )
            lines.append("")

        return "\n".join(lines)

    def build_prompt(
        self,
        user_query: str,
        schema_context: str,
        chat_history: list[dict] = None,
        error_context: str = None
    ) -> str:
        """Build the full prompt for SQL generation."""
        system_parts = [
            "You are an expert SQL assistant. Generate accurate SQLite SQL queries based on the provided schema.",
            "",
            "STRICT RULES:",
            "1. Use ONLY tables and columns from the provided schema.",
            "2. Generate syntactically correct SQLite SQL.",
            "3. Use proper JOINs when multiple tables are needed.",
            "4. Include WHERE clauses for filtering when appropriate.",
            "5. Use aliases for readability.",
            "6. ALWAYS include a LIMIT clause (default 50) unless counting/aggregating.",
            "7. Do NOT use features unsupported by SQLite (e.g., FULL OUTER JOIN).",
            "",
            schema_context,
        ]

        if error_context:
            system_parts.extend([
                "=== PREVIOUS ERROR ===",
                f"The previous SQL query had this error: {error_context}",
                "Please fix the query and avoid the same mistake.",
                ""
            ])

        system_prompt = "\n".join(system_parts)

        # Build messages for multi-turn
        messages = [{"role": "system", "content": system_prompt}]

        if chat_history:
            for msg in chat_history[-6:]:  # Keep last 6 turns
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

        messages.append({
            "role": "user",
            "content": (
                f"Natural language query: {user_query}\n\n"
                "Respond in this exact format:\n"
                "SQL:\n```sql\n<your SQL query>\n```\n\n"
                "EXPLANATION:\n<brief explanation of what the query does and why these tables/joins were chosen>"
            )
        })

        return system_prompt, messages

    def build_nl_response_prompt(self, user_query: str, sql: str, results: list, columns: list) -> list[dict]:
        """Build prompt for converting SQL results to natural language."""
        # Format results as a readable table
        if not results:
            result_text = "No results returned."
        else:
            # Limit display to first 20 rows
            display_results = results[:20]
            header = " | ".join(columns)
            separator = "-" * len(header)
            rows = []
            for row in display_results:
                rows.append(" | ".join(str(v) for v in row))
            result_text = f"{header}\n{separator}\n" + "\n".join(rows)
            if len(results) > 20:
                result_text += f"\n... and {len(results) - 20} more rows"

        return [
            {
                "role": "system",
                "content": (
                    "You are a helpful data analyst. Convert SQL query results into clear, "
                    "natural language answers. Be concise but informative. Include key numbers and insights."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Original question: {user_query}\n\n"
                    f"SQL executed:\n```sql\n{sql}\n```\n\n"
                    f"Results ({len(results)} rows):\n{result_text}\n\n"
                    "Provide a clear natural language answer to the original question based on these results."
                )
            }
        ]
