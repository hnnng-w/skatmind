"""Small fake-clock lifetime tests; no Product persistence or concurrency simulation."""

from dataclasses import FrozenInstanceError, replace

import pytest

from skatmind.app_web.operation_feedback import (
    FeedbackSource,
    OperationReceipt,
    PendingOperationFeedback,
    render_operation_receipt,
)
from skatmind.app_web.operation_feedback_mapping import learning_import_message
from skatmind.session_contracts import SessionPlayerV1


def source():
    return FeedbackSource((object(), object()), (3, "exact-fingerprint", 2))


def publish(slot, binding, *, now=10, key="session_created"):
    attempt = slot.begin()
    slot.publish(attempt, binding, (key, ()), now=now)
    return slot.pending


@pytest.mark.parametrize("now,delivered", ((10, True), (69.999, True), (70, False), (71, False)))
def test_monotonic_delivery_deadline_and_single_read(now, delivered):
    slot, binding = PendingOperationFeedback(), source()
    receipt = publish(slot, binding)
    assert (slot.take(binding, now=now) is receipt) == delivered
    assert slot.take(binding, now=now) is None


def test_replacement_and_late_old_publication_are_not_a_queue():
    slot, binding = PendingOperationFeedback(), source()
    old = slot.begin()
    current = slot.begin()
    slot.publish(current, binding, ("declaration", ()), now=12)
    receipt = slot.pending
    slot.publish(old, binding, ("details", ()), now=13)
    assert slot.take(binding, now=15) is receipt
    assert receipt.expires_at == 72


@pytest.mark.parametrize("change", ("identity", "content", "generation", "game"))
def test_exact_source_mismatch_discards_receipt(change):
    slot, binding = PendingOperationFeedback(), source()
    publish(slot, binding)
    current = (replace(binding, references=(object(), binding.references[1]))
        if change == "identity" else
        replace(binding, references=(binding.references[0], object())) if change == "content" else
        replace(binding, values=(4, "exact-fingerprint", 2)) if change == "generation" else
        replace(binding, values=(3, "exact-fingerprint", 1)))
    assert slot.take(current, now=15) is None
    assert slot.take(binding, now=15) is None


def test_family_isolation_and_warning_priority():
    session, match, learning = (PendingOperationFeedback() for _ in range(3))
    binding = source()
    for slot in (session, match, learning):
        publish(slot, binding)
    assert session.take(binding, now=20, suppressed=True) is None
    assert match.take(binding, now=20) is not None
    assert learning.pending is not None
    learning.begin()  # A rejected/no-op/new relevant attempt supersedes old success.
    assert learning.take(binding, now=20) is None


@pytest.mark.parametrize("key,parameters", (
    ("feedback.unknown", ()), ("session_created", ()),
    ("feedback.initial_cards", (("count", 11), ("player", "raw-private-id"))),
    ("feedback.play", (("card", "invalid"), ("player", 1))),
    ("feedback.play", (("card", "CK"), ("player", True))),
    ("feedback.initial_cards", (("count", 31), ("player", 1))),
    ("feedback.game_passed", (("number", 37),)),
    ("feedback.details", (("path", "private"),)),
))
def test_only_finite_keys_and_bounded_parameters(key, parameters):
    with pytest.raises(ValueError):
        OperationReceipt(key, parameters, object(), source(), 70)


@pytest.mark.parametrize("locale", ("de", "en"))
def test_pure_render_resolves_full_accepted_label_and_localized_card(locale):
    label = '<A & "B">' + "LongName" * 30
    player = SessionPlayerV1(player_id="private-id", player_label=label, seat="forehand")
    receipt = OperationReceipt("feedback.play", (("card", "CK"), ("player", 1)),
                               object(), source(), 70)
    first = render_operation_receipt(receipt, locale, (player,))
    assert first == render_operation_receipt(receipt, locale, (player,))
    assert '&lt;A &amp; &quot;B&quot;&gt;' + "LongName" * 30 in first
    assert "private-id" not in first and "CK recorded" not in first
    assert first.count('role="status"') == 1 and 'aria-live="polite"' in first
    assert '<button' not in first and 'autofocus' not in first
    with pytest.raises(FrozenInstanceError):
        receipt.message_key = "feedback.details"


def test_real_partial_session_correction_keeps_actionable_retained_outcome(tmp_path):
    from test_session_history import _promoted_private_suffix_state

    from skatmind.app_web.session_frontend import (
        correct_guided_session_command_v1,
        import_guided_session_v1,
    )
    from skatmind.app_web.task_first_session_rendering import render_task_first_session_v1
    from skatmind.app_web.translation_catalog import translate_frontend_message_v1
    from skatmind.session_commands import SetSessionGameMetadataCommandV1
    from skatmind.session_history_contracts import SessionCommandCorrectionV1
    from skatmind.session_persistence_codec import build_session_persistence_document_v1

    state = _promoted_private_suffix_state(second_opponent_card=True)
    active = import_guided_session_v1(tmp_path, handle="a" * 64,
        document=build_session_persistence_document_v1(state).to_dict())
    operation = correct_guided_session_command_v1(active, SessionCommandCorrectionV1(
        expected_revision=state.revision, target_revision=2,
        replacement_command=SetSessionGameMetadataCommandV1(
            expected_revision=1, game_id="without-promotion")))
    assert operation.status == "partial" and operation.diagnostics
    assert active.last_operation is operation and active.state.revision == 2
    assert active.operation_feedback.pending is None
    before = active.path.read_bytes()
    for locale in ("de", "en"):
        rendered = render_task_first_session_v1(active, locale=locale)
        assert translate_frontend_message_v1(locale, "task.operation.partial") in rendered
        assert "data-operation-feedback" not in rendered
    assert active.path.read_bytes() == before


@pytest.mark.parametrize("status,relation", (("unknown", "new_match"),
    ("unchanged", "duplicate_snapshot"), ("resolution_required", "same_revision_content_conflict"),
    ("applied", "unknown")))
def test_import_outcomes_never_fall_through_to_new_version(status, relation):
    assert learning_import_message(status, relation, "select_imported") is None
