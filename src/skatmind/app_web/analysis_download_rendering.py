"""Private markup for already available analysis artifacts; no export preparation."""
from html import escape

from .render_locale import html_message, localized_render


@localized_render
def analysis_downloads(*, request_href: str | None = None, result_href: str | None = None) -> str:
    links = []
    for href, key in ((request_href, "result.download_request"),
                      (result_href, "result.download_result")):
        if href is not None:
            links.append(f'<li><a class="button-link secondary" href="{escape(href, quote=True)}" '
                         f'download>{html_message(key)}</a></li>')
    if not links:
        return ""
    return ('<nav class="analysis-downloads" aria-label="' + html_message("result.downloads")
            + '"><h3>' + html_message("result.downloads") + '</h3><ul>'
            + ''.join(links) + '</ul></nav>')
