"""Compact read-only result with optional guarded retained Coaching presentation."""

from collections.abc import Mapping
from html import escape

from skatmind.learning_dataset_v2_partition_contracts import (
    LEARNING_DATASET_PARTITION_UNAVAILABLE_REASONS,
)

from .learning_focus_rendering import render_learning_focuses
from .stateful_localization import text, translated
from .task_first_rendering import disclosure, paragraph, technical_details

# Presentation order only. Canonical/standalone download tuples remain authoritative.
_DOWNLOAD_GROUPS = (
    ("summaries", ("cross_game_summary", "tactical_motif_cross_game_summary",
                   "tactical_cross_game_coaching")),
    ("evidence", ("player_catalog", "human_evidence", "strategy_teacher_evidence",
                  "tactical_motif_evidence")),
    ("dataset", ("learning_dataset_v2", "known_player_partitions", "unseen_player_partitions")),
)
_NORMAL_COUNTS = frozenset((
    "cross_game_match_count", "observed_decision_count", "record_count", "skipped_decision_count",
    "commentary_evidence_count", "response_evidence_count", "strategy_teacher_evidence_count",
    "tactical_evidence_count", "tactical_skipped_decision_count", "tactical_motif_occurrence_count",
    "tactical_coaching_focus_area_count", "tactical_coaching_player_with_focus_count",
))


def _count(value):
    return value if type(value) is int and value >= 0 else None


def learning_result_technical_facts(prepared):
    """Keep raw statuses/reasons, secondary facts and defensive diagnostics once."""
    if prepared is None:
        return None
    return {key: value for key, value in prepared.items()
            if key not in _NORMAL_COUNTS or _count(value) is None}


def _coverage_status(prepared):
    observed, records, skipped = (
        _count(prepared.get(key))
        for key in ("observed_decision_count", "record_count", "skipped_decision_count"))
    status = prepared.get("dataset_status")
    if None in (observed, records, skipped) or observed != records + skipped:
        return "unknown"
    # Only qualify retained status; never repair contradictory metadata or infer a new status.
    supported = ((status == "empty" and observed == 0)
        or (status == "unavailable" and observed > 0 and records == 0)
        or (status == "partial" and records > 0 and skipped > 0)
        or (status == "complete" and records > 0 and skipped == 0))
    return status if supported else "unknown"


def _tactical_status(prepared):
    evidence, skipped = (_count(prepared.get(key))
        for key in ("tactical_evidence_count", "tactical_skipped_decision_count"))
    status = prepared.get("tactical_collection_status")
    if None in (evidence, skipped):
        return "unknown"
    supported = ((status == "empty" and evidence == skipped == 0)
        or (status == "partial" and skipped > 0)
        or (status == "complete" and evidence > 0 and skipped == 0))
    return status if supported else "unknown"


def _coaching_status(prepared):
    decisions, focuses, players = (_count(prepared.get(key)) for key in (
        "tactical_coaching_decision_count", "tactical_coaching_focus_area_count",
        "tactical_coaching_player_with_focus_count"))
    status = prepared.get("tactical_coaching_status")
    if None in (decisions, focuses, players):
        return "unknown"
    supported = ((status == "empty" and decisions == focuses == players == 0)
        or (status == "insufficient_evidence" and decisions > 0 and focuses == players == 0)
        or (status == "available" and decisions > 0 and focuses >= players > 0))
    return status if supported else "unknown"


