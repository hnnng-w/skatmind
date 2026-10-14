"""Shared native basic/supplement fields and closed technical rollout controls."""

from html import escape

from .stateful_localization import translated
from .task_first_rendering import disclosure, select_field


def rollout_basic_fields(locale, settings, missing, supplied, *, help_prefix="recorded"):
    basic = '<div class="recorded-field">' + select_field(
        locale, "objective", "rollout.objective", (
        (value, translated(locale, f"rollout.option.{value}"))
        for value in ("complete_settlement", "played_game_goal")), settings["objective"],
        described_by=f"{help_prefix}-objective-help")
    basic += '<!-- validation-messages:objective --></div>'
    for name in missing:
        help_ids = f"{help_prefix}-settlement-help" + (
            f" {help_prefix}-matadors-help" if name == "matadors" else "")
        basic += ('<div class="recorded-field rollout-settlement-inputs"><label>'
            + translated(locale, "rollout.analysis_" + name)
            + ' <input type="text" inputmode="numeric" maxlength="21" '
            + f'name="analysis_{name}" aria-describedby="{help_ids}" '
            + f'value="{escape(str(supplied.get(name, "")))}"></label>'
            + f'<!-- validation-messages:analysis_{name} --></div>')
    return basic


def rollout_technical_fields(locale, settings):
    advanced = '<div class="recorded-technical-fields">'
    for name, key, maximum in (("requested_worlds", "rollout.worlds", 1000),
                               ("random_seed", "rollout.seed", 2**64 - 1)):
        advanced += (f'<div class="recorded-field"><label>{translated(locale, key)} '
            '<input type="number" '
            f'name="{name}" min="{1 if name == "requested_worlds" else 0}" '
            f'max="{maximum}" step="1" required value="{settings[name]}"></label>'
            f'<!-- validation-messages:{name} --></div>')
    advanced = disclosure(locale, "task.advanced", advanced + '</div>')
    return advanced.replace('</summary>', ' <span class="recorded-technical-error">'
        + translated(locale, "rollout.technical_invalid") + '</span></summary>', 1)
