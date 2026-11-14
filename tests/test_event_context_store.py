import json
from dataclasses import replace

import pytest
from event_context_fixtures import changed_document, synthetic_context, synthetic_match

from skatmind.event_context_contracts import CheckpointV1
from skatmind.event_context_operations import (
    EventContextConflict,
    reconfirm_event_checkpoint_v1,
    set_event_checkpoint_v1,
    set_event_terms_v1,
)
from skatmind.event_context_projection import prepare_event_context_v1
from skatmind.event_context_sources import build_recording_facts_v1
from skatmind.event_context_store import (
    EVENT_CONTEXT_FILENAME,
    EventContextJournalV1,
    append_event_revision_v1,
    event_context_bytes_v1,
    load_event_context_v1,
    resume_event_context_v1,
    save_event_context_v1,
)


def fixture():
    document = synthetic_match()
    context = synthetic_context(document)
    facts = build_recording_facts_v1(document, through_position=24, decision_position=25)
    prepared = prepare_event_context_v1(context, (facts,), target=facts.source.source,
                                         game_position=25, decision_index=1)
    return document, context, prepared


def test_save_reopen_frozen_basis_survives_correction_and_unknown_original(tmp_path):
    document, context, prepared = fixture()
    empty = load_event_context_v1(tmp_path)
    assert not list(tmp_path.iterdir())  # Passive load creates no Product data.
    journal = append_event_revision_v1(empty, context, prepared=prepared)
    assert save_event_context_v1(tmp_path, journal,
                                 expected_fingerprint=empty.fingerprint) == "saved"
    original = (tmp_path / EVENT_CONTEXT_FILENAME).read_bytes()
    assert load_event_context_v1(tmp_path) == journal
    corrected = set_event_checkpoint_v1(context, replace(context.checkpoints[0],
        personal_points=-20, provenance="Explicit correction"), expected_revision=0)
    updated = append_event_revision_v1(journal, corrected)
    save_event_context_v1(tmp_path, updated, expected_fingerprint=journal.fingerprint)
    resumed = load_event_context_v1(tmp_path)
    assert resumed.preparations == (prepared,)
    assert prepared.checkpoint.personal_points == 780
    assert resumed.revisions[0] == context
    assert resumed.revisions[1] == corrected
    assert original != (tmp_path / EVENT_CONTEXT_FILENAME).read_bytes()
    assert (changed_document(document).content_fingerprint
            != prepared.target_source.content_fingerprint)
    # No current recording is required to reconstruct the exact consumed context.
    assert resume_event_context_v1(event_context_bytes_v1(resumed)) == resumed


def test_noop_stale_source_failed_write_and_append_only_history(tmp_path, monkeypatch):
    _, context, prepared = fixture()
    empty = EventContextJournalV1()
    journal = append_event_revision_v1(empty, context, prepared=prepared)
    save_event_context_v1(tmp_path, journal, expected_fingerprint=empty.fingerprint)
    original = (tmp_path / EVENT_CONTEXT_FILENAME).read_bytes()
    assert set_event_checkpoint_v1(context, context.checkpoints[0], expected_revision=0) is context
    assert save_event_context_v1(tmp_path, journal,
                                 expected_fingerprint=journal.fingerprint) == "unchanged"
    for expected, guard in ((empty.fingerprint, lambda: True),
                            (journal.fingerprint, lambda: False)):
        with pytest.raises(EventContextConflict):
            save_event_context_v1(tmp_path, journal, expected_fingerprint=expected,
                                   source_guard=guard)
    with pytest.raises(EventContextConflict):
        set_event_checkpoint_v1(context, context.checkpoints[0], expected_revision=9)
    with pytest.raises(ValueError, match="immutable"):
        save_event_context_v1(tmp_path, empty, expected_fingerprint=journal.fingerprint)
    changed = set_event_checkpoint_v1(context, replace(context.checkpoints[0], personal_points=781),
                                     expected_revision=0)
    updated = append_event_revision_v1(journal, changed)
    def fail(*_args):
        raise OSError("Synthetic replace failure")
    monkeypatch.setattr("skatmind.event_context_store.os.replace", fail)
    with pytest.raises(OSError):
        save_event_context_v1(tmp_path, updated, expected_fingerprint=journal.fingerprint)
    assert (tmp_path / EVENT_CONTEXT_FILENAME).read_bytes() == original
    assert list(tmp_path.iterdir()) == [tmp_path / EVENT_CONTEXT_FILENAME]


