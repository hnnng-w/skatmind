"""Bounded best-effort presentation receipts, separate from retained Product results."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field, replace
from html import escape

from skatmind.deck import get_full_deck

from .stateful_localization import card_name, text

DELIVERY_TTL_SECONDS = 60
FEEDBACK_MARKER = "<!-- operation-feedback -->"
ENTRY_FEEDBACK_MARKER = "<!-- entry-operation-feedback -->"
METADATA_FEEDBACK_MARKER = "<!-- metadata-operation-feedback -->"
RESULTS_FEEDBACK_MARKER = "<!-- results-operation-feedback -->"

# Parameters are accepted roster ordinals, canonical Cards and bounded counts only.
# Full accepted labels are resolved on the exact bound source, never copied/truncated.
MESSAGE_PARAMETERS = {
    "session_created": (), "match_created": (), "learning_created": (),
    "initial_cards": ("count", "player"), "play": ("card", "player"),
    "plays": ("count",), "skat": ("count",), "discards": ("count",),
    "hand": ("player",), "public_hand": ("player",),
    "declarer": (), "declaration": (), "details": (), "ending": (),
    "game_started": ("number",), "game_passed": ("number",), "correction": (),
    "version_added": (), "version_selected": (), "prepared": (),
}


@dataclass(frozen=True, slots=True)
class FeedbackSource:
    references: tuple[object, ...]
    values: tuple[object, ...]

    def matches(self, other: FeedbackSource) -> bool:
        return (self.values == other.values and len(self.references) == len(other.references)
                and all(a is b for a, b in zip(self.references, other.references, strict=True)))


@dataclass(frozen=True, slots=True)
class OperationReceipt:
    message_key: str
    parameters: tuple[tuple[str, str | int], ...]
    operation_identity: object
    source: FeedbackSource
    expires_at: float
    area: str = "task"

    def __post_init__(self):
        name = self.message_key.removeprefix("feedback.")
        if (type(self.source) is not FeedbackSource
                or type(self.expires_at) not in {int, float} or not math.isfinite(self.expires_at)
                or self.area not in {"task", "metadata"}
                or self.message_key != "feedback." + name or name not in MESSAGE_PARAMETERS
                or type(self.parameters) is not tuple
                or tuple(key for key, _ in self.parameters) != MESSAGE_PARAMETERS[name]):
            raise ValueError("Receipt requires an allowlisted message and exact parameters.")
        for key, value in self.parameters:
            if key == "card":
                valid = type(value) is str and value in get_full_deck()
            else:
                maximum = {"player": 3, "count": 30, "number": 36}[key]
                valid = type(value) is int and 1 <= value <= maximum
            if not valid:
                raise ValueError("Receipt parameters must be bounded accepted values.")


@dataclass(slots=True)
class PendingOperationFeedback:
    """One slot owned by the existing family Product lock; never a history."""

    pending: OperationReceipt | None = field(default=None, repr=False)
    attempt: object | None = field(default=None, repr=False)

    def begin(self) -> object:
        self.pending = None
        self.attempt = object()
        return self.attempt

    def publish(self, attempt, source, message, *, now=None):
        if self.attempt is not attempt or message is None:
            return
        key, parameters = message
        self.pending = OperationReceipt("feedback." + key, parameters, attempt, source,
            (time.monotonic() if now is None else now) + DELIVERY_TTL_SECONDS)

    def take(self, source, *, now=None, suppressed=False):
        receipt = self.pending
        self.pending = None
        if (receipt is None or suppressed or receipt.operation_identity is not self.attempt
                or (time.monotonic() if now is None else now) >= receipt.expires_at
                or not receipt.source.matches(source)):
            return None
        return receipt

    def place_at_metadata(self):
        """The existing local-time redirect returns to metadata, without renewing TTL."""
        if self.pending is not None:
            self.pending = replace(self.pending, area="metadata")


def feedback_lock(active):
    if hasattr(active, "capture"):
        return active.capture.lock
    if hasattr(active, "corpus"):
        return active.corpus.lock
    return active.lock


def feedback_source(active) -> FeedbackSource:
    """Caller owns the existing Product lock. No I/O, replay, hashing or projection."""
    if hasattr(active, "capture"):
        game = active.workspace.slots[active.selected_position - 1].observed_game
        return FeedbackSource((active, active.workspace, game), (
            active.capture.content_fingerprint, active.position_generation,
            active.selected_position, active.capture.report_store.generation, active.retired))
    if hasattr(active, "corpus"):
        corpus = active.corpus
        return FeedbackSource((active, corpus.store, corpus.prepared_artifacts,
            corpus.tactical_prepared_artifacts, corpus.tactical_coaching_prepared_artifacts), (
            corpus.generation, corpus.store.document.content_fingerprint,
            corpus.strategy_source_store.revision))
    return FeedbackSource((active, active.document, active.execution), (
        active.generation, active.document.content_fingerprint, active.retired))


def feedback_players(active):
    return (active.workspace.match_definition.participants if hasattr(active, "capture")
            else () if hasattr(active, "corpus") else active.state.players)


def player_ordinal(players, player_id):
    return next(index for index, player in enumerate(players, 1) if player.player_id == player_id)


def render_operation_receipt(receipt, locale, players=()):
    """Pure escaped presentation. Delivery is exclusively an HTTP responsibility."""
    values = dict(receipt.parameters)
    if "player" in values:
        index = values["player"]
        values["player"] = (players[index - 1].player_label
                            or text(locale, "task.player", number=index))
    if "card" in values:
        values["card"] = card_name(locale, values["card"])
    return ('<div class="operation-feedback" role="status" aria-live="polite" '
            'aria-atomic="true" data-operation-feedback data-dismiss-label="'
            + escape(text(locale, "feedback.dismiss"), quote=True) + '" data-dismissed-label="'
            + escape(text(locale, "feedback.dismissed"), quote=True) + '"><span>'
            + escape(text(locale, receipt.message_key, **values), quote=True) + '</span></div>')


def deliver_operation_feedback(handler, content, *, status):
    """Called only after final HTML/source validation, never by a pure renderer."""
    delivery = getattr(handler, "_operation_feedback_delivery", None)
    if delivery is None or FEEDBACK_MARKER not in content:
        return content
    app = handler.server.app_context
    active, family, rendered_source, suppressed = delivery
    with feedback_lock(active):
        with app.lock:
            current = getattr(app.managed_stateful, "active_" + family)
            feedback_family = {"session": "sessions", "match": "matches",
                               "learning": "learning"}[family]
            feedback = app.form_feedback.current(feedback_family, active_identity=active)
        source = feedback_source(active)
        if current is not active or not rendered_source.matches(source):
            # A stale response must not consume a newer source's receipt.
            return (content.replace(FEEDBACK_MARKER, "").replace(ENTRY_FEEDBACK_MARKER, "")
                    .replace(METADATA_FEEDBACK_MARKER, "").replace(RESULTS_FEEDBACK_MARKER, ""))
        receipt = active.operation_feedback.take(source, suppressed=(
            suppressed or status >= 400 or feedback is not None
            or getattr(active, "retired", False)))
        rendered = "" if receipt is None else render_operation_receipt(
            receipt, handler._frontend_state().locale, feedback_players(active))
    marker = (METADATA_FEEDBACK_MARKER if receipt is not None and receipt.area == "metadata" else
              RESULTS_FEEDBACK_MARKER if receipt is not None
              and receipt.message_key == "feedback.prepared" else
              ENTRY_FEEDBACK_MARKER if receipt is not None
              and receipt.message_key == "feedback.version_added" else FEEDBACK_MARKER)
    return (content.replace(marker, rendered, 1).replace(FEEDBACK_MARKER, "")
            .replace(ENTRY_FEEDBACK_MARKER, "").replace(METADATA_FEEDBACK_MARKER, "")
            .replace(RESULTS_FEEDBACK_MARKER, ""))
