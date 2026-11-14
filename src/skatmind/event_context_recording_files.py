"""Strict existing file loaders for the leaf managed-context adapter."""

from .match_workspace_persistence import load_match_workspace_file_v1
from .session_persistence import load_session_persistence_file_v1


def load_event_recording_v1(path, family):
    if family == "match":
        return load_match_workspace_file_v1(path).document
    if family == "session":
        return load_session_persistence_file_v1(path).document
    raise ValueError("Unsupported event recording family.")