def test_explicit_reconfirmation_retains_disagreement_and_does_not_hide_new_backfill():
    document = synthetic_match()
    context = synthetic_context(document)
    context = set_event_checkpoint_v1(context, CheckpointV1(through_position=25,
        personal_points=999, own_losses=3, provenance="Supplied total"), expected_revision=0)
    facts = build_recording_facts_v1(document, through_position=25)
    prepared = prepare_event_context_v1(context, (facts,), target=facts.source.source,
                                         game_position=26)
    assert prepared.status == "conflict"
    reconfirmed = reconfirm_event_checkpoint_v1(context, prepared, through_position=25,
        expected_revision=1, provenance="Checked the original list; retain the supplied total")
    journal = EventContextJournalV1(revisions=(synthetic_context(document), context),
                                     preparations=(prepared,))
    journal = append_event_revision_v1(journal, reconfirmed)
    assert resume_event_context_v1(event_context_bytes_v1(journal)) == journal
    value = prepare_event_context_v1(reconfirmed, (facts,), target=facts.source.source,
                                      game_position=26)
    assert value.status == "ready" and value.personal_points == 999
    changed = replace(facts, outcomes=tuple(replace(row, settlement_score=row.settlement_score + 24)
        if row.status == "settled" else row for row in facts.outcomes))
    assert prepare_event_context_v1(reconfirmed, (changed,), target=facts.source.source,
                                    game_position=26).status == "conflict"


@pytest.mark.parametrize("mutation", ["version", "unknown", "score", "fingerprint", "history"])
def test_strict_resume_rejects_tampered_or_unreconstructable_values(mutation):
    _, context, prepared = fixture()
    journal = EventContextJournalV1(revisions=(context,), preparations=(prepared,))
    value = json.loads(event_context_bytes_v1(journal))
    if mutation == "version":
        value["version"] = True
    elif mutation == "unknown":
        value["journal"]["revisions"][0]["extra"] = "ignored?"
    elif mutation == "score":
        value["journal"]["preparations"][0]["personal_points"] = 900
    elif mutation == "fingerprint":
        value["content_fingerprint"] = "f" * 64
    else:
        value["journal"]["revisions"] = []
    with pytest.raises(ValueError):
        resume_event_context_v1(json.dumps(value).encode())


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'[]', b'\xef\xbb\xbf{}'])
def test_strict_json_rejection(raw):
    with pytest.raises(ValueError):
        resume_event_context_v1(raw)


def test_later_terms_and_factual_corrections_have_explicit_historical_applicability():
    _, context, prepared = fixture()
    financial = replace(context.terms[0].financial, currency="EUR")
    changed = set_event_terms_v1(context, replace(context.terms[0], from_position=25,
        financial=financial), expected_revision=0, correction=False, provenance="Later terms")
    assert changed.applicable_terms(12) == context.terms[0]
    assert changed.applicable_terms(25).financial.currency == "EUR"
    correction = set_event_terms_v1(changed, replace(changed.terms[0],
        scoring_source=replace(changed.terms[0].scoring_source, edition="Corrected edition")),
        expected_revision=1, correction=True, provenance="Later-entered factual correction")
    journal = EventContextJournalV1(revisions=(context, changed, correction),
                                     preparations=(prepared,))
    assert resume_event_context_v1(event_context_bytes_v1(journal)).preparations[0] == prepared
    assert prepared.terms.scoring_source.edition == "1"


