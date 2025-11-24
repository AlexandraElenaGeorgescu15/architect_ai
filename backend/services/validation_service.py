"""
Validation Service - Refactored from validation/output_validator.py
Validates generated artifacts with quality scoring.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import re

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.models.dto import ArtifactType, ValidationResultDTO
from backend.core.config import settings
from backend.services.custom_validator_service import get_custom_validator_service

logger = logging.getLogger(__name__)

# Optional imports for validation (graceful degradation)
try:
    from validation.output_validator import ArtifactValidator
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False
    logger.warning("ArtifactValidator not available. Validation will be limited.")


class ValidationService:
    """
    Validation service for artifact quality assurance.
    
    Features:
    - Artifact-specific validation (ERD, Architecture, Sequence, etc.)
    - Quality scoring (0-100)
    - Multiple validators per artifact type
    - Validation caching
    - Detailed validation reports
    """
    
    def __init__(self):
        """Initialize Validation Service."""
        self.validator = ArtifactValidator() if VALIDATOR_AVAILABLE else None
        self.custom_validator_service = get_custom_validator_service()
        
        logger.info("Validation Service initialized")
    
    async def validate_artifact(
        self,
        artifact_type: ArtifactType,
        content: str,
        meeting_notes: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResultDTO:
        """
        Validate an artifact and return quality score.
        
        Args:
            artifact_type: Type of artifact
            content: Artifact content to validate
            meeting_notes: Optional meeting notes for context validation
            context: Optional additional context
        
        Returns:
            ValidationResultDTO with score, is_valid, and details
        """
        if not content or not content.strip():
            return ValidationResultDTO(
                score=0.0,
                is_valid=False,
                validators={},
                errors=["Empty artifact content"],
                warnings=[]
            )
        
        # Use ArtifactValidator if available
        if self.validator:
            try:
                result = self.validator.validate(
                    artifact_type=artifact_type.value,
                    content=content,
                    meeting_notes=meeting_notes or ""
                )
                
                dto = ValidationResultDTO(
                    score=result.get("score", 0.0),
                    is_valid=result.get("is_valid", False),
                    validators=result.get("validators", {}),
                    errors=result.get("errors", []),
                    warnings=result.get("warnings", [])
                )
                return self._apply_custom_validators(artifact_type, content, dto)
            except Exception as e:
                logger.error(f"Error in ArtifactValidator: {e}", exc_info=True)
                # Fall through to basic validation
        
        # Fallback: Basic validation
        dto = self._basic_validation(artifact_type, content, meeting_notes)
        return self._apply_custom_validators(artifact_type, content, dto)
    
    def _basic_validation(
        self,
        artifact_type: ArtifactType,
        content: str,
        meeting_notes: Optional[str] = None
    ) -> ValidationResultDTO:
        """
        Basic validation when ArtifactValidator is not available.
        
        Args:
            artifact_type: Type of artifact
            content: Artifact content
            meeting_notes: Optional meeting notes
        
        Returns:
            ValidationResultDTO
        """
        errors = []
        warnings = []
        validators = {}
        score = 100.0
        
        # Basic checks
        if not content or len(content.strip()) < 10:
            errors.append("Content too short")
            score -= 50.0
        
        # Artifact-specific validation
        if artifact_type.value.startswith("mermaid_"):
            # Mermaid diagram validation
            mermaid_errors = self._validate_mermaid(content)
            errors.extend(mermaid_errors)
            score -= len(mermaid_errors) * 10.0
            
            # Check for required diagram type
            diagram_type = artifact_type.value.replace("mermaid_", "")
            if diagram_type not in content.lower():
                warnings.append(f"Expected {diagram_type} diagram type")
                score -= 5.0
        
        elif artifact_type == ArtifactType.CODE_PROTOTYPE:
            # Code validation
            code_errors = self._validate_code(content)
            errors.extend(code_errors)
            score -= len(code_errors) * 15.0
        
        elif artifact_type == ArtifactType.API_DOCS:
            # API docs validation
            api_errors = self._validate_api_docs(content)
            errors.extend(api_errors)
            score -= len(api_errors) * 10.0
        
        # Meeting notes relevance (if provided)
        if meeting_notes:
            relevance_score = self._check_relevance(content, meeting_notes)
            if relevance_score < 0.5:
                warnings.append("Low relevance to meeting notes")
                score -= 10.0
        
        # Clamp score to 0-100
        score = max(0.0, min(100.0, score))
        is_valid = score >= 60.0 and len(errors) == 0
        
        validators["basic"] = {
            "score": score,
            "errors": len(errors),
            "warnings": len(warnings)
        }
        
        return ValidationResultDTO(
            score=score,
            is_valid=is_valid,
            validators=validators,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_mermaid(self, content: str) -> List[str]:
        """Validate Mermaid diagram syntax."""
        errors = []
        
        # Check for Mermaid diagram type
        diagram_types = [
            "erDiagram", "flowchart", "graph", "sequenceDiagram",
            "classDiagram", "stateDiagram", "gantt", "pie", "journey"
        ]
        
        has_diagram_type = any(dt in content for dt in diagram_types)
        if not has_diagram_type:
            errors.append("Missing Mermaid diagram type declaration")
        
        # Check for balanced brackets
        if content.count('{') != content.count('}'):
            errors.append("Unbalanced curly braces")
        
        if content.count('[') != content.count(']'):
            errors.append("Unbalanced square brackets")
        
        # Check for basic syntax
        if '-->' not in content and '---' not in content and '||' not in content:
            if "erDiagram" not in content and "gantt" not in content and "pie" not in content:
                warnings.append("No relationships/connections found")
        
        return errors
    
    def _validate_code(self, content: str) -> List[str]:
        """Validate code prototype."""
        errors = []
        
        # Check for code structure
        if 'def ' not in content and 'function ' not in content and 'class ' not in content:
            if 'export ' not in content and 'const ' not in content:
                warnings.append("No functions or classes found")
        
        # Check for syntax errors (basic)
        if content.count('(') != content.count(')'):
            errors.append("Unbalanced parentheses")
        
        if content.count('[') != content.count(']'):
            errors.append("Unbalanced square brackets")
        
        return errors
    
    def _validate_api_docs(self, content: str) -> List[str]:
        """Validate API documentation."""
        errors = []
        
        # Check for API endpoints
        api_patterns = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        has_endpoints = any(pattern in content for pattern in api_patterns)
        
        if not has_endpoints:
            errors.append("No API endpoints found")
        
        # Check for paths
        if '/' not in content and 'api' not in content.lower():
            warnings.append("No API paths found")
        
        return errors
    
    def _check_relevance(self, content: str, meeting_notes: str) -> float:
        """
        Check relevance of content to meeting notes.
        
        Returns:
            Relevance score (0.0 to 1.0)
        """
        if not meeting_notes:
            return 1.0
        
        # Extract key terms from meeting notes
        meeting_words = set(word.lower() for word in meeting_notes.split() if len(word) > 3)
        content_words = set(word.lower() for word in content.split() if len(word) > 3)
        
        # Calculate overlap
        if not meeting_words:
            return 1.0
        
        overlap = len(meeting_words & content_words)
        relevance = overlap / len(meeting_words)
        
        return min(1.0, relevance)
    
    def _apply_custom_validators(
        self,
        artifact_type: ArtifactType,
        content: str,
        validation: ValidationResultDTO,
    ) -> ValidationResultDTO:
        """Apply user-configured validators."""
        custom_results = self.custom_validator_service.run_validators(artifact_type, content)
        if not custom_results:
            return validation
        
        for rule in custom_results:
            key = f"custom:{rule.get('id')}"
            validation.validators[key] = {
                "severity": rule.get("severity", "error"),
                "message": rule.get("message"),
            }
            message = rule.get("message", "Custom validator triggered.")
            severity = rule.get("severity", "error")
            if severity == "warning":
                validation.warnings.append(message)
            else:
                validation.errors.append(message)
        
        if validation.errors:
            validation.is_valid = False
            validation.score = max(0.0, validation.score - 5.0 * len(validation.errors))
        
        return validation
    
    def validate_batch(
        self,
        artifacts: List[Dict[str, Any]]
    ) -> List[ValidationResultDTO]:
        """
        Validate multiple artifacts in batch.
        
        Args:
            artifacts: List of artifact dictionaries with 'type', 'content', 'meeting_notes'
        
        Returns:
            List of ValidationResultDTO
        """
        results = []
        
        for artifact in artifacts:
            artifact_type = ArtifactType(artifact.get("type", "mermaid_erd"))
            content = artifact.get("content", "")
            meeting_notes = artifact.get("meeting_notes")
            
            # Run validation (would be async in production)
            import asyncio
            result = asyncio.run(
                self.validate_artifact(
                    artifact_type=artifact_type,
                    content=content,
                    meeting_notes=meeting_notes
                )
            )
            results.append(result)
        
        return results


# Global service instance
_service: Optional[ValidationService] = None


def get_service() -> ValidationService:
    """Get or create global Validation Service instance."""
    global _service
    if _service is None:
        _service = ValidationService()
    return _service



