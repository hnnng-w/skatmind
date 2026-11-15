from dataclasses import replace
from fractions import Fraction

import pytest
from accounting_fixtures import completed_cent_session, own_loss_match
from event_context_fixtures import synthetic_context

from skatmind.accounting_state import (
    CentRoundV1,
    ConfirmedGameV1,
    NetConfirmationV1,
    TournamentAccountingV1,
    freeze_preparation,
)
from skatmind.accounting_store import (
    ACCOUNTING_FILENAME,
    AccountingConflict,
    AccountingJournalV1,
    accounting_bytes,
    append_accounting,
    load_accounting,
    resume_accounting,
    save_accounting,
)
from skatmind.event_context_contracts import (
    CENT_RULE,
    CheckpointV1,
    EventContextV1,
    EventTermsV1,
    FinancialFactsV1,
)
from skatmind.event_context_projection import prepare_event_context_v1
from skatmind.event_context_sources import build_event_binding_v1, build_recording_facts_v1
from skatmind.mode_accounting import CENT_SOURCE, STANDARD_RULE, STANDARD_SOURCE, SignedMoneyV1


@pytest.fixture(scope="module")
def genuine_sources():
    # Construct the small real accepted-log fixture once, not once per scalar case.
    session = completed_cent_session()
    match = own_loss_match()
    return match, session


def cent(session):
    binding = build_event_binding_v1(session, game_position=1, selected_player_id="player-a")
    context = EventContextV1(event_id="round-a", series_id="block-a", event_name="Synthetic Cent",
        series_name="Block A", participant_ids=("player-a", "player-b", "player-c"),
        selected_participant_id="player-a", bindings=(binding,), terms=(EventTermsV1(
            from_position=1, mode="cent", scoring_rule=CENT_RULE, scoring_source=CENT_SOURCE,
            financial=FinancialFactsV1(currency="EUR", cent_tariff="1/2",
                                      provenance="Confirmed synthetic tariff")),))
    return CentRoundV1(context=context, table_id="table-a",
        participant_labels=("Alice", "Bob", "Carol"),
        recordings=(build_recording_facts_v1(session, selected_player_id="player-a"),),
        confirmations=(), rule_source=CENT_SOURCE, provenance="Synthetic actual conditions")


def tournament(context, facts, *, boundary=25, before=4, game=28):
    prepared = prepare_event_context_v1(context, facts, target=facts[0].source.source,
                                        game_position=game)
    return TournamentAccountingV1(context=context, preparation=freeze_preparation(prepared),
        rule=STANDARD_RULE, rule_source=STANDARD_SOURCE, rule_from_position=boundary,
        losses_before=before, obligations=(), receipts=(), receipts_complete=False,
        currency="EUR", provenance="Confirmed actual interval")


def test_genuine_outcome_reuse_and_contradiction_reconciliation(genuine_sources):
    _, session = genuine_sources
    row = cent(session)
    fact = row.recordings[0].outcomes[0]
    assert row.game(1)[0] == "settled" and row.game(1)[2] == "derived"
    declarer = next(r for r in row.game(1)[1] if r.player_id == fact.declarer_id)
    assert declarer.gross.value == Fraction(fact.settlement_score, 100)
    wrong = ConfirmedGameV1(position=1, status="settled", declarer_id=fact.declarer_id,
        settlement=-fact.settlement_score, provenance="Contradictory external note")
    conflict = replace(row, confirmations=(wrong,))
    assert conflict.game(1)[0] == "source_conflict"
    corrected = replace(conflict, confirmations=(replace(wrong, settlement=fact.settlement_score,
        reconciliation="Checked original result"),))
    assert corrected.game(1)[0] == "settled" and corrected.game(1)[2] == "supplied"
    passed = replace(row, confirmations=(ConfirmedGameV1(position=1, status="passed",
        provenance="Wrong passed deal"),))
    assert passed.game(1)[0] == "source_conflict"
    external = replace(row, confirmations=(ConfirmedGameV1(position=1, status="external",
        personal_net=SignedMoneyV1.parse("-1.23"), provenance="Actual personal game posting"),))
    assert external.personal_totals() == (Fraction(-123, 100), None)


def test_checkpoint_fee_continuation_backfill_and_duplicate_match_session(genuine_sources):
    match, session = genuine_sources
    context = synthetic_context(match)
    # Confirmed cumulative anchors cover unknown earlier detail. A later exact
    # Session and Match represent the same game and must be consumed once.
    context = replace(context, checkpoints=(
        CheckpointV1(through_position=24, personal_points=780, own_losses=4, provenance="Anchor A"),
        CheckpointV1(through_position=26, personal_points=800, own_losses=5,
                     provenance="Anchor B")))
    facts = build_recording_facts_v1(match)
    base = tournament(context, (facts,))
    assert base.prepared.own_losses == 6
    assert next(c.value.value for c in base.components if c.kind == "additional_losses") == -4
    assert next(c.value for c in base.components if c.kind == "earlier_losses") is None
    binding = build_event_binding_v1(session, game_position=27, selected_player_id="player-b")
    duplicate = replace(context, bindings=(*context.bindings, binding))
    combined = tournament(duplicate, (facts, build_recording_facts_v1(session,
        selected_player_id="player-b")))
    assert combined.prepared.own_losses == 6 and combined.components == base.components
    assert len(combined.prepared.basis[26].sources) == 2
    backfilled = replace(duplicate, checkpoints=(*duplicate.checkpoints, CheckpointV1(
        through_position=27, personal_points=combined.prepared.personal_points, own_losses=6,
        provenance="Confirmed later cumulative total")))
    after = tournament(backfilled, (facts, build_recording_facts_v1(session,
        selected_player_id="player-b")))
    assert after.components == base.components
    assert replace(base, rule="unverified").components[3].value is None
    # Establishing the counter does not retroactively establish an earlier fee edition.
    assert next(c for c in base.components if c.kind == "earlier_losses").value is None


