"""Entry point for the Graph DSL project.

Usage:
    python main.py <script.dsl> [--data-dir <dir>] [--output <image.png>]

If --output is given, the graph visualisation is saved to that file;
otherwise it is displayed interactively.
"""

import argparse
import sys
from pathlib import Path

from dsl.lexer import Lexer
from dsl.parser import Parser
from dsl.interpreter import Interpreter
from dsl.errors import DSLError
from graph.graphviz_backend import GraphvizTranspiler
from graph.visualizer import visualize


def main() -> None:
    ap = argparse.ArgumentParser(description="Graph-construction DSL interpreter")
    ap.add_argument("script", help="Path to a .dsl script file")
    ap.add_argument(
        "--data-dir",
        default=None,
        help="Directory containing CSV data files (defaults to script's directory)",
    )
    ap.add_argument(
        "--output", "-o",
        default=None,
        help="Save graph image to this file instead of showing it",
    )
    ap.add_argument(
        "--backend",
        choices=["networkx", "graphviz"],
        default="networkx",
        help="Choose whether to build and render the graph or transpile it to Graphviz DOT",
    )
    args = ap.parse_args()

    script_path = Path(args.script)
    if not script_path.exists():
        print(f"Error: script file not found: {script_path}", file=sys.stderr)
        sys.exit(1)

    data_dir = Path(args.data_dir) if args.data_dir else script_path.parent

    source = script_path.read_text(encoding="utf-8")

    try:
        # 1. Lex
        tokens = Lexer(source).tokenize()

        # 2. Parse
        ast = Parser(tokens).parse()

        if args.backend == "graphviz":
            transpiler = GraphvizTranspiler(data_dir=data_dir)
            dot_output = transpiler.run(ast)
            if args.output:
                Path(args.output).write_text(dot_output, encoding="utf-8")
                print(f"Graphviz DOT saved to {args.output}")
            else:
                print(dot_output)
        else:
            interpreter = Interpreter(data_dir=data_dir)
            builder = interpreter.run(ast)
            print(builder.summary())
            visualize(builder.graph, output_path=args.output)

    except DSLError as exc:
        print(f"DSL Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
