"""Private original-Match source adapter for the single-series empirical baseline."""

import re
from dataclasses import dataclass

from .event_context_contracts import TOURNAMENT_RULE, RecordingVersionV1, bounded_text
from .event_context_projection import ESTABLISHED, prepare_event_context_v1
from .event_context_sources import build_recording_facts_v1, recording_version_v1
from .fixed_three_player_list_contribution import build_fixed_three_player_list_contributions
from .match_tournament_format import EUROSKAT_36_STANDARD_V1_FORMAT
from .match_workspace_persistence_contracts import MatchWorkspacePersistenceDocumentV1
from .rfc3339 import parse_rfc3339_datetime
from .tournament_money_valuation import ListGame, TournamentPrefix


def evidence_time(value):
    """Only compare unambiguous instants at supported (microsecond or coarser) precision."""
    if value is None or value.endswith("-00:00"):
        return None
    if re.search(r"\.\d{7}", value):
        return None
    try:
        return parse_rfc3339_datetime(value, "evidence_time")
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class AvailableList:
    """Independent evidence that this exact complete outcome block was available."""

    source: RecordingVersionV1
    available_at: str | None
    reference: str
    scoring_rule: str
    mode: str
    series_count: int

    def __post_init__(self):
        if type(self.source) is not RecordingVersionV1 or self.source.source.family != "match":
            raise ValueError("Availability must identify one exact Match version.")
        if self.available_at is not None:
            bounded_text(self.available_at, 64)
        for value in (self.reference, self.scoring_rule, self.mode):
            bounded_text(value)
        if type(self.series_count) is not int or self.series_count < 1:
            raise ValueError("Expected the evidenced donor series count.")


@dataclass(frozen=True, slots=True)
class RecordedList:
    document: MatchWorkspacePersistenceDocumentV1
    evidence: AvailableList | None

    def __post_init__(self):
        if type(self.document) is not MatchWorkspacePersistenceDocumentV1 or (
                self.evidence is not None and type(self.evidence) is not AvailableList):
            raise ValueError("Expected an original Match document and optional availability fact.")


def supported_match(document):
    definition = document.workspace.match_definition
    return (definition.game_platform.casefold() == "euroskat"
            and definition.tournament_format is EUROSKAT_36_STANDARD_V1_FORMAT)


def score_game(players, game):
    score = game.settlement_score
    rows = build_fixed_three_player_list_contributions(player_ids=players,
        entry_outcome=("passed_deal" if score is None else
                       "declarer_win" if score > 0 else "declarer_loss"),
        declarer_player_id=game.declarer_id, settlement_score=score)
    return tuple(row.total_performance_points for row in rows)


def add_points(first, second):
    return tuple(a + b for a, b in zip(first, second, strict=True))


@dataclass(frozen=True, slots=True)
class DonorBlock:
    evidence: AvailableList
    players: tuple[str, ...]  # Canonical table places, not rotating forehand order.
    games: tuple[ListGame, ...]
    cumulative: tuple[tuple[int, ...], ...]

    def suffix_points(self, through):
        return tuple(a - b for a, b in zip(self.cumulative[-1], self.cumulative[through],
                                          strict=True))

    def suffix_games(self, through, places):
        mapped = dict(zip(self.players, places, strict=True))
        return tuple(ListGame(mapped.get(g.declarer_id), g.settlement_score)
                     for g in self.games[through:])


@dataclass(frozen=True, slots=True)
class Population:
    donors: tuple[DonorBlock, ...] = ()
    excluded: tuple[tuple[RecordingVersionV1, str], ...] = ()

    @property
    def unique_donor_count(self):
        return len(self.donors)

    @property
    def excluded_source_count(self):
        return len(self.excluded)


def _aliases(document):
    definition = document.workspace.match_definition
    keys = {("match", definition.match_id)}
    if definition.external_match_id and supported_match(document):
        keys.add(("euroskat", definition.external_match_id))
    return keys


def _groups(target, sources):
    # Transitive: a revision can change the external ID while retaining the local ID.
    groups = [(_aliases(target), [])]
    for item in sources:
        keys, rows = _aliases(item.document), [item]
        for old_keys, old_rows in groups.copy():
            if not keys.isdisjoint(old_keys):
                keys.update(old_keys)
                rows.extend(old_rows)
                groups.remove((old_keys, old_rows))
        groups.append((keys, rows))
    return groups


