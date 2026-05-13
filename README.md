# Graph DSL — Domain-Specific Language for Graph Construction from Tabular Data

## Overview

This project implements a custom Domain-Specific Language (DSL) that allows users to
declaratively describe how to build a directed graph from existing tabular data (CSV files).

The DSL is **not** a SQL generator. It specifies which entities become graph nodes,
which fields serve as keys, and which relationships become edges.

## Architecture

```
DSL script  →  Lexer  →  Tokens  →  Parser  →  AST  →  Backend
                                                           ↑
                                                      CSV Loader
```

| Component          | File                     | Responsibility                                |
|--------------------|--------------------------|-----------------------------------------------|
| Token definitions  | `dsl/tokens.py`          | Token types and the Token dataclass            |
| Lexer              | `dsl/lexer.py`           | Scans source text into tokens                  |
| AST nodes          | `dsl/ast_nodes.py`       | Data classes for LOAD, NODE, EDGE statements   |
| Parser             | `dsl/parser.py`          | Recursive-descent parser producing an AST      |
| Runtime            | `dsl/runtime.py`         | Shared AST execution and filtering logic       |
| Interpreter        | `dsl/interpreter.py`     | Backend that builds the in-memory graph        |
| Graphviz backend   | `graph/graphviz_backend.py` | Backend that emits Graphviz DOT syntax      |
| Bayesian backend   | `graph/bayesian_tree.py` | Builds a Bayesian tree and propagates probabilities |
| Error classes      | `dsl/errors.py`          | Custom exceptions (LexerError, ParserError, …) |
| CSV Loader         | `loader/csv_loader.py`   | Reads CSV files into row-dict lists            |
| Graph Builder      | `graph/builder.py`       | Wraps networkx for node/edge construction      |
| Visualizer         | `graph/visualizer.py`    | Renders graph with matplotlib                  |
| CLI entry point    | `main.py`                | Command-line interface                         |

## DSL Syntax

```
# Comments start with '#'

LOAD <table_name>;

NODE <Label> KEY <key_column> [NAME <name_column>] FROM <table_name>;

EDGE <Label>
    FROM <table_name>
    SOURCE <source_column>
    TARGET <target_column>
    [WEIGHT <weight_column>];
```

For Bayesian trees:

```text
NODE Event KEY <event_id_column> NAME <name_column> PRIOR <prior_column> FROM <events_table>;

EDGE Causes
    FROM <conditionals_table>
    SOURCE <parent_event_column>
    TARGET <child_event_column>
    PROBABILITY <probability_column>
    GIVEN <parent_state_column>;
```

### Example

```
LOAD users;
LOAD orders;

NODE User KEY id NAME name FROM users;
NODE Product KEY product_id FROM orders;

EDGE Bought
    FROM orders
    SOURCE user_id
    TARGET product_id
    WEIGHT amount;
```

### Bayesian Tree Example

```text
LOAD bayes_events;
LOAD bayes_conditionals;

NODE Event KEY event_id NAME name PRIOR prior FROM bayes_events;

EDGE Causes
    FROM bayes_conditionals
    SOURCE parent_event
    TARGET child_event
    PROBABILITY probability
    GIVEN parent_state;
```

## Installation

```bash
cd graph_dsl
pip install -r requirements.txt
```

Dependencies: `networkx`, `matplotlib`, `graphviz` (standard Python 3.9+).

The Graphviz backend also requires the Graphviz system binary (`dot`) to be
installed and available on `PATH`.

## Usage

```bash
# Run with interactive graph window
python main.py examples/scripts/build_graph.dsl --data-dir examples/data

# Save graph image to file
python main.py examples/scripts/build_graph.dsl --data-dir examples/data --output graph.png

# Transpile to Graphviz DOT
python main.py examples/scripts/build_graph.dsl --data-dir examples/data --backend graphviz --dot-output graph.dot

# Save DOT and render a Graphviz image from it
python main.py examples/scripts/build_graph.dsl --data-dir examples/data --backend graphviz --dot-output graph.dot --output graph.png

# Evaluate and render a Bayesian tree
python main.py examples/scripts/bayesian_tree.dsl --data-dir examples/data --backend bayes --dot-output bayes.dot --output bayes.png
```

### Command-line arguments

| Argument      | Required | Description                                        |
|---------------|----------|----------------------------------------------------|
| `script`      | Yes      | Path to a `.dsl` script file                       |
| `--data-dir`  | No       | Directory with CSV files (defaults to script's dir) |
| `--output`    | No       | Save the rendered graph image to this file |
| `--dot-output`| No       | Save Graphviz DOT to this file when using the `graphviz` or `bayes` backend |
| `--backend`   | No       | `networkx` to render with matplotlib, `graphviz` to emit DOT and render via Graphviz, `bayes` to evaluate and render a Bayesian tree |

## Running Tests

```bash
cd graph_dsl
python -m unittest tests.test_pipeline -v
```

## Example Data

- `examples/data/users.csv` — user records (id, name, city)
- `examples/data/orders.csv` — purchase records (order_id, user_id, product_id, amount)
- `examples/data/friendships.csv` — social connections (person_a, person_b, since)

## Example DSL Scripts

- `examples/scripts/build_graph.dsl` — User-Product purchase graph with weighted edges
- `examples/scripts/social_graph.dsl` — Social friendship graph
- `examples/scripts/bayesian_tree.dsl` — Bayesian tree built from priors and conditional probabilities
- `examples/scripts/bayesian_incident_tree.dsl` — Larger Bayesian tree for an incident-response scenario

## Possible Future Improvements

- Support for additional data formats (JSON, Parquet, SQL databases)
- Bidirectional / undirected edges (`EDGE ... UNDIRECTED`)
- Node and edge filtering (`WHERE` clauses)
- Graph export to standard formats (GraphML, GEXF, DOT)
- Graph analysis commands within the DSL (shortest path, centrality, clustering)
- Interactive REPL mode for step-by-step graph building
- Type system for node/edge attributes
- Multi-graph support (multiple independent graphs in one script)
