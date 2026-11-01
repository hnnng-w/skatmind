"""Explicit private managed-home services, outside ordinary recording discovery."""

from pathlib import Path

from skatmind.automatic_learning_store import (
    AutomaticLearningStoreV1,
    initialize_automatic_learning_store_v1,
    resolve_automatic_learning_root_v1,
    resume_automatic_learning_store_v1,
)

from .contracts import ManagedHomeV1


def automatic_learning_root_v1(home: ManagedHomeV1) -> Path:
    if type(home) is not ManagedHomeV1:
        raise ValueError("Expected an exact managed home.")
    return resolve_automatic_learning_root_v1(home.root)


def initialize_managed_automatic_learning_v1(home: ManagedHomeV1) -> AutomaticLearningStoreV1:
    return initialize_automatic_learning_store_v1(automatic_learning_root_v1(home))


def resume_managed_automatic_learning_v1(home: ManagedHomeV1) -> AutomaticLearningStoreV1:
    return resume_automatic_learning_store_v1(automatic_learning_root_v1(home))
