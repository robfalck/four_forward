"""Persistent leaderboard — top scores stored as JSON in the user's home dir."""

from __future__ import annotations

import json
from pathlib import Path

MAX_ENTRIES = 10
_SAVE_PATH = Path.home() / ".four_forward_scores.json"


class Leaderboard:
    def __init__(self) -> None:
        self.entries: list[dict] = []  # [{name, score}, ...] sorted high→low
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        try:
            data = json.loads(_SAVE_PATH.read_text())
            self.entries = [
                {"name": str(e["name"]), "score": float(e["score"])}
                for e in data
                if "name" in e and "score" in e
            ][:MAX_ENTRIES]
        except Exception:
            self.entries = []

    def save(self) -> None:
        try:
            _SAVE_PATH.write_text(json.dumps(self.entries, indent=2))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Queries / mutations
    # ------------------------------------------------------------------

    def qualifies(self, score: float) -> bool:
        """Return True if score would appear in the top-N list."""
        if len(self.entries) < MAX_ENTRIES:
            return True
        return score > self.entries[-1]["score"]

    def add(self, name: str, score: float) -> int:
        """Insert entry, keep sorted, trim to MAX_ENTRIES. Returns rank (1-based)."""
        self.entries.append({"name": name.strip() or "UNKNOWN", "score": score})
        self.entries.sort(key=lambda e: e["score"], reverse=True)
        self.entries = self.entries[:MAX_ENTRIES]
        self.save()
        return next(i + 1 for i, e in enumerate(self.entries) if e["score"] == score)
