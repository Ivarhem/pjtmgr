import pytest
from unittest.mock import MagicMock
from app.core.code_generator import (
    int_to_base36,
    base36_to_int,
    next_partner_code,
    next_business_code,
    next_period_code,
    RESERVED_PARTNER_CODE,
)


class TestBase36:
    def test_zero(self):
        assert int_to_base36(0) == "000"

    def test_one(self):
        assert int_to_base36(1) == "001"

    def test_ten(self):
        assert int_to_base36(10) == "00A"

    def test_thirty_five(self):
        assert int_to_base36(35) == "00Z"

    def test_thirty_six(self):
        assert int_to_base36(36) == "010"

    def test_max(self):
        assert int_to_base36(46655) == "ZZZ"

    def test_roundtrip(self):
        for n in [0, 1, 35, 36, 100, 46655]:
            assert base36_to_int(int_to_base36(n)) == n

    def test_width_1(self):
        assert int_to_base36(0, width=1) == "0"
        assert int_to_base36(25, width=1) == "P"


class TestNextPartnerCode:
    def _mock_db(self, last_code: str | None):
        """MAX(partner_code) 쿼리 결과를 모킹."""
        db = MagicMock()
        row = MagicMock()
        row.__getitem__ = lambda self, idx: last_code
        query = db.execute.return_value
        query.scalar.return_value = last_code
        return db

    def test_first_partner(self):
        db = self._mock_db(None)
        assert next_partner_code(db) == "P000"

    def test_increment(self):
        db = self._mock_db("P001")
        assert next_partner_code(db) == "P002"

    def test_skip_reserved(self):
        """PXXX(=P + base36 'XXX')에 도달하면 건너뛴다."""
        db = self._mock_db("PXXW")
        code = next_partner_code(db)
        # XXW(=44251) → XXX(=44252, reserved) → XXY(=44253)
        assert code == "PXXY"


class TestNextBusinessCode:
    def _mock_db(self, last_code: str | None):
        db = MagicMock()
        db.execute.return_value.scalar.return_value = last_code
        return db

    def test_first_business(self):
        db = self._mock_db(None)
        assert next_business_code(db, "P000") == "P000-B000"

    def test_increment(self):
        db = self._mock_db("P000-B002")
        assert next_business_code(db, "P000") == "P000-B003"

    def test_null_partner(self):
        db = self._mock_db(None)
        assert next_business_code(db, RESERVED_PARTNER_CODE) == "PXXX-B000"


class TestNextPeriodCode:
    def _mock_db(self, last_code: str | None):
        db = MagicMock()
        db.execute.return_value.scalar.return_value = last_code
        return db

    def test_first_period(self):
        db = self._mock_db(None)
        assert next_period_code(db, "P000-B000", 2026) == "P000-B000-Y26A"

    def test_increment(self):
        db = self._mock_db("P000-B000-Y26A")
        assert next_period_code(db, "P000-B000", 2026) == "P000-B000-Y26B"

    def test_slot_exhausted(self):
        db = self._mock_db("P000-B000-Y26Z")
        with pytest.raises(Exception, match="최대 26개"):
            next_period_code(db, "P000-B000", 2026)
