"""Freeze workflow (M11).

Writes a frozen snapshot of results to data/frozen/, hashes it,
and creates a git commit + tag so predictions are locked to a specific state.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FROZEN_DIR = _REPO_ROOT / "data" / "frozen"
_BUILD_DIR  = _REPO_ROOT / "data" / "build"

_FREEZE_TAG = "predictions-frozen-v1"
_FREEZE_TAG_ILLUSTRATIVE = "predictions-frozen-illustrative-v1"


class FreezeError(Exception):
    """Raised when the freeze preconditions are not met."""


def _git(*args: str, capture: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=_REPO_ROOT,
        capture_output=capture,
        text=True,
    )
    if result.returncode != 0:
        raise FreezeError(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout.strip() if capture else ""


def _check_clean() -> None:
    """Refuse if the working tree has uncommitted changes."""
    status = _git("status", "--porcelain")
    if status:
        raise FreezeError(
            "git working tree is dirty — commit or stash all changes before freezing.\n"
            f"Unclean files:\n{status}"
        )


def _check_no_existing_tag(tag: str) -> None:
    """Refuse if the freeze tag already exists (re-run protection)."""
    tags = _git("tag", "--list", tag)
    if tags:
        raise FreezeError(
            f"freeze tag {tag!r} already exists — predictions already frozen. "
            "To re-freeze, delete the tag first (git tag -d <tag>) and re-run."
        )


def run_freeze(mode: str = "strict", out_dir: Path | None = None) -> Path:
    """Run the full freeze workflow.

    Args:
        mode: must be "strict" (freeze refuses dev mode).
        out_dir: where frozen artifacts go (default data/frozen/).

    Returns:
        Path to the written FROZEN.json.

    Raises:
        FreezeError: if preconditions not met (dirty tree, tag exists, dev mode).
    """
    if mode != "strict":
        raise FreezeError(
            "freeze requires strict mode — run with mode='strict'. "
            "Dev mode is not frozen (unsourced rows would be embedded)."
        )

    _check_clean()

    from pharmashed.montecarlo import RunContext  # noqa: PLC0415
    from pharmashed.export import export_build, sha256_file  # noqa: PLC0415

    ctx = RunContext.from_paths(mode="strict")

    # Determine tag name (illustrative tag if any row is non-sourced per D36)
    any_illustrative = any(r.status != "sourced" for r in ctx.consumption_rows)
    tag = _FREEZE_TAG_ILLUSTRATIVE if any_illustrative else _FREEZE_TAG

    _check_no_existing_tag(tag)

    frozen_dir = Path(out_dir) if out_dir else _FROZEN_DIR
    frozen_dir.mkdir(parents=True, exist_ok=True)

    git_commit = _git("rev-parse", "HEAD")

    # Write to frozen dir with the tag embedded
    results_path = export_build(ctx, frozen_dir, variant="full", frozen_tag=tag)

    # Also write build dir copy (without frozen_tag, for the live API)
    _BUILD_DIR.mkdir(parents=True, exist_ok=True)
    export_build(ctx, _BUILD_DIR, variant="full", frozen_tag=None)

    # Hash the frozen results.json
    sha = sha256_file(results_path)

    frozen_json = {
        "sha256": sha,
        "frozen_tag": tag,
        "engine_version": _engine_version(),
        "git_commit": git_commit,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    frozen_json_path = frozen_dir / "FROZEN.json"
    frozen_json_path.write_text(json.dumps(frozen_json, indent=2))

    # git add, commit, tag
    _git("add", str(frozen_dir.relative_to(_REPO_ROOT)))
    _git("commit", "-m", f"freeze predictions {tag}")
    _git("tag", tag)

    return frozen_json_path


def verify_frozen(frozen_dir: Path | None = None) -> dict:
    """Verify the frozen snapshot: re-hash results.json and compare with FROZEN.json.

    Args:
        frozen_dir: directory to check (default data/frozen/).

    Returns:
        Dict with 'ok' bool and 'detail' str.

    Raises:
        FreezeError: if FROZEN.json or results.json not found.
    """
    from pharmashed.export import sha256_file  # noqa: PLC0415

    d = Path(frozen_dir) if frozen_dir else _FROZEN_DIR
    frozen_json_path = d / "FROZEN.json"
    results_path = d / "results.json"

    if not frozen_json_path.exists():
        raise FreezeError(f"FROZEN.json not found in {d}")
    if not results_path.exists():
        raise FreezeError(f"results.json not found in {d}")

    record = json.loads(frozen_json_path.read_text())
    expected_sha = record["sha256"]
    actual_sha = sha256_file(results_path)

    if actual_sha != expected_sha:
        return {
            "ok": False,
            "detail": f"SHA-256 mismatch: expected {expected_sha}, got {actual_sha}",
        }

    # Verify tag exists in git
    tag = record.get("frozen_tag", _FREEZE_TAG)
    try:
        _git("rev-parse", f"refs/tags/{tag}")
        tag_ok = True
    except FreezeError:
        tag_ok = False

    if not tag_ok:
        return {"ok": False, "detail": f"git tag {tag!r} not found"}

    return {"ok": True, "detail": f"frozen at {record.get('created_at', '?')} tag={tag}"}


def _engine_version() -> str:
    try:
        import pharmashed as _pkg  # noqa: PLC0415
        return getattr(_pkg, "__version__", "0.0.0")
    except Exception:
        return "0.0.0"
