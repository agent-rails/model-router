from __future__ import annotations

import json
from pathlib import Path

from model_router.telemetry import RoutingEvent


def event_to_json(event: RoutingEvent) -> dict:
    return {
        "timestamp": event.timestamp.isoformat(),
        "category": event.category,
        "tags": sorted(event.tags),
        "prompt_chars": event.prompt_chars,
        "is_agentic": event.is_agentic,
        "tool_schema_count": event.tool_schema_count,
        "decision": {
            "model": event.decision.model.value,
            "effort": event.decision.effort.value,
            "tier": event.decision.tier.value,
            "source": event.decision.source.value,
            "reason": event.decision.reason,
        },
    }


class JsonlSink:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path).expanduser()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, event: RoutingEvent) -> None:
        line = json.dumps(event_to_json(event))
        with self._path.open("a") as f:
            f.write(line + "\n")

    def read_all(self) -> list[dict]:
        if not self._path.exists():
            return []
        with self._path.open() as f:
            return [json.loads(line) for line in f if line.strip()]
