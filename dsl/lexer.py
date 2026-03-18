"""Lexer (tokenizer) for the graph-construction DSL.

Scans raw DSL source text character by character and produces a list of Tokens.
"""

from typing import Optional, List

from dsl.tokens import Token, TokenType, KEYWORDS
from dsl.errors import LexerError


class Lexer:
    """Converts a DSL source string into a sequence of tokens."""

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []

    def _current(self) -> Optional[str]:
        if self.pos < len(self.source):
            return self.source[self.pos]
        return None

    def _advance(self) -> None:
        if self._current() == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        self.pos += 1

    def _skip_whitespace(self) -> None:
        while self._current() is not None and self._current() in " \t\r\n":
            self._advance()

    def _skip_comment(self) -> None:
        """Skip single-line comments starting with '#'."""
        while self._current() is not None and self._current() != "\n":
            self._advance()

    def _read_identifier(self) -> Token:
        """Read an alphanumeric identifier or keyword."""
        start_col = self.col
        start_line = self.line
        chars: List[str] = []
        while self._current() is not None and (self._current().isalnum() or self._current() == "_"):
            chars.append(self._current())
            self._advance()
        word = "".join(chars)
        token_type = KEYWORDS.get(word.upper(), TokenType.IDENTIFIER)
        return Token(type=token_type, value=word, line=start_line, col=start_col)

    def _read_number(self) -> Token:
        """Read an integer or decimal numeric literal."""
        start_col = self.col
        start_line = self.line
        chars: List[str] = []
        seen_dot = False

        while self._current() is not None:
            ch = self._current()
            if ch.isdigit():
                chars.append(ch)
                self._advance()
                continue
            if ch == "." and not seen_dot:
                seen_dot = True
                chars.append(ch)
                self._advance()
                continue
            break

        return Token(
            type=TokenType.NUMBER,
            value="".join(chars),
            line=start_line,
            col=start_col,
        )

    def tokenize(self) -> List[Token]:
        """Scan the entire source and return a list of tokens."""
        while True:
            self._skip_whitespace()
            ch = self._current()

            if ch is None:
                self.tokens.append(Token(TokenType.EOF, "", self.line, self.col))
                break

            if ch == "#":
                self._skip_comment()
                continue

            if ch == ";":
                self.tokens.append(Token(TokenType.SEMICOLON, ";", self.line, self.col))
                self._advance()
                continue

            if ch == "(":
                self.tokens.append(Token(TokenType.LPAREN, "(", self.line, self.col))
                self._advance()
                continue

            if ch == ")":
                self.tokens.append(Token(TokenType.RPAREN, ")", self.line, self.col))
                self._advance()
                continue

            if ch == ">":
                line = self.line
                col = self.col
                self._advance()
                if self._current() == "=":
                    self.tokens.append(Token(TokenType.GREATER_EQUAL, ">=", line, col))
                    self._advance()
                else:
                    self.tokens.append(Token(TokenType.GREATER, ">", line, col))
                continue

            if ch == "<":
                line = self.line
                col = self.col
                self._advance()
                if self._current() == "=":
                    self.tokens.append(Token(TokenType.LESS_EQUAL, "<=", line, col))
                    self._advance()
                else:
                    self.tokens.append(Token(TokenType.LESS, "<", line, col))
                continue

            if ch.isalpha() or ch == "_":
                self.tokens.append(self._read_identifier())
                continue

            if ch.isdigit():
                self.tokens.append(self._read_number())
                continue

            raise LexerError(ch, self.line, self.col)

        return self.tokens
