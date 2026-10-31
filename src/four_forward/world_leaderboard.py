"""Worldwide leaderboard backed by a Supabase table (schema: supabase/leaderboard.sql).

Network calls run on daemon threads so the game loop never blocks; the renderer
reads `entries`, `status` and `submit_status` each frame.
"""

from __future__ import annotations

import json
import threading
import urllib.request

from .constants import WORLD_LEADERBOARD_KEY, WORLD_LEADERBOARD_URL

_TIMEOUT_S = 5.0
TOP_N = 10


class WorldLeaderboard:
    def __init__(self) -> None:
        self.enabled = bool(WORLD_LEADERBOARD_URL and WORLD_LEADERBOARD_KEY)
        self.entries: list[dict] = []  # [{name, score, difficulty}, ...] best per player
        self.status = "ready" if self.enabled else "disabled"  # disabled|loading|ready|error
        self.submit_status = ""  # ""|sending|sent|failed

    # ------------------------------------------------------------------
    # Public API (non-blocking)
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Fetch the current top scores in the background."""
        if self.enabled:
            self.status = "loading"
            threading.Thread(target=self._fetch, daemon=True).start()

    def submit(self, name: str, score: float, difficulty: str) -> None:
        """Send a score in the background, then refresh the top scores."""
        if not self.enabled:
            return
        self.submit_status = "sending"
        body = {"name": name, "score": round(score, 1), "difficulty": difficulty}
        threading.Thread(target=self._submit, args=(body,), daemon=True).start()

    # ------------------------------------------------------------------
    # Worker-thread bodies
    # ------------------------------------------------------------------

    def _fetch(self) -> None:
        try:
            rows = self._post("rpc/top_scores", {"n": TOP_N})
            self.entries = [
                {
                    "name": str(r["name"]),
                    "score": float(r["score"]),
                    "difficulty": str(r["difficulty"]),
                }
                for r in rows
            ]
            self.status = "ready"
        except Exception:
            self.status = "error"

    def _submit(self, body: dict) -> None:
        try:
            self._post("scores", body, prefer="return=minimal")
            self.submit_status = "sent"
        except Exception:
            self.submit_status = "failed"
            return
        self._fetch()

    def _post(self, path: str, body: dict, prefer: str | None = None) -> list:
        headers = {"apikey": WORLD_LEADERBOARD_KEY, "Content-Type": "application/json"}
        # Legacy anon keys are JWTs and also go in Authorization; the newer
        # sb_publishable_ keys are not JWTs and must only be sent as apikey.
        if WORLD_LEADERBOARD_KEY.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {WORLD_LEADERBOARD_KEY}"
        if prefer:
            headers["Prefer"] = prefer
        req = urllib.request.Request(
            f"{WORLD_LEADERBOARD_URL.rstrip('/')}/rest/v1/{path}",
            data=json.dumps(body).encode(),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            raw = resp.read()
        return json.loads(raw) if raw else []
