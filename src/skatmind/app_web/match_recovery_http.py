from __future__ import annotations

from .match_recovery import (
    MatchRecoveryConflict,
    apply_match_recovery,
    preview_match_recovery,
    select_match_recovery,
)


def dispatch_match_recovery(app, active, path, values):
    """Exact leaf forms; serialize active-item switching without app-lock I/O."""
    action = path.rsplit("/", 1)[-1]
    expected = {
        "select": {"recovery_selection"},
        "preview": {"recovery_selection", "card"},
        "apply": {"recovery_selection", "confirm_apply"},
        "cancel": set(),
    }[action]
    if set(values) != expected:
        raise ValueError("Recovery requires exactly its registered fields.")
    with app.managed_stateful.match_lifecycle_lock, active.capture.lock:
        with app.lock:
            if app.managed_stateful.active_match is not active:
                raise MatchRecoveryConflict()
        if action == "select":
            select_match_recovery(active, values["recovery_selection"])
        elif action == "preview":
            preview_match_recovery(active, values["recovery_selection"], card=values["card"])
        elif action == "apply":
            if values["confirm_apply"] != "on":
                raise ValueError("Correction requires explicit confirmation.")
            apply_match_recovery(active, values["recovery_selection"])
        else:
            active.operation_feedback.begin()
            active.recovery.clear()
        fragment = "match-recovery" if action in {"select", "preview"} else "match-recording"
        return f"/matches/position/{active.selected_position}#{fragment}"
