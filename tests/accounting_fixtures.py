"""Disposable source-only #321/#322 inputs; no application, UAT or analysis startup."""

from dataclasses import replace

from event_context_fixtures import synthetic_match
from test_historical_game import build_historical_input
from test_session_transitions import _complete_retrospective_session

from skatmind.session_persistence_codec import build_session_persistence_document_v1


def completed_cent_session():
    state = _complete_retrospective_session(
        build_historical_input(game_type="grand", hand_game=False))
    return build_session_persistence_document_v1(state)


def own_loss_match():
    from test_match_workspace_contracts import _definition, _observed_game, _set_game
    from test_observed_game_contracts import (
        declaration_from_historical,
        observed_plays_from_historical,
    )

    from skatmind.match_workspace_contracts import create_match_workspace_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )

    data = build_historical_input(game_type="grand", hand_game=False)
    definition = _definition(perspective_player_id="player-b",
                             match_id="synthetic-progressive-match")
    game = _observed_game(definition, match_position=27, game_timecode=None,
        perspective_initial_hand=next(p["initial_hand"] for p in data["players"]
                                      if p["player_id"] == "player-b"),
        declarer_player_id=data["declarer_player_id"],
        declaration=declaration_from_historical(data),
        original_skat=data["skat"], discarded_cards=data["discarded_cards"],
        plays=observed_plays_from_historical(data))
    return build_match_workspace_persistence_document_v1(_set_game(
        create_match_workspace_v1(definition), game))


def main():
    import argparse
    from pathlib import Path

    from skatmind.match_workspace_persistence import save_match_workspace_file_v1
    from skatmind.session_persistence import save_session_persistence_file_v1

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    root = args.output_directory
    if not root.is_dir():
        parser.error("Use an existing disposable development directory.")
    names = ("synthetic-checkpoint-match.json", "synthetic-cent-established.json",
             "synthetic-progressive-match.json")
    if any((root / name).exists() for name in names):
        parser.error("Synthetic files already exist; use a fresh directory.")
    match = synthetic_match()
    session = completed_cent_session()
    session = build_session_persistence_document_v1(replace(session.state,
        session_id="synthetic-cent-established"))
    first = save_match_workspace_file_v1(root / names[0], match, expected_content_fingerprint=None)
    second = save_session_persistence_file_v1(root / names[1], session,
                                             expected_content_fingerprint=None)
    third = save_match_workspace_file_v1(root / names[2], own_loss_match(),
                                        expected_content_fingerprint=None)
    if any(result.status != "saved" for result in (first, second, third)):
        parser.error("A synthetic source could not be saved; inspect the disposable directory.")
    print("Three synthetic sources saved. No profile, accounting, server or UAT was created.")


if __name__ == "__main__":
    main()