def test_independent_event_and_recording_bindings_are_not_merged():
    _, context, prepared = fixture()
    binding = context.bindings[0]
    second = replace(context, event_id="second", series_id="second-series", bindings=(
        replace(binding, attached_source=replace(binding.attached_source,
            source=replace(binding.source, product_id="another-match"))),))
    journal = EventContextJournalV1(revisions=(context, second), preparations=(prepared,))
    assert journal.for_source(binding.source) == context
    with pytest.raises(ValueError, match="Duplicate"):
        EventContextJournalV1(revisions=(context, replace(second, bindings=context.bindings)))


def test_frozen_derived_contribution_survives_overwritten_recording_after_restart(tmp_path):
    from test_match_workspace_contracts import _observed_game, _set_game

    from skatmind.game_declaration import GameDeclaration
    from skatmind.match_workspace_operations import clear_match_workspace_slot_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )
    from skatmind.observed_game_trace import ObservedPlayV1

    original = synthetic_match()
    game = _observed_game(original.workspace.match_definition, match_position=26,
        game_timecode=None, declarer_player_id="player-a",
        declaration=GameDeclaration(game_type="grand", bid_value=24), plays=(ObservedPlayV1(
            decision_index=1, player_id="player-c", card="CA", decision_timecode=None),))
    document = build_match_workspace_persistence_document_v1(_set_game(original.workspace, game))
    context = synthetic_context(document)
    facts = build_recording_facts_v1(document, through_position=25, decision_position=26)
    prepared = prepare_event_context_v1(context, (facts,), target=facts.source.source,
                                         game_position=26, decision_index=1)
    assert prepared.personal_points == 820 and prepared.own_losses == 3
    assert prepared.target_game_id == "observed-game-26"
    empty = EventContextJournalV1()
    journal = append_event_revision_v1(empty, context, prepared=prepared)
    save_event_context_v1(tmp_path, journal, expected_fingerprint=empty.fingerprint)
    corrected = clear_match_workspace_slot_v1(document.workspace, match_position=25,
        expected_revision=document.workspace.revision).workspace
    current = build_recording_facts_v1(build_match_workspace_persistence_document_v1(corrected),
        through_position=25, decision_position=26)
    current_value = prepare_event_context_v1(context, (current,), target=facts.source.source,
                                             game_position=26, decision_index=1)
    assert current_value.personal_points == 780 and current_value.status == "incomplete"
    frozen = load_event_context_v1(tmp_path).preparations[0]
    assert frozen == prepared
    assert frozen.basis[24].fact.settlement_score < 0
    assert frozen.basis[24].contribution(context) == (40, 0)


def test_confirmed_pool_prize_and_exact_amount_facts_survive_without_filling_unknowns():
    from skatmind.event_context_contracts import (
        AmountV1,
        FinancialFactsV1,
        PoolFactV1,
        RuleSourceV1,
    )

    document, context, _ = fixture()
    financial = FinancialFactsV1(currency="EUR", entry_paid=AmountV1.parse("5.00"),
        table_paid=AmountV1.parse("0.75"), table_committed=AmountV1.parse("0"),
        pools=(PoolFactV1(pool_id="confirmed-base-pool", participation="yes"),),
        payout_source=RuleSourceV1(reference="Supplied event notice", edition="confirmed-copy-1"),
        prize_facts="First place EUR 20; other places not supplied.", prize_completeness="partial",
        provenance="Confirmed synthetic receipt and partial notice")
    context = replace(context, terms=(replace(context.terms[0], financial=financial),))
    facts = build_recording_facts_v1(document, through_position=24, decision_position=25)
    prepared = prepare_event_context_v1(context, (facts,), target=facts.source.source,
                                         game_position=25, decision_index=1)
    journal = EventContextJournalV1(revisions=(context,), preparations=(prepared,))
    resumed = resume_event_context_v1(event_context_bytes_v1(journal)).preparations[0]
    assert resumed.status == "ready"
    assert resumed.terms.financial == financial
    assert resumed.terms.financial.entry_committed is None
    assert resumed.terms.financial.pools[0].entitlement == "unknown"
    assert resumed.terms.financial.table_committed == AmountV1(numerator=0)
    assert "prize_facts" in resumed.financial_missing
