"""Utility functions for fine-tuning configuration/settings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yaml = None


DEFAULT_SETTINGS: Dict[str, Any] = {
    "max_chunks": 500,
    "preferred_paths": [
        # Generic defaults (cross-project): prioritise likely source roots
        "src/app",
        "src",
        "Controllers",
        "controllers",
        "Services",
        "services",
        "Models",
        "models",
        "Dtos",
        "dtos",
    ],
    "exclude_paths": [
        "WeatherForecast",
        "SampleData",
        "architect_ai_cursor_poc",
    ],
    "token_overlap": 2,
    "intent_split_markers": ["-", "*", "•"],
}


SETTINGS_LOCATIONS = [
    Path("finetuning_config.json"),
    Path("finetuning_config.yaml"),
    Path("finetuning_config.yml"),
    Path("architect_ai_cursor_poc/finetuning_config.json"),
    Path("architect_ai_cursor_poc/finetuning_config.yaml"),
    Path("architect_ai_cursor_poc/finetuning_config.yml"),
]


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML not installed; cannot read YAML configuration")
    return yaml.safe_load(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def load_finetuning_settings() -> Dict[str, Any]:
    """Load settings from disk, falling back to defaults."""

    for candidate in SETTINGS_LOCATIONS:
        if candidate.exists():
            try:
                if candidate.suffix.lower() in {".json"}:
                    data = _load_json(candidate)
                else:
                    data = _load_yaml(candidate)
                if isinstance(data, dict):
                    merged = {**DEFAULT_SETTINGS, **data}
                    return merged
            except Exception as exc:  # pragma: no cover - defensive
                print(f"[WARN] Failed to load finetuning settings from {candidate}: {exc}")
                continue
    return DEFAULT_SETTINGS.copy()


