import pytest
from shared.exceptions import AppException, InfrastructureError, ValidationError


class TestAppException:
    def test_is_exception_subclass(self):
        assert issubclass(AppException, Exception)

    def test_message_is_accessible(self):
        exc = AppException("something went wrong")
        assert str(exc) == "something went wrong"

    def test_can_be_raised_and_caught_as_exception(self):
        with pytest.raises(Exception):
            raise AppException("error")

    def test_can_be_raised_and_caught_as_itself(self):
        with pytest.raises(AppException):
            raise AppException("error")


class TestValidationError:
    def test_is_app_exception_subclass(self):
        assert issubclass(ValidationError, AppException)

    def test_is_exception_subclass(self):
        assert issubclass(ValidationError, Exception)

    def test_message_preserved(self):
        exc = ValidationError("price must be positive")
        assert str(exc) == "price must be positive"

    def test_caught_as_app_exception(self):
        with pytest.raises(AppException):
            raise ValidationError("bad input")

    def test_caught_as_itself(self):
        with pytest.raises(ValidationError):
            raise ValidationError("invalid side")


class TestInfrastructureError:
    def test_is_app_exception_subclass(self):
        assert issubclass(InfrastructureError, AppException)

    def test_is_exception_subclass(self):
        assert issubclass(InfrastructureError, Exception)

    def test_message_preserved(self):
        exc = InfrastructureError("kafka down")
        assert str(exc) == "kafka down"

    def test_caught_as_app_exception(self):
        with pytest.raises(AppException):
            raise InfrastructureError("connection failed")

    def test_caught_as_itself(self):
        with pytest.raises(InfrastructureError):
            raise InfrastructureError("db unavailable")
