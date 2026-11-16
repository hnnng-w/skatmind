"""Private event facts, independent of recording and retained-analysis contracts."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, fields
from fractions import Fraction
from typing import get_type_hints

from .automatic_learning_codec import (
    Record,
    _convert,
    canonical_json,
    digest,
    integer,
    text,
    unique,
)

EVENT_CONTEXT_VERSION = 1
TOURNAMENT_RULE = "fixed_three_player_isko_v1"
CENT_RULE = "cent_game_points_v1"
EVENT_MODES = ("tournament", "tournament_cent", "cent")
CENT_TARIFFS = ("1/2", "1", "2", "3", "5")


def identity(domain, value):
    return hashlib.sha256(b"skatmind\0event_context_v1\0" + domain.encode("ascii")
                          + b"\0" + canonical_json(value)).hexdigest()


def bounded_text(value, maximum=500):
    text(value)
    if len(value) > maximum or any(ord(char) < 32 for char in value):
        raise ValueError("Event text is too long or contains control characters.")


def position(value, *, zero=False, end=36):
    integer(value, 0 if zero else 1)
    if value > end:
        raise ValueError("Event position is outside its fixed bounds.")


@dataclass(frozen=True, slots=True, kw_only=True)
class RuleSourceV1(Record):
    reference: str
    edition: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        bounded_text(self.reference)
        bounded_text(self.edition, 120)


@dataclass(frozen=True, slots=True, kw_only=True)
class AmountV1(Record):
    """Exact confirmed amount in currency units, never binary floating point."""

    numerator: int
    denominator: int = 1
    version: int = 1

    def __post_init__(self):
        self.validate()
        integer(self.numerator)
        integer(self.denominator, 1)
        value = Fraction(self.numerator, self.denominator)
        if (value.numerator, value.denominator) != (self.numerator, self.denominator):
            raise ValueError("Amounts must be reduced exact nonnegative fractions.")
        if self.numerator > 10**12 or self.denominator > 10**6:
            raise ValueError("Amount exceeds the private fact bound.")

    @classmethod
    def parse(cls, value):
        if type(value) is not str or not re.fullmatch(
                r"[0-9]{1,12}(?:\.[0-9]{1,6}|/[1-9][0-9]{0,5})?", value):
            raise ValueError("Use an exact nonnegative decimal amount.")
        number = Fraction(value)
        return cls(numerator=number.numerator, denominator=number.denominator)


@dataclass(frozen=True, slots=True, kw_only=True)
class PoolFactV1(Record):
    pool_id: str
    participation: str = "unknown"
    entitlement: str = "unknown"
    version: int = 1

    def __post_init__(self):
        self.validate()
        bounded_text(self.pool_id, 120)
        if self.participation not in ("unknown", "yes", "no") or self.entitlement not in (
                "unknown", "yes", "no"):
            raise ValueError("Pool participation and entitlement must be explicit facts.")


@dataclass(frozen=True, slots=True, kw_only=True)
class FinancialFactsV1(Record):
    currency: str | None = None
    entry_paid: AmountV1 | None = None
    entry_committed: AmountV1 | None = None
    table_paid: AmountV1 | None = None
    table_committed: AmountV1 | None = None
    cent_tariff: str | None = None
    pools: tuple[PoolFactV1, ...] = ()
    fee_source: RuleSourceV1 | None = None
    payout_source: RuleSourceV1 | None = None
    prize_facts: str | None = None
    prize_completeness: str = "unknown"
    provenance: str | None = None
    version: int = 1

    def __post_init__(self):
        self.validate()
        if self.currency is not None and not re.fullmatch(r"[A-Z]{3}", self.currency):
            raise ValueError("Currency must be an explicit three-letter code.")
        amounts = (self.entry_paid, self.entry_committed, self.table_paid, self.table_committed)
        if any(value is not None for value in amounts) and self.currency is None:
            raise ValueError("Known amounts require a currency.")
        if self.cent_tariff is not None and self.cent_tariff not in (*CENT_TARIFFS, "1/4"):
            raise ValueError("Unsupported exact Cent tariff.")
        unique(tuple(pool.pool_id for pool in self.pools))
        if len(self.pools) > 8:
            raise ValueError("At most eight selected pools can be recorded.")
        if self.prize_completeness not in ("unknown", "partial", "complete"):
            raise ValueError("Prize completeness must be explicit.")
        if (self.prize_facts is None) != (self.prize_completeness == "unknown"):
            raise ValueError("Prize facts require their explicit completeness.")
        for value in (self.prize_facts, self.provenance):
            if value is not None:
                bounded_text(value, 2000)
        if (any(value is not None for value in amounts) or self.pools or self.prize_facts
                or self.cent_tariff) and self.provenance is None:
            raise ValueError("Confirmed financial facts require provenance.")
        if self.prize_facts is not None and self.payout_source is None:
            raise ValueError("Prize facts require an identified payout source/version.")

    @property
    def missing(self):
        # Completeness describes recorded inputs only, never readiness for forecasting.
        return tuple(name for name in ("currency", "entry_paid", "entry_committed", "table_paid",
            "table_committed", "fee_source", "payout_source", "provenance")
            if getattr(self, name) is None) + (("prize_facts",)
                if self.prize_completeness != "complete" else ())


@dataclass(frozen=True, slots=True, kw_only=True)
class EventTermsV1(Record):
    from_position: int
    mode: str
    scoring_rule: str
    scoring_source: RuleSourceV1
    financial: FinancialFactsV1 = FinancialFactsV1()
    version: int = 1
    platform: str | None = None

    def validate(self):
        # The original closed v1 wire shape and fingerprints remain exact. Only
        # explicit v2 terms carry the actual platform; legacy terms do not imply it.
        for name, annotation in get_type_hints(type(self)).items():
            _convert(annotation, getattr(self, name), decode=False)
        if self.version == 1 and self.platform is None:
            return
        if self.version != 2 or self.platform not in ("euroskat", "in_person", "unknown"):
            raise ValueError("Unsupported event terms version/platform.")

    def to_dict(self):
        value = Record.to_dict(self)
        if self.version == 1:
            del value["platform"]
        return value

    @classmethod
    def from_dict(cls, value):
        expected = {field.name for field in fields(cls)}
        if type(value) is not dict:
            raise ValueError("Invalid event terms.")
        if type(value.get("version")) is int and value["version"] == 1:
            if set(value) != expected - {"platform"}:
                raise ValueError("Invalid legacy event terms field set.")
            value = {**value, "platform": None}
        return Record.from_dict.__func__(cls, value)

    def __post_init__(self):
        self.validate()
        position(self.from_position)
        if self.mode not in EVENT_MODES:
            raise ValueError("Unsupported event mode.")
        if self.scoring_rule != (CENT_RULE if self.mode == "cent" else TOURNAMENT_RULE):
            raise ValueError("Mode and scoring rules are incompatible.")
        tariff = self.financial.cent_tariff
        if (self.mode == "tournament" and tariff is not None
                or self.mode == "tournament_cent" and tariff not in (None, "1/4")
                or self.mode == "cent" and tariff not in (None, *CENT_TARIFFS)):
            raise ValueError("Cent tariff is incompatible with the event mode.")
        if tariff is not None and self.financial.currency != "EUR":
            raise ValueError("The selected EuroSkat Cent tariff requires EUR.")


@dataclass(frozen=True, slots=True, kw_only=True)
class RecordingKeyV1(Record):
    family: str
    product_id: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        if self.family not in ("match", "session"):
            raise ValueError("Event context supports managed Match and Session sources.")
        bounded_text(self.product_id)


@dataclass(frozen=True, slots=True, kw_only=True)
class RecordingVersionV1(Record):
    source: RecordingKeyV1
    content_fingerprint: str
    revision: int
    contract_version: int = 1
    version: int = 1

    def __post_init__(self):
        self.validate()
        digest(self.content_fingerprint)
        integer(self.revision)
        if self.contract_version != 1:
            raise ValueError("Unsupported recording version.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ParticipantMapV1(Record):
    source_player_id: str
    event_player_id: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        bounded_text(self.source_player_id)
        bounded_text(self.event_player_id)


@dataclass(frozen=True, slots=True, kw_only=True)
class EventBindingV1(Record):
    attached_source: RecordingVersionV1
    # Session maps one game; Match maps its unchanged complete 1..36 positions.
    game_position: int | None
    players: tuple[ParticipantMapV1, ...]
    source_selected_player_id: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        if len(self.players) != 3:
            raise ValueError("Exactly three explicit participant bindings are required.")
        unique(tuple(item.source_player_id for item in self.players))
        unique(tuple(item.event_player_id for item in self.players))
        if self.source_selected_player_id not in tuple(p.source_player_id for p in self.players):
            raise ValueError("The selected source participant must be bound.")
        if self.attached_source.source.family == "match":
            if self.game_position is not None:
                raise ValueError("A Match retains its fixed 36-position format.")
        else:
            position(self.game_position)

    @property
    def source(self):
        return self.attached_source.source

    def player(self, player_id):
        return next(item.event_player_id for item in self.players
                    if item.source_player_id == player_id)


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointV1(Record):
    through_position: int
    personal_points: int
    own_losses: int
    provenance: str
    # A reconfirmation acknowledges this exact disagreement, never future backfill.
    acknowledged_disagreement: str | None = None
    version: int = 1

    def __post_init__(self):
        self.validate()
        position(self.through_position, zero=True)
        integer(self.own_losses)
        if self.own_losses > self.through_position:
            raise ValueError("Own losses cannot exceed covered positions.")
        if self.through_position == 0 and (self.personal_points or self.own_losses):
            raise ValueError("The empty prefix is zero.")
        bounded_text(self.provenance)
        if self.acknowledged_disagreement is not None:
            digest(self.acknowledged_disagreement)


@dataclass(frozen=True, slots=True, kw_only=True)
class EventContextV1(Record):
    event_id: str
    series_id: str
    event_name: str
    series_name: str
    participant_ids: tuple[str, ...]
    selected_participant_id: str
    bindings: tuple[EventBindingV1, ...]
    terms: tuple[EventTermsV1, ...]
    checkpoints: tuple[CheckpointV1, ...] = ()
    revision: int = 0
    change: str = "created"
    provenance: str = "Confirmed by the recording owner."
    version: int = 1

    def __post_init__(self):
        self.validate()
        for value in (self.event_id, self.series_id, self.event_name, self.series_name,
                      self.provenance):
            bounded_text(value)
        integer(self.revision)
        if self.change not in ("created", "checkpoint", "checkpoint_removed", "reconciliation",
                               "terms_correction", "terms_change", "attachment"):
            raise ValueError("An explicit context revision reason is required.")
        if (len(self.participant_ids) != 3
                or self.selected_participant_id not in self.participant_ids):
            raise ValueError("The selected participant must belong to the fixed three players.")
        for value in self.participant_ids:
            bounded_text(value)
        unique(self.participant_ids)
        if not self.bindings or len(self.bindings) > 37:
            raise ValueError("A context requires bounded source bindings.")
        unique(tuple(binding.source for binding in self.bindings))
        if sum(binding.source.family == "match" for binding in self.bindings) > 1:
            raise ValueError("One event cannot merge independent Matches.")
        for binding in self.bindings:
            if (set(p.event_player_id for p in binding.players) != set(self.participant_ids)
                    or binding.player(binding.source_selected_player_id)
                    != self.selected_participant_id):
                raise ValueError("Source participants and perspective must bind exactly.")
        match = next((binding for binding in self.bindings
                      if binding.source.family == "match"), None)
        if match is not None:
            from .fixed_three_player_list_rotation import (
                build_fixed_three_player_list_seat_assignment,
            )

            places = {f"place_{index}": item.event_player_id
                      for index, item in enumerate(match.players, 1)}
            for binding in self.bindings:
                if binding.source.family == "session":
                    seats = build_fixed_three_player_list_seat_assignment(
                        binding.game_position, places)
                    if tuple(item.event_player_id for item in binding.players) != (
                            seats.forehand_player_id, seats.middlehand_player_id,
                            seats.rearhand_player_id):
                        raise ValueError("Session binding contradicts fixed Match seat rotation.")
        if (not self.terms or self.terms[0].from_position != 1
                or tuple(term.from_position for term in self.terms)
                != tuple(sorted(set(term.from_position for term in self.terms)))):
            raise ValueError("Terms require explicit ordered applicability starting at position 1.")
        if len({term.scoring_rule for term in self.terms}) != 1:
            raise ValueError("An event cannot change its scoring family.")
        if match is not None and not self.tournament:
            raise ValueError("A fixed Match cannot be relabeled as Cent-Skat.")
        if not self.tournament and self.checkpoints:
            raise ValueError("List-score checkpoints apply only to tournament scoring.")
        if not self.tournament and (any(term.from_position > 3 for term in self.terms)
                or any(binding.game_position > 3 for binding in self.bindings)):
            raise ValueError("Cent context records positions 1 through 3 without round execution.")
        if tuple(c.through_position for c in self.checkpoints) != tuple(sorted(set(
                c.through_position for c in self.checkpoints))):
            raise ValueError("Checkpoint prefix boundaries must be unique and ordered.")
        for earlier, later in zip(self.checkpoints, self.checkpoints[1:], strict=False):
            if not 0 <= later.own_losses - earlier.own_losses <= (
                    later.through_position - earlier.through_position):
                raise ValueError("Cumulative own losses contradict checkpoint coverage.")

    @property
    def tournament(self):
        return self.terms[0].scoring_rule == TOURNAMENT_RULE

    @property
    def fingerprint(self):
        return identity("revision", self.to_dict())

    def applicable_terms(self, game_position):
        position(game_position, end=37)
        return next(term for term in reversed(self.terms) if term.from_position <= game_position)

    def binding(self, source):
        return next((binding for binding in self.bindings if binding.source == source), None)
