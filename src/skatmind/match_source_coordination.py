"""In-process saved-Match publication barrier, independent of browser refreshes.

Callers acquire Product/app locks before this barrier and never acquire them
inside it. Expensive preparation runs outside all three. The generation detects
accepted writes even when a source is subsequently restored byte-for-byte.
"""

import threading
import weakref
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MatchSourceCoordinator:
    lock: object = field(default_factory=threading.RLock)
    generation: int = 0
    _sources: object = field(default_factory=weakref.WeakValueDictionary, repr=False)

    def watch_source(self, name):
        """A weak per-recording epoch; unrelated recordings do not expire native views."""
        with self.lock:
            value = self._sources.get(name)
            if value is None:
                value = SavedSourceEpoch(self)
                self._sources[name] = value
            return value

    def accepted_write(self, name):
        """Caller holds the directory barrier through replacement and this notification."""
        self.generation += 1
        value = self._sources.get(name)
        if value is not None:
            value.generation += 1


@dataclass
class SavedSourceEpoch:
    owner: MatchSourceCoordinator
    generation: int = 0

    @property
    def lock(self):
        return self.owner.lock


_LOCK = threading.Lock()
_COORDINATORS = weakref.WeakValueDictionary()


def match_source_coordinator(root: Path) -> MatchSourceCoordinator:
    info = root.stat()
    key = info.st_dev, info.st_ino
    with _LOCK:
        value = _COORDINATORS.get(key)
        if value is None:
            value = MatchSourceCoordinator()
            _COORDINATORS[key] = value
        return value
