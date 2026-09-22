# ruff: noqa: E501 - Keep complete server-rendered elements legible.
from __future__ import annotations

from dataclasses import replace
from html import escape

from .candidate_table_rendering import candidate_table_html
from .guided_contracts import (
    ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH,
    ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH,
    REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH,
    REVIEW_RESULT_DOWNLOAD_ROUTE_PATH,
)
from .recorded_decision_context_rendering import render_recorded_decision_context
from .render_locale import html_message as _t
from .render_locale import localized_render
from .result_localization import RESULT_LABEL_KEYS, result_label, result_value
from .result_presentation import (
    BrowserSafeResultPresentationV1,
    ResultSectionV1,
    ResultTableV1,
)


def _details(values) -> str:
    if not values:
        return ""
    return (
        '<dl class="result-details">'
        + "".join(
            f"<dt>{escape(result_label(detail.label))}</dt><dd>{escape(result_value(detail.label, detail.value))}</dd>" for detail in values
        )
        + "</dl>"
    )


def _items(values) -> str:
    if not values:
        return ""
    return (
        '<ul class="result-list">'
        + "".join(f"<li>{escape(value)}</li>" for value in values)
        + "</ul>"
    )


def _table(table: ResultTableV1, *, candidate_identity: str | None = None) -> str:
    if candidate_identity is not None:
        return '<div class="result-table-wrap candidate-comparison">' + candidate_table_html(
            caption_html=escape(result_label(table.caption)),
            columns_html=tuple(escape(result_label(column)) for column in table.columns),
            rows_html=tuple(tuple(escape(cell) if index == 0 else
                escape(result_value(table.columns[index], cell))
                for index, cell in enumerate(row)) for row in table.rows),
            identity=candidate_identity) + '</div>'
    headings = "".join(f'<th scope="col">{escape(result_label(column))}</th>' for column in table.columns)
    rows = "".join(
        "<tr>"
        + "".join(
            (f'<th scope="row">{escape(cell)}</th>' if index == 0 else f"<td>{escape(result_value(table.columns[index], cell))}</td>")
            for index, cell in enumerate(row)
        )
        + "</tr>"
        for row in table.rows
    )
    return (
        '<div class="result-table-wrap"><table>'
        f"<caption>{escape(result_label(table.caption))}</caption>"
        f"<thead><tr>{headings}</tr></thead><tbody>{rows}</tbody>"
        "</table></div>"
    )


def _section_body(section: ResultSectionV1, *, candidate_identity: str | None = None) -> str:
    return (
        "".join(f"<p>{escape(paragraph)}</p>" for paragraph in section.paragraphs)
        + _details(section.details)
        + _items(section.items)
        + "".join(_table(table, candidate_identity=(
            f"{candidate_identity}-table-{index}" if candidate_identity is not None else None))
            for index, table in enumerate(section.tables))
    )


def _download_links(
    *,
    page: str,
    request_download_available: bool,
    result_download_available: bool,
    request_download_route: str | None = None,
    result_download_route: str | None = None,
) -> str:
    if request_download_route is not None and result_download_route is not None:
        request_href = request_download_route
        result_href = result_download_route
    elif page == "analyze":
        request_href = ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH
        result_href = ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH
    else:
        request_href = REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH
        result_href = REVIEW_RESULT_DOWNLOAD_ROUTE_PATH
    links = []
    if request_download_available:
        links.append(
            f'<li><a href="{escape(request_href, quote=True)}" '
            f'download>{_t("guided.request_download")}</a></li>'
        )
    if result_download_available:
        links.append(
            f'<li><a href="{escape(result_href, quote=True)}" '
            f'download>{_t("task.result_download")}</a></li>'
        )
    if not links:
        return ""
    return f'<nav aria-label="{_t("task.learning.results")}"><ul>' + "".join(links) + "</ul></nav>"


