"""Private adapter edge coverage reusing canonical legality fixtures."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from test_historical_defender_open_play_continuation import build_event_record
from test_historical_game import build_historical_input
from test_session_history import _public_hand_with_plays_state
from test_session_transitions import _complete_retrospective_session

import skatmind.api.v1.session as api
from skatmind.app_web.compact_declaration_form import explicit_declaration_values
from skatmind.app_web.session_declaration_correction import (
    accepted_record,
    apply_correction,
    correction_entries,
    preview_correction,
    select_correction,
)
from skatmind.app_web.session_declaration_correction_rendering import render_session_correction
from skatmind.app_web.session_frontend import import_guided_session_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text


def context(tmp_path, state):
    return import_guided_session_v1(tmp_path, handle="a" * 64,
        document=api.build_session_persistence_document(state).value.to_dict())


def choose(active, kind="set_declaration"):
    entry, = [s for s in correction_entries(active) if s.record.command.kind == kind]
    select_correction(active, entry.token)
    return active.declaration_correction.selected


def test_missing_and_ambiguous_records_do_not_choose_arbitrarily():
    record = SimpleNamespace(command=SimpleNamespace(kind="set_declarer"))
    for records in ((), (record, record)):
        source = SimpleNamespace(state=SimpleNamespace(command_log=records))
        assert accepted_record(source, "set_declarer") is None


def test_declaration_can_precede_declarer_and_prefill_is_exact_command(tmp_path):
    state = _complete_retrospective_session(build_historical_input(hand_game=True))
    declaration = next(r for r in state.command_log if r.command.kind == "set_declaration")
    declarer = next(r for r in state.command_log if r.command.kind == "set_declarer")
    # Canonical replay of swapped fact order, not a forged projection.
    current = api.create_session(session_id=state.session_id, players=state.players,
        capture_mode=state.initial_capture_mode, local_player_id=state.local_player_id).value
    for record in state.command_log:
        command = (declaration.command if record is declarer else
                   declarer.command if record is declaration else record.command)
        result = api.apply_session_command(current,
            replace(command, expected_revision=current.revision)).value
        assert result.status == "applied"
        current = result.state
    active = context(tmp_path, current)
    selected = choose(active)
    assert selected.record.command.declaration == declaration.command.declaration
    assert len(correction_entries(active)) == 2
    assert selected.record.revision < accepted_record(active, "set_declarer").revision
    replacement = replace(selected.record.command,
        declaration=replace(selected.record.command.declaration, bid_value=20))
    preview = preview_correction(active, selected, replacement)
    assert preview.status == "applied" and preview.state.phase == "ended"
    assert len([r for r in preview.replayed_suffix_records
                if r.command.kind == "record_play"]) == 30
    assert explicit_declaration_values(selected.record.command.declaration)["matadors"] == ""


def test_public_hand_removal_and_end_remain_inspectable(tmp_path):
    active = context(tmp_path, _public_hand_with_plays_state())
    selected = choose(active)
    original = selected.record.command
    result = preview_correction(active, selected, replace(original,
        declaration=replace(original.declaration, ouvert=False)))
    assert result.status == "partial"
    assert [r.command.kind for r in result.discarded_suffix_records] == [
        "set_public_hand", "record_play", "record_play"]
    for locale in ("de", "en"):
        page = render_session_correction(active, locale)
        assert text(locale, "session.correction.removal", plays=2, other=1) in page
        assert text(locale, "task.command.set_public_hand") in page
    before = active.path.read_bytes()
    assert active.path.read_bytes() == before


@pytest.mark.parametrize("event", (False, True))
def test_hand_change_removes_discards_and_complete_ending_without_salvage(tmp_path, event):
    source = build_event_record(after_play_count=12) if event else build_historical_input()
    active = context(tmp_path, _complete_retrospective_session(source))
    before = active.path.read_bytes()
    selected = choose(active)
    command = selected.record.command
    result = preview_correction(active, selected, replace(command,
        declaration=replace(command.declaration, hand_game=True)))
    assert result.status == "partial" and result.state.phase == "play"
    kinds = [r.command.kind for r in result.discarded_suffix_records]
    assert kinds[0] == "record_discard" and kinds[-1] == "set_game_end"
    assert kinds.count("record_discard") == 2 and kinds.count("record_play") == 30
    assert kinds.count("set_game_event") == int(event)
    for locale in ("de", "en"):
        page = render_session_correction(active, locale)
        assert text(locale, "task.value.normal_completion") in page
        assert text(locale, "session.correction.removal", plays=30, other=3 + int(event)) in page
    assert active.path.read_bytes() == before
    with active.lock:
        outcome = apply_correction(active, active.declaration_correction.preview.apply_token)
        assert outcome.status == "partial"
    assert active.state == result.state
