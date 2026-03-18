"""Unit tests covering the full DSL pipeline: lexer → parser → interpreter."""

import math
import unittest
from pathlib import Path

from dsl.ast_nodes import (
    ComparisonExpression,
    EdgeStatement,
    IdentifierValue,
    LoadStatement,
    LogicalExpression,
    NodeStatement,
    NumberValue,
)
from dsl.lexer import Lexer
from dsl.parser import Parser
from dsl.interpreter import Interpreter
from dsl.errors import LexerError, ParserError, InterpreterError
from graph.graphviz_backend import GraphvizTranspiler
from graph.visualizer import _connected_subgraph, _layout_positions


TEST_DATA = Path(__file__).resolve().parent / "data"


class TestLexer(unittest.TestCase):

    def test_load_statement(self):
        tokens = Lexer("LOAD users;").tokenize()
        types = [t.type.name for t in tokens]
        self.assertEqual(types, ["LOAD", "IDENTIFIER", "SEMICOLON", "EOF"])

    def test_full_program(self):
        src = "LOAD t; NODE A KEY id FROM t;"
        tokens = Lexer(src).tokenize()
        self.assertTrue(len(tokens) > 0)
        self.assertEqual(tokens[-1].type.name, "EOF")

    def test_where_tokens(self):
        src = "EDGE Bought FROM orders SOURCE user_id TARGET product_id WHERE (amount > 1) AND (amount < 5);"
        tokens = Lexer(src).tokenize()
        types = [t.type.name for t in tokens]
        self.assertIn("WHERE", types)
        self.assertIn("LPAREN", types)
        self.assertIn("RPAREN", types)
        self.assertIn("AND", types)
        self.assertIn("GREATER", types)
        self.assertIn("LESS", types)
        self.assertIn("NUMBER", types)

    def test_name_tokens(self):
        tokens = Lexer("NODE User KEY id NAME name FROM users;").tokenize()
        types = [t.type.name for t in tokens]
        self.assertIn("NAME", types)

    def test_where_inclusive_tokens(self):
        tokens = Lexer("EDGE Bought FROM orders SOURCE user_id TARGET product_id WHERE amount >= 1 AND amount <= 5;").tokenize()
        types = [t.type.name for t in tokens]
        self.assertIn("GREATER_EQUAL", types)
        self.assertIn("LESS_EQUAL", types)

    def test_comment_skipping(self):
        src = "# this is a comment\nLOAD t;"
        tokens = Lexer(src).tokenize()
        types = [t.type.name for t in tokens]
        self.assertNotIn("COMMENT", types)
        self.assertIn("LOAD", types)

    def test_unexpected_character(self):
        with self.assertRaises(LexerError):
            Lexer("LOAD @invalid;").tokenize()


class TestParser(unittest.TestCase):

    def _parse(self, source: str):
        tokens = Lexer(source).tokenize()
        return Parser(tokens).parse()

    def test_load(self):
        stmts = self._parse("LOAD users;")
        self.assertEqual(len(stmts), 1)
        self.assertIsInstance(stmts[0], LoadStatement)
        self.assertEqual(stmts[0].table_name, "users")

    def test_node(self):
        stmts = self._parse("NODE User KEY id FROM users;")
        self.assertEqual(len(stmts), 1)
        self.assertIsInstance(stmts[0], NodeStatement)
        self.assertEqual(stmts[0].label, "User")
        self.assertEqual(stmts[0].key_field, "id")
        self.assertIsNone(stmts[0].name_field)
        self.assertEqual(stmts[0].table_name, "users")

    def test_node_with_name_field(self):
        stmts = self._parse("NODE User KEY id NAME name FROM users;")
        self.assertEqual(len(stmts), 1)
        self.assertIsInstance(stmts[0], NodeStatement)
        self.assertEqual(stmts[0].name_field, "name")

    def test_edge_with_weight(self):
        src = "EDGE Bought FROM orders SOURCE uid TARGET pid WEIGHT amt;"
        stmts = self._parse(src)
        self.assertEqual(len(stmts), 1)
        edge = stmts[0]
        self.assertIsInstance(edge, EdgeStatement)
        self.assertEqual(edge.weight_field, "amt")

    def test_edge_without_weight(self):
        src = "EDGE Follows FROM social SOURCE a TARGET b;"
        stmts = self._parse(src)
        edge = stmts[0]
        self.assertIsNone(edge.weight_field)

    def test_multiple_statements(self):
        src = """
        LOAD users;
        LOAD orders;
        NODE User KEY id FROM users;
        EDGE Bought FROM orders SOURCE user_id TARGET product_id WEIGHT amount;
        """
        stmts = self._parse(src)
        self.assertEqual(len(stmts), 4)

    def test_node_with_parenthesized_where(self):
        stmts = self._parse("NODE Product KEY product_id FROM orders WHERE (amount > 1) AND (amount < 5);")
        stmt = stmts[0]
        self.assertIsInstance(stmt, NodeStatement)
        self.assertIsInstance(stmt.where, LogicalExpression)
        self.assertEqual(stmt.where.operator, "AND")
        self.assertEqual(stmt.where.left, ComparisonExpression("amount", ">", NumberValue(1.0)))
        self.assertEqual(stmt.where.right, ComparisonExpression("amount", "<", NumberValue(5.0)))

    def test_where_precedence(self):
        stmts = self._parse(
            "EDGE Bought FROM orders SOURCE user_id TARGET product_id "
            "WHERE amount > 4 OR amount < 2 AND product_id < P3;"
        )
        stmt = stmts[0]
        self.assertIsInstance(stmt, EdgeStatement)
        self.assertIsInstance(stmt.where, LogicalExpression)
        self.assertEqual(stmt.where.operator, "OR")
        self.assertEqual(stmt.where.left, ComparisonExpression("amount", ">", NumberValue(4.0)))
        self.assertEqual(
            stmt.where.right,
            LogicalExpression(
                operator="AND",
                left=ComparisonExpression("amount", "<", NumberValue(2.0)),
                right=ComparisonExpression("product_id", "<", IdentifierValue("P3")),
            ),
        )

    def test_where_inclusive_comparisons(self):
        stmts = self._parse(
            "EDGE Bought FROM orders SOURCE user_id TARGET product_id "
            "WHERE amount >= 2 AND amount <= 5;"
        )
        stmt = stmts[0]
        self.assertIsInstance(stmt, EdgeStatement)
        self.assertEqual(
            stmt.where,
            LogicalExpression(
                operator="AND",
                left=ComparisonExpression("amount", ">=", NumberValue(2.0)),
                right=ComparisonExpression("amount", "<=", NumberValue(5.0)),
            ),
        )

    def test_missing_semicolon(self):
        with self.assertRaises(ParserError):
            self._parse("LOAD users")

    def test_unexpected_token(self):
        with self.assertRaises(ParserError):
            self._parse("WEIGHT something;")


