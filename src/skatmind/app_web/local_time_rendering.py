"""Shared compact native controls; no browser/OS timezone inference or conversion."""

from html import escape

from .local_time_conversion import LocalTimeError
from .local_time_forms import LocalTimeFormContext, occurrence_choices
from .stateful_localization import text, translated
from .task_first_rendering import hidden, input_field, paragraph, select_field
from .time_zone_provider import TimeZoneUnavailable, packaged_time_zone, time_zone_inventory


def zone_selector(locale, *, name, selected, settings=False):
    warning = ""
    try:
        keys = time_zone_inventory().keys
        if selected:
            packaged_time_zone(selected)
    except TimeZoneUnavailable as error:
        keys = () if error.reason == "database" else time_zone_inventory().keys
        warning = paragraph(locale, "validation.local_time." + error.reason)
    options = (("", text(locale, "local_time.app_default")),) if settings else ()
    if selected and selected not in keys:
        options += ((selected, selected + " — " + text(locale, "local_time.unavailable")),)
    options += tuple((key, key) for key in keys)
    return select_field(locale, name, "local_time.zone", options, selected) + warning


def render_time_zone_settings(profile, generation, locale):
    selected = "" if profile is None else profile.interface_preferences.time_zone or ""
    return ('<section class="settings-panel" id="time-zone-settings"><h3>'
        + translated(locale, "local_time.zone") + '</h3>'
        + paragraph(locale, "local_time.preference_help")
        + '<form method="post" action="/actions/profile/time-zone">'
        + hidden("profile_generation", generation)
        + zone_selector(locale, name="time_zone", selected=selected, settings=True)
        + '<button type="submit">' + translated(locale, "local_time.save_zone")
        + '</button></form>' + paragraph(locale, "local_time.future_only") + '</section>')


def render_local_time_editor(locale, context: LocalTimeFormContext, *, original=None, new=True,
                             include_generation=True):
    values = dict(context.submitted)
    core = hidden("time_form", context.marker) + hidden("time_selection", context.selection)
    if include_generation:
        core += hidden("profile_generation", context.profile_generation)
    if original is not None:
        core += paragraph(locale, "local_time.original_help")
        core += '<p class="recorded-time"><code>' + escape(original) + '</code></p>'
    if new:
        core += hidden("time_mode", "enter")
    else:
        core += select_field(locale, "time_mode", "local_time.mode", tuple(
            (mode, text(locale, "local_time." + mode)) for mode in ("keep", "replace", "remove")),
            values.get("time_mode", "keep"))
    fields = input_field(locale, "local_date", "local_time.date", kind="date")
    fields = fields.replace('type="date"', 'type="date" min="0001-01-01" max="9999-12-31"')
    fields += input_field(locale, "local_time", "local_time.time", kind="time").replace(
        'type="time"', 'type="time" step="0.000001"')
    fields += zone_selector(locale, name="local_zone",
                            selected=values.get("local_zone", context.zone))
    choices = ()
    if values.get("local_date") and values.get("local_time") and values.get("local_zone"):
        try:
            candidates = occurrence_choices(values, context)
            if len(candidates) == 2:
                choices = tuple((token, text(locale, "local_time." + token.split(".")[0],
                    offset=candidate.offset)) for token, candidate in candidates)
        except (LocalTimeError, TimeZoneUnavailable):
            pass
    if choices:
        fields += select_field(locale, "local_occurrence", "local_time.occurrence",
            (("", text(locale, "local_time.choose_occurrence")), *choices), "")
    else:
        fields += hidden("local_occurrence", "")
    fields += paragraph(locale, "local_time.entry_help")
    # CSS responds to the native mode without disabling/clearing submitted controls.
    core += '<div class="local-time-fields"><div class="local-time-grid">' + fields + '</div></div>'
    return ('<details class="local-time-editor"><summary>'
        + translated(locale, "local_time.heading") + '</summary>' + core + '</details>')
