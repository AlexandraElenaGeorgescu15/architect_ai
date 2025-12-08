"""
Template Service

Loads curated artifact templates so users can kick-start projects with
pre-filled meeting notes and recommended artifact bundles.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.core.config import settings
from backend.models.dto import ArtifactType


class TemplateService:
    """Loads and serves template metadata."""

    def __init__(self):
        base_path = Path(settings.base_path)
        self.templates_path = base_path / "config" / "templates" / "templates.json"
        self._templates: List[Dict[str, Any]] = []
        
        # Log initialization
        from backend.core.logger import get_logger
        logger = get_logger(__name__)
        logger.info(f"Initializing TemplateService with path: {self.templates_path}")
        
        self._load_templates()

    def _load_templates(self) -> None:
        from backend.core.logger import get_logger
        logger = get_logger(__name__)
        
        if not self.templates_path.exists():
            logger.warning(f"Templates file not found at {self.templates_path}")
            self._templates = []
            return

        try:
            with self.templates_path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)

            parsed = []
            for item in data:
                item["recommended_artifacts"] = [
                    ArtifactType(artifact) for artifact in item.get("recommended_artifacts", [])
                ]
                parsed.append(item)
            self._templates = parsed
            logger.info(f"Loaded {len(self._templates)} templates")
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
            self._templates = []

    def list_templates(self) -> List[Dict[str, Any]]:
        return self._templates

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        return next((tpl for tpl in self._templates if tpl.get("id") == template_id), None)


_template_service: Optional[TemplateService] = None


def get_template_service() -> TemplateService:
    global _template_service  # noqa: PLW0603 - intentional singleton
    if _template_service is None:
        _template_service = TemplateService()
    return _template_service