class TestInterpreter(unittest.TestCase):

    def test_full_pipeline(self):
        src = """
        LOAD users;
        LOAD orders;
        NODE User KEY id NAME name FROM users;
        NODE Product KEY product_id FROM orders;
        EDGE Bought FROM orders SOURCE user_id TARGET product_id WEIGHT amount;
        """
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        interpreter = Interpreter(data_dir=TEST_DATA)
        builder = interpreter.run(ast)

        g = builder.graph
        self.assertGreater(g.number_of_nodes(), 0)
        self.assertGreater(g.number_of_edges(), 0)

        # Users 1..4 + products P1, P2, P3 = 7 nodes
        self.assertEqual(g.number_of_nodes(), 7)
        # 6 order rows = 6 edges
        self.assertEqual(g.number_of_edges(), 6)
        self.assertEqual(g.nodes["1"]["display_name"], "Alice")
        self.assertEqual(g.nodes["P1"]["display_name"], "P1")

    def test_missing_table(self):
        src = "NODE User KEY id FROM nonexistent;"
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        interpreter = Interpreter(data_dir=TEST_DATA)
        with self.assertRaises(InterpreterError):
            interpreter.run(ast)

    def test_missing_column(self):
        src = """
        LOAD users;
        NODE User KEY nonexistent_column FROM users;
        """
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        interpreter = Interpreter(data_dir=TEST_DATA)
        with self.assertRaises(InterpreterError):
            interpreter.run(ast)

    def test_where_filters_edges(self):
        src = """
        LOAD orders;
        EDGE Bought FROM orders SOURCE user_id TARGET product_id WEIGHT amount
            WHERE (amount > 1) AND (amount < 5);
        """
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        interpreter = Interpreter(data_dir=TEST_DATA)
        builder = interpreter.run(ast)

        g = builder.graph
        self.assertEqual(g.number_of_edges(), 3)
        self.assertEqual(set(g.edges()), {("1", "P1"), ("3", "P3"), ("2", "P3")})

    def test_where_filters_nodes(self):
        src = """
        LOAD orders;
        NODE Product KEY product_id FROM orders WHERE (amount > 1) AND (amount < 5);
        """
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        interpreter = Interpreter(data_dir=TEST_DATA)
        builder = interpreter.run(ast)

        g = builder.graph
        self.assertEqual(set(g.nodes()), {"P1", "P3"})

    def test_where_filters_with_inclusive_comparisons(self):
        src = """
        LOAD orders;
        EDGE Bought FROM orders SOURCE user_id TARGET product_id
            WHERE amount >= 2 AND amount <= 3;
        """
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        interpreter = Interpreter(data_dir=TEST_DATA)
        builder = interpreter.run(ast)

        g = builder.graph
        self.assertEqual(set(g.edges()), {("1", "P1"), ("3", "P3"), ("2", "P3")})

    def test_where_missing_column(self):
        src = """
        LOAD orders;
        EDGE Bought FROM orders SOURCE user_id TARGET product_id WHERE missing > 1;
        """
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        interpreter = Interpreter(data_dir=TEST_DATA)
        with self.assertRaises(InterpreterError):
            interpreter.run(ast)

    def test_missing_name_column(self):
        src = """
        LOAD users;
        NODE User KEY id NAME nickname FROM users;
        """
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        interpreter = Interpreter(data_dir=TEST_DATA)
        with self.assertRaises(InterpreterError):
            interpreter.run(ast)

    def test_summary_uses_display_name(self):
        src = """
        LOAD users;
        NODE User KEY id NAME name FROM users WHERE id < 2;
        """
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        interpreter = Interpreter(data_dir=TEST_DATA)
        builder = interpreter.run(ast)

        self.assertIn("[User] Alice (1)", builder.summary())


