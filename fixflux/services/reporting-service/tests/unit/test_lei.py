import pytest

from reporting_service.lei import is_valid_lei

# GLEIF's own LEI, as published on gleif.org (ISO 17442 structure page).
GLEIF_LEI = "506700GE1G29325QX363"


class TestIsValidLei:
    def test_accepts_real_published_lei(self):
        assert is_valid_lei(GLEIF_LEI)

    def test_accepts_every_synthetic_lei_in_reference_data(self):
        from reporting_service.config import load_reference_data

        participants = load_reference_data()["participants"]
        assert participants
        assert all(is_valid_lei(p["lei"]) for p in participants.values())

    @pytest.mark.parametrize(
        "value",
        [
            "506700GE1G29325QX364",  # one check digit off
            "506700GE1G29325QX36",  # 19 characters
            "506700GE1G29325QX3631",  # 21 characters
            "506700ge1g29325qx363",  # lower case
            "506700GE1G29325QX3A3",  # letter in check digits
            "",
        ],
    )
    def test_rejects_malformed_or_bad_checksum(self, value):
        assert not is_valid_lei(value)
