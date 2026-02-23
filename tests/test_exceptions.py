"""Tests for datawiserai exception classes."""

import pytest
from datawiserai._exceptions import DatawiserAPIError, DatawiserError, TickerNotFoundError


class TestDatawiserError:
    def test_is_exception(self):
        err = DatawiserError("something went wrong")
        assert isinstance(err, Exception)
        assert str(err) == "something went wrong"


class TestDatawiserAPIError:
    def test_inherits_datawiser_error(self):
        err = DatawiserAPIError(404, "Not Found")
        assert isinstance(err, DatawiserError)

    def test_attributes(self):
        err = DatawiserAPIError(401, "Unauthorized")
        assert err.status_code == 401
        assert err.message == "Unauthorized"

    def test_str_representation(self):
        err = DatawiserAPIError(500, "Internal Server Error")
        assert "500" in str(err)
        assert "Internal Server Error" in str(err)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(DatawiserAPIError) as exc_info:
            raise DatawiserAPIError(403, "Forbidden")
        assert exc_info.value.status_code == 403

    def test_also_caught_as_datawiser_error(self):
        with pytest.raises(DatawiserError):
            raise DatawiserAPIError(503, "Service Unavailable")


class TestTickerNotFoundError:
    def test_inherits_datawiser_error(self):
        err = TickerNotFoundError("XYZ", "free-float")
        assert isinstance(err, DatawiserError)

    def test_attributes(self):
        err = TickerNotFoundError("AAPL", "shares-outstanding")
        assert err.ticker == "AAPL"
        assert err.endpoint == "shares-outstanding"

    def test_str_contains_ticker_and_endpoint(self):
        err = TickerNotFoundError("MSFT", "reference")
        assert "MSFT" in str(err)
        assert "reference" in str(err)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(TickerNotFoundError) as exc_info:
            raise TickerNotFoundError("GOOG", "free-float-events")
        assert exc_info.value.ticker == "GOOG"
        assert exc_info.value.endpoint == "free-float-events"
