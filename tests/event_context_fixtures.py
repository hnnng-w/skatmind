"""Tiny synthetic #321 evidence; no maintainer data, analysis or large game corpus."""

from dataclasses import replace

from test_historical_game import build_historical_input
from test_match_workspace_contracts import _definition, _observed_game, _seat_order, _set_game
from test_observed_game_contracts import declaration_from_historical, observed_plays_from_historical

from skatmind.event_context_contracts import (
    TOURNAMENT_RULE,
    CheckpointV1,
    EventContextV1,
    EventTermsV1,
    RuleSourceV1,
)
from skatmind.event_context_sources import build_event_binding_v1
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_operations import replace_match_workspace_definition_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1


def synthetic_match(*, settled_position=25, missing_skat=False):
    definition = _definition()
    data = build_historical_input(game_type="grand", hand_game=False)
    mapping = dict(zip((p["player_id"] for p in data["players"]),
                       _seat_order(definition, settled_position), strict=True))
    for player in data["players"]:
        player["player_id"] = mapping[player["player_id"]]
    data["declarer_player_id"] = mapping[data["declarer_player_id"]]
    for trick in data["tricks"]:
        trick["leader_player_id"] = mapping[trick["leader_player_id"]]
        for play in trick["plays"]:
            play["player_id"] = mapping[play["player_id"]]
    game = _observed_game(definition, match_position=settled_position, game_timecode=None,
        perspective_initial_hand=next(p["initial_hand"] for p in data["players"]
                                     if p["player_id"] == definition.perspective_player_id),
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        original_skat=None if missing_skat else data["skat"],
        discarded_cards=data["discarded_cards"], plays=observed_plays_from_historical(data))
    workspace = _set_game(create_match_workspace_v1(definition), game)
    return build_match_workspace_persistence_document_v1(workspace)


def synthetic_context(document, *, checkpoint=True):
    binding = build_event_binding_v1(document)
    return EventContextV1(event_id="synthetic-event", series_id="synthetic-series",
        event_name="Synthetic afternoon event", series_name="Synthetic list 1",
        participant_ids=tuple(p.event_player_id for p in binding.players),
        selected_participant_id=binding.player(binding.source_selected_player_id),
        bindings=(binding,), terms=(EventTermsV1(from_position=1, mode="tournament",
            scoring_rule=TOURNAMENT_RULE, scoring_source=RuleSourceV1(
                reference="Confirmed synthetic fixed-three-player list rules", edition="1")),),
        checkpoints=(CheckpointV1(through_position=24, personal_points=780, own_losses=3,
                                 provenance="Synthetic confirmed list through position 24"),)
        if checkpoint else ())


def changed_document(document):
    workspace = document.workspace
    changed = replace_match_workspace_definition_v1(workspace,
        replace(workspace.match_definition, title="Corrected synthetic source"),
        expected_revision=workspace.revision).workspace
    return build_match_workspace_persistence_document_v1(changed)


def main():
    """Generate one disposable source-only Match for the later combined checklist."""
    import argparse
    from pathlib import Path

    from skatmind.match_workspace_persistence import save_match_workspace_file_v1

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="A new synthetic Workspace file in an existing development directory.")
    args = parser.parse_args()
    result = save_match_workspace_file_v1(args.output, synthetic_match(),
                                         expected_content_fingerprint=None)
    if result.status != "saved":
        parser.error("The synthetic output already exists; choose a fresh development filename.")
    print("Synthetic Match saved: only game 25 is recorded; positions 1-24 remain missing.")
    print("Import it through Match JSON transfer, then confirm checkpoint 24 / 780 / 3.")


if __name__ == "__main__":
    main()
