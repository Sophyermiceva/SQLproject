"""Bayesian tree backend and probability propagation."""

from dataclasses import dataclass
from typing import Dict, List, Tuple

import networkx as nx

from dsl.ast_nodes import EdgeStatement, NodeStatement
from dsl.errors import InterpreterError
from dsl.runtime import ProgramRunner
from loader.csv_loader import Table


ConditionalProbabilities = Dict[bool, float]
EdgeKey = Tuple[str, str]


@dataclass(frozen=True)
class BayesianTreeResult:
    """Computed Bayesian tree graph and marginal probabilities."""

    graph: nx.DiGraph
    probabilities: Dict[str, float]
    leaf_probabilities: Dict[str, float]
    conditional_probabilities: Dict[EdgeKey, ConditionalProbabilities]

    def summary(self) -> str:
        """Return a compact report of event and leaf probabilities."""
        lines = ["Bayesian tree event probabilities:"]
        for node in self.graph.nodes():
            display_name = self.graph.nodes[node].get("display_name", str(node))
            lines.append(f"  {display_name}: {self.probabilities[node]:.4f}")

        lines.append("")
        lines.append("Leaf event probabilities:")
        for node, probability in self.leaf_probabilities.items():
            display_name = self.graph.nodes[node].get("display_name", str(node))
            lines.append(f"  {display_name}: {probability:.4f}")
        return "\n".join(lines)

    def to_dot(self) -> str:
        """Render the Bayesian tree as Graphviz DOT."""
        lines = [
            "digraph BayesianTree {",
            '  rankdir="TB";',
            '  graph [pad="0.3", nodesep="0.6", ranksep="0.9"];',
            '  node [shape="box", style="rounded,filled", fillcolor="#f7fbff", color="#4a6a8a"];',
            '  edge [color="#51657a"];',
        ]

        for node in nx.topological_sort(self.graph):
            node_data = self.graph.nodes[node]
            display_name = node_data.get("display_name", str(node))
            label = f"{display_name}\nP={self.probabilities[node]:.4f}"
            lines.append(f'  "{_escape(node)}" [label="{_escape(label)}"];')

        for source, target in self.graph.edges():
            conditionals = self.conditional_probabilities[(source, target)]
            edge_label = (
                f"P(T|T)={conditionals[True]:.2f}\n"
                f"P(T|F)={conditionals[False]:.2f}"
            )
            lines.append(
                f'  "{_escape(source)}" -> "{_escape(target)}" '
                f'[label="{_escape(edge_label)}"];'
            )

        lines.append("}")
        return "\n".join(lines)


