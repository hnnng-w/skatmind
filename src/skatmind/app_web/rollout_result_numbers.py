"""Request-local display formatting; never used for ranking or comparison."""

from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from .render_locale import message


def decimal_number(value: object) -> str:
    if type(value) not in (int, float):
        return message("status.unavailable")
    number = Decimal(str(value))
    if not number.is_finite():
        return message("status.unavailable")
    with localcontext() as context:
        context.rounding = ROUND_HALF_EVEN
        context.prec = max(28, len(number.as_tuple().digits) + max(number.adjusted(), 0) + 4)
        rounded = number.quantize(Decimal("0.01"))
    if rounded == 0:
        rounded = abs(rounded)
    return format(rounded, ".2f").replace(".", message("rollout.number.decimal_separator"))


def simulation_success(successes: object, samples: object) -> str:
    if (type(successes) is not int or type(samples) is not int
            or samples <= 0 or not 0 <= successes <= samples):
        return message("status.unavailable")
    with localcontext() as context:
        context.rounding = ROUND_HALF_EVEN
        context.prec = max(28, len(str(samples)) + 4)
        percentage = Decimal(successes) * 100 / Decimal(samples)
        places = 2
        rounded = percentage.quantize(Decimal("0.01"))
        # Rounded endpoints must not turn a nonzero fraction into zero, or a
        # less-than-certain simulated fraction into 100%. Counts stay visible.
        while ((successes > 0 and rounded == 0)
               or (successes < samples and rounded == 100)):
            places += 1
            rounded = percentage.quantize(Decimal(1).scaleb(-places))
    rendered = format(rounded, "f").rstrip("0").rstrip(".")
    rendered = rendered.replace(".", message("rollout.number.decimal_separator"))
    return message("rollout.number.success", successes=successes, samples=samples,
                   percentage=rendered)
