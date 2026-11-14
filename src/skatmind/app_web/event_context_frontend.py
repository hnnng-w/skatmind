"""Managed-source capture and context-only operations; no analysis/Learning dependency."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass, replace

from skatmind.automatic_learning_codec import canonical_json
from skatmind.errors import SkatMindError
from skatmind.event_context_contracts import EventContextV1
from skatmind.event_context_operations import (
    EventContextConflict,
    reconfirm_event_checkpoint_v1,
    revise_event_context_v1,
    set_event_checkpoint_v1,
    set_event_terms_v1,
)
from skatmind.event_context_projection import prepare_event_context_v1
from skatmind.event_context_recording_files import load_event_recording_v1
from skatmind.event_context_sources import (
    build_event_binding_v1,
    build_recording_facts_v1,
    recording_players_v1,
    recording_version_v1,
    validate_session_match_seats_v1,
)
from skatmind.event_context_store import (
    append_event_revision_v1,
    load_event_context_v1,
    save_event_context_v1,
)

from .event_context_forms import (
    EVENT_FIELDS,
    EventFormError,
    number,
    parse_event_checkpoint,
    parse_event_terms,
)
from .managed_item_discovery import discover_managed_items_v1
from .recorded_review_opening import RecordingOpenConflict, require_recording_fresh_v1
from .workflow_state import StaleFrontendWorkflowRevisionError


class EventFormConflict(StaleFrontendWorkflowRevisionError):
    def __init__(self, reason="stale"):
        self.reason = reason
        super().__init__("The event context or its recording changed.")


@dataclass(frozen=True)
class EventPage:
    journal: object
    context: object
    document: object
    documents: tuple
    prepared: object
    selection: str


def _documents(app, event, active, family, document):
    result = [(active.path, document)]
    if event is None:
        return tuple(result)
    target = recording_version_v1(document).source
    discoveries = {}
    for binding in event.bindings:
        if binding.source == target:
            continue
        category = "matches" if binding.source.family == "match" else "sessions"
        if category not in discoveries:
            discoveries[category] = discover_managed_items_v1(
                app.managed_stateful.root(category), family=category, generation=1,
                active_handle=None)
        discovery = discoveries[category]
        if discovery.view.candidate_limit_reached:
            raise EventFormConflict("source")
        entries = [entry for entry in discovery.entries
                   if entry.summary.semantic_product_id == binding.source.product_id]
        if len(entries) != 1 or entries[0].summary.status != "available":
            continue  # The preparation reports source_unavailable for uncovered positions.
        try:
            loaded = load_event_recording_v1(entries[0].path, binding.source.family)
            if recording_version_v1(loaded).source == binding.source:
                result.append((entries[0].path, loaded))
        except (OSError, ValueError, SkatMindError):
            continue
    return tuple(result)


def _facts(event, documents, *, game_position, target):
    result = []
    for _path, document in documents:
        source = recording_version_v1(document).source
        binding = event.binding(source)
        if binding is None:
            continue
        through = game_position - 1 if source.family == "match" else int(
            binding.game_position < game_position)
        result.append(build_recording_facts_v1(document, through_position=through,
            decision_position=game_position if source == target and game_position <= 36 else None,
            selected_player_id=binding.source_selected_player_id))
    return tuple(result)


def capture_event_page(app, active, family, *, event_id=None):
    active.require_attached()
    try:
        require_recording_fresh_v1(active, family)
    except RecordingOpenConflict as error:
        raise EventFormConflict("source") from error
    source_family = "match" if family == "matches" else "session"
    document = load_event_recording_v1(active.path, source_family)
    source = recording_version_v1(document).source
    journal = load_event_context_v1(app.managed_stateful.managed_home.root)
    event = journal.for_source(source) if event_id is None else journal.context(event_id)
    documents = _documents(app, event, active, family, document)
    prepared = None
    binding = None if event is None else event.binding(source)
    if binding is not None:
        game_position = active.selected_position if family == "matches" else binding.game_position
        prepared = prepare_event_context_v1(event,
            _facts(event, documents, game_position=game_position, target=source),
            target=source, game_position=game_position)
    scope = [journal.fingerprint, active.handle,
        active.position_generation if family == "matches" else active.generation,
        active.selected_position if family == "matches" else None,
        [recording_version_v1(item).to_dict() for _, item in documents], event_id]
    selection = hmac.new(app.language_context.key,
        b"event_context_form_v1\0" + canonical_json(scope), hashlib.sha256).hexdigest()
    return EventPage(journal, event, document, documents, prepared, selection)


def checkpoint_review(page, through):
    context = page.context
    source = recording_version_v1(page.document).source
    target = next((binding.source for binding in context.bindings
                   if binding.source.family == "match"), source)
    if target.family == "session" and context.binding(target).game_position <= through:
        return None
    cutoff = through + 1 if target.family == "match" else context.binding(target).game_position
    return prepare_event_context_v1(context,
        _facts(context, page.documents, game_position=cutoff, target=target),
        target=target, game_position=cutoff)


def _selected(document, values):
    players, selected = recording_players_v1(document)
    if selected is None:
        selected = players[number(values, "selected_player", minimum=1, maximum=3) - 1]
    elif values.get("selected_player", ""):
        raise EventFormError("participant", "selected_player")
    return selected


def _attach(app, page, values):
    event = page.journal.context(values.get("event_choice"))
    if event is None:
        raise EventFormError("attachment", "event_choice")
    players, _ = recording_players_v1(page.document)
    mapping = {player: event.participant_ids[number(values, f"map_{index}", minimum=1, maximum=3)-1]
               for index, player in enumerate(players, 1)}
    binding = build_event_binding_v1(page.document,
        game_position=number(values, "game_position", minimum=1), player_map=mapping,
        selected_player_id=_selected(page.document, values))
    existing = page.journal.for_source(binding.source)
    if existing is not None and existing.event_id != event.event_id:
        raise EventFormError("attachment")
    match_binding = next((item for item in event.bindings if item.source.family == "match"), None)
    if match_binding is not None:
        # Use the exact managed identity and strict loader, never a name/filename join.
        state = app.managed_stateful
        discovery = discover_managed_items_v1(state.root("matches"), family="matches",
                                              generation=1, active_handle=None)
        entries = [entry for entry in discovery.entries if entry.summary.semantic_product_id
                   == match_binding.source.product_id and entry.summary.status == "available"]
        if len(entries) != 1 or discovery.view.candidate_limit_reached:
            raise EventFormConflict("source")
        document = load_event_recording_v1(entries[0].path, "match")
        validate_session_match_seats_v1(event, page.document, binding, document)
    previous = event.binding(binding.source)
    if (previous is not None
            and replace(binding, attached_source=previous.attached_source) == previous):
        return event
    return revise_event_context_v1(event, expected_revision=event.revision, change="attachment",
        provenance=values.get("provenance", "").strip(), bindings=tuple(
            item for item in event.bindings if item.source != binding.source) + (binding,))


def dispatch_event_context(app, route, values):
    family, action = route.split("/")[1], route.rsplit("/", 1)[1]
    if set(values) - {"managed_handle", "event_selection", *EVENT_FIELDS[action]}:
        raise EventFormError("invalid")
    if action == "attach" and family != "sessions":
        raise EventFormError("attachment")
    managed = app.managed_stateful
    gate = managed.match_lifecycle_lock if family == "matches" else managed.session_lifecycle_lock
    with gate:
        with app.lock:
            active = managed.active_match if family == "matches" else managed.active_session
        if active is None or values.get("managed_handle") != active.handle:
            raise EventFormConflict()
        with active.capture.lock if family == "matches" else active.lock:
            event_id = values.get("event_choice") if action == "attach" else None
            page = capture_event_page(app, active, family, event_id=event_id)
            selection = values.get("event_selection", "")
            if (not re.fullmatch(r"[0-9a-f]{64}", selection)
                    or not hmac.compare_digest(selection, page.selection)):
                raise EventFormConflict()
            context, prepared = page.context, None
            source = recording_version_v1(page.document).source
            if action == "create":
                if context is not None:
                    raise EventFormConflict()
                binding = build_event_binding_v1(page.document,
                    game_position=None if family == "matches" else
                    number(values, "game_position", minimum=1),
                    selected_player_id=_selected(page.document, values))
                checkpoints = ()
                if any(values.get(name, "") for name in ("through_position", "personal_points",
                                                        "own_losses")):
                    checkpoints = (parse_event_checkpoint(values),)
                context = EventContextV1(event_id="event-" + secrets.token_hex(16),
                    series_id="series-" + secrets.token_hex(16),
                    event_name=values.get("event_name", "").strip(),
                    series_name=values.get("series_name", "").strip(),
                    participant_ids=tuple(p.event_player_id for p in binding.players),
                    selected_participant_id=binding.player(binding.source_selected_player_id),
                    bindings=(binding,), terms=(parse_event_terms(values, from_position=1),),
                    checkpoints=checkpoints)
            elif action == "attach":
                context = _attach(app, page, values)
            elif context is None:
                raise EventFormConflict()
            elif action == "checkpoint":
                context = set_event_checkpoint_v1(context, parse_event_checkpoint(values),
                                                   expected_revision=context.revision)
            elif action == "terms":
                if values.get("change_kind") not in ("correction", "later"):
                    raise EventFormError("applicability", "change_kind")
                context = set_event_terms_v1(context, parse_event_terms(values,
                    from_position=number(values, "from_position", minimum=1)),
                    expected_revision=context.revision,
                    correction=values["change_kind"] == "correction",
                    provenance=values.get("provenance", "").strip(),
                    event_name=values.get("event_name", "").strip(),
                    series_name=values.get("series_name", "").strip())
            elif action == "remove":
                through = number(values, "through_position")
                context = revise_event_context_v1(context, expected_revision=context.revision,
                    change="checkpoint_removed", provenance=values.get("provenance", "").strip(),
                    checkpoints=tuple(c for c in context.checkpoints
                                      if c.through_position != through))
            elif action == "reconfirm":
                through = number(values, "through_position")
                prepared = checkpoint_review(page, through)
                if prepared is None:
                    raise EventFormError("applicability")
                disagreement = next((item for item in prepared.disagreements
                    if item.checkpoint.through_position == through), None)
                if disagreement is None or values.get("disagreement") != disagreement.fingerprint:
                    raise EventFormConflict()
                context = reconfirm_event_checkpoint_v1(context, prepared, through_position=through,
                    expected_revision=context.revision,
                    provenance=values.get("provenance", "").strip())
            elif action == "freeze":
                game = (active.selected_position if family == "matches"
                        else context.binding(source).game_position)
                prepared = prepare_event_context_v1(context,
                    _facts(context, page.documents, game_position=game, target=source),
                    target=source,
                    game_position=game, decision_index=number(values, "decision_index", minimum=1,
                                                              maximum=30))
                if prepared.status in ("source_unavailable", "decision_unavailable"):
                    raise EventFormError("decision", "decision_index")
            journal = append_event_revision_v1(page.journal, context, prepared=prepared)

            def guard():
                try:
                    return capture_event_page(app, active, family,
                                              event_id=event_id).selection == page.selection
                except (OSError, ValueError, SkatMindError, StaleFrontendWorkflowRevisionError):
                    return False

            try:
                save_event_context_v1(managed.managed_home.root, journal,
                    expected_fingerprint=page.journal.fingerprint, source_guard=guard)
            except EventContextConflict as error:
                raise EventFormConflict() from error
            except OSError as error:
                raise EventFormConflict("save") from error
            if family == "matches" and action in ("create", "checkpoint") and context.checkpoints:
                from .match_frontend import select_unified_match_position_v1

                through = number(values, "through_position")
                select_unified_match_position_v1(active, min(through + 1, 36))
    return (f"/matches/position/{active.selected_position}" if family == "matches"
            else "/sessions/current") + "#event-context"
