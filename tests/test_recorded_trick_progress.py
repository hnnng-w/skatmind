from dataclasses import FrozenInstanceError, replace

import pytest
from test_match_capture_game_updates import _entry, _start
from test_match_workspace_contracts import _definition

from skatmind.app_web.recorded_trick_progress import (
    project_match_trick_progress,
    project_session_trick_progress,
)
from skatmind.game_declaration import GameDeclaration
from skatmind.match_capture_application import (
    append_match_capture_plays_v1,
    set_match_capture_declaration_v1,
)
from skatmind.match_workspace_contracts import create_match_workspace_v1

# Independently counted Grand prefixes: CA/SK/H9=15, C10/SQ/H8=13,
# CK/SJ/H7=6 to B, S9/DA/SA=22 to A, then 7, 6, 3, 10, 4, 13 to A.
GRAND_PREFIXES = (
    ((0, 0), (0, 0), (0, 0)),
    ((1, 15), (0, 0), (0, 0)),
    ((2, 28), (0, 0), (0, 0)),
    ((2, 28), (1, 6), (0, 0)),
    ((3, 50), (1, 6), (0, 0)),
    ((4, 57), (1, 6), (0, 0)),
    ((5, 63), (1, 6), (0, 0)),
    ((6, 66), (1, 6), (0, 0)),
    ((7, 76), (1, 6), (0, 0)),
    ((8, 80), (1, 6), (0, 0)),
    ((9, 93), (1, 6), (0, 0)),
)


def progress_data():
    from test_historical_game import build_historical_input

    from skatmind.deck import get_full_deck
    return build_historical_input(hand_game=True, declarer_player_id="player-a", bid_value=24,
        deck=[c for c in get_full_deck() if c not in {"HA", "D10"}] + ["HA", "D10"])


def live_from_data(data, perspective="player-a"):
    from test_session_transitions import _apply, _deal_card

    from skatmind.session_commands import (
        SetSessionDeclarationCommandV1,
        SetSessionDeclarerCommandV1,
    )
    from skatmind.session_contracts import SessionPlayerV1
    from skatmind.session_transitions import create_session_state_v1
    state = create_session_state_v1(session_id="progress-session", capture_mode="live",
        local_player_id=perspective, players=tuple(SessionPlayerV1(player_id=p["player_id"],
            player_label=p.get("player_label"), seat=p["seat"]) for p in data["players"]))
    for card in next(p["initial_hand"] for p in data["players"] if p["player_id"] == perspective):
        state = _deal_card(state, destination="player_hand", player_id=perspective, card=card)
    state = _apply(state, SetSessionDeclarerCommandV1(expected_revision=state.revision,
        declarer_player_id=data["declarer_player_id"]))
    return _apply(state, SetSessionDeclarationCommandV1(expected_revision=state.revision,
        declaration=GameDeclaration(**data["declaration"])))


def match_trace(cards=(), *, game_type="grand", position=3, declarer="player-a",
                perspective="player-a"):
    workspace = create_match_workspace_v1(_definition(perspective_player_id=perspective))
    workspace = _start(workspace, position=position).workspace_change.workspace
    workspace = set_match_capture_declaration_v1(workspace, match_position=position,
        declarer_player_id=declarer,
        declaration=GameDeclaration(game_type=game_type, hand_game=True),
        expected_revision=workspace.revision).workspace_change.workspace
    if cards:
        workspace = append_match_capture_plays_v1(workspace, match_position=position,
            entries=tuple(_entry(card) for card in cards),
            expected_revision=workspace.revision).workspace_change.workspace
    return workspace


def totals(prefix):
    return tuple((value.tricks, value.points) for _, value in prefix.players)


