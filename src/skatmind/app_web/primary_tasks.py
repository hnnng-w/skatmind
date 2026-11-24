"""Recording task selection is UI ownership, independent of Session information mode."""


def retire_help(app, *, active_only=False):
    managed = app.managed_stateful
    for family in ("session", "match"):
        with app.lock:
            active = getattr(managed, "active_" + family)
        if active is not None:
            lock = active.lock if family == "session" else active.capture.lock
            with lock, app.lock:
                if getattr(managed, "active_" + family) is active:
                    if not active_only or active.live.effort is not None:
                        active.live.configure(None)


def enter_recording_task(app, route):
    with app.lock:
        changed = app.recording_task != route
        app.recording_task = route
    if changed:
        retire_help(app)