class BayesianTreeBuilder(ProgramRunner[BayesianTreeResult]):
    """Build a Bayesian tree from node priors and conditional edge tables."""

    backend_name = "bayes"

    def __init__(self, data_dir: str = "."):
        super().__init__(data_dir=data_dir)
        self.graph = nx.DiGraph()
        self.conditional_probabilities: Dict[EdgeKey, ConditionalProbabilities] = {}
        self.node_order: List[str] = []

    def _handle_node(self, stmt: NodeStatement, table: Table) -> None:
        if not table:
            return
        if stmt.prior_field is None:
            raise InterpreterError("Bayesian tree nodes must declare PRIOR <column>")

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
        if stmt.prior_field not in columns:
            raise InterpreterError(
                f"Prior field '{stmt.prior_field}' not found in table columns: "
                f"{list(table[0].keys())}"
            )

        for row in table:
            node_id = row[stmt.key_field]
            display_name = row[stmt.name_field] if stmt.name_field else str(node_id)
            prior_raw = row[stmt.prior_field].strip()
            prior = None if prior_raw == "" else _parse_probability(prior_raw, stmt.prior_field)
            row_attributes = {
                key: value
                for key, value in row.items()
                if key not in {"label", "display_name", "prior"}
            }
            if node_id not in self.graph:
                self.node_order.append(node_id)
            self.graph.add_node(
                node_id,
                label=stmt.label,
                display_name=display_name,
                prior=prior,
                **row_attributes,
            )

    def _handle_edge(self, stmt: EdgeStatement, table: Table) -> None:
        if not table:
            return
        if stmt.weight_field is not None:
            raise InterpreterError("Bayesian tree edges do not support WEIGHT; use PROBABILITY")
        if stmt.probability_field is None or stmt.given_field is None:
            raise InterpreterError(
                "Bayesian tree edges must declare PROBABILITY <column> GIVEN <column>"
            )

        columns = set(table[0].keys())
        for field_name, field_value in [
            ("source", stmt.source_field),
            ("target", stmt.target_field),
            ("probability", stmt.probability_field),
            ("given", stmt.given_field),
        ]:
            if field_value not in columns:
                raise InterpreterError(
                    f"Edge {field_name} field '{field_value}' not found in columns: "
                    f"{sorted(columns)}"
                )

        for row in table:
            source = row[stmt.source_field]
            target = row[stmt.target_field]
            if source not in self.graph or target not in self.graph:
                raise InterpreterError(
                    "Bayesian tree edges require events to be declared first with NODE"
                )

            given_value = _parse_boolean(row[stmt.given_field], stmt.given_field)
            probability = _parse_probability(row[stmt.probability_field], stmt.probability_field)

            parents = list(self.graph.predecessors(target))
            if parents and parents[0] != source:
                raise InterpreterError(
                    f"Bayesian tree node '{target}' has multiple parents: "
                    f"'{parents[0]}' and '{source}'"
                )

            self.graph.add_edge(source, target, label=stmt.label)
            edge_key = (source, target)
            edge_probabilities = self.conditional_probabilities.setdefault(edge_key, {})
            if given_value in edge_probabilities:
                raise InterpreterError(
                    f"Duplicate conditional probability for edge '{source}' -> '{target}' "
                    f"when {stmt.given_field}={row[stmt.given_field]!r}"
                )
            edge_probabilities[given_value] = probability

    def _build_result(self) -> BayesianTreeResult:
        self._validate_tree()
        probabilities = self._compute_probabilities()
        leaf_probabilities = {
            node: probabilities[node]
            for node in self.node_order
            if self.graph.out_degree(node) == 0
        }
        return BayesianTreeResult(
            graph=self.graph.copy(),
            probabilities=probabilities,
            leaf_probabilities=leaf_probabilities,
            conditional_probabilities={
                edge: values.copy()
                for edge, values in self.conditional_probabilities.items()
            },
        )

    def _validate_tree(self) -> None:
        if self.graph.number_of_nodes() == 0:
            raise InterpreterError("Bayesian tree is empty")
        if not nx.is_directed_acyclic_graph(self.graph):
            raise InterpreterError("Bayesian tree must be acyclic")
        if nx.number_weakly_connected_components(self.graph) != 1:
            raise InterpreterError("Bayesian tree must be connected")

        roots = [node for node in self.graph.nodes() if self.graph.in_degree(node) == 0]
        if len(roots) != 1:
            raise InterpreterError(
                f"Bayesian tree must have exactly one root event, found {len(roots)}"
            )

        for node in self.graph.nodes():
            indegree = self.graph.in_degree(node)
            prior = self.graph.nodes[node].get("prior")
            if indegree == 0:
                if prior is None:
                    raise InterpreterError(
                        f"Root event '{node}' must define a prior probability"
                    )
                continue

            if prior is not None:
                raise InterpreterError(
                    f"Non-root event '{node}' cannot define a prior probability"
                )

            parent = next(self.graph.predecessors(node))
            edge_probabilities = self.conditional_probabilities.get((parent, node), {})
            if set(edge_probabilities) != {True, False}:
                raise InterpreterError(
                    f"Edge '{parent}' -> '{node}' must define probabilities for "
                    f"both GIVEN=true and GIVEN=false"
                )

    def _compute_probabilities(self) -> Dict[str, float]:
        probabilities: Dict[str, float] = {}
        for node in nx.topological_sort(self.graph):
            if self.graph.in_degree(node) == 0:
                probabilities[node] = self.graph.nodes[node]["prior"]
                continue

            parent = next(self.graph.predecessors(node))
            parent_probability = probabilities[parent]
            conditionals = self.conditional_probabilities[(parent, node)]
            probabilities[node] = (
                conditionals[True] * parent_probability
                + conditionals[False] * (1.0 - parent_probability)
            )
        return probabilities


def _parse_probability(raw_value: str, field_name: str) -> float:
    """Parse and validate a probability in the [0, 1] interval."""
    try:
        probability = float(raw_value)
    except ValueError as exc:
        raise InterpreterError(
            f"Field '{field_name}' must contain numeric probabilities, got {raw_value!r}"
        ) from exc
    if probability < 0.0 or probability > 1.0:
        raise InterpreterError(
            f"Field '{field_name}' must be between 0 and 1, got {probability}"
        )
    return probability


def _parse_boolean(raw_value: str, field_name: str) -> bool:
    """Parse a tabular boolean value used in conditional rows."""
    normalized = raw_value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise InterpreterError(
        f"Field '{field_name}' must be a boolean value, got {raw_value!r}"
    )


def _escape(value: str) -> str:
    """Escape string content for Graphviz double-quoted strings."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
