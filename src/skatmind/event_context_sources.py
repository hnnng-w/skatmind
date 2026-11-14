"""Existing recording adapters; settlement facts are derived without Card analysis."""

from .event_context_contracts import (
    EventBindingV1,
    ParticipantMapV1,
    RecordingKeyV1,
    RecordingVersionV1,
    identity,
    position,
)
from .event_context_projection import (
    DecisionCutoffV1,
    DeclarationFactV1,
    GameSignatureV1,
    OutcomeFactV1,
    RecordingFactsV1,
)
from .historical_game import build_historical_game_record, build_historical_game_summary
from .match_historical_materialization import materialize_match_observed_game_historical_v1
from .match_workspace_persistence_codec import resume_match_workspace_document_v1
from .match_workspace_persistence_contracts import MatchWorkspacePersistenceDocumentV1
from .performance_rating import get_game_outcome_for_rating
from .session_historical_export import export_session_historical_game_request_v1
from .session_persistence_codec import resume_session_document_v1
from .session_persistence_contracts import SessionPersistenceDocumentV1
from .session_transitions import replay_session_state_v1

# These paths establish ordinary or accepted-concession outcomes without a proof
# search. Other Session endings remain explicitly unsettled for this adapter.
ESTABLISHED_SESSION_ENDINGS = ("normal_completion", "declarer_concession", "defender_concession")


def recording_version_v1(document):
    if type(document) is MatchWorkspacePersistenceDocumentV1:
        return RecordingVersionV1(source=RecordingKeyV1(family="match",
            product_id=document.workspace.match_definition.match_id),
            content_fingerprint=document.content_fingerprint, revision=document.workspace.revision)
    if type(document) is SessionPersistenceDocumentV1:
        return RecordingVersionV1(source=RecordingKeyV1(family="session",
            product_id=document.state.session_id), content_fingerprint=document.content_fingerprint,
            revision=document.state.revision)
    raise ValueError("Expected a strict Match or Session persistence document.")


def recording_players_v1(document):
    if type(document) is MatchWorkspacePersistenceDocumentV1:
        definition = document.workspace.match_definition
        return tuple(p.player_id for p in definition.participants), definition.perspective_player_id
    if type(document) is SessionPersistenceDocumentV1:
        return tuple(p.player_id for p in document.state.players), document.state.local_player_id
    raise ValueError("Expected an exact supported recording document.")


def build_event_binding_v1(document, *, game_position=None, player_map=None,
                           selected_player_id=None):
    players, selected = recording_players_v1(document)
    # Existing perspective is authoritative; full-deal Sessions without a local
    # player may explicitly identify one existing participant when first attached.
    if selected is None:
        selected = selected_player_id
    elif selected_player_id is not None and selected_player_id != selected:
        raise ValueError("Do not replace the recording's selected participant.")
    mapping = {player: player for player in players} if player_map is None else player_map
    if set(mapping) != set(players):
        raise ValueError("Participant mapping must cover the actual recording players exactly.")
    return EventBindingV1(attached_source=recording_version_v1(document),
        game_position=game_position,
        players=tuple(ParticipantMapV1(source_player_id=player, event_player_id=mapping[player])
                      for player in players), source_selected_player_id=selected)


def validate_session_match_seats_v1(context, session, binding, match_document):
    """An explicit mapping must also respect the fixed Match's actual rotation."""
    from .match_workspace_rotation import build_match_workspace_seat_assignment_v1

    match_binding = context.binding(recording_version_v1(match_document).source)
    if match_binding is None:
        raise ValueError("The supplied Match is not attached to this event.")
    seats = build_match_workspace_seat_assignment_v1(match_document.workspace.match_definition,
                                                     binding.game_position)
    for player in session.state.players:
        expected = match_binding.player(getattr(seats, player.seat + "_player_id"))
        if binding.player(player.player_id) != expected:
            raise ValueError("Session participant mapping contradicts Match seat rotation.")


