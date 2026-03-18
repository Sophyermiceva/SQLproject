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

## Installation

```bash
cd graph_dsl
pip install -r requirements.txt
```

Dependencies: `networkx`, `matplotlib` (standard Python 3.9+).

## Usage

```bash
# Run with interactive graph window
python main.py examples/scripts/build_graph.dsl --data-dir examples/data

# Save graph image to file
python main.py examples/scripts/build_graph.dsl --data-dir examples/data --output graph.png

# Transpile to Graphviz DOT
python main.py examples/scripts/build_graph.dsl --data-dir examples/data --backend graphviz --output graph.dot
```

### Command-line arguments

| Argument      | Required | Description                                        |
|---------------|----------|----------------------------------------------------|
| `script`      | Yes      | Path to a `.dsl` script file                       |
| `--data-dir`  | No       | Directory with CSV files (defaults to script's dir) |
| `--output`    | No       | Save output to this file: image for `networkx`, DOT for `graphviz` |
| `--backend`   | No       | `networkx` to render the graph, `graphviz` to emit DOT syntax |

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

## Possible Future Improvements

- Support for additional data formats (JSON, Parquet, SQL databases)
- Bidirectional / undirected edges (`EDGE ... UNDIRECTED`)
- Node and edge filtering (`WHERE` clauses)
- Graph export to standard formats (GraphML, GEXF, DOT)
- Graph analysis commands within the DSL (shortest path, centrality, clustering)
- Interactive REPL mode for step-by-step graph building
- Type system for node/edge attributes
- Multi-graph support (multiple independent graphs in one script)