def test_append_only_resume_noop_stale_save_and_failure_preserve_bytes(
        tmp_path, genuine_sources, monkeypatch):
    row = cent(genuine_sources[1])
    empty = load_accounting(tmp_path)
    assert not (tmp_path / ACCOUNTING_FILENAME).exists()
    journal = append_accounting(empty, row)
    assert save_accounting(tmp_path, journal, expected_fingerprint=empty.fingerprint,
                           source_guard=lambda: True) == "saved"
    raw = (tmp_path / ACCOUNTING_FILENAME).read_bytes()
    assert resume_accounting(raw) == journal
    assert append_accounting(journal, row) == journal
    assert save_accounting(tmp_path, journal, expected_fingerprint=journal.fingerprint,
                           source_guard=lambda: True) == "unchanged"
    corrected = append_accounting(journal, replace(row, provenance="Explicit correction"))
    with pytest.raises(AccountingConflict):
        save_accounting(tmp_path, corrected, expected_fingerprint=empty.fingerprint,
                        source_guard=lambda: True)
    with pytest.raises(AccountingConflict):
        save_accounting(tmp_path, corrected, expected_fingerprint=journal.fingerprint,
                        source_guard=lambda: False)
    def fail(*args):
        raise OSError("Synthetic pre-replace failure")
    monkeypatch.setattr("skatmind.accounting_store.os.replace", fail)
    with pytest.raises(OSError):
        save_accounting(tmp_path, corrected, expected_fingerprint=journal.fingerprint,
                        source_guard=lambda: True)
    assert (tmp_path / ACCOUNTING_FILENAME).read_bytes() == raw
    assert corrected.rounds[0] == journal.rounds[0]
    assert not tuple(tmp_path.glob("*.tmp"))


def test_strict_codec_and_immutable_source_ownership(genuine_sources):
    row = cent(genuine_sources[1])
    journal = append_accounting(AccountingJournalV1(), row)
    raw = accounting_bytes(journal)
    for broken in (raw.replace(b'"version":1', b'"version":true', 1),
                   raw.replace(b'"currency":"EUR"', b'"currency":"USD"'),
                   raw.replace(b'"revision":0', b'"revision":2'),
                   raw.replace(b'"journal":', b'"extra":0,"journal":')):
        with pytest.raises(ValueError):
            resume_accounting(broken)
    with pytest.raises(ValueError, match="independent"):
        append_accounting(journal, replace(row, context=replace(row.context,
            event_id="another-round", series_id="another-block")))


def test_aggregate_net_is_reconciliation_not_additional_gain_and_overlap_rejected(genuine_sources):
    row = cent(genuine_sources[1])
    confirmed = replace(row, net_confirmation=NetConfirmationV1(scope="block",
        round_ids=(row.identity,),
        activity_fingerprints=(row.activity_fingerprint,),
        personal_net=SignedMoneyV1.parse("2.75"), provenance="Actual whole block net"))
    assert confirmed.personal_totals() == row.personal_totals()
    # A separate empty source identity is enough to test coverage arithmetic;
    # constructing another accepted-log archive would add no evidence here.
    binding = row.context.bindings[0]
    source = replace(binding.attached_source,
                     source=replace(binding.source, product_id="other-session"))
    context = replace(row.context, event_id="round-b", series_id="block-b",
        bindings=(replace(binding, attached_source=source),))
    second = replace(row, context=context, previous_round_id=row.identity,
        recordings=(replace(row.recordings[0], source=source),))
    second = replace(second, net_confirmation=NetConfirmationV1(
            scope="table_stay", round_ids=(row.identity, context.event_id),
            activity_fingerprints=(row.activity_fingerprint, second.activity_fingerprint),
            personal_net=SignedMoneyV1.parse("3"), provenance="Actual table-stay result"))
    with pytest.raises(ValueError, match="overlap"):
        AccountingJournalV1(rounds=(confirmed, second))
    assert AccountingJournalV1(rounds=(row, second)).round_heads[-1] == second


def test_source_only_fixture_generator_refuses_overwrite(tmp_path, monkeypatch):
    import accounting_fixtures

    monkeypatch.setattr("sys.argv", ["accounting_fixtures", "--output-directory", str(tmp_path)])
    accounting_fixtures.main()
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert set(before) == {"synthetic-checkpoint-match.json", "synthetic-cent-established.json",
                           "synthetic-progressive-match.json"}
    with pytest.raises(SystemExit):
        accounting_fixtures.main()
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}