@pytest.mark.parametrize("count", range(7))
def test_exact_prefixes_credit_winner_not_contributor_and_ignore_incomplete(count):
    # Grand: SJ beats HJ and DJ (6); B leads C7/C8/C9, A wins a zero-point Trick.
    workspace = match_trace("HJ SJ DJ C7 C8 C9".split()[:count])
    view = project_match_trick_progress(workspace, 3)
    expected = ((0, 0), (0, 0), (0, 0)) if count < 3 else (
        ((0, 0), (1, 6), (0, 0)) if count < 6 else ((1, 0), (1, 6), (0, 0)))
    assert totals(view.latest) == expected
    assert sum(v.tricks for _, v in view.latest.players) == count // 3
    assert sum(v.points for _, v in view.latest.players) == (0 if count < 3 else 6)
    assert len(view.tricks) == (count + 2) // 3
    if count >= 3:
        assert totals(view.tricks[0].prefix) == ((0, 0), (1, 6), (0, 0))
    if count > 3:
        assert view.tricks[1].plays[0].player_id == "player-b"
    if count % 3:
        assert view.tricks[-1].winner_player_id is view.tricks[-1].points is None
        assert view.tricks[-1].prefix is None
    assert view == project_match_trick_progress(workspace, 3)
    with pytest.raises(FrozenInstanceError):
        view.latest.players[0][1].points = 99


@pytest.mark.parametrize("game_type,cards,winner,points", (
    ("hearts", "HA H10 CJ", 2, 23),
    ("grand", "HA H10 HJ", 2, 23),
    ("null", "C10 CJ CQ", 2, 15),
    ("null", "HJ SJ DJ", 0, 6),
))
@pytest.mark.parametrize("position,order", (
    (1, ("player-b", "player-c", "player-a")),
    (2, ("player-c", "player-a", "player-b")),
    (3, ("player-a", "player-b", "player-c")),
))
@pytest.mark.parametrize("declarer", ("player-a", "player-b", "player-c"))
def test_rules_rotation_and_party_identity(
    game_type, cards, winner, points, position, order, declarer,
):
    for perspective in order:
        view = project_match_trick_progress(match_trace(cards.split(), game_type=game_type,
            position=position, declarer=declarer, perspective=perspective), position)
        assert tuple(p.player_id for p in view.players) == order
        assert tuple(p.seat for p in view.players) == ("forehand", "middlehand", "rearhand")
        assert view.tricks[0].winner_player_id == order[winner]
        assert totals(view.latest) == tuple(
            (1, points) if i == winner else (0, 0) for i in range(3))
        won = declarer == order[winner]
        assert (view.latest.declarer.tricks, view.latest.declarer.points) == (
            (1, points) if won else (0, 0))
        assert (view.latest.defenders.tricks, view.latest.defenders.points) == (
            (0, 0) if won else (1, points))


def test_session_adapter_consumes_existing_replay_without_rules_or_replay(monkeypatch):
    from test_historical_game import build_historical_input
    from test_session_transitions import _complete_retrospective_session

    import skatmind.rules as rules
    import skatmind.session_transitions as transitions
    facts = transitions.replay_session_state_v1(
        _complete_retrospective_session(build_historical_input(hand_game=True)))
    def forbidden(*args, **kwargs):
        pytest.fail("The Session progress adapter must consume retained facts")
    monkeypatch.setattr(transitions, "replay_session_state_v1", forbidden)
    monkeypatch.setattr(rules, "get_trick_winner", forbidden)
    view = project_session_trick_progress(facts)
    assert view.completed_count == 10 and len(view.tricks) == 10 and view.status == "ended"
    # The adapter doesn't use private hands/Skat or settlement values.
    assert project_session_trick_progress(replace(facts, known_skat=(),
        initial_known_hands=(), remaining_known_hands=())) == view
    assert "known_skat" not in repr(view) and "playable_hands" not in repr(view)


