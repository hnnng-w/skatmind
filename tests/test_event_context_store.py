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
    EventContextJournalV2,
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


def test_explicit_platform_terms_roundtrip_without_rewriting_legacy_frozen_basis(tmp_path):
    from skatmind.event_context_contracts import EventTermsV1

    document, context, prepared = fixture()
    legacy = context.terms[0].to_dict()
    assert "platform" not in legacy and legacy["version"] == 1
    assert EventTermsV1.from_dict(legacy).to_dict() == legacy
    empty = load_event_context_v1(tmp_path)
    original = append_event_revision_v1(empty, context, prepared=prepared)
    term = replace(context.terms[0], version=2, platform="euroskat")
    corrected = set_event_terms_v1(context, term, expected_revision=0, correction=True,
                                   provenance="Explicit actual platform selection")
    current = append_event_revision_v1(original, corrected)
    save_event_context_v1(tmp_path, current, expected_fingerprint=empty.fingerprint)
    restored = load_event_context_v1(tmp_path)
    assert restored == current and restored.preparations == (prepared,)
    assert restored.revisions[0].terms[0].to_dict() == legacy
    assert restored.heads[0].terms[0].platform == "euroskat"
    for invalid in ({**legacy, "platform": "euroskat"},
                    {**term.to_dict(), "version": 1},
                    {k: v for k, v in term.to_dict().items() if k != "platform"},
                    {**term.to_dict(), "platform": "name-inferred"},
                    {**term.to_dict(), "version": True}):
        with pytest.raises(ValueError):
            EventTermsV1.from_dict(invalid)


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
    empty = EventContextJournalV2()
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
    journal = EventContextJournalV2(revisions=(synthetic_context(document), context),
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
    journal = EventContextJournalV2(revisions=(context,), preparations=(prepared,))
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
    journal = EventContextJournalV2(revisions=(context, changed, correction),
                                     preparations=(prepared,))
    assert resume_event_context_v1(event_context_bytes_v1(journal)).preparations[0] == prepared
    assert prepared.terms.scoring_source.edition == "1"


def test_independent_event_and_recording_bindings_are_not_merged():
    _, context, prepared = fixture()
    binding = context.bindings[0]
    second = replace(context, event_id="second", series_id="second-series", bindings=(
        replace(binding, attached_source=replace(binding.attached_source,
            source=replace(binding.source, product_id="another-match"))),))
    journal = EventContextJournalV2(revisions=(context, second), preparations=(prepared,))
    assert journal.for_source(binding.source) == context
    with pytest.raises(ValueError, match="Duplicate"):
        EventContextJournalV2(revisions=(context, replace(second, bindings=context.bindings)))


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
    empty = EventContextJournalV2()
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
    journal = EventContextJournalV2(revisions=(context,), preparations=(prepared,))
    resumed = resume_event_context_v1(event_context_bytes_v1(journal)).preparations[0]
    assert resumed.status == "ready"
    assert resumed.terms.financial == financial
    assert resumed.terms.financial.entry_committed is None
    assert resumed.terms.financial.pools[0].entitlement == "unknown"
    assert resumed.terms.financial.table_committed == AmountV1(numerator=0)
    assert "prize_facts" in resumed.financial_missing


def test_reconciliation_survives_genuine_later_play_but_preparation_and_cas_are_stale(tmp_path):
    from test_match_workspace_contracts import _observed_game, _set_game

    from skatmind.event_context_projection import preparation_is_current_v1
    from skatmind.game_declaration import GameDeclaration
    from skatmind.match_capture_application import append_match_capture_play_v1
    from skatmind.match_capture_application_contracts import MatchCaptureCardEntryV1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )

    original = synthetic_match()
    game = _observed_game(original.workspace.match_definition, match_position=26,
        game_timecode=None, declarer_player_id="player-a",
        declaration=GameDeclaration(game_type="grand", bid_value=24))
    document = build_match_workspace_persistence_document_v1(_set_game(original.workspace, game))
    initial = synthetic_context(document)
    context = set_event_checkpoint_v1(initial, CheckpointV1(through_position=25,
        personal_points=999, own_losses=3, provenance="Confirmed supplied total"),
        expected_revision=0)
    facts = build_recording_facts_v1(document, through_position=25)
    prepared = prepare_event_context_v1(context, (facts,), target=facts.source.source,
                                         game_position=26)
    assert prepared.status == "conflict"
    reconfirmed = reconfirm_event_checkpoint_v1(context, prepared, through_position=25,
        expected_revision=1, provenance="Rechecked the original list")
    journal = EventContextJournalV2(revisions=(initial, context), preparations=(prepared,))
    journal = append_event_revision_v1(journal, reconfirmed)
    save_event_context_v1(tmp_path, journal,
                           expected_fingerprint=EventContextJournalV2().fingerprint)
    current = prepare_event_context_v1(reconfirmed, (facts,), target=facts.source.source,
                                        game_position=26)
    changed = append_match_capture_play_v1(document.workspace, match_position=26,
        entry=MatchCaptureCardEntryV1(card="CA", decision_timecode=None),
        expected_revision=document.workspace.revision)
    assert changed.status == "applied"
    later_document = build_match_workspace_persistence_document_v1(
        changed.workspace_change.workspace)
    later = build_recording_facts_v1(later_document, through_position=25)
    assert later.outcomes == facts.outcomes
    assert later.source != facts.source
    after = prepare_event_context_v1(reconfirmed, (later,), target=facts.source.source,
                                      game_position=26)
    assert after.status == "ready"
    assert after.personal_points == 999 and after.own_losses == 3
    assert not preparation_is_current_v1(current, reconfirmed, (later,))
    assert load_event_context_v1(tmp_path).preparations == (prepared,)
    with pytest.raises(EventContextConflict):
        save_event_context_v1(tmp_path, journal, expected_fingerprint=journal.fingerprint,
                               source_guard=lambda: facts.source == later.source)