def _settled_fact(record, number):
    summary = build_historical_game_summary(record)
    settlement = summary.get("final_settlement_summary", {})
    outcome, score = get_game_outcome_for_rating(settlement), settlement.get("settlement_score")
    if (settlement.get("is_complete") is not True or outcome not in (
            "declarer_win", "declarer_loss") or type(score) is not int):
        return OutcomeFactV1(position=number, status="unsettled")
    # Normalize only identity aliases, not game facts. Equal outcomes alone do not
    # make two complete contradictory recordings the same accounting evidence.
    from .historical_game import build_serializable_historical_record

    value = build_serializable_historical_record(record)
    seats = {player.player_id: player.seat for player in record.players}
    value.pop("game_id")
    value.pop("played_at", None)
    for player in value["players"]:
        player["player_id"] = seats[player["player_id"]]
        player.pop("player_label", None)
        player["initial_hand"] = sorted(player["initial_hand"])
    value["declarer_player_id"] = seats[record.declarer_player_id]
    for trick in value["tricks"]:
        trick["leader_player_id"] = seats[trick["leader_player_id"]]
        for play in trick["plays"]:
            play["player_id"] = seats[play["player_id"]]
    value["skat"] = sorted(value["skat"])
    value["discarded_cards"] = sorted(value["discarded_cards"])
    return OutcomeFactV1(position=number, status="settled", declarer_id=record.declarer_player_id,
        outcome=outcome, settlement_score=score, evidence_fingerprint=identity("outcome", value))


def _signature(number, players, declarer, declaration, plays):
    from .game_declaration import build_serializable_game_declaration

    seats = {player.player_id: player.seat for player in players}
    known = {} if declaration is None else build_serializable_game_declaration(declaration)
    if declarer is not None:
        known["declarer_seat"] = seats[declarer]
    prefix, fingerprints = [], []
    for actor, card in plays:
        prefix.append([seats[actor], card])
        fingerprints.append(identity("observed_trace", prefix))
    return GameSignatureV1(position=number, declaration=tuple(
        DeclarationFactV1(name=name, value=str(value))
        for name, value in sorted(known.items()) if value is not None),
        trace_prefixes=tuple(fingerprints))


def build_recording_facts_v1(document, *, through_position=36, decision_position=None,
                             selected_player_id=None):
    """Strict source validation, then only requested earlier outcomes and target actors."""
    position(through_position, zero=True)
    if type(document) is MatchWorkspacePersistenceDocumentV1:
        document = resume_match_workspace_document_v1(document.to_dict()).document
        workspace = document.workspace
        outcomes, decisions, signatures = [], [], []
        for slot in workspace.slots[:through_position]:
            number = slot.match_position
            if slot.observed_game is not None:
                game = slot.observed_game
                signatures.append(_signature(number, game.players, game.declarer_player_id,
                    game.declaration, tuple((play.player_id, play.card) for play in game.plays)))
            if slot.slot_kind in ("empty", "passed_deal"):
                outcomes.append(OutcomeFactV1(position=number,
                    status="missing" if slot.slot_kind == "empty" else "passed"))
            elif len(slot.observed_game.plays) < 30:
                outcomes.append(OutcomeFactV1(position=number, status="unfinished"))
            else:
                materialized = materialize_match_observed_game_historical_v1(
                    workspace, match_position=number)
                outcomes.append(_settled_fact(materialized.historical_game, number)
                    if materialized.status == "available" else
                    OutcomeFactV1(position=number, status="unsettled"))
        if decision_position is not None:
            position(decision_position)
            game = workspace.slots[decision_position - 1].observed_game
            if game is not None:
                decisions = [DecisionCutoffV1(position=decision_position,
                    decision_index=index, actor_id=play.player_id, game_id=game.game_id)
                    for index, play in enumerate(game.plays, 1)]
    elif type(document) is SessionPersistenceDocumentV1:
        document = resume_session_document_v1(document).document
        projection = replay_session_state_v1(document.state)
        outcomes, decisions, signatures = [], [], []
        if through_position:
            signatures.append(_signature(1, projection.players, projection.declarer_player_id,
                                         projection.declaration, projection.plays))
            fact = OutcomeFactV1(position=1,
                status="unfinished" if projection.phase != "ended" else "unsettled")
            if (projection.game_end_reason in ESTABLISHED_SESSION_ENDINGS
                    and document.state.validation.historical_export.status == "available"):
                exported = export_session_historical_game_request_v1(document.state)
                if exported.status == "available":
                    record = build_historical_game_record(
                        exported.request.to_dict()["document"]["historical_game_input"])
                    fact = _settled_fact(record, 1)
            outcomes.append(fact)
        if decision_position is not None:
            decisions = [DecisionCutoffV1(position=1, decision_index=index, actor_id=actor,
                                          game_id=projection.game_id)
                         for index, (actor, _card) in enumerate(projection.plays, 1)]
    else:
        raise ValueError("Expected a strict supported recording document.")
    players, selected = recording_players_v1(document)
    if selected is None:
        selected = selected_player_id
    return RecordingFactsV1(source=recording_version_v1(document), player_ids=players,
        selected_player_id=selected, outcomes=tuple(outcomes), decisions=tuple(decisions),
        signatures=tuple(signatures))
