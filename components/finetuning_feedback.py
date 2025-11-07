"""Fine-tuning feedback persistence utilities."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class FeedbackEntry:
    """Single feedback item captured from the user."""

    id: str
    artifact_type: str
    issue: str
    expected_style: str
    reference_code: str
    meeting_context: str
    created_at: str

    @classmethod
    def create(
        cls,
        artifact_type: str,
        issue: str,
        expected_style: str,
        reference_code: str = "",
        meeting_context: str = "",
    ) -> "FeedbackEntry":
        return cls(
            id=str(uuid.uuid4()),
            artifact_type=artifact_type.strip() or "unspecified",
            issue=issue.strip(),
            expected_style=expected_style.strip(),
            reference_code=reference_code.strip(),
            meeting_context=meeting_context.strip(),
            created_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        )


class FinetuningFeedbackStore:
    """JSONL-backed persistence layer for fine-tuning feedback."""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: List[FeedbackEntry] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.storage_path.exists():
            self._entries = []
            return

        entries: List[FeedbackEntry] = []
        with self.storage_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                payload = line.strip()
                if not payload:
                    continue
                try:
                    data = json.loads(payload)
                    entries.append(FeedbackEntry(**data))
                except Exception:
                    # Ignore corrupt lines but continue loading remaining data.
                    continue
        self._entries = entries

    def _save(self) -> None:
        with self.storage_path.open("w", encoding="utf-8") as fh:
            for entry in self._entries:
                fh.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def list_feedback(self) -> List[FeedbackEntry]:
        return list(self._entries)

    def add_feedback(self, entry: FeedbackEntry) -> FeedbackEntry:
        self._entries.append(entry)
        self._save()
        return entry

    def delete_feedback(self, entry_id: str) -> bool:
        original_len = len(self._entries)
        self._entries = [entry for entry in self._entries if entry.id != entry_id]
        if len(self._entries) != original_len:
            self._save()
            return True
        return False

    def to_training_examples(self) -> List[Dict[str, str]]:
        """Transform feedback into instruction/input/output examples."""

        examples: List[Dict[str, str]] = []
        for entry in self._entries:
            input_parts = [
                f"Artifact Type: {entry.artifact_type}",
                f"Issue: {entry.issue}",
            ]
            if entry.meeting_context:
                input_parts.append(f"Meeting Context: {entry.meeting_context}")
            if entry.reference_code:
                input_parts.append("Reference Code:\n" + entry.reference_code)

            # Use expected_style if provided, fallback to reference_code, then generic message
            output_payload = entry.expected_style or entry.reference_code
            
            # Check for empty strings (not just None)
            if not output_payload or not output_payload.strip():
                output_payload = (
                    "Adjust the artifact to match the documented styling and architectural"
                    " conventions used throughout the project."
                )

            examples.append(
                {
                    "instruction": "Resolve the feedback for this artifact while respecting project conventions.",
                    "input": "\n\n".join(input_parts),
                    "output": output_payload,
                    "source": "feedback",  # Tag for UI filtering
                }
            )
        return examples

    def summary_by_artifact(self) -> Dict[str, int]:
        summary: Dict[str, int] = {}
        for entry in self._entries:
            summary[entry.artifact_type] = summary.get(entry.artifact_type, 0) + 1
        return summary


_GLOBAL_STORE: Optional[FinetuningFeedbackStore] = None


def get_feedback_store() -> FinetuningFeedbackStore:
    global _GLOBAL_STORE
    if _GLOBAL_STORE is None:
        base_dir = Path(__file__).parent.parent
        storage_path = base_dir / "outputs" / "finetuning" / "feedback.jsonl"
        _GLOBAL_STORE = FinetuningFeedbackStore(storage_path)
    return _GLOBAL_STORE


# Convenience singleton for importers.
feedback_store = get_feedback_store()

