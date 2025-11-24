"""
Custom Validator Service

Allows teams to define additional validation rules (e.g., regex checks) that run
after the built-in validator. Rules are stored in config/custom_validators.json
so they can be versioned with the project.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import uuid4

from backend.core.config import settings
from backend.models.dto import ArtifactType


class CustomValidatorService:
    """Loads, persists, and executes custom validators."""

    def __init__(self):
        base_path = Path(settings.base_path)
        self.validators_path = base_path / "config" / "custom_validators.json"
        self.validators: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if not self.validators_path.exists():
            self.validators = []
            return
        with self.validators_path.open("r", encoding="utf-8") as fp:
            self.validators = json.load(fp) or []

    def _save(self) -> None:
        self.validators_path.parent.mkdir(parents=True, exist_ok=True)
        with self.validators_path.open("w", encoding="utf-8") as fp:
            json.dump(self.validators, fp, indent=2)

    def list_validators(self) -> List[Dict[str, Any]]:
        return self.validators

    def add_validator(self, validator: Dict[str, Any]) -> Dict[str, Any]:
        validator["id"] = validator.get("id") or uuid4().hex
        self.validators.append(validator)
        self._save()
        return validator

    def remove_validator(self, validator_id: str) -> bool:
        original_len = len(self.validators)
        self.validators = [v for v in self.validators if v.get("id") != validator_id]
        if len(self.validators) != original_len:
            self._save()
            return True
        return False

    def run_validators(
        self,
        artifact_type: ArtifactType,
        content: str,
    ) -> List[Dict[str, Any]]:
        """Execute applicable validators and return results."""
        results: List[Dict[str, Any]] = []
        for validator in self.validators:
            targets = validator.get("artifact_types") or ["*"]
            if "*" not in targets and artifact_type.value not in targets:
                continue

            rule_type = validator.get("rule_type")
            if rule_type == "regex":
                pattern = validator.get("pattern")
                if not pattern:
                    continue
                if not re.search(pattern, content, re.MULTILINE):
                    results.append(
                        {
                            "id": validator.get("id"),
                            "name": validator.get("name", "Custom Validator"),
                            "message": validator.get("message", "Pattern not found."),
                            "severity": validator.get("severity", "error"),
                        }
                    )
            # Future: add other rule types (jsonpath, LLM, etc.)

        return results


_custom_validator_service: Optional[CustomValidatorService] = None


def get_custom_validator_service() -> CustomValidatorService:
    global _custom_validator_service  # noqa: PLW0603
    if _custom_validator_service is None:
        _custom_validator_service = CustomValidatorService()
    return _custom_validator_service

