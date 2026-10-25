import re

_LEI_FORMAT = re.compile(r"^[0-9A-Z]{18}[0-9]{2}$")


def is_valid_lei(value: str) -> bool:
    """ISO 17442 LEI: 20 alphanumeric characters ending in two ISO 7064
    MOD 97-10 check digits - with letters mapped A=10..Z=35, the whole code
    read as one integer is congruent to 1 mod 97."""
    if not _LEI_FORMAT.match(value):
        return False
    return int("".join(str(int(c, 36)) for c in value)) % 97 == 1
