"""Entry point for the Graph DSL project.

Usage:
    python main.py <script.dsl> [--data-dir <dir>] [--output <image.png>]
                  [--dot-output <graph.dot>]

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
from graph.bayesian_tree import BayesianTreeBuilder
from graph.graphviz_backend import GraphvizTranspiler, render_dot, save_dot
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
        help="Save the rendered graph image to this file instead of showing it",
    )
    ap.add_argument(
        "--dot-output",
        default=None,
        help="Save Graphviz DOT output to this file when using the graphviz backend",
    )
    ap.add_argument(
        "--backend",
        choices=["networkx", "graphviz", "bayes"],
        default="networkx",
        help="Choose whether to build the graph, emit Graphviz DOT, or evaluate a Bayesian tree",
    )
    args = ap.parse_args()

    script_path = Path(args.script)
    if not script_path.exists():
        print(f"Error: script file not found: {script_path}", file=sys.stderr)
        sys.exit(1)

    data_dir = Path(args.data_dir) if args.data_dir else script_path.parent

    source = script_path.read_text(encoding="utf-8")

    try:
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()

        if args.backend == "graphviz":
            transpiler = GraphvizTranspiler(data_dir=data_dir)
            dot_output = transpiler.run(ast)

            dot_path = None
            if args.dot_output:
                dot_path = save_dot(dot_output, args.dot_output)
                print(f"Graphviz DOT saved to {dot_path}")

            if args.output:
                if dot_path is None:
                    dot_path = save_dot(dot_output, Path(args.output).with_suffix(".dot"))
                    print(f"Graphviz DOT saved to {dot_path}")
                image_path = render_dot(dot_output, args.output, dot_path=dot_path)
                print(f"Graph image saved to {image_path}")
            elif dot_path is None:
                print(dot_output)
        elif args.backend == "bayes":
            builder = BayesianTreeBuilder(data_dir=data_dir)
            result = builder.run(ast)
            print(result.summary())

            dot_output = result.to_dot()
            dot_path = None
            if args.dot_output:
                dot_path = save_dot(dot_output, args.dot_output)
                print(f"Graphviz DOT saved to {dot_path}")

            if args.output:
                if dot_path is None:
                    dot_path = save_dot(dot_output, Path(args.output).with_suffix(".dot"))
                    print(f"Graphviz DOT saved to {dot_path}")
                image_path = render_dot(dot_output, args.output, dot_path=dot_path)
                print(f"Graph image saved to {image_path}")
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
