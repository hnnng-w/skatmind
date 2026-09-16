from __future__ import annotations

from .learning_direct_entry import (
    LEARNING_ENTRY_LOCATION,
    LearningEntryConflict,
    add_recorded_match_v1,
)
from .validation_mapping import map_frontend_exception_v1


def dispatch_learning_direct_entry(handler, values):
    app = handler.server.app_context
    with app.lock:
        target = app.managed_stateful.active_learning
    if target is None:
        raise LearningEntryConflict()
    handler._submitted_active = target
    result = add_recorded_match_v1(app, target, values)
    # Do not attach a late result/feedback to a different active collection.
    with app.managed_stateful.learning_lifecycle_lock:
        with app.lock:
            if app.managed_stateful.active_learning is not target:
                raise LearningEntryConflict()
        if result.http_status == 409:
            raise LearningEntryConflict()
        if result.status == "resolution_required":
            # Normal no-change outcome; retain the safe chosen source and show the
            # native explicit retain choice, without retrying the import.
            definition = handler._current_form_definition
            handler._retain_form_feedback(definition,
                issues=map_frontend_exception_v1(ValueError("Explicit resolution required."),
                                                 definition, status=400), status=400)
            handler._learning_page()
            return
        handler._redirect(LEARNING_ENTRY_LOCATION)