class TestVisualizer(unittest.TestCase):

    def test_connected_subgraph_hides_isolated_nodes(self):
        src = """
        LOAD users;
        LOAD orders;
        NODE User KEY id NAME name FROM users;
        NODE Product KEY product_id FROM orders;
        EDGE Bought FROM orders SOURCE user_id TARGET product_id WHERE amount > 4;
        """
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        interpreter = Interpreter(data_dir=TEST_DATA)
        builder = interpreter.run(ast)

        visible_graph = _connected_subgraph(builder.graph)

        self.assertEqual(set(visible_graph.nodes()), {"2", "P1"})
        self.assertEqual(set(visible_graph.edges()), {("2", "P1")})

    def test_layout_fills_available_frame(self):
        src = """
        LOAD users;
        LOAD orders;
        NODE User KEY id NAME name FROM users;
        NODE Product KEY product_id FROM orders;
        EDGE Bought FROM orders SOURCE user_id TARGET product_id;
        """
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        interpreter = Interpreter(data_dir=TEST_DATA)
        builder = interpreter.run(ast)

        visible_graph = _connected_subgraph(builder.graph)
        positions = _layout_positions(visible_graph)

        edge_lengths = []
        for source, target in visible_graph.edges():
            source_pos = positions[source]
            target_pos = positions[target]
            edge_lengths.append(math.dist(source_pos, target_pos))

        self.assertTrue(edge_lengths)
        self.assertGreater(min(edge_lengths), 1.0)
        xs = [coords[0] for coords in positions.values()]
        ys = [coords[1] for coords in positions.values()]
        self.assertGreater(max(xs) - min(xs), 8.0)
        self.assertGreater(max(ys) - min(ys), 5.0)


class TestGraphvizBackend(unittest.TestCase):

    def test_transpiles_program_to_dot(self):
        src = """
        LOAD users;
        LOAD orders;
        NODE User KEY id NAME name FROM users WHERE id <= 2;
        NODE Product KEY product_id FROM orders WHERE amount >= 5;
        EDGE Bought FROM orders SOURCE user_id TARGET product_id WEIGHT amount WHERE amount >= 5;
        """
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        transpiler = GraphvizTranspiler(data_dir=TEST_DATA)

        dot = transpiler.run(ast)

        self.assertIn('digraph DSLGraph {', dot)
        self.assertIn('"1" [label="Alice\\n(1)"', dot)
        self.assertIn('"2" [label="Bob\\n(2)"', dot)
        self.assertIn('"P1" [label="P1"', dot)
        self.assertIn('"2" -> "P1" [label="Bought\\nw=5.0"]', dot)

    def test_graphviz_backend_validates_missing_name_column(self):
        src = """
        LOAD users;
        NODE User KEY id NAME nickname FROM users;
        """
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        transpiler = GraphvizTranspiler(data_dir=TEST_DATA)

        with self.assertRaises(InterpreterError):
            transpiler.run(ast)


class TestAdditionalFixtures(unittest.TestCase):

    def test_non_numeric_weight_is_preserved(self):
        src = """
        LOAD orders_text_weight;
        EDGE Severity FROM orders_text_weight SOURCE user_id TARGET product_id WEIGHT amount;
        """
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        interpreter = Interpreter(data_dir=TEST_DATA)
        builder = interpreter.run(ast)

        self.assertEqual(builder.graph["1"]["P1"]["weight"], "low")

    def test_isolated_nodes_are_removed_from_visible_subgraph(self):
        src = """
        LOAD isolated_users;
        NODE User KEY id NAME name FROM isolated_users;
        """
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        interpreter = Interpreter(data_dir=TEST_DATA)
        builder = interpreter.run(ast)

        visible_graph = _connected_subgraph(builder.graph)
        self.assertEqual(visible_graph.number_of_nodes(), 0)


if __name__ == "__main__":
    unittest.main()
