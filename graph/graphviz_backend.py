"""Graphviz DOT backend for the graph DSL."""

from typing import Dict, List, Optional, Tuple

from dsl.ast_nodes import EdgeStatement, NodeStatement
from dsl.errors import InterpreterError
from dsl.runtime import ProgramRunner
from loader.csv_loader import Table


class GraphvizTranspiler(ProgramRunner[str]):
    """Transpile the DSL program into Graphviz DOT syntax."""

    backend_name = "graphviz"

    def __init__(self, data_dir: str = "."):
        super().__init__(data_dir=data_dir)
        self.nodes: Dict[str, Dict[str, str]] = {}
        self.edges: List[Tuple[str, str, Dict[str, object]]] = []

    def _handle_node(self, stmt: NodeStatement, table: Table) -> None:
        if not table:
            return

        columns = set(table[0].keys())
        if stmt.key_field not in columns:
            raise InterpreterError(
                f"Key field '{stmt.key_field}' not found in table columns: "
                f"{list(table[0].keys())}"
            )
        if stmt.name_field and stmt.name_field not in columns:
            raise InterpreterError(
                f"Name field '{stmt.name_field}' not found in table columns: "
                f"{list(table[0].keys())}"
            )

        for row in table:
            node_id = row[stmt.key_field]
            display_name = row[stmt.name_field] if stmt.name_field else str(node_id)
            self.nodes[node_id] = {
                "label": stmt.label,
                "display_name": display_name,
            }

    def _handle_edge(self, stmt: EdgeStatement, table: Table) -> None:
        if not table:
            return

        columns = set(table[0].keys())
        for field_name, field_value in [("source", stmt.source_field), ("target", stmt.target_field)]:
            if field_value not in columns:
                raise InterpreterError(
                    f"Edge {field_name} field '{field_value}' not found in columns: "
                    f"{sorted(columns)}"
                )
        if stmt.weight_field and stmt.weight_field not in columns:
            raise InterpreterError(
                f"Weight field '{stmt.weight_field}' not found in columns: {sorted(columns)}"
            )

        for row in table:
            source = row[stmt.source_field]
            target = row[stmt.target_field]
            attrs: Dict[str, object] = {"label": stmt.label}
            if stmt.weight_field:
                weight_raw = row[stmt.weight_field]
                try:
                    attrs["weight"] = float(weight_raw)
                except ValueError:
                    attrs["weight"] = weight_raw
            self.edges.append((source, target, attrs))

    def _build_result(self) -> str:
        return self.to_dot()

    def to_dot(self) -> str:
        lines = [
            "digraph DSLGraph {",
            '  rankdir="LR";',
            '  graph [pad="0.3", nodesep="0.8", ranksep="1.0"];',
            '  node [shape="ellipse", style="filled", fillcolor="#f7f7f7", color="#555555"];',
            '  edge [color="#666666"];',
        ]

        all_node_ids = set(self.nodes)
        for source, target, _ in self.edges:
            all_node_ids.add(source)
            all_node_ids.add(target)

        for node_id in sorted(all_node_ids):
            node_data = self.nodes.get(
                node_id,
                {"label": "unknown", "display_name": str(node_id)},
            )
            display_name = node_data["display_name"]
            if display_name == str(node_id):
                label = display_name
            else:
                label = f"{display_name}\n({node_id})"
            lines.append(
                f'  "{_escape(node_id)}" '
                f'[label="{_escape(label)}", tooltip="{_escape(node_data["label"])}"];'
            )

        for source, target, attrs in self.edges:
            edge_label = attrs["label"]
            if "weight" in attrs:
                edge_label = f"{edge_label}\nw={attrs['weight']}"
            lines.append(
                f'  "{_escape(source)}" -> "{_escape(target)}" '
                f'[label="{_escape(str(edge_label))}"];'
            )

        lines.append("}")
        return "\n".join(lines)


def _escape(value: str) -> str:
    """Escape string content for Graphviz double-quoted strings."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
