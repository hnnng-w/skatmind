"""Private single-decision layout; callers supply only their already escaped cells."""

from html import escape


def candidate_table_html(*, caption_html, columns_html, rows_html, identity):
    """One native table, with visual local labels and explicit static header links.

    This accepts trusted renderer output, never raw Result/Report dictionaries.
    The caller owns localization, formatting, ordering and its page-local identity.
    Explicit table roles retain semantics when narrow CSS changes display types.
    """
    prefix = escape(identity, quote=True)
    headers = tuple(f"{prefix}-column-{i}" for i in range(len(columns_html)))
    headings = ''.join(
        f'<th scope="col" role="columnheader" id="{key}">{label}</th>'
        for key, label in zip(headers, columns_html, strict=True))
    rows = []
    for index, row in enumerate(rows_html):
        row_id = f"{prefix}-card-{index}"
        cells = []
        for column, (label, value) in enumerate(zip(columns_html, row, strict=True)):
            content = (f'<span class="candidate-label" aria-hidden="true">{label}</span>'
                       f'<span class="candidate-value">{value}</span>')
            if column == 0:
                cells.append(f'<th scope="row" role="rowheader" id="{row_id}" '
                             f'headers="{headers[0]}">{content}</th>')
            else:
                cells.append(f'<td role="cell" headers="{row_id} {headers[column]}">'
                             f'{content}</td>')
        rows.append('<tr role="row">' + ''.join(cells) + '</tr>')
    return ('<table class="candidate-table" role="table">'
            f'<caption>{caption_html}</caption><thead role="rowgroup">'
            f'<tr role="row">{headings}</tr></thead><tbody role="rowgroup">'
            + ''.join(rows) + '</tbody></table>')
