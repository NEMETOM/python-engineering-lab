import pytest

from tests.unit.fakes import FakeClock


@pytest.fixture
def clock():
    return FakeClock()
