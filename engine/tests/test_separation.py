"""M12 import-rule enforcement: only checks/ may read data/observed/."""

from __future__ import annotations

import re
from pathlib import Path

_ENGINE_SRC = Path(__file__).resolve().parents[1] / "src" / "pharmashed"
_CHECKS_DIR = _ENGINE_SRC / "checks"

_FORBIDDEN_PATTERNS = [
    re.compile(r"observed"),
    re.compile(r"rodrigues"),
]


def test_observed_not_imported_outside_checks():
    """No file in pharmashed/ (outside checks/) may reference 'observed' or 'rodrigues'."""
    violations = []
    for py_file in _ENGINE_SRC.rglob("*.py"):
        if py_file.is_relative_to(_CHECKS_DIR):
            continue  # checks/ is allowed
        text = py_file.read_text()
        for pattern in _FORBIDDEN_PATTERNS:
            if pattern.search(text):
                violations.append(f"{py_file.relative_to(_ENGINE_SRC)}: matches '{pattern.pattern}'")

    assert not violations, (
        "Files outside checks/ reference observed data:\n" + "\n".join(violations)
    )


def test_checks_does_not_write_frozen():
    """checks/ must never write to data/frozen/."""
    frozen_writes = []
    for py_file in _CHECKS_DIR.rglob("*.py"):
        text = py_file.read_text()
        if "frozen" in text and ("write" in text or "open" in text) and "data/frozen" in text:
            frozen_writes.append(str(py_file.relative_to(_CHECKS_DIR)))

    assert not frozen_writes, (
        "checks/ files appear to write to data/frozen/:\n" + "\n".join(frozen_writes)
    )
