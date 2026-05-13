"""Token types and the Token dataclass used by the lexer and parser."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict


class TokenType(Enum):
    # Keywords
    LOAD = auto()
    NODE = auto()
    EDGE = auto()
    KEY = auto()
    NAME = auto()
    FROM = auto()
    SOURCE = auto()
    TARGET = auto()
    WEIGHT = auto()
    PRIOR = auto()
    PROBABILITY = auto()
    GIVEN = auto()
    WHERE = auto()
    AND = auto()
    OR = auto()

    # Literals / symbols
    IDENTIFIER = auto()
    NUMBER = auto()
    SEMICOLON = auto()
    LPAREN = auto()
    RPAREN = auto()
    GREATER = auto()
    LESS = auto()
    GREATER_EQUAL = auto()
    LESS_EQUAL = auto()

    # Special
    EOF = auto()


# Maps uppercase keyword strings to their token types.
KEYWORDS: Dict[str, TokenType] = {
    "LOAD": TokenType.LOAD,
    "NODE": TokenType.NODE,
    "EDGE": TokenType.EDGE,
    "KEY": TokenType.KEY,
    "NAME": TokenType.NAME,
    "FROM": TokenType.FROM,
    "SOURCE": TokenType.SOURCE,
    "TARGET": TokenType.TARGET,
    "WEIGHT": TokenType.WEIGHT,
    "PRIOR": TokenType.PRIOR,
    "PROBABILITY": TokenType.PROBABILITY,
    "GIVEN": TokenType.GIVEN,
    "WHERE": TokenType.WHERE,
    "AND": TokenType.AND,
    "OR": TokenType.OR,
}


@dataclass
class Token:
    """A single lexical token produced by the lexer."""
    type: TokenType
    value: str
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, ln={self.line})"
