"""Graph visualizer using matplotlib and networkx."""

import math
from typing import Optional, Dict, List, Tuple

import networkx as nx
import matplotlib.pyplot as plt


# Distinct colors assigned to node labels so different entity types are visible.
_PALETTE = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2",
    "#59a14f", "#edc948", "#b07aa1", "#ff9da7",
]


def visualize(graph: nx.DiGraph, output_path: Optional[str] = None) -> None:
    """Draw the graph and either display it interactively or save to a file.

    Nodes are colored by their 'label' attribute; edge labels show the
    relationship type and optional weight.
    """
    visible_graph = _connected_subgraph(graph)
    if visible_graph.number_of_nodes() == 0:
        print("Nothing to visualize — the graph is empty.")
        return

    # Assign a color to each unique node label.
    labels_seen: Dict[str, str] = {}
    node_colors: List[str] = []
    for _, data in visible_graph.nodes(data=True):
        lbl = data.get("label", "unknown")
        if lbl not in labels_seen:
            labels_seen[lbl] = _PALETTE[len(labels_seen) % len(_PALETTE)]
        node_colors.append(labels_seen[lbl])

    pos = _layout_positions(visible_graph)
    node_labels = {
        node: data.get("display_name", str(node))
        for node, data in visible_graph.nodes(data=True)
    }

    plt.figure(figsize=(14, 10))
    nx.draw_networkx_nodes(
        visible_graph,
        pos,
        node_color=node_colors,
        node_size=1100,
        alpha=0.95,
        edgecolors="#ffffff",
        linewidths=1.5,
    )
    nx.draw_networkx_labels(visible_graph, pos, labels=node_labels, font_size=10)
    nx.draw_networkx_edges(
        visible_graph,
        pos,
        arrows=True,
        arrowsize=20,
        edge_color="#888888",
        width=1.5,
        connectionstyle="arc3,rad=0.12",
        min_source_margin=24,
        min_target_margin=24,
    )

    # Build edge labels from relationship name and optional weight.
    edge_labels: Dict[Tuple, str] = {}
    for src, tgt, data in visible_graph.edges(data=True):
        parts = [data.get("label", "")]
        if "weight" in data:
            parts.append(f"w={data['weight']}")
        edge_labels[(src, tgt)] = " ".join(parts)

    nx.draw_networkx_edge_labels(
        visible_graph,
        pos,
        edge_labels=edge_labels,
        font_size=8,
        rotate=False,
        label_pos=0.55,
        bbox={
            "boxstyle": "round,pad=0.2",
            "fc": "white",
            "ec": "none",
            "alpha": 0.85,
        },
    )

    # Build a legend for node types.
    for label_name, color in labels_seen.items():
        plt.scatter([], [], c=color, s=100, label=label_name)
    plt.legend(scatterpoints=1, frameon=True, title="Node types")

    plt.title("Graph constructed from DSL")
    plt.axis("off")
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150)
        print(f"Graph image saved to {output_path}")
    else:
        plt.show()


def _connected_subgraph(graph: nx.DiGraph) -> nx.DiGraph:
    """Return a copy containing only nodes that participate in at least one edge."""
    connected_nodes = [node for node, degree in graph.degree() if degree > 0]
    return graph.subgraph(connected_nodes).copy()


def _layout_positions(graph: nx.DiGraph) -> Dict[str, Tuple[float, float]]:
    """Compute a roomier deterministic layout so edges remain visible."""
    node_count = graph.number_of_nodes()
    if node_count == 1:
        only_node = next(iter(graph.nodes()))
        return {only_node: (0.0, 0.0)}

    k = max(2.5, 3.2 / max(math.sqrt(node_count), 1.0))
    base_pos = nx.spring_layout(
        graph,
        seed=42,
        k=k,
        iterations=500,
        scale=1.0,
    )

    spread = max(5.0, 2.5 * math.sqrt(node_count))
    spaced_pos = {
        node: (coords[0] * spread, coords[1] * spread)
        for node, coords in base_pos.items()
    }
    return _normalize_positions(spaced_pos)


def _normalize_positions(
    positions: Dict[str, Tuple[float, float]]
) -> Dict[str, Tuple[float, float]]:
    """Rescale positions to fill the drawing frame without collapsing spacing."""
    xs = [coords[0] for coords in positions.values()]
    ys = [coords[1] for coords in positions.values()]
    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)
    width = max(max_x - min_x, 1e-9)
    height = max(max_y - min_y, 1e-9)

    target_width = 15.0
    target_height = 10.5
    scale = min(target_width / width, target_height / height)
    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0

    return {
        node: ((coords[0] - center_x) * scale, (coords[1] - center_y) * scale)
        for node, coords in positions.items()
    }
