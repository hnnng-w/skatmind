"""Bounded private checkpoint. Only the archive can attest to an available result."""

import hashlib
import os
import re
from pathlib import Path

from skatmind import automatic_learning_io as io
from skatmind.automatic_learning_codec import canonical_json, decode_json
from skatmind.whole_game_rollout_workflow import parse_rollout_settings, serialize_rollout_settings

from .analysis_controls import COUNTS, TIMEOUTS

LIMIT = 96 * 1024
HEX = re.compile(r"[a-f0-9]{64}\Z")
ROW = re.compile(r"(?:[1-9]|[12][0-9]|3[0-6]):(?:[1-9]|[12][0-9]|30)\Z")


def file_identity(path):
    stat = io.checked_path(path)
    # Size/mtime also distinguish a newly imported copy if its inode was recycled.
    return hashlib.sha256(repr(io.stamp(stat)).encode("ascii")).hexdigest()


class ProgressFile:
    def __init__(self, home: Path, filename: str):
        self.root = home / "whole-match-reviews"
        self.path = self.root / (hashlib.sha256(filename.encode()).hexdigest() + ".json")

    def lease(self):
        io.checked_root(self.root.parent)
        self.root.mkdir(exist_ok=True)
        io.checked_root(self.root)
        try:
            with (self.root / ".coordination.lock").open("xb") as f:
                f.write(b"\0")
        except FileExistsError:
            pass
        return io.acquire_local_lease(self.root)

    def read(self):
        try:
            io.checked_root(self.root)
            raw = io.read_bounded(self.path, LIMIT)
        except FileNotFoundError:
            return None
        value = decode_json(raw)
        checksum = value.pop("digest", None)
        if (hashlib.sha256(canonical_json(value)).hexdigest() != checksum or set(value) != {
                "version", "run", "source", "file", "settings", "supplements", "refs", "phase"}
                or type(value["version"]) is not int or value["version"] != 1
                or not all(isinstance(value[k], str) and HEX.fullmatch(value[k])
                           for k in ("run", "source", "file"))
                or value["phase"] not in ("working", "paused", "finished", "unsaved", "quota",
                                          "failed")
                or type(value["refs"]) is not dict or len(value["refs"]) > 360
                or type(value["supplements"]) is not dict or len(value["supplements"]) > 36):
            raise ValueError("Invalid whole-Match progress.")
        settings = parse_rollout_settings(value["settings"])
        if (serialize_rollout_settings(settings) != value["settings"]
                or (settings.requested_worlds, settings.wall_clock_timeout_ms)
                not in zip(COUNTS, TIMEOUTS, strict=True)
                or settings.max_card_transitions != 300_000
                or settings.max_preparation_work != 100_000
                or settings.objective != "complete_settlement" and value["supplements"]):
            raise ValueError("Invalid frozen settings.")
        for pos, row in value["supplements"].items():
            if (pos not in map(str, range(1, 37)) or type(row) is not dict
                    or not row or set(row) - {"bid_value", "matadors"}
                    or any(type(v) is not int for v in row.values())):
                raise ValueError("Invalid game-specific assumptions.")
        for k, ref in value["refs"].items():
            if (not ROW.fullmatch(k) or type(ref) is not list or len(ref) != 2
                    or ref[0] not in ("computed", "reused", "saving")
                    or type(ref[1]) is not str or not HEX.fullmatch(ref[1])):
                raise ValueError("Invalid decision evidence reference.")
        return value

    def write(self, value):
        # Caller owns the dedicated nonblocking worker lease across writes.
        raw = canonical_json({**value, "digest": hashlib.sha256(canonical_json(value)).hexdigest()})
        if len(raw) > LIMIT:
            raise ValueError("Whole-Match progress limit exceeded.")
        io.checked_root(self.root)
        temporary = io.write_temporary(self.root, raw)
        try:
            os.replace(temporary, self.path)
            io.sync_directory(self.root)
        finally:
            io.discard_temporary(self.root, temporary)

    @staticmethod
    def initial(source, file, run, settings, supplements):
        return {"version": 1, "source": source, "file": file, "run": run, "phase": "working",
                "settings": serialize_rollout_settings(settings), "supplements": supplements,
                "refs": {}}
