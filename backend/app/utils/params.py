from .errors import ValidationError


def parse_enum(enum_cls, value, field):
    """Convert a request value to an enum member, accepting its value ("Job Market Data")."""
    try:
        return enum_cls(value)
    except ValueError:
        raise ValidationError(
            f"Invalid {field}",
            details={field: f"Must be one of: {', '.join(m.value for m in enum_cls)}"},
        )
