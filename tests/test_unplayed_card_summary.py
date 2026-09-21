import re
from dataclasses import replace

import pytest
from test_historical_game import build_historical_input
from test_recorded_trick_progress import live_from_data, match_trace
from test_session_transitions import _apply, _complete_retrospective_session

from skatmind.app_web.recorded_trick_progress import (
    project_match_trick_progress,
    project_session_trick_progress,
)
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.app_web.unplayed_card_rendering import render_unplayed_cards
from skatmind.app_web.unplayed_card_summary import project_unplayed_cards
from skatmind.game_declaration import GameDeclaration
from skatmind.session_commands import RecordSessionPlayCommandV1
from skatmind.session_transitions import replay_session_state_v1


def complete_facts(game_type="grand", hand_game=False):
    data = build_historical_input(game_type=game_type, hand_game=hand_game)
    state = live_from_data(data)
    for trick in data["tricks"]:
        for play in trick["plays"]:
            state = _apply(state, RecordSessionPlayCommandV1(
                expected_revision=state.revision, **play))
    return replay_session_state_v1(state)


@pytest.fixture(scope="module")
def complete():
    return complete_facts()


@pytest.mark.parametrize("game_type", ("clubs", "spades", "hearts", "diamonds", "grand", "null"))
@pytest.mark.parametrize("hand_game", (False, True))
def test_all_contracts_use_hand_flag_and_pair_without_source_completion(game_type, hand_game):
    from test_match_capture_game_updates import _entry
    from test_observed_game_contracts import build_complete_observed_record

    from skatmind.match_capture_application import (
        append_match_capture_plays_v1,
        set_match_capture_declaration_v1,
    )
    from skatmind.observed_game_evidence import build_observed_game_evidence_summary_v1
    facts = complete_facts(game_type, hand_game)
    before = facts.to_dict()
    progress = project_session_trick_progress(facts)
    original_progress = progress
    summary = project_unplayed_cards(progress, facts.declaration)
    assert summary.cards == (("D8", "D7") if hand_game else ("SK", "SQ"))
    assert summary.hand_game is hand_game
    assert facts.known_skat == facts.discarded_cards == ()
    # No extra replay/rules or hidden-hand construction is needed by the helper.
    record = build_complete_observed_record(game_type=game_type, hand_game=hand_game,
        include_original_skat=False, include_discards=False)
    record_before = record.to_dict()
    evidence = build_observed_game_evidence_summary_v1(record)
    for locale in ("de", "en"):
        html = render_unplayed_cards(summary, locale, original_skat=None, discarded_cards=None)
        assert text(locale, "unplayed.hand_skat" if hand_game else "unplayed.discards") in html
        assert text(locale, "unplayed.no_discards") in html if hand_game else (
            text(locale, "unplayed.original_skat") in html)
    assert record.to_dict() == record_before and facts.to_dict() == before
    assert build_observed_game_evidence_summary_v1(record) == evidence
    assert not evidence.original_skat_known and not evidence.discarded_cards_known
    assert not evidence.complete_initial_deal_reconstructable
    assert project_session_trick_progress(facts) == original_progress
    workspace = match_trace(game_type=game_type)
    workspace = set_match_capture_declaration_v1(workspace, match_position=3,
        declarer_player_id="player-b", declaration=facts.declaration,
        expected_revision=workspace.revision).workspace_change.workspace
    workspace = append_match_capture_plays_v1(workspace, match_position=3,
        entries=tuple(_entry(card) for _, card in facts.plays),
        expected_revision=workspace.revision).workspace_change.workspace
    assert project_unplayed_cards(project_match_trick_progress(workspace, 3),
                                  workspace.slots[2].observed_game.declaration) == summary


