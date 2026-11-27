"""Private Live choices. An effort choice never records whether advice is running."""

import os
import re
from hashlib import sha256

from skatmind.accounting_state import CentRoundV1
from skatmind.accounting_store import load_accounting
from skatmind.automatic_learning_codec import canonical_json, decode_json
from skatmind.automatic_learning_io import (
    checked_root,
    read_bounded,
    sync_directory,
    write_temporary,
)
from skatmind.event_context_sources import recording_version_v1

from .analysis_controls import EFFORTS
from .whole_match_progress import file_identity
from .workflow_state import StaleFrontendWorkflowRevisionError

_HEX_DIGEST = re.compile("[0-9a-f]{64}")


def _digest(*values):
    return sha256(canonical_json(list(values))).hexdigest()


def _path(home, *scope):
    return home / (".live-effort-" + _digest(*scope) + ".json")


def recording_choices_path(path):
    return _path(path.parent.parent, "recording", path.parent.name, path.name)


def _read(path):
    """At most two exact endpoints, each with one block and up to 36 game choices."""
    checked_root(path.parent)
    try:
        records = decode_json(read_bounded(path, 16384))
    except FileNotFoundError:
        return {}
    if len(records) > 2:
        raise ValueError("Invalid saved Live effort choices.")
    for endpoint, choices in records.items():
        if not _HEX_DIGEST.fullmatch(endpoint) or type(choices) is not dict or len(choices) > 37:
            raise ValueError("Invalid saved Live effort endpoint.")
        for key, effort in choices.items():
            if (key != "block" and not _HEX_DIGEST.fullmatch(key)) or effort not in EFFORTS:
                raise ValueError("Invalid saved Live effort choice.")
    return records


def _write(path, records):
    temp = write_temporary(path.parent, canonical_json(records))
    try:
        os.replace(temp, path)
        sync_directory(path.parent)
    finally:
        temp.unlink(missing_ok=True)


def _endpoint(path, fingerprint):
    return _digest(file_identity(path), fingerprint)


def advance_recording_choices(path, staged, previous, current, game_keys):
    """At the managed file's replacement boundary, authorize only its exact successor.

    Keep the prior endpoint too: an interrupted recording save may have left either
    file on disk. Cleared games do not confer their choices on a restarted slot.
    """
    choices_path = recording_choices_path(path)
    prior = _endpoint(path, previous)
    choices = _read(choices_path).get(prior)
    if choices:
        allowed = {"block", *game_keys}
        successor = {key: value for key, value in choices.items() if key in allowed}
        _write(choices_path, {prior: choices, _endpoint(staged, current): successor})


def match_game_key(game):
    return _digest(game.match_position, game.game_id)


SESSION_GAME = _digest("session-game")


def resolve_recording_effort(recording, fingerprint, stamp, game, default, *,
                            selected=None, block=False):
    path = recording_choices_path(recording)
    endpoint = _digest(stamp, fingerprint)
    choices = _read(path).get(endpoint, {})
    if selected is None:
        return choices.get(game, choices.get("block", default))
    choices[game] = selected
    if block:
        choices["block"] = selected
    _write(path, {endpoint: choices})
    return selected


def cent_scope(active):
    """Only the unique recording admitted by the current accounting owner is a member."""
    from .cent_continuity import entries_for, unique_entry, validate_binding

    source = recording_version_v1(active.document).source
    row = load_accounting(active.category_root.parent).for_source(source)
    if not isinstance(row, CentRoundV1):
        return None
    if (unique_entry(entries_for(active.category_root), source).path != active.path
            or file_identity(active.path) != active.saved_file_identity):
        raise StaleFrontendWorkflowRevisionError()
    binding = validate_binding(row, active.document, active.path)
    return _digest("cent", row.table_id, row.identity), _digest(binding.to_dict())


def resolve_session_effort(active, scope, default, *, selected=None, block=False):
    if scope is None:
        if block:
            raise StaleFrontendWorkflowRevisionError()
        return resolve_recording_effort(active.path, active.document.content_fingerprint,
            active.saved_file_identity, SESSION_GAME, default, selected=selected)
    owner, game = scope
    path = _path(active.category_root.parent, "cent", owner)
    choices = _read(path).get(owner, {})
    if selected is None:
        # A game can already have a deliberate choice when attached to a round.
        return choices.get(game) or resolve_recording_effort(
            active.path, active.document.content_fingerprint, active.saved_file_identity,
            SESSION_GAME, choices.get("block", default))
    choices[game] = selected
    if block:
        choices["block"] = selected
    _write(path, {owner: choices})
    return selected


def submitted_effort(values):
    block = values.pop("apply_block", None)
    if (block not in (None, "on") or set(values) != {"analysis_effort"}
            or values["analysis_effort"] not in EFFORTS):
        raise ValueError("Expected a supported Live effort and optional block choice.")
    return values["analysis_effort"], block == "on"