@pytest.mark.parametrize("declarer", ("player-a", "player-b", "player-c"))
@pytest.mark.parametrize("perspective", ("player-a", "player-b", "player-c"))
def test_session_every_accepted_boundary_and_independent_party_prefix(declarer, perspective):
    from test_session_transitions import _apply

    from skatmind.session_commands import RecordSessionPlayCommandV1
    from skatmind.session_transitions import replay_session_state_v1
    data = progress_data()
    data["declarer_player_id"] = declarer
    state = live_from_data(data, perspective)
    plays = [p for trick in data["tricks"] for p in trick["plays"]]
    for count in range(31):
        facts = replay_session_state_v1(state)
        view = project_session_trick_progress(facts)
        expected = GRAND_PREFIXES[count // 3]
        assert totals(view.latest) == expected
        own = expected[("player-a", "player-b", "player-c").index(declarer)]
        assert (view.latest.declarer.tricks, view.latest.declarer.points) == own
        assert view.latest.defenders.tricks == count // 3 - own[0]
        assert view.latest.defenders.points == sum(v[1] for v in expected) - own[1]
        assert sum(v.tricks for _, v in view.latest.players) == count // 3
        for index, trick in enumerate(view.tricks[:count // 3], 1):
            assert totals(trick.prefix) == GRAND_PREFIXES[index]
        if count == 30:
            assert len(view.tricks) == 10 and view.status == "complete"
            assert state.phase == "play" and facts.game_end_reason is None
        else:
            state = _apply(state, RecordSessionPlayCommandV1(expected_revision=state.revision,
                player_id=plays[count]["player_id"], card=plays[count]["card"]))


@pytest.mark.parametrize("count", (0, 1, 2, 3, 5, 29, 30))
def test_known_skat_and_authorized_hands_do_not_change_public_totals(count):
    from test_session_transitions import _apply, _retrospective_before_play

    from skatmind.match_capture_application import set_match_capture_original_skat_v1
    from skatmind.session_commands import RecordSessionPlayCommandV1
    from skatmind.session_transitions import replay_session_state_v1
    data = progress_data()
    state = _retrospective_before_play(data)
    plays = [p for trick in data["tricks"] for p in trick["plays"]][:count]
    for play in plays:
        state = _apply(state, RecordSessionPlayCommandV1(expected_revision=state.revision, **play))
    view = project_session_trick_progress(replay_session_state_v1(state))
    assert totals(view.latest) == GRAND_PREFIXES[count // 3]
    workspace = match_trace([p["card"] for p in plays])
    unknown = project_match_trick_progress(workspace, 3)
    workspace = set_match_capture_original_skat_v1(workspace, match_position=3,
        cards=("HA", "D10"), expected_revision=workspace.revision).workspace_change.workspace
    known = project_match_trick_progress(workspace, 3)
    assert known == unknown
    assert totals(known.latest) == GRAND_PREFIXES[count // 3]
    assert sum(v.points for _, v in known.latest.players) <= 99


@pytest.mark.parametrize("count", (0, 1, 2, 3, 5, 29))
def test_shortened_end_counts_only_observed_complete_tricks(count):
    from test_session_transitions import _complete_retrospective_session

    from skatmind.app_web.recorded_trick_rendering import render_recorded_history
    from skatmind.session_transitions import replay_session_state_v1
    data = progress_data()
    data["tricks"] = data["tricks"][:(count + 2) // 3]
    if count % 3:
        data["tricks"][-1]["plays"] = data["tricks"][-1]["plays"][:count % 3]
    data.update(game_end_reason="defender_concession", game_end={"schema_version": 1,
        "kind": "defender_concession", "conceding_defender_player_id": "player-b",
        "concession_form": "explicit_verbal"})
    view = project_session_trick_progress(
        replay_session_state_v1(_complete_retrospective_session(data)))
    assert view.status == "ended" and totals(view.latest) == GRAND_PREFIXES[count // 3]
    if count % 3:
        assert view.tricks[-1].prefix is None
        assert "Recording ended with an incomplete trick" in render_recorded_history(view, "en")


def test_partial_session_correction_uses_actual_retained_suffix_and_undo():
    from test_session_transitions import _apply

    from skatmind.session_commands import RecordSessionPlayCommandV1
    from skatmind.session_history import correct_session_command_v1, rewind_session_state_v1
    from skatmind.session_history_contracts import SessionCommandCorrectionV1
    from skatmind.session_transitions import replay_session_state_v1
    state = live_from_data(progress_data())
    start = state.revision
    for play in [p for t in progress_data()["tricks"] for p in t["plays"]][:6]:
        state = _apply(state, RecordSessionPlayCommandV1(expected_revision=state.revision, **play))
    # Unknown opponent's SK -> SJ wins Trick 1, so the old A lead at Play 4 rejects.
    result = correct_session_command_v1(state, SessionCommandCorrectionV1(
        expected_revision=state.revision, target_revision=start + 2,
        replacement_command=RecordSessionPlayCommandV1(expected_revision=start + 1,
            player_id="player-b", card="SJ")))
    assert result.status == "partial"
    facts = replay_session_state_v1(result.state)
    assert facts.played_card_count == 3
    view = project_session_trick_progress(facts)
    assert totals(view.latest) == ((0, 0), (1, 13), (0, 0))
    assert view.tricks[0].winner_player_id == "player-b"
    undone = rewind_session_state_v1(result.state, expected_revision=result.state.revision,
                                     target_revision=start + 2)
    view = project_session_trick_progress(replay_session_state_v1(undone.state))
    assert totals(view.latest) == GRAND_PREFIXES[0] and len(view.tricks[0].plays) == 2


def test_warning_and_unknown_party_and_unplayed_slot_statuses():
    from skatmind.app_web.recorded_trick_rendering import render_recorded_summary
    from skatmind.match_capture_application import mark_match_capture_passed_deal_v1
    from skatmind.session_commands import SetSessionDeclarationCommandV1
    from skatmind.session_history import rewind_session_state_v1
    from skatmind.session_transitions import apply_session_command_v1, replay_session_state_v1
    workspace = match_trace("SA H7 S7 CA S8".split())
    view = project_match_trick_progress(workspace, 3)
    assert view.warning.play_index == 2 and view.warning.witness_index == 5
    assert totals(view.latest) == ((1, 11), (0, 0), (0, 0))
    assert 'href="#match-play-2"' in render_recorded_summary(view, "en")
    workspace = create_match_workspace_v1(_definition())
    empty = project_match_trick_progress(workspace, 1)
    assert empty.status == "empty" and empty.latest is None and empty.tricks == ()
    started = _start(workspace).workspace_change.workspace
    assert project_match_trick_progress(started, 1).status == "undeclared"
    passed = mark_match_capture_passed_deal_v1(workspace, match_position=1,
        expected_revision=0, game_timecode=None).workspace_change.workspace
    assert project_match_trick_progress(passed, 1).status == "passed_deal"
    # A legal Session declaration can precede explicit declarer identity.
    state = live_from_data(progress_data())
    state = rewind_session_state_v1(state, expected_revision=state.revision,
                                   target_revision=10).state
    state = apply_session_command_v1(state, SetSessionDeclarationCommandV1(
        expected_revision=10, declaration=GameDeclaration(game_type="grand", hand_game=True))).state
    view = project_session_trick_progress(replay_session_state_v1(state))
    assert view.latest.declarer is view.latest.defenders is None
    assert "assignment is unknown" in render_recorded_summary(view, "en")


@pytest.mark.parametrize("locale", ("en", "de"))
def test_null_render_omits_point_metrics_and_escapes_names(locale):
    from skatmind.app_web.recorded_trick_rendering import (
        render_recorded_history,
        render_recorded_summary,
    )
    from skatmind.app_web.stateful_localization import card_name
    from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
    view = project_match_trick_progress(match_trace("C10 CJ CQ".split(), game_type="null"), 3)
    view = replace(view, players=tuple(replace(p, player_label='<script>Long & name</script>')
                                      for p in view.players))
    rendered = render_recorded_summary(view, locale) + render_recorded_history(view, locale)
    assert 'data-trick-metric="points"' not in rendered and 'data-trick-metric="tricks"' in rendered
    assert '<script>' not in rendered and '&lt;script&gt;Long &amp; name' in rendered
    assert text(locale, "trick_progress.null_scope") in rendered
    assert card_name(locale, "CJ") in rendered and '(CJ)' in rendered
    assert view.tricks[0].points == 15