@localized_render
def render_result_presentation_v1(
    presentation: BrowserSafeResultPresentationV1,
    *,
    request_download_available: bool = False,
    result_download_available: bool = False,
    page: str | None = None,
    request_download_route: str | None = None,
    result_download_route: str | None = None,
    recorded_context=None,
    recorded_context_locale: str = "en",
) -> str:
    """Renders one browser-safe Result projection as semantic escaped HTML."""

    if type(presentation) is not BrowserSafeResultPresentationV1:
        raise ValueError("presentation must be an exact browser-safe Result presentation.")
    if type(request_download_available) is not bool:
        raise ValueError("request_download_available must be a boolean.")
    if type(result_download_available) is not bool:
        raise ValueError("result_download_available must be a boolean.")
    effective_page = page or (
        "analyze" if presentation.workflow == "position_analysis" else "review"
    )
    if effective_page not in {"analyze", "review"}:
        raise ValueError("page must be 'analyze' or 'review'.")
    if (request_download_route is None) != (result_download_route is None):
        raise ValueError("Custom Result download routes must be both present or null.")
    for route in (request_download_route, result_download_route):
        if route is not None and (type(route) is not str or not route.startswith("/")):
            raise ValueError("Custom Result download routes must be absolute local routes.")

    rendered = []
    technical_extras = []
    for index, section in enumerate(presentation.sections):
        identifier = f"result-section-{index + 1}"
        if section.title != "Technical details":
            technical_extras.extend(detail for detail in section.details
                                    if detail.label not in RESULT_LABEL_KEYS or "fixed policy" in detail.label)
            if section.title == "Recommendation" and presentation.workflow == "position_analysis":
                technical_extras.extend(section.paragraphs)
                section = replace(section, paragraphs=())
            technical_extras.extend(item for item in section.items if item.startswith(
                ("Replay Coaching:", "Information-set Coaching:", "Tactical Review:")))
            section = replace(section,
                details=tuple(detail for detail in section.details if detail.label in RESULT_LABEL_KEYS and "fixed policy" not in detail.label),
                items=tuple(item for item in section.items if not item.startswith(
                    ("Replay Coaching:", "Information-set Coaching:", "Tactical Review:"))))
        if section.title == "Summary" and recorded_context is not None:
            section = replace(section, details=tuple(detail for detail in section.details
                if detail.label not in {"Contract", "Next player", "Current Trick"}))
        body = _section_body(section, candidate_identity=(identifier
            if presentation.workflow == "position_analysis" and section.title == "Alternatives"
            else None))
        if section.title == "Summary" and recorded_context is not None:
            body = render_recorded_decision_context(
                recorded_context, recorded_context_locale, scores=False) + body
        if index == 0 and presentation.warnings:
            body = (
                f'<aside aria-label="{_t("result.warnings")}"><h3>{_t("result.warnings")}</h3>'
                + f'<p>{_t("result.warning_count", count=len(presentation.warnings))}</p>'
                + "</aside>"
                + body
            )
        if section.title == "Technical details":
            exact = [*technical_extras, *presentation.warnings]
            body += '<div lang="en">' + ''.join(
                '<p>' + escape(item if isinstance(item, str) else f"{item.label}: {item.value}") + '</p>'
                for item in exact) + '</div>'
            body += '<dl lang="en">' + ''.join(
                '<dt>' + escape(detail.label) + '</dt><dd>' + escape(detail.value) + '</dd>'
                for original in presentation.sections for detail in original.details
                if original.title != "Technical details") + '</dl>'
            body = (
                f'<details><summary>{_t("task.technical")}</summary>'
                + body
                + _download_links(
                    page=effective_page,
                    request_download_available=request_download_available,
                    result_download_available=result_download_available,
                    request_download_route=request_download_route,
                    result_download_route=result_download_route,
                )
                + "</details>"
            )
        rendered.append(
            f'<section aria-labelledby="{identifier}">'
            f'<h2 id="{identifier}">{escape(result_label(section.title))}</h2>{body}</section>'
        )
    return '<div class="result-presentation">' + "".join(rendered) + "</div>"


def render_safe_result_error_summary_v1(*, title: str, message: str) -> str:
    """Renders a minimized escaped error summary outside normal Result states."""

    if type(title) is not str or not title or type(message) is not str or not message:
        raise ValueError("Safe Result error title and message must be non-empty text.")
    return (
        '<section class="result-error" aria-labelledby="result-error-heading">'
        f'<h2 id="result-error-heading">{escape(title)}</h2>'
        f"<p>{escape(message)}</p></section>"
    )
