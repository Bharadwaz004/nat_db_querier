"""
Graph Traversal Module
Finds valid join paths between retrieved tables using the relationship graph.
"""
from collections import deque


class GraphTraverser:
    """Traverses FK relationship graph to find join paths."""

    def __init__(self, graph: dict):
        self.graph = graph  # adjacency list from schema ingestion

    def find_join_path(self, source: str, target: str, max_depth: int = 4) -> list[dict] | None:
        """BFS to find shortest join path between two tables."""
        if source == target:
            return []
        if source not in self.graph or target not in self.graph:
            return None

        visited = {source}
        queue = deque([(source, [])])

        while queue:
            current, path = queue.popleft()
            if len(path) >= max_depth:
                continue

            for edge in self.graph.get(current, []):
                next_table = edge["to_table"]
                if next_table in visited:
                    continue

                new_path = path + [{
                    "from_table": edge["from_table"],
                    "from_column": edge["from_column"],
                    "to_table": edge["to_table"],
                    "to_column": edge["to_column"],
                    "join_type": "INNER JOIN"
                }]

                if next_table == target:
                    return new_path

                visited.add(next_table)
                queue.append((next_table, new_path))

        return None

    def find_all_joins(self, tables: list[str]) -> list[dict]:
        """Find join paths connecting all specified tables."""
        if len(tables) <= 1:
            return []

        all_joins = []
        connected = {tables[0]}

        for table in tables[1:]:
            # Try to connect this table to any already-connected table
            best_path = None
            best_length = float('inf')

            for connected_table in connected:
                path = self.find_join_path(connected_table, table)
                if path is not None and len(path) < best_length:
                    best_path = path
                    best_length = len(path)

            if best_path:
                all_joins.extend(best_path)
                # Add intermediate tables to connected set
                for join in best_path:
                    connected.add(join["to_table"])
                    connected.add(join["from_table"])

        # Deduplicate joins
        seen = set()
        unique_joins = []
        for join in all_joins:
            key = (join["from_table"], join["from_column"], join["to_table"], join["to_column"])
            reverse_key = (join["to_table"], join["to_column"], join["from_table"], join["from_column"])
            if key not in seen and reverse_key not in seen:
                seen.add(key)
                unique_joins.append(join)

        return unique_joins

    def get_related_tables(self, table: str, depth: int = 1) -> list[str]:
        """Get tables directly related to the given table."""
        related = set()
        if table in self.graph:
            for edge in self.graph[table]:
                related.add(edge["to_table"])
                if depth > 1:
                    for sub_edge in self.graph.get(edge["to_table"], []):
                        related.add(sub_edge["to_table"])
        related.discard(table)
        return list(related)
