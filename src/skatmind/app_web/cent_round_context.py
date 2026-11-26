"""Cent-Skat session display and continuation terms from the accounting journal."""

from skatmind.event_context_contracts import CENT_TARIFFS

from .translation_catalog import translate_frontend_message_v1 as translate

AUTOMATIC_ROUND_PROVENANCE = "Native three-game round with automatic numbering."


def round_labels(journal, locale, *, next_table=None):
    """Return saved labels and the proposed label in append-only creation order."""
    sessions = {}
    counts = {}
    labels = {}
    for row in journal.round_heads:
        session = sessions.setdefault(row.table_id, len(sessions) + 1)
        number = counts.get(row.table_id, 0) + 1
        counts[row.table_id] = number
        label = translate(locale, "cent.title", session=session, number=number)
        if row.context.provenance != AUTOMATIC_ROUND_PROVENANCE:
            label += " · " + row.context.event_name
        labels[row.identity] = label
    proposed = translate(locale, "cent.title", session=sessions.get(next_table, len(sessions) + 1),
                         number=counts.get(next_table, 0) + 1)
    return labels, proposed


def session_tariff(journal, table_id):
    rates = {term.financial.cent_tariff for row in journal.round_heads if row.table_id == table_id
             for term in row.context.terms}
    if len(rates) == 1:
        rate = rates.pop()
        if rate in CENT_TARIFFS:
            return rate
    return None
