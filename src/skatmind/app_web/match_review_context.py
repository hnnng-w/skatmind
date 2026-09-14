from __future__ import annotations

import hashlib
import hmac

from .recorded_review_opening import RecordingOpenConflict, require_recording_fresh_v1


def match_review_binding_v1(active) -> str:
    values = (active.handle, active.capture.content_fingerprint,
              active.selected_position, active.position_generation)
    return hmac.new(active.card_entry_key, repr(values).encode(), hashlib.sha256).hexdigest()


def require_match_review_binding_v1(active, values) -> None:
    binding = values.pop("review_binding", None)
    if (type(binding) is not str
            or not hmac.compare_digest(binding, match_review_binding_v1(active))
            or str(values.get("match_position")) != str(active.selected_position)):
        raise RecordingOpenConflict()
    require_recording_fresh_v1(active, "matches")
