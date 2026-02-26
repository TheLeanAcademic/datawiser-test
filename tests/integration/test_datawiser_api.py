"""
Integration tests for the DataWiser API.

These tests make real HTTP requests to the DataWiser API and require a valid
DATAWISER_API_KEY environment variable to be set. They are skipped automatically
if the key is not present.

Run locally with:
    DATAWISER_API_KEY=your_key pytest tests/integration/ -v
"""

from __future__ import annotations

import os

import pytest

from datawiserai import Client, FreeFloat, Reference, SharesOutstanding, Universe
from datawiserai._exceptions import DatawiserAPIError

# ---------------------------------------------------------------------------
# Skip all tests in this module if no API key is configured
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATAWISER_API_KEY"),
    reason="DATAWISER_API_KEY environment variable not set",
)

# Use a well-known, stable ticker for integration tests
TEST_TICKER = "MSFT"


@pytest.fixture(scope="module")
def client():
    """Return a DataWiser client using the real API key."""
    return Client(api_key=os.environ["DATAWISER_API_KEY"])


# ---------------------------------------------------------------------------
# Universe
# ---------------------------------------------------------------------------

class TestUniverseIntegration:
    def test_get_universe_returns_universe_object(self, client):
        result = client.get_universe()
        assert isinstance(result, Universe)

    def test_universe_is_non_empty(self, client):
        result = client.get_universe()
        assert len(result) > 0

    def test_universe_contains_known_ticker(self, client):
        result = client.get_universe()
        tickers = [entry.ticker for entry in result]
        assert TEST_TICKER in tickers


# ---------------------------------------------------------------------------
# Free Float
# ---------------------------------------------------------------------------

class TestFreeFloatIntegration:
    def test_get_free_float_returns_free_float_object(self, client):
        result = client.get_free_float(TEST_TICKER)
        assert isinstance(result, FreeFloat)

    def test_free_float_ticker_matches(self, client):
        result = client.get_free_float(TEST_TICKER)
        assert result.ticker == TEST_TICKER

    def test_free_float_has_events(self, client):
        result = client.get_free_float(TEST_TICKER)
        assert len(result.events) > 0

    def test_free_float_factor_is_valid(self, client):
        result = client.get_free_float(TEST_TICKER)
        for event in result.events:
            assert 0.0 <= event.free_float_factor <= 1.0

    def test_free_float_pct_is_valid(self, client):
        result = client.get_free_float(TEST_TICKER)
        for event in result.events:
            assert 0.0 <= event.free_float_pct <= 100.0


# ---------------------------------------------------------------------------
# Shares Outstanding
# ---------------------------------------------------------------------------

class TestSharesOutstandingIntegration:
    def test_get_shares_outstanding_returns_correct_type(self, client):
        result = client.get_shares_outstanding(TEST_TICKER)
        assert isinstance(result, SharesOutstanding)

    def test_shares_outstanding_ticker_matches(self, client):
        result = client.get_shares_outstanding(TEST_TICKER)
        assert result.ticker == TEST_TICKER

    def test_shares_outstanding_has_events(self, client):
        result = client.get_shares_outstanding(TEST_TICKER)
        assert len(result.events) > 0

    def test_shares_outstanding_positive(self, client):
        result = client.get_shares_outstanding(TEST_TICKER)
        for event in result.events:
            assert event.shares > 0


# ---------------------------------------------------------------------------
# Reference
# ---------------------------------------------------------------------------

class TestReferenceIntegration:
    def test_get_reference_returns_reference_object(self, client):
        result = client.get_reference(TEST_TICKER)
        assert isinstance(result, Reference)

    def test_reference_ticker_matches(self, client):
        result = client.get_reference(TEST_TICKER)
        assert result.ticker == TEST_TICKER

    def test_reference_has_company_name(self, client):
        result = client.get_reference(TEST_TICKER)
        assert result.company_name and len(result.company_name) > 0

    def test_reference_has_security_id(self, client):
        result = client.get_reference(TEST_TICKER)
        assert result.security_id and len(result.security_id) > 0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandlingIntegration:
    def test_invalid_ticker_raises_error(self, client):
        with pytest.raises((DatawiserAPIError, Exception)):
            client.get_free_float("XXXXXXXXXX_INVALID")

    def test_invalid_api_key_raises_api_error(self):
        bad_client = Client(api_key="invalid-key-00000000")
        with pytest.raises(DatawiserAPIError) as exc_info:
            bad_client.get_universe()
        assert exc_info.value.status_code in (401, 403)