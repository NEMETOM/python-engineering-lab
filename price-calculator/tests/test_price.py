import pytest
from calculator.price import apply_discount, add_vat

def test_apply_discount_correct():
    assert apply_discount(100, 10) == 90

def test_apply_discount_zero():
    assert apply_discount(100, 0) == 100

def test_apply_discount_invalid_price():
    with pytest.raises(ValueError):
        apply_discount(-10, 10)

def test_apply_discount_invalid_discount():
    with pytest.raises(ValueError):
        apply_discount(100, 150)

def test_add_var_corrct():
    assert add_vat(100, 20) == 120

def test_add_vat_invalid():
    with pytest.raises(ValueError):
        add_vat(100, -5)
                          