"""Tests for FileCache."""

import gzip
import json
import pytest
from pathlib import Path

from datawiserai._cache import FileCache


@pytest.fixture
def cache(tmp_path):
    return FileCache(tmp_path / "cache")

SAMPLE_DATA = {"ticker": "OLP", "securityId": "abc123", "events": []}


class TestFileCachePut:
    def test_creates_cache_file(self, cache, tmp_path):
        cache.put("free-float", "OLP", SAMPLE_DATA, "2024-01-01T00:00:00Z")
        path = cache._path("free-float", "OLP")
        assert path.exists()

    def test_stored_data_is_readable(self, cache):
        cache.put("free-float", "OLP", SAMPLE_DATA, "2024-01-01T00:00:00Z")
        with gzip.open(cache._path("free-float", "OLP"), "rt", encoding="utf-8") as f:
            entry = json.load(f)
        assert entry["data"] == SAMPLE_DATA
        assert entry["last_update"] == "2024-01-01T00:00:00Z"
        assert "cached_at" in entry

    def test_creates_subdirectory(self, cache):
        cache.put("shares-outstanding", "MSFT", SAMPLE_DATA, "2024-06-01T00:00:00Z")
        assert (cache._dir / "shares-outstanding").is_dir()


class TestFileCacheGet:
    def test_returns_none_for_missing_entry(self, cache):
        data, ts = cache.get("free-float", "NONEXISTENT")
        assert data is None
        assert ts is None

    def test_returns_stored_data_and_timestamp(self, cache):
        cache.put("free-float", "OLP", SAMPLE_DATA, "2024-01-15T00:00:00Z")
        data, ts = cache.get("free-float", "OLP")
        assert data == SAMPLE_DATA
        assert ts == "2024-01-15T00:00:00Z"

    def test_returns_none_for_corrupted_json(self, cache, tmp_path):
        path = cache._path("free-float", "BAD")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not valid json")
        data, ts = cache.get("free-float", "BAD")
        assert data is None
        assert ts is None

    def test_returns_none_for_missing_key(self, cache):
        path = cache._path("free-float", "MISSING_KEY")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"no_data_key": True}))
        data, ts = cache.get("free-float", "MISSING_KEY")
        assert data is None
        assert ts is None

    def test_different_endpoints_isolated(self, cache):
        cache.put("free-float", "OLP", {"endpoint": "ff"}, "2024-01-01")
        cache.put("reference", "OLP", {"endpoint": "ref"}, "2024-02-01")
        ff_data, _ = cache.get("free-float", "OLP")
        ref_data, _ = cache.get("reference", "OLP")
        assert ff_data["endpoint"] == "ff"
        assert ref_data["endpoint"] == "ref"


class TestFileCacheClear:
    def test_clear_all_removes_all_files(self, cache):
        cache.put("free-float", "OLP", SAMPLE_DATA, "2024-01-01")
        cache.put("reference", "OLP", SAMPLE_DATA, "2024-01-01")
        removed = cache.clear()
        assert removed == 2
        data, _ = cache.get("free-float", "OLP")
        assert data is None

    def test_clear_specific_endpoint(self, cache):
        cache.put("free-float", "OLP", SAMPLE_DATA, "2024-01-01")
        cache.put("reference", "OLP", SAMPLE_DATA, "2024-01-01")
        removed = cache.clear("free-float")
        assert removed == 1
        ff_data, _ = cache.get("free-float", "OLP")
        ref_data, _ = cache.get("reference", "OLP")
        assert ff_data is None
        assert ref_data == SAMPLE_DATA

    def test_clear_nonexistent_endpoint_returns_zero(self, cache):
        removed = cache.clear("nonexistent-endpoint")
        assert removed == 0

    def test_clear_empty_cache_returns_zero(self, cache):
        removed = cache.clear()
        assert removed == 0

    def test_clear_multiple_tickers(self, cache):
        for ticker in ["A", "B", "C"]:
            cache.put("free-float", ticker, SAMPLE_DATA, "2024-01-01")
        removed = cache.clear("free-float")
        assert removed == 3
