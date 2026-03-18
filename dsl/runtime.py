"""Shared AST execution logic for swappable graph backends."""

from pathlib import Path
from typing import Dict, Generic, List, Optional, TypeVar, Union

from dsl.ast_nodes import (
    EdgeStatement,
    Expression,
    IdentifierValue,
    LoadStatement,
    LogicalExpression,
    NodeStatement,
    NumberValue,
    Statement,
)
from dsl.errors import InterpreterError
from loader.csv_loader import Row, Table, load_csv


BackendResult = TypeVar("BackendResult")


class ProgramRunner(Generic[BackendResult]):
    """Executes parsed DSL statements and delegates graph output to a backend."""

    backend_name = "backend"

    def __init__(self, data_dir: Union[str, Path] = "."):
        self.data_dir = Path(data_dir)
        self.tables: Dict[str, Table] = {}

    def _resolve_table(self, name: str) -> Table:
        """Return a previously loaded table or raise an error."""
        if name not in self.tables:
            raise InterpreterError(
                f"Table '{name}' has not been loaded. "
                f"Add a LOAD {name}; statement before using it."
            )
        return self.tables[name]

    def _exec_load(self, stmt: LoadStatement) -> None:
        file_path = self.data_dir / f"{stmt.table_name}.csv"
        self.tables[stmt.table_name] = load_csv(file_path)
        print(f"  Loaded table '{stmt.table_name}' ({len(self.tables[stmt.table_name])} rows)")

    def _coerce_number(self, value: object) -> Union[float, None]:
        try:
            return float(str(value))
        except (TypeError, ValueError):
            return None

    def _resolve_compare_value(
        self, expr_value: Union[IdentifierValue, NumberValue]
    ) -> Union[str, float]:
        if isinstance(expr_value, NumberValue):
            return expr_value.value
        return expr_value.value

    def _evaluate_expression(self, expr: Expression, row: Row) -> bool:
        if isinstance(expr, LogicalExpression):
            left = self._evaluate_expression(expr.left, row)
            if expr.operator == "AND":
                return left and self._evaluate_expression(expr.right, row)
            return left or self._evaluate_expression(expr.right, row)

        if expr.field not in row:
            raise InterpreterError(f"Column '{expr.field}' not found in row data")

        left_raw = row[expr.field]
        right_raw = self._resolve_compare_value(expr.value)
        left_num = self._coerce_number(left_raw)
        right_num = self._coerce_number(right_raw)

        if left_num is not None and right_num is not None:
            left_value = left_num
            right_value = right_num
        else:
            left_value = left_raw
            right_value = str(right_raw)

        if expr.operator == ">":
            return left_value > right_value
        if expr.operator == ">=":
            return left_value >= right_value
        if expr.operator == "<":
            return left_value < right_value
        if expr.operator == "<=":
            return left_value <= right_value

        raise InterpreterError(f"Unsupported operator '{expr.operator}'")

    def _filter_table(self, table: Table, where: Optional[Expression]) -> Table:
        if where is None:
            return table
        return [row for row in table if self._evaluate_expression(where, row)]

    def _handle_node(self, stmt: NodeStatement, table: Table) -> None:
        raise NotImplementedError

    def _handle_edge(self, stmt: EdgeStatement, table: Table) -> None:
        raise NotImplementedError

    def _build_result(self) -> BackendResult:
        raise NotImplementedError

    def _exec_node(self, stmt: NodeStatement) -> None:
        table = self._resolve_table(stmt.table_name)
        filtered_table = self._filter_table(table, stmt.where)
        self._handle_node(stmt, filtered_table)
        name_info = f" named by '{stmt.name_field}'" if stmt.name_field else ""
        print(
            f"  Created nodes [{stmt.label}] keyed by '{stmt.key_field}'{name_info}"
        )

    def _exec_edge(self, stmt: EdgeStatement) -> None:
        table = self._resolve_table(stmt.table_name)
        filtered_table = self._filter_table(table, stmt.where)
        self._handle_edge(stmt, filtered_table)
        weight_info = f" with weight '{stmt.weight_field}'" if stmt.weight_field else ""
        print(
            f"  Created edges [{stmt.label}] "
            f"{stmt.source_field} -> {stmt.target_field}{weight_info}"
        )

    def run(self, statements: List[Statement]) -> BackendResult:
        """Execute every statement and return the backend-specific output."""
        print(f"{self.backend_name.capitalize()}: executing DSL program...")
        for stmt in statements:
            if isinstance(stmt, LoadStatement):
                self._exec_load(stmt)
            elif isinstance(stmt, NodeStatement):
                self._exec_node(stmt)
            elif isinstance(stmt, EdgeStatement):
                self._exec_edge(stmt)
            else:
                raise InterpreterError(f"Unknown statement type: {type(stmt)}")
        print(f"{self.backend_name.capitalize()}: done.\n")
        return self._build_result()
