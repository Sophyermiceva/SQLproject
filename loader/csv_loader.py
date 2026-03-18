"""CSV file loader.

Reads a CSV file into a list of dictionaries (one dict per row),
which is a lightweight representation of a data table.
"""

import csv
from pathlib import Path
from typing import Dict, List, Union

from dsl.errors import InterpreterError

# Each table is represented as a list of row-dicts.
Row = Dict[str, str]
Table = List[Row]


def load_csv(file_path: Union[str, Path]) -> Table:
    """Load a CSV file and return its rows as a list of dictionaries.

    Raises InterpreterError if the file does not exist or cannot be read.
    """
    path = Path(file_path)
    if not path.exists():
        raise InterpreterError(f"Data file not found: {path}")

    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows: Table = list(reader)
    except Exception as exc:
        raise InterpreterError(f"Failed to read '{path}': {exc}") from exc

    if not rows:
        raise InterpreterError(f"Data file is empty: {path}")

    return rows
