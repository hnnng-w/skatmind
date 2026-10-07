"""Exact checkout and artifact identity for validation-only evidence."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
    ).encode()).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_digest(value: object, length: int = 64) -> None:
    if not isinstance(value, str) or not re.fullmatch(f"[0-9a-f]{{{length}}}", value):
        raise ValueError("Invalid evidence digest")


def read_json(path: Path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite JSON")))


def source_identity(root: Path = ROOT) -> dict:
    def git(*args):
        return subprocess.run(["git", *args], cwd=root, capture_output=True, check=True).stdout

    commit = git("rev-parse", "HEAD").decode().strip()
    require_digest(commit, 40)
    names = git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
    files = sorted(set(name.decode("utf-8") for name in names.split(b"\0") if name))
    return {"commit": commit, "source_digest": digest({
        name: file_digest(root / name) for name in files
    })}


def external_directory(path: Path) -> Path:
    path = path.resolve()
    if path.is_relative_to(ROOT):
        raise ValueError("Validation evidence must remain outside the repository")
    path.mkdir(parents=True, exist_ok=True)
    return path
