"""Localize typed ordinary Result scalars without changing their numeric policy."""

from .render_locale import localized_render, message


@localized_render
def ordinary_scalar(value: object, format_spec: str = "") -> str:
    if type(value) not in {int, float}:
        return str(value)
    # Reuse only the request-local separator, not rollout rounding or endpoints.
    return format(value, format_spec).replace(
        ".", message("rollout.number.decimal_separator"))
