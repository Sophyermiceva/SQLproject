"""Interpreter backend that executes the AST into an in-memory graph."""

from dsl.ast_nodes import EdgeStatement, NodeStatement
from dsl.runtime import ProgramRunner
from graph.builder import GraphBuilder
from loader.csv_loader import Table


class Interpreter(ProgramRunner[GraphBuilder]):
    """Executes a parsed DSL program (a list of AST statements)."""

    backend_name = "interpreter"

    def __init__(self, data_dir: str = "."):
        super().__init__(data_dir=data_dir)
        self.builder = GraphBuilder()

    def _handle_node(self, stmt: NodeStatement, filtered_table: Table) -> None:
        self.builder.add_nodes(
            stmt.label,
            stmt.key_field,
            filtered_table,
            name_field=stmt.name_field,
        )

    def _handle_edge(self, stmt: EdgeStatement, filtered_table: Table) -> None:
        self.builder.add_edges(
            label=stmt.label,
            table=filtered_table,
            source_field=stmt.source_field,
            target_field=stmt.target_field,
            weight_field=stmt.weight_field,
        )

    def _build_result(self) -> GraphBuilder:
        return self.builder