def _admission_gap(document, source, fact, cutoff):
    if not supported_match(document):
        return "unsupported_platform_or_format"
    if fact is None:
        return "complete_list_availability_missing"
    if fact.source != source:
        return "availability_source_mismatch"
    if fact.mode != "tournament" or fact.scoring_rule != TOURNAMENT_RULE:
        return "incompatible_scoring"
    if fact.series_count != 1:
        return "unsupported_series_count"
    if cutoff is None:
        return "target_cutoff_missing"
    available = evidence_time(fact.available_at)
    if available is None:
        return "complete_list_availability_ambiguous"
    if available >= cutoff:
        return "not_available_before_cutoff"
    start = document.workspace.match_definition.played_at
    if start is not None:
        started = evidence_time(start)
        if started is None or available <= started:
            return "availability_not_after_start"
    return None


def prepare_population(target, sources, *, work_hook):
    """Quarantine ambiguous logical identities before weighting; extract each donor once."""
    if type(sources) is not tuple or len(sources) > 128 or any(
            type(item) is not RecordedList for item in sources):
        raise ValueError("Expected at most 128 original Match sources.")
    cutoff = evidence_time(target.workspace.match_definition.played_at)
    admitted, excluded = [], []
    for keys, rows in _groups(target, sources):
        work_hook()
        versions = [recording_version_v1(item.document) for item in rows]
        evidence = {row.evidence for row in rows if row.evidence is not None}
        if not keys.isdisjoint(_aliases(target)):
            reason = "target_match"
        elif len(set(versions)) != 1:
            reason = "conflicting_revisions"
        elif len(evidence) > 1:
            reason = "conflicting_availability_facts"
        else:
            doc = rows[0].document
            fact = next(iter(evidence), None)
            reason = _admission_gap(doc, versions[0], fact, cutoff)
        if reason is None:
            recording = build_recording_facts_v1(doc, work_hook=work_hook)
            gap = next((r for r in recording.outcomes if r.status not in ESTABLISHED), None)
            if gap:
                reason = f"position_{gap.position}:{gap.status}"
            else:
                games = tuple(ListGame(r.declarer_id, r.settlement_score)
                              for r in recording.outcomes)
                totals = [(0, 0, 0)]
                for game in games:
                    totals.append(add_points(totals[-1], score_game(recording.player_ids, game)))
                admitted.append(DonorBlock(fact, recording.player_ids, games, tuple(totals)))
                versions = versions[1:]
                reason = "duplicate_copy"
        excluded.extend((v, reason) for v in versions)
    return Population(tuple(sorted(admitted, key=lambda d: d.evidence.source.source.product_id)),
        tuple(sorted(excluded, key=lambda r: (r[0].source.product_id, r[0].revision,
                                              r[0].content_fingerprint, r[1]))))


def prepare_target(document, context, position, decision, work_hook):
    recording = build_recording_facts_v1(document, through_position=position-1,
                                        decision_position=position, work_hook=work_hook)
    p = prepare_event_context_v1(context, (recording,), target=recording.source.source,
                                 game_position=position, decision_index=decision)
    places = tuple(r.event_player_id for r in context.binding(p.target_key).players)
    gaps = tuple(f"opponent_prefix:{player}:position_{row.fact.position}:{row.fact.status}"
                 for row in p.basis if row.fact.status not in ESTABLISHED
                 for player in places if player != p.selected_participant_id)
    if p.status != "ready" or gaps:
        return None, places, (), ((p.status,) if p.status != "ready" else ()) + gaps
    prefix = TournamentPrefix(p, context)
    points = (0, 0, 0)
    for row in p.basis:
        points = add_points(points, score_game(places,
            ListGame(row.fact.declarer_id, row.fact.settlement_score)))
    # An acknowledged personal checkpoint governs the payee only.
    return prefix, places, tuple(p.personal_points if player == p.selected_participant_id else n
                                  for player, n in zip(places, points, strict=True)), ()