def render_learning_result(prepared, locale, *, display=None):
    """No source access, execution, state mutation or receipt delivery."""
    def number(key):
        value = _count(prepared.get(key))
        return text(locale, "learning.result.unknown") if value is None else str(value)

    coverage = _coverage_status(prepared)
    coaching = _coaching_status(prepared)
    consistent = display is not None and all(
        prepared.get(key) == value and type(prepared.get(key)) is type(value)
        for key, value in display.expected_coaching)
    body = '<div id="learning-result-primary">'
    body += paragraph(locale, "learning.result.overview", matches=number("cross_game_match_count"),
        observed=number("observed_decision_count"), records=number("record_count"))
    if coverage != "complete":
        body += paragraph(locale, "learning.result.dataset." + coverage)
    if consistent and coaching != "unknown":
        if display.focuses:
            body += render_learning_focuses(display.focuses, locale)
        elif coverage not in ("empty", "unavailable", "unknown"):
            body += paragraph(locale, "learning.result.explanation." + display.explanation)
    else:
        body += paragraph(locale, "learning.result.coaching." + (
            coaching if display is None else "unknown"))
    if coverage in ("complete", "partial") and not (consistent and display.focuses):
        body += '<p><a class="button-link" href="/review/recorded">' + translated(
            locale, "learning.result.choose_decision") + '</a></p>'
    body += '</div>'
    inputs = ''
    if display is not None:
        inputs += '<ul>' + ''.join('<li>' + escape(label) + '</li>'
            for label in display.sources) + '</ul>'
        if display.analysis_sources:
            inputs += '<ul>' + ''.join('<li>' + escape(label) + '</li>'
                for label in display.analysis_sources) + '</ul>'
    else:
        inputs += paragraph(locale, "learning.result.reference_unavailable")
    inputs += '<p><a href="#insight-versions">' + translated(
        locale, "task.learning.selected") + '</a> · <a href="#learning-sources">' + translated(
        locale, "task.learning.attach_file") + '</a></p>'
    body += disclosure(locale, "learning.result.included_data", inputs).replace(
        '<details ', '<details id="learning-result-inputs" ', 1)
    details = paragraph(locale, "learning.result.matches", count=number("cross_game_match_count"))
    details += paragraph(locale, "learning.result.coverage",
        observed=number("observed_decision_count"), records=number("record_count"),
        skipped=number("skipped_decision_count"))
    details += paragraph(locale, "learning.result.dataset." + coverage)
    details += paragraph(locale, "learning.result.human",
        comments=number("commentary_evidence_count"), responses=number("response_evidence_count"))
    details += paragraph(locale, "learning.result.teacher",
                      count=number("strategy_teacher_evidence_count"))
    if display is not None:
        details += '<dl>' + ''.join('<dt>' + translated(locale, "learning.result.count." + key)
            + '</dt><dd>' + str(value) + '</dd>'
            for key, value in display.coaching_counts) + '</dl>'
    details += paragraph(locale, "learning.result.tactical",
        evidence=number("tactical_evidence_count"),
        skipped=number("tactical_skipped_decision_count"),
        occurrences=number("tactical_motif_occurrence_count"),
        status=text(locale, "learning.result.tactical." + _tactical_status(prepared)))
    details += paragraph(locale, "learning.result.focus_counts",
        focuses=number("tactical_coaching_focus_area_count"),
        players=number("tactical_coaching_player_with_focus_count"))
    details += '<h3>' + translated(locale, "learning.result.partitions") + '</h3>'
    for mode in ("known_player", "unseen_player"):
        partition = prepared.get(mode)
        status = partition.get("status") if isinstance(partition, Mapping) else None
        if status not in ("complete", "unavailable"):
            status = "unknown"
        details += paragraph(locale, "learning.result.partition",
            mode=text(locale, "learning.result." + mode),
            status=text(locale, "learning.result.partition." + status))
        reason = partition.get("unavailable_reason") if isinstance(partition, Mapping) else None
        if status == "unavailable":
            details += paragraph(locale, "learning.result.partition_reason." + (
                reason if isinstance(reason, str)
                and reason in LEARNING_DATASET_PARTITION_UNAVAILABLE_REASONS else "unknown"))
    details += '<div class="learning-downloads"><h3>' + translated(
        locale, "learning.result.downloads") + '</h3>'
    for group, kinds in _DOWNLOAD_GROUPS:
        details += '<h4>' + translated(locale, "learning.result.group." + group) + '</h4><ul>'
        for kind in kinds:
            details += (f'<li><a href="/learning/downloads/{kind.replace("_", "-")}.json" download>'
                + translated(locale, "task.download." + kind) + ' (JSON)</a></li>')
        details += '</ul>'
    details += '</div>' + technical_details(locale, learning_result_technical_facts(prepared))
    body += disclosure(locale, "learning.result.technical_downloads", details).replace(
        '<details ', '<details id="learning-result-technical" ', 1)
    return body
