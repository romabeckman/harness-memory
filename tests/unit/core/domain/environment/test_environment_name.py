import pytest

from core.domain.environment.value_objects.environment_name import EnvironmentName


class TestEnvironmentName:
    def test_creates_environment_name_successfully(self) -> None:
        name = EnvironmentName("production-us-east")
        assert name.value == "production-us-east"

    def test_rejects_empty_or_whitespace_name(self) -> None:
        with pytest.raises(ValueError, match="environment name must not be empty"):
            EnvironmentName("   ")

    def test_rejects_name_exceeding_max_length(self) -> None:
        with pytest.raises(ValueError, match="environment name exceeds maximum length"):
            EnvironmentName("a" * 65)

    def test_rejects_invalid_characters(self) -> None:
        with pytest.raises(ValueError, match="environment name contains invalid characters"):
            EnvironmentName("Invalid@Name!")

    def test_equality_by_value(self) -> None:
        name1 = EnvironmentName("staging")
        name2 = EnvironmentName("staging")
        name3 = EnvironmentName("production")

        assert name1 == name2
        assert name1 != name3
        assert len({name1, name2}) == 1
