"""Recursive-descent parser for the graph-construction DSL."""

from typing import List, Optional

from dsl.tokens import Token, TokenType
from dsl.ast_nodes import (
    ComparisonExpression,
    EdgeStatement,
    Expression,
    IdentifierValue,
    LoadStatement,
    LogicalExpression,
    NodeStatement,
    NumberValue,
    Statement,
    Value,
)
from dsl.errors import ParserError


class Parser:
    """Parses a list of tokens into a list of AST statements."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _peek_type(self) -> TokenType:
        return self._current().type

    def _expect(self, expected: TokenType) -> Token:
        """Consume the current token if it matches, otherwise raise an error."""
        token = self._current()
        if token.type != expected:
            raise ParserError(
                f"Expected {expected.name}, got {token.type.name} ('{token.value}')",
                line=token.line,
            )
        self.pos += 1
        return token

    def _expect_identifier(self) -> str:
        """Consume an IDENTIFIER token and return its value."""
        token = self._current()
        if token.type not in {
            TokenType.IDENTIFIER,
            TokenType.NAME,
        }:
            raise ParserError(
                f"Expected IDENTIFIER, got {token.type.name} ('{token.value}')",
                line=token.line,
            )
        self.pos += 1
        return token.value

    def _match(self, token_type: TokenType) -> bool:
        if self._peek_type() != token_type:
            return False
        self.pos += 1
        return True

    def _parse_value(self) -> Value:
        token = self._current()
        if token.type == TokenType.NUMBER:
            self.pos += 1
            return NumberValue(float(token.value))
        if token.type == TokenType.IDENTIFIER:
            self.pos += 1
            return IdentifierValue(token.value)
        raise ParserError(
            f"Expected comparison value, got {token.type.name} ('{token.value}')",
            line=token.line,
        )

    def _parse_comparison(self) -> ComparisonExpression:
        field = self._expect_identifier()
        operator_token = self._current()
        if operator_token.type == TokenType.GREATER:
            self.pos += 1
            operator = ">"
        elif operator_token.type == TokenType.GREATER_EQUAL:
            self.pos += 1
            operator = ">="
        elif operator_token.type == TokenType.LESS:
            self.pos += 1
            operator = "<"
        elif operator_token.type == TokenType.LESS_EQUAL:
            self.pos += 1
            operator = "<="
        else:
            raise ParserError(
                f"Expected comparison operator, got {operator_token.type.name} "
                f"('{operator_token.value}')",
                line=operator_token.line,
            )
        value = self._parse_value()
        return ComparisonExpression(field=field, operator=operator, value=value)

    def _parse_expression_term(self) -> Expression:
        if self._match(TokenType.LPAREN):
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN)
            return expr
        return self._parse_comparison()

    def _parse_and_expression(self) -> Expression:
        expr = self._parse_expression_term()
        while self._match(TokenType.AND):
            expr = LogicalExpression(
                operator="AND",
                left=expr,
                right=self._parse_expression_term(),
            )
        return expr

    def _parse_expression(self) -> Expression:
        expr = self._parse_and_expression()
        while self._match(TokenType.OR):
            expr = LogicalExpression(
                operator="OR",
                left=expr,
                right=self._parse_and_expression(),
            )
        return expr

    def _parse_optional_where(self) -> Optional[Expression]:
        if not self._match(TokenType.WHERE):
            return None
        return self._parse_expression()

    # ------------------------------------------------------------------
    # Statement parsers
    # ------------------------------------------------------------------

    def _parse_load(self) -> LoadStatement:
        self._expect(TokenType.LOAD)
        name = self._expect_identifier()
        self._expect(TokenType.SEMICOLON)
        return LoadStatement(table_name=name)

    def _parse_node(self) -> NodeStatement:
        self._expect(TokenType.NODE)
        label = self._expect_identifier()
        self._expect(TokenType.KEY)
        key_field = self._expect_identifier()
        name_field: Optional[str] = None
        if self._peek_type() == TokenType.NAME:
            self._expect(TokenType.NAME)
            name_field = self._expect_identifier()
        self._expect(TokenType.FROM)
        table_name = self._expect_identifier()
        where = self._parse_optional_where()
        self._expect(TokenType.SEMICOLON)
        return NodeStatement(
            label=label,
            key_field=key_field,
            name_field=name_field,
            table_name=table_name,
            where=where,
        )

    def _parse_edge(self) -> EdgeStatement:
        self._expect(TokenType.EDGE)
        label = self._expect_identifier()
        self._expect(TokenType.FROM)
        table_name = self._expect_identifier()
        self._expect(TokenType.SOURCE)
        source_field = self._expect_identifier()
        self._expect(TokenType.TARGET)
        target_field = self._expect_identifier()

        weight_field: Optional[str] = None
        if self._peek_type() == TokenType.WEIGHT:
            self._expect(TokenType.WEIGHT)
            weight_field = self._expect_identifier()

        where = self._parse_optional_where()
        self._expect(TokenType.SEMICOLON)
        return EdgeStatement(
            label=label,
            table_name=table_name,
            source_field=source_field,
            target_field=target_field,
            weight_field=weight_field,
            where=where,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def parse(self) -> List[Statement]:
        """Parse the full token stream and return a list of AST statements."""
        statements: List[Statement] = []

        while self._peek_type() != TokenType.EOF:
            tt = self._peek_type()
            if tt == TokenType.LOAD:
                statements.append(self._parse_load())
            elif tt == TokenType.NODE:
                statements.append(self._parse_node())
            elif tt == TokenType.EDGE:
                statements.append(self._parse_edge())
            else:
                token = self._current()
                raise ParserError(
                    f"Unexpected token {token.type.name} ('{token.value}')",
                    line=token.line,
                )

        return statements
