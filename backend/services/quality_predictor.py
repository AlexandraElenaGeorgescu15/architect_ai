"""
Lightweight quality prediction module.

The goal is to give users an early indicator of whether a generation attempt
is likely to pass validation without waiting for the full pipeline to finish.
This is intentionally heuristic-based so it can run quickly before generation.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

from backend.models.dto import ArtifactType


@dataclass
class QualityPrediction:
    """Structured prediction output."""

    label: str  # high / medium / low
    confidence: float  # 0-1
    score: float  # underlying score 0-1
    reasons: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class QualityPredictor:
    """
    Simple heuristic predictor that estimates quality based on available signals.

    Signals considered:
    - Meeting notes depth (length, bullet markers)
    - Context richness (presence of RAG/KG/pattern data)
    - Artifact type complexity (ERG vs code)
    - Prior validation telemetry (if passed in context metadata)
    """

    def predict(
        self,
        artifact_type: ArtifactType,
        meeting_notes: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> QualityPrediction:
        score = 0.55  # baseline neutral confidence
        reasons: Dict[str, float] = {}

        notes = meeting_notes or ""
        notes_length = len(notes)

        # Meeting notes depth
        if notes_length > 1200:
            score += 0.2
            reasons["notes_depth"] = 0.2
        elif notes_length > 600:
            score += 0.1
            reasons["notes_depth"] = 0.1
        elif notes_length < 200:
            score -= 0.15
            reasons["notes_depth"] = -0.15

        # Structure cues (bullet points, numbered lists)
        if any(token in notes for token in ["- ", "* ", "1.", "2."]):
            score += 0.05
            reasons["notes_structure"] = 0.05

        # Context richness (rag/kgs/patterns)
        rag_chunks = len(context.get("sources", {}).get("rag", {}).get("snippets", [])) if context else 0
        if rag_chunks >= 15:
            score += 0.1
            reasons["context_rag"] = 0.1
        elif rag_chunks == 0:
            score -= 0.1
            reasons["context_rag"] = -0.1

        if context and context.get("sources", {}).get("knowledge_graph"):
            score += 0.05
            reasons["knowledge_graph"] = 0.05

        if context and context.get("sources", {}).get("pattern_mining"):
            score += 0.03
            reasons["pattern_signals"] = 0.03

        # Artifact complexity adjustments
        complex_types = {
            ArtifactType.CODE_PROTOTYPE,
            ArtifactType.API_DOCS,
            ArtifactType.DEV_VISUAL_PROTOTYPE,
        }
        if artifact_type in complex_types:
            score -= 0.1
            reasons["artifact_complexity"] = -0.1

        # Clamp and derive label
        score = max(0.0, min(1.0, score))

        if score >= 0.75:
            label = "high"
        elif score >= 0.5:
            label = "medium"
        else:
            label = "low"

        return QualityPrediction(
            label=label,
            confidence=score,
            score=score,
            reasons=reasons,
        )


_predictor: Optional[QualityPredictor] = None


def get_quality_predictor() -> QualityPredictor:
    global _predictor  # noqa: PLW0603 - intentional singleton
    if _predictor is None:
        _predictor = QualityPredictor()
    return _predictor


