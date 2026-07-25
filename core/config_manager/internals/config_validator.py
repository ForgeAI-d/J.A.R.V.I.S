from copy import deepcopy

from .defaults import DEFAULT_CONFIGS
from .schema import CONFIG_SCHEMA


class ConfigValidator:

    VERSION = "1.0.0"

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.changes = []

    def validate(
        self,
        namespace,
        config
    ):
        self.errors.clear()
        self.warnings.clear()
        self.changes.clear()

        schema = CONFIG_SCHEMA.get(namespace)
        defaults = DEFAULT_CONFIGS.get(namespace)

        if schema is None:
            self.errors.append(
                f"Unknown namespace: {namespace}"
            )
            return False, config

        validated = deepcopy(config)

        self._apply_defaults(
            validated,
            defaults
        )

        self._validate_types(
            validated,
            schema
        )

        return (
            len(self.errors) == 0,
            validated
        )

    def _apply_defaults(
        self,
        config,
        defaults
    ):
        for key, value in defaults.items():

            if key not in config:
                config[key] = deepcopy(value)

                self.changes.append(
                    f"Added missing key '{key}'"
                )

    def _validate_types(
        self,
        config,
        schema
    ):
        for key, expected_type in schema.items():

            if key not in config:
                continue

            if not isinstance(
                config[key],
                expected_type
            ):
                self.errors.append(
                    (
                        f"Invalid type for '{key}': "
                        f"expected "
                        f"{expected_type.__name__}, "
                        f"got "
                        f"{type(config[key]).__name__}"
                    )
                )

    def get_report(self):
        return {
            "valid": len(self.errors) == 0,
            "errors": deepcopy(self.errors),
            "warnings": deepcopy(self.warnings),
            "changes": deepcopy(self.changes)
        }


if __name__ == "__main__":

    validator = ConfigValidator()

    config = {
        "boot_mode": "development"
    }

    valid, config = validator.validate(
        "boot",
        config
    )

    print("=== CONFIG VALIDATOR TEST ===")
    print()

    print("Valid:")
    print(valid)

    print()

    print("Config:")
    print(config)

    print()

    print("Report:")
    print(
        validator.get_report()
    )