def legacy_reconciliation_journal():
    from skatmind.event_context_projection import _prepare_from_basis
    from skatmind.event_context_store import EventContextJournalV1

    document = synthetic_match()
    initial = synthetic_context(document)
    context = set_event_checkpoint_v1(initial, CheckpointV1(through_position=25,
        personal_points=999, own_losses=3, provenance="Supplied total"), expected_revision=0)
    facts = build_recording_facts_v1(document, through_position=25)
    def legacy_prepare(context, facts):
        current = prepare_event_context_v1(context, (facts,), target=facts.source.source,
                                            game_position=26)
        return _prepare_from_basis(context, current.basis, target=facts.source.source,
            target_source=facts.source, game_position=26, decision_index=None, actor=None,
            game_id=None, preparation_version=1)
    conflict = legacy_prepare(context, facts)
    confirmed = reconfirm_event_checkpoint_v1(context, conflict, through_position=25,
        expected_revision=1, provenance="Checked original list")
    ready = legacy_prepare(confirmed, facts)
    later = build_recording_facts_v1(changed_document(document), through_position=25)
    changed = legacy_prepare(confirmed, later)
    return EventContextJournalV1(revisions=(initial, context, confirmed),
        preparations=(conflict, ready, changed)), later


def test_published_v1_bytes_statuses_and_explicit_v2_transition_are_preserved(tmp_path):
    import hashlib

    from skatmind.event_context_projection import preparation_is_current_v1
    from skatmind.event_context_store import EventContextJournalV1

    old, later = legacy_reconciliation_journal()
    raw = event_context_bytes_v1(old)
    # Captured on the published starting HEAD before changing Product code.
    assert old.fingerprint == "530d4b65725f35b2ae1cd000114c73231a8a9f0e64897f54cc2b8bce25747eec"
    assert hashlib.sha256(raw).hexdigest() == (
        "badc00b3c8dbe991dc8205aefcbed9845d756c7a38ab50977ba7ec8cc4d7aa37")
    path = tmp_path / EVENT_CONTEXT_FILENAME
    path.write_bytes(raw)
    loaded = load_event_context_v1(tmp_path)
    assert type(loaded) is EventContextJournalV1
    assert [item.status for item in loaded.preparations] == ["conflict", "ready", "conflict"]
    assert save_event_context_v1(tmp_path, loaded,
        expected_fingerprint=loaded.fingerprint) == "unchanged"
    assert path.read_bytes() == raw
    context = loaded.heads[0]
    current = prepare_event_context_v1(context, (later,), target=later.source.source,
        game_position=26, acknowledgement_aliases=loaded.reconciliation_aliases)
    assert current.version == 2 and current.status == "ready"
    assert current.acknowledgement_aliases
    assert preparation_is_current_v1(current, context, (later,))
    upgraded = append_event_revision_v1(loaded, context, prepared=current)
    assert type(upgraded) is EventContextJournalV2
    assert upgraded.revisions == loaded.revisions
    assert upgraded.preparations[:-1] == loaded.preparations
    save_event_context_v1(tmp_path, upgraded, expected_fingerprint=loaded.fingerprint)
    assert load_event_context_v1(tmp_path) == upgraded
    assert event_context_bytes_v1(old) == raw
    with pytest.raises(ValueError, match="immutable"):
        save_event_context_v1(tmp_path, old, expected_fingerprint=upgraded.fingerprint)


