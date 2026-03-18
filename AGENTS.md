# AGENTS.md

## Project
DSL for generating graphs from tabular data.

Pipeline:
    DSL → Lexer → Parser → AST → Semantic Checks → Graph

---

## Components

- Lexer: deterministic tokenization
- Parser: recursive descent, no generators
- AST: immutable, minimal structures
- Semantic: validate tables, keys, references
- Graph: build nodes/edges, apply filters

---

## Rules

- Python only
- No unnecessary abstractions
- Keep functions small and explicit
- Fail fast on invalid input
- Do not change grammar unless asked

---

## Performance

- Linear parsing
- Avoid unnecessary allocations
- No quadratic behavior

---

## Testing

- Lexer → tokens correct
- Parser → AST correct
- Semantic → invalid rejected
- Graph → correct output

---

## DSL Example

LOAD users;
NODE User KEY id FROM users;
EDGE Bought FROM orders SOURCE user_id TARGET product_id;

---

## Non-Goals

- No UI
- No DB integration
- No frameworks
