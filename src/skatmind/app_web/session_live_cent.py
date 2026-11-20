"""Read only the current accounting owner's terms for this Session's position."""

from dataclasses import dataclass
from hashlib import sha256

from skatmind.accounting_state import CentRoundV1
from skatmind.accounting_store import read_accounting_bytes, resume_accounting, watch_cent_source
from skatmind.event_context_sources import recording_players_v1, recording_version_v1
from skatmind.live_cent import LiveCentTerms
from skatmind.match_source_coordination import SavedSourceEpoch
from skatmind.mode_accounting import CENT_ACCOUNTING_RULE


@dataclass(frozen=True, slots=True)
class CentBinding:
    round_id: str
    round_revision: int
    context_fingerprint: str
    position: int
    terms: LiveCentTerms


def _binding(raw, document):
    if raw is None:
        return None
    source = recording_version_v1(document).source
    row = resume_accounting(raw).for_source(source)
    if not isinstance(row, CentRoundV1):
        return None
    context = row.context
    binding = context.binding(source)
    players, perspective = recording_players_v1(document)
    if (players != tuple(p.source_player_id for p in binding.players)
            or perspective != binding.source_selected_player_id):
        raise ValueError("The Session no longer matches the round's participant binding.")
    offset = players.index(perspective)
    relative = tuple(binding.player(p) for p in players[offset:] + players[:offset])
    terms = context.applicable_terms(binding.game_position)
    return CentBinding(row.identity, row.revision, context.fingerprint, binding.game_position,
        LiveCentTerms(relative, terms.financial.cent_tariff,
                      terms.platform == "euroskat" and row.rule == CENT_ACCOUNTING_RULE))


def _digest(raw):
    return None if raw is None else sha256(raw).digest()


@dataclass(frozen=True, slots=True)
class CentAuthority:
    binding: CentBinding | None
    file_digest: bytes | None
    source: SavedSourceEpoch
    generation: int

    @property
    def unchanged(self):
        return self.source.generation == self.generation

    def current(self, root, document):
        if not self.unchanged:
            return False
        raw = read_accounting_bytes(root)
        # Identical bytes were strictly decoded at admission. Different bytes
        # can still represent an unrelated account; reconcile the same owner.
        return _digest(raw) == self.file_digest or _binding(raw, document) == self.binding


def capture_cent_authority(root, document):
    source = watch_cent_source(root, document.state.session_id)
    generation = source.generation
    raw = read_accounting_bytes(root)
    return CentAuthority(_binding(raw, document), _digest(raw), source, generation)
