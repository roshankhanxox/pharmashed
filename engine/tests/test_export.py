"""Tests for M11 export pipeline."""

from __future__ import annotations

import json
import struct
import tempfile
from pathlib import Path

import numpy as np
import pytest

from pharmashed.contracts import (
    DrawsIndex,
    Methodology,
    Results,
    Sites,
)
from pharmashed.export import export_build, sha256_file
from pharmashed.montecarlo import PairResult, RunContext

# --- minimal RunContext factory for tests (avoids disk I/O) ---

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _minimal_ctx() -> RunContext:
    """Load the real CSV/YAML files in dev mode (low N_DRAWS for speed)."""
    ctx = RunContext.from_paths(mode="dev")
    ctx.n_draws = 50
    ctx.n_stored = 50
    return ctx


# --- tests ---


def test_export_creates_all_artifacts(tmp_path):
    ctx = _minimal_ctx()
    results_path = export_build(ctx, tmp_path)

    expected = [
        "results.json",
        "draws.bin",
        "draws_index.json",
        "sites.json",
        "provenance.json",
        "methodology.json",
        "glossary.json",
    ]
    for name in expected:
        assert (tmp_path / name).exists(), f"{name} not written"


def test_results_json_validates(tmp_path):
    ctx = _minimal_ctx()
    export_build(ctx, tmp_path)
    data = json.loads((tmp_path / "results.json").read_text())
    # Pydantic round-trip validates the schema
    results = Results.model_validate(data)
    assert len(results.results) > 0
    assert len(results.drugs) == 6


def test_draws_bin_float32_little_endian(tmp_path):
    ctx = _minimal_ctx()
    export_build(ctx, tmp_path)

    index_data = json.loads((tmp_path / "draws_index.json").read_text())
    idx = DrawsIndex.model_validate(index_data)
    raw = (tmp_path / "draws.bin").read_bytes()

    first = idx.entries[0]
    floats = struct.unpack_from(f"<{first.count}f", raw, first.offset * 4)
    assert len(floats) == first.count
    # All RQ values should be finite positives
    assert all(np.isfinite(v) for v in floats)


def test_draws_index_entry_per_pair(tmp_path):
    ctx = _minimal_ctx()
    export_build(ctx, tmp_path)
    index = DrawsIndex.model_validate(
        json.loads((tmp_path / "draws_index.json").read_text())
    )
    n_valid_sites = sum(1 for s in ctx.sites if s.valid)
    assert len(index.entries) == n_valid_sites * 6  # 6 drugs


def test_sites_json_validates(tmp_path):
    ctx = _minimal_ctx()
    export_build(ctx, tmp_path)
    data = json.loads((tmp_path / "sites.json").read_text())
    sites_doc = Sites.model_validate(data)
    assert len(sites_doc.cities) == 5
    assert len(sites_doc.sites) == len(ctx.sites)


def test_methodology_json_validates(tmp_path):
    ctx = _minimal_ctx()
    export_build(ctx, tmp_path)
    data = json.loads((tmp_path / "methodology.json").read_text())
    meth = Methodology.model_validate(data)
    assert len(meth.stages) == 7
    assert len(meth.ablations.per_city) > 0
    variants = {ab.variant for ab in meth.ablations.per_city}
    assert variants == {"full", "pop_only", "wwtp_only"}


def test_provenance_json_is_dict(tmp_path):
    ctx = _minimal_ctx()
    export_build(ctx, tmp_path)
    prov = json.loads((tmp_path / "provenance.json").read_text())
    assert isinstance(prov, dict)
    # Should have prior:lambda and prior:Q
    assert "prior:lambda" in prov
    assert "prior:Q" in prov


def test_glossary_has_all_symbols(tmp_path):
    ctx = _minimal_ctx()
    export_build(ctx, tmp_path)
    glossary = json.loads((tmp_path / "glossary.json").read_text())
    for sym in ("PEC", "PNEC", "RQ", "LOD", "score"):
        assert sym in glossary


def test_score_tier_in_result_entries(tmp_path):
    ctx = _minimal_ctx()
    export_build(ctx, tmp_path)
    results = Results.model_validate(
        json.loads((tmp_path / "results.json").read_text())
    )
    for entry in results.results:
        assert 0.0 <= entry.score <= 1.0
        assert entry.tier in ("high", "medium", "low")


def test_rank_in_city_is_valid(tmp_path):
    ctx = _minimal_ctx()
    export_build(ctx, tmp_path)
    results = Results.model_validate(
        json.loads((tmp_path / "results.json").read_text())
    )
    for entry in results.results:
        assert 1 <= entry.rank_in_city <= entry.n_in_city


def test_sha256_file(tmp_path):
    f = tmp_path / "test.bin"
    f.write_bytes(b"hello world")
    h = sha256_file(f)
    assert len(h) == 64  # hex SHA-256
    assert h == sha256_file(f)  # deterministic


def test_frozen_tag_embedded(tmp_path):
    ctx = _minimal_ctx()
    export_build(ctx, tmp_path, frozen_tag="predictions-frozen-test-v1")
    results = Results.model_validate(
        json.loads((tmp_path / "results.json").read_text())
    )
    assert results.meta.frozen_tag == "predictions-frozen-test-v1"
