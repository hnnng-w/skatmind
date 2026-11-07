"""Independent typed Historical source/Result reconciliation, without analysis execution."""

from .historical_game import build_historical_game_summary, build_serializable_historical_record
from .historical_play_prefix import (
    build_serializable_derived_trick,
    replay_historical_play_prefix,
)

_OPTIONAL = {
    "decision_snapshot_summary": "decision_snapshots",
    "historical_game_review_summary": "immediate_review",
    "historical_search_review_summary": "search_review",
    "historical_information_set_search_review_summary": "information_set_search_review",
    "historical_replay_coaching_summary": "replay_coaching",
    "historical_information_set_replay_coaching_summary": "information_set_replay_coaching",
    "historical_tactical_motif_review_summary": "historical_tactical_motif_review",
}


def validate_historical_execution(game, invocation, execution):
    document = execution.result.to_dict()["document"]
    summary = document["historical_game_summary"]
    if (document["input_file"] != invocation.input_reference
            or summary["game_id"] != game.game_id
            or summary["record"] != build_serializable_historical_record(game)):
        raise ValueError("Historical Result changed the canonical original Game.")
    replay = replay_historical_play_prefix(game)
    if summary["derived_tricks"] != [build_serializable_derived_trick(row)
                                     for row in replay.completed_tricks]:
        raise ValueError("Historical Result changed chronological play or Trick ownership.")
    # Ordinary settlement and accepted concessions/exposure/throw are pure rules.
    # The two proof-bearing endings retain their original proof: never rerun a solver.
    if game.game_end_reason not in ("defender_open_play", "party_wide_all_remaining_tricks_claim"):
        base = build_historical_game_summary(game)
        if any(summary.get(key) != value for key, value in base.items()):
            raise ValueError("Historical Result contradicts the recorded outcome.")
    else:
        _validate_proof_source(game, replay, summary)
    options = invocation.options.historical_game
    external = invocation.external_documents
    statistics = external.opponent_statistics_to_dict()
    application = document.get("historical_opponent_profile_application_summary")
    if statistics is None:
        if application is not None:
            raise ValueError("Historical Result invented external Profile application.")
    else:
        from .historical_opponent_profile_binding import (
            resolve_historical_opponent_profile_bindings,
        )
        from .input_loader import build_opponent_statistics_from_document
        bindings = resolve_historical_opponent_profile_bindings(game,
            build_opponent_statistics_from_document(statistics),
            statistics_input_file=external.opponent_statistics_reference)
        if application != bindings.application_summary:
            raise ValueError("Historical Result changed source-time Profile bindings.")
    plays = tuple(play for trick in game.tricks for play in trick.plays)
    players = {player.player_id: player for player in game.players}
    for name, option in _OPTIONAL.items():
        if (name in summary) != getattr(options, option):
            raise ValueError("Historical assessment presence contradicts executed options.")
        if name not in summary:
            continue
        family = summary[name]
        if family.get("source_game_id", game.game_id) != game.game_id:
            raise ValueError("Historical assessment changed Game identity.")
        decisions = family.get("decisions")
        if decisions is None:
            continue
        if len(decisions) != len(plays) or family.get("decision_count", len(plays)) != len(plays):
            raise ValueError("Historical assessment coverage contradicts the play prefix.")
        for index, (decision, play) in enumerate(zip(decisions, plays, strict=True), 1):
            expected = {"source_game_id": game.game_id, "decision_index": index,
                "acting_player_id": play.player_id, "actual_card_played": play.card,
                "actual_card": play.card, "acting_seat": players[play.player_id].seat,
                "trick_number": (index - 1) // 3 + 1, "play_index": (index - 1) % 3 + 1}
            if any(decision[key] != value for key, value in expected.items() if key in decision):
                raise ValueError("Historical assessment changed an observed Decision.")
    review = summary.get("historical_game_review_summary")
    if review is not None:
        from .historical_game_review import _build_player_summaries
        from .simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
        settings = {"sample_count": options.immediate_sample_count or
                    DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
                    "base_random_seed": options.immediate_base_random_seed,
                    "opponent_policy_mode": "external_profiles" if
                    invocation.external_documents.opponent_statistics_document is not None
                    else "default"}
        if review["settings"] != settings or review["player_summaries"] != _build_player_summaries(
                historical_record=game, decisions=review["decisions"]):
            raise ValueError("Historical review settings or participant counts disagree.")


def _validate_proof_source(game, replay, summary):
    from .historical_defender_open_play import _build_point_accounting
    points = _build_point_accounting(game, replay)
    if any(summary["point_accounting"].get(key) != value for key, value in points.items()):
        raise ValueError("Historical proof evidence contradicts original point accounting.")
    prefix = {"played_card_count": replay.played_card_count,
        "completed_trick_count": len(replay.completed_tricks),
        "current_trick_card_count": 0 if replay.current_trick is None
            else len(replay.current_trick.plays),
        "remaining_hand_sizes": {key: len(cards) for key, cards in replay.remaining_hands},
        "next_player_id": replay.next_player_id}
    if summary["play_prefix_summary"] != prefix:
        raise ValueError("Historical proof changed its source cutoff.")
    end = summary["historical_game_end_summary"]
    if (end["kind"] != game.game_end_reason
            or end["event_after_play_count"] != replay.played_card_count
            or end["event_after_completed_trick_count"] != len(replay.completed_tricks)
            or end["event_during_incomplete_trick"] != (replay.current_trick is not None)):
        raise ValueError("Historical proof changed its source event.")
    for key, value in (("declarer_trick_points", points["completed_trick_declarer_points"]),
                       ("defender_trick_points", points["completed_trick_defender_points"]),
                       ("skat_points", points["skat_points"])):
        if summary[key] != value:
            raise ValueError("Historical proof changed recorded points.")
    if game.game_end_reason == "defender_open_play":
        event = game.game_end
        if (set(event.exposed_cards) != set(replay.remaining_hand_for(
                event.exposing_defender_player_id)) or not 5 <= len(replay.completed_tricks) < 10):
            raise ValueError("Historical exposure contradicts its exact original hand.")
    else:
        from .party_wide_claim_contracts import build_party_wide_all_remaining_tricks_claim_v1
        from .party_wide_claim_evidence import (
            build_party_wide_claim_evidence_from_historical_replay_v1,
        )
        from .party_wide_claim_proof_contracts import (
            build_party_wide_claim_proof_assignment_v1,
            prepare_party_wide_claim_proof_request_v1,
        )
        event = game.game_end
        claim = build_party_wide_all_remaining_tricks_claim_v1(
            claimant_player_id=event.claimant_player_id, claiming_party=event.claiming_party)
        evidence = build_party_wide_claim_evidence_from_historical_replay_v1(game, replay)
        preparation = prepare_party_wide_claim_proof_request_v1(claim, evidence)
        proof = end["exact_proof"]
        assignment = build_party_wide_claim_proof_assignment_v1(
            preparation=preparation, **proof["assignment"])
        if (proof["status"] != "valid" or proof["proof_complete"] is not True
                or proof["claim_satisfied"] is not True
                or proof["counterexample_found"] is not False
                or end["claimant_player_id"] != event.claimant_player_id
                or end["claiming_party"] != event.claiming_party
                or end["remaining_trick_count"] != evidence.remaining_trick_count):
            raise ValueError("Historical Claim proof contradicts its original preparation.")
        for party in ("declarer", "defenders"):
            field = "defender" if party == "defenders" else party
            assigned = assignment.assigned_card_points if party == assignment.recipient_party else 0
            final = points["observed_" + field + "_points"] + assigned
            if (summary["point_accounting"]["assigned_" + field + "_points"] != assigned
                    or summary["point_accounting"]["final_" + field + "_points"] != final
                    or summary[field + "_points"] != final):
                raise ValueError("Historical Claim assignment contradicts original points.")