@pytest.mark.parametrize("mutation", ("v1_status", "v1_fields", "v2_alias", "v2_version"))
def test_versioned_reconstruction_does_not_relax_frozen_validation(mutation):
    from skatmind.event_context_contracts import identity

    old, later = legacy_reconciliation_journal()
    context = old.heads[0]
    current = prepare_event_context_v1(context, (later,), target=later.source.source,
        game_position=26, acknowledgement_aliases=old.reconciliation_aliases)
    upgraded = append_event_revision_v1(old, context, prepared=current)
    data = json.loads(event_context_bytes_v1(upgraded))
    if mutation == "v1_status":
        data["journal"]["preparations"][2]["status"] = "ready"
    elif mutation == "v1_fields":
        data["journal"]["preparations"][0]["acknowledgement_aliases"] = []
    elif mutation == "v2_alias":
        data["journal"]["preparations"] = [current.to_dict()]
    else:
        data["journal"]["preparations"][-1]["version"] = 3
    data["content_fingerprint"] = identity("journal_v2", data["journal"])
    with pytest.raises(ValueError):
        resume_event_context_v1(json.dumps(data).encode())


@pytest.mark.parametrize("difference", ("settlement", "mapping", "checkpoint", "rule_source"))
def test_reconciliation_requires_new_confirmation_for_relevant_comparison_changes(difference):
    from test_match_workspace_contracts import _observed_game, _set_game

    from skatmind.event_context_operations import revise_event_context_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )

    document = synthetic_match()
    context = synthetic_context(document)
    context = set_event_checkpoint_v1(context, CheckpointV1(through_position=25,
        personal_points=999, own_losses=3, provenance="Supplied total"), expected_revision=0)
    facts = build_recording_facts_v1(document, through_position=25)
    prepared = prepare_event_context_v1(context, (facts,), target=facts.source.source,
                                         game_position=26)
    context = reconfirm_event_checkpoint_v1(context, prepared, through_position=25,
        expected_revision=1, provenance="Confirmed original list")
    if difference == "settlement":
        game = document.workspace.slots[24].observed_game
        corrected = _observed_game(document.workspace.match_definition, match_position=25,
            game_timecode=None, perspective_initial_hand=game.perspective_initial_hand,
            declarer_player_id=game.declarer_player_id, declaration=replace(game.declaration,
                bid_value=96), original_skat=game.original_skat,
            discarded_cards=game.discarded_cards,
            plays=game.plays)
        facts = build_recording_facts_v1(build_match_workspace_persistence_document_v1(
            _set_game(document.workspace, corrected)), through_position=25)
    elif difference == "mapping":
        binding = context.bindings[0]
        mapping = {"player-a": "player-a", "player-b": "player-c", "player-c": "player-b"}
        binding = replace(binding, players=tuple(replace(player,
            event_player_id=mapping[player.source_player_id]) for player in binding.players))
        context = revise_event_context_v1(context, expected_revision=2, change="attachment",
                                           provenance="Corrected mapping", bindings=(binding,))
    elif difference == "checkpoint":
        context = set_event_checkpoint_v1(context, replace(context.checkpoints[0],
            personal_points=781), expected_revision=2)
    else:
        context = set_event_terms_v1(context, replace(context.terms[0],
            scoring_source=replace(context.terms[0].scoring_source, edition="Corrected rules")),
            expected_revision=2, correction=True, provenance="Corrected rule source")
    value = prepare_event_context_v1(context, (facts,), target=facts.source.source,
                                      game_position=26)
    assert value.status == "conflict"
