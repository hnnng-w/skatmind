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
