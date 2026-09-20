from core.domain.environment.value_objects.environment_type import EnvironmentType


class TestEnvironmentType:
    def test_supports_expected_values(self) -> None:
        assert EnvironmentType.DEVELOPMENT.value == "development"
        assert EnvironmentType.STAGING.value == "staging"
        assert EnvironmentType.PRODUCTION.value == "production"
        assert EnvironmentType.OTHER.value == "other"
