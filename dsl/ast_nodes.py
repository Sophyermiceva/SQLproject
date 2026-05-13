"""AST (Abstract Syntax Tree) node classes.

Each class represents a single statement type in the DSL.
The parser produces a list of these nodes; the interpreter consumes them.
"""

from dataclasses import dataclass
from typing import Optional, Union


@dataclass(frozen=True)
class IdentifierValue:
    value: str


@dataclass(frozen=True)
class NumberValue:
    value: float


Value = Union[IdentifierValue, NumberValue]


@dataclass(frozen=True)
class ComparisonExpression:
    field: str
    operator: str
    value: Value


@dataclass(frozen=True)
class LogicalExpression:
    operator: str
    left: "Expression"
    right: "Expression"


Expression = Union[ComparisonExpression, LogicalExpression]


@dataclass(frozen=True)
class LoadStatement:
    """LOAD <table_name>;"""
    table_name: str


@dataclass(frozen=True)
class NodeStatement:
    """NODE <label> KEY <key_field> [NAME <name_field>] [PRIOR <prior_field>] FROM <table_name>;"""
    label: str
    key_field: str
    table_name: str
    name_field: Optional[str] = None
    prior_field: Optional[str] = None
    where: Optional[Expression] = None


@dataclass(frozen=True)
class EdgeStatement:
    """
    EDGE <label>
        FROM <table_name>
        SOURCE <source_field>
        TARGET <target_field>
        [WEIGHT <weight_field>];
    """
    label: str
    table_name: str
    source_field: str
    target_field: str
    weight_field: Optional[str] = None
    probability_field: Optional[str] = None
    given_field: Optional[str] = None
    where: Optional[Expression] = None


# Union type for any top-level statement.
Statement = Union[LoadStatement, NodeStatement, EdgeStatement]