@pytest.mark.parametrize("count", (0, 1, 28, 29, 30))
@pytest.mark.parametrize("ended", (False, True))
def test_bounded_prefixes_and_shortened_ending(complete, count, ended):
    data = build_historical_input(hand_game=True)
    data["tricks"] = data["tricks"][:(count + 2) // 3]
    if count % 3:
        data["tricks"][-1]["plays"] = data["tricks"][-1]["plays"][:count % 3]
    if count < 30:
        data.update(game_end_reason="defender_concession", game_end={"schema_version": 1,
            "kind": "defender_concession", "conceding_defender_player_id": "player-a",
            "concession_form": "explicit_verbal"})
    facts = replay_session_state_v1(_complete_retrospective_session(data))
    if not ended:
        facts = replace(facts, game_end_reason=None, game_end=None, phase="play")
    summary = project_unplayed_cards(project_session_trick_progress(facts), facts.declaration)
    assert (summary is not None) == (count == 30)


@pytest.mark.parametrize("recorded", (None, ("SK",), ("SQ", "SK")))
@pytest.mark.parametrize("original", (None, ("D8",), ("D8", "D7"), ("HQ", "D8")))
def test_source_sets_remain_separate_and_partial_input_is_not_exact(complete, recorded, original):
    summary = project_unplayed_cards(project_session_trick_progress(complete), complete.declaration)
    html = render_unplayed_cards(summary, "en", original_skat=original, discarded_cards=recorded)
    visible = re.sub(r"<[^>]+>", "", html)
    assert summary.cards == ("SK", "SQ")
    assert "Original Skat" in html and "Discarded Cards" in html
    assert visible.count("(SQ)") == 1
    assert visible.count("(SK)") == 1
    assert "Recorded input" not in html
    assert (text("en", "unplayed.derived") in html) == (recorded != ("SQ", "SK"))
    if recorded:
        assert text("en", "unplayed.recorded") in html
    if original is None:
        assert '<strong>Original Skat</strong>: Not recorded' in html
    else:
        assert all(f"({card})" in html for card in original)


def test_known_empty_hand_discards_and_exact_skat_display_once():
    facts = complete_facts(hand_game=True)
    summary = project_unplayed_cards(project_session_trick_progress(facts), facts.declaration)
    html = render_unplayed_cards(summary, "en", original_skat=("D7", "D8"), discarded_cards=())
    visible = re.sub(r"<[^>]+>", "", html)
    assert visible.count("(D8)") == visible.count("(D7)") == 1
    assert " — Recorded</p>" in html and "No discards in a Hand game" in html


@pytest.mark.parametrize("recorded", ((), ("CA",), ("CA", "SK")))
def test_defensive_conflicting_pair_keeps_both_evidence_sources(complete, recorded):
    # These inconsistent display inputs are not presented as successful canonical entry.
    summary = project_unplayed_cards(project_session_trick_progress(complete), complete.declaration)
    html = render_unplayed_cards(summary, "en", original_skat=None, discarded_cards=recorded)
    assert text("en", "unplayed.conflict") in html
    assert text("en", "unplayed.recorded_input") in html
    assert text("en", "unplayed.derived") in html
    assert all(f"({card})" in html for card in (*recorded, *summary.cards))
    assert (text("en", "task.known_empty") in html) == (recorded == ())


def test_accepted_original_skat_may_overlap_discards_without_merging_sources():
    from test_observed_game_contracts import build_observed_record, observed_plays_from_historical
    facts = complete_facts()
    record = build_observed_record(declarer_player_id="player-b", declaration=facts.declaration,
        original_skat=("SK", "D8"), discarded_cards=("SK", "SQ"),
        plays=observed_plays_from_historical(build_historical_input()))
    summary = project_unplayed_cards(project_session_trick_progress(facts), facts.declaration)
    html = render_unplayed_cards(summary, "en", original_skat=record.original_skat,
                                discarded_cards=record.discarded_cards)
    assert re.sub(r'<[^>]+>', '', html).count("(SK)") == 2  # Two different recorded facts.
    assert text("en", "unplayed.conflict") not in html
    assert text("en", "unplayed.derived") not in html


def test_different_legitimate_original_skat_same_plays_and_readonly_no_rules(complete, monkeypatch):
    from test_observed_game_contracts import build_observed_record, observed_plays_from_historical

    import skatmind.rules as rules
    import skatmind.session_transitions as transitions
    data = build_historical_input()
    records = tuple(build_observed_record(declarer_player_id="player-b",
        declaration=complete.declaration, original_skat=skat, discarded_cards=("SK", "SQ"),
        plays=observed_plays_from_historical(data)) for skat in (("D8", "D7"), ("HQ", "D8")))
    assert records[0].plays == records[1].plays
    progress = project_session_trick_progress(complete)
    def forbidden(*args, **kwargs):
        pytest.fail("The summary must use retained facts, not rules or replay")
    monkeypatch.setattr(rules, "get_legal_cards", forbidden)
    monkeypatch.setattr(transitions, "replay_session_state_v1", forbidden)
    for record in records:
        before = record.to_dict()
        summary = project_unplayed_cards(progress, record.declaration)
        assert summary.cards == ("SK", "SQ")
        render_unplayed_cards(summary, "en", original_skat=record.original_skat,
                              discarded_cards=record.discarded_cards)
        assert record.to_dict() == before


def test_complete_session_correction_uses_actual_partial_suffix_not_candidate_length():
    from test_recorded_trick_progress import progress_data

    from skatmind.session_history import correct_session_command_v1
    from skatmind.session_history_contracts import SessionCommandCorrectionV1
    data = progress_data()
    state = live_from_data(data)
    start = state.revision
    for trick in data["tricks"]:
        for play in trick["plays"]:
            state = _apply(state, RecordSessionPlayCommandV1(
                expected_revision=state.revision, **play))
    facts = replay_session_state_v1(state)
    summary = project_unplayed_cards(project_session_trick_progress(facts), facts.declaration)
    assert summary.cards == ("HA", "D10")
    corrected = correct_session_command_v1(state, SessionCommandCorrectionV1(
        expected_revision=state.revision, target_revision=start + 2,
        replacement_command=RecordSessionPlayCommandV1(expected_revision=start + 1,
            player_id="player-b", card="SJ")))
    assert corrected.status == "partial"
    facts = replay_session_state_v1(corrected.state)
    assert facts.played_card_count == 3
    assert project_unplayed_cards(project_session_trick_progress(facts), facts.declaration) is None


def test_empty_passed_and_undeclared_slots():
    from test_match_workspace_contracts import _definition

    from skatmind.match_capture_application import mark_match_capture_passed_deal_v1
    from skatmind.match_workspace_contracts import create_match_workspace_v1
    workspace = create_match_workspace_v1(_definition())
    assert project_unplayed_cards(project_match_trick_progress(workspace, 1), None) is None
    workspace = mark_match_capture_passed_deal_v1(workspace, match_position=1,
        expected_revision=0, game_timecode=None).workspace_change.workspace
    assert project_unplayed_cards(project_match_trick_progress(workspace, 1), None) is None
    assert project_unplayed_cards(project_match_trick_progress(match_trace(), 3), None) is None


@pytest.mark.parametrize("hand", (False, True))
@pytest.mark.parametrize("known_skat,known_discards", (
    (False, False), (False, True), (True, False), (True, True),
))
def test_accepted_match_recorded_evidence_and_readiness_survive_projection_and_rewind(
    hand, known_skat, known_discards,
):
    from test_match_capture_game_updates import _entry

    from skatmind.match_capture_application import (
        append_match_capture_plays_v1,
        set_match_capture_declaration_v1,
        set_match_capture_discarded_cards_v1,
        set_match_capture_original_skat_v1,
        truncate_match_capture_plays_v1,
    )
    from skatmind.observed_game_evidence import build_observed_game_evidence_summary_v1
    data = build_historical_input(hand_game=hand)
    workspace = match_trace()
    workspace = set_match_capture_declaration_v1(workspace, match_position=3,
        declarer_player_id="player-b", declaration=GameDeclaration(**data["declaration"]),
        expected_revision=workspace.revision).workspace_change.workspace
    for known, setter, cards in (
        (known_skat, set_match_capture_original_skat_v1, ("D8", "D7")),
        (known_discards, set_match_capture_discarded_cards_v1, () if hand else ("SK", "SQ")),
    ):
        if known:
            workspace = setter(workspace, match_position=3, cards=cards,
                expected_revision=workspace.revision).workspace_change.workspace
    workspace = append_match_capture_plays_v1(workspace, match_position=3,
        entries=tuple(_entry(p["card"]) for t in data["tricks"] for p in t["plays"]),
        expected_revision=workspace.revision).workspace_change.workspace
    game = workspace.slots[2].observed_game
    before, evidence = game.to_dict(), build_observed_game_evidence_summary_v1(game)
    summary = project_unplayed_cards(project_match_trick_progress(workspace, 3), game.declaration)
    assert summary.cards == (("D8", "D7") if hand else ("SK", "SQ"))
    render_unplayed_cards(summary, "en", original_skat=game.original_skat,
                          discarded_cards=game.discarded_cards)
    assert game.to_dict() == before
    assert build_observed_game_evidence_summary_v1(game) == evidence
    assert evidence.original_skat_known is known_skat
    assert evidence.discarded_cards_known is known_discards
    assert evidence.complete_initial_deal_reconstructable == (known_skat and known_discards)
    workspace = truncate_match_capture_plays_v1(workspace, match_position=3, target_play_count=29,
        expected_revision=workspace.revision).workspace_change.workspace
    remaining = workspace.slots[2].observed_game
    assert remaining.original_skat == game.original_skat
    assert remaining.discarded_cards == game.discarded_cards
    assert project_unplayed_cards(project_match_trick_progress(workspace, 3),
                                  remaining.declaration) is None


@pytest.mark.parametrize("fault", (
    "missing", "declaration", "status", "players", "duplicate_player", "no_declarer",
    "tricks", "incomplete", "prefix", "size", "card", "duplicate_card", "actor", "count",
    "index", "number",
))
def test_defensive_structural_guard_invents_no_pair(complete, fault):
    progress = project_session_trick_progress(complete)
    declaration = complete.declaration
    if fault == "missing":
        progress = None
    elif fault == "declaration":
        declaration = GameDeclaration(game_type="null")
    elif fault == "status":
        progress = replace(progress, status=[])
    elif fault == "players":
        progress = replace(progress, players=(None,) * 3)
    elif fault == "duplicate_player":
        progress = replace(progress, players=(progress.players[0],) * 3)
    elif fault == "no_declarer":
        progress = replace(progress, declarer_player_id=None)
    elif fault == "tricks":
        progress = replace(progress, tricks=progress.tricks[:9])
    else:
        trick = progress.tricks[-1]
        play = trick.plays[-1]
        if fault == "incomplete":
            trick = replace(trick, prefix=None)
        elif fault == "prefix":
            trick = replace(trick, prefix="not a completed prefix")
        elif fault == "size":
            trick = replace(trick, plays=trick.plays[:2])
        elif fault == "number":
            trick = replace(trick, number=9)
        else:
            values = {"card": {"card": []},
                "duplicate_card": {"card": progress.tricks[0].plays[0].card},
                "actor": {"player_id": "unknown"},
                "count": {"player_id": trick.plays[0].player_id},
                "index": {"decision_index": 29}}[fault]
            trick = replace(trick, plays=(*trick.plays[:2], replace(play, **values)))
        progress = replace(progress, tricks=(*progress.tricks[:9], trick))
    assert project_unplayed_cards(progress, declaration) is None
