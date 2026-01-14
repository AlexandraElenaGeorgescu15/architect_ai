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
from dataclasses import dataclass

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
        logger.info(f"🔍 [VALIDATION] Starting validation: artifact_type={artifact_type.value}, "
                   f"content_length={len(content) if content else 0}, "
                   f"has_meeting_notes={bool(meeting_notes)}, has_context={bool(context)}")
        
        if not content or not content.strip():
            logger.warning(f"⚠️ [VALIDATION] Empty artifact content, returning invalid result")
            return ValidationResultDTO(
                score=0.0,
                is_valid=False,
                validators={},
                errors=["Empty artifact content"],
                warnings=[]
            )
        
        # Use ArtifactValidator if available
        if self.validator:
            logger.info(f"✅ [VALIDATION] Using ArtifactValidator for validation")
            try:
                # Build context dict for ArtifactValidator
                validation_context = context or {}
                if meeting_notes:
                    validation_context["meeting_notes"] = meeting_notes
                logger.debug(f"📋 [VALIDATION] Validation context keys: {list(validation_context.keys())}")
                
                # ArtifactValidator.validate returns a ValidationResult dataclass.
                # Convert it into our DTO representation.
                result = self.validator.validate(
                    artifact_type=artifact_type.value,
                    content=content,
                    context=validation_context
                )

                score = float(getattr(result, "score", 0.0) or 0.0)
                is_valid = bool(getattr(result, "is_valid", False))
                result_errors = list(getattr(result, "errors", []) or [])
                result_warnings = list(getattr(result, "warnings", []) or [])

                logger.info(
                    f"📊 [VALIDATION] ArtifactValidator result: score={score:.1f}, "
                    f"is_valid={is_valid}, "
                    f"errors={len(result_errors)}, "
                    f"warnings={len(result_warnings)}"
                )

                dto = ValidationResultDTO(
                    score=score,
                    is_valid=is_valid,
                    validators={
                        "artifact_validator": {
                            "score": score,
                            "errors": len(result_errors),
                            "warnings": len(result_warnings),
                        }
                    },
                    errors=result_errors,
                    warnings=result_warnings,
                )
                final_dto = self._apply_custom_validators(artifact_type, content, dto)
                logger.info(
                    f"✅ [VALIDATION] Final validation result: score={final_dto.score:.1f}, "
                    f"is_valid={final_dto.is_valid}"
                )
                return final_dto
            except Exception as e:
                logger.error(f"❌ [VALIDATION] Error in ArtifactValidator: {e}", exc_info=True)
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
            # Mermaid diagram validation (uses cleaned content internally)
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
        
        elif artifact_type.value.startswith("html_"):
            # HTML validation
            html_errors = self._validate_html(content)
            errors.extend(html_errors)
            score -= len(html_errors) * 10.0
        
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
    
    def _fix_erd_syntax(self, content: str) -> str:
        """
        Fix ERD diagrams that incorrectly use class diagram syntax.
        Converts: class USER { - id (primary key) } 
        To: USER { int id PK }
        """
        import re
        
        # Only fix if this is an ERD diagram
        if "erDiagram" not in content:
            return content
        
        # Pattern to match class diagram syntax in ERD: class ENTITY { - field (description) }
        class_pattern = r'class\s+(\w+)\s*\{([^}]+)\}'
        
        def convert_class_to_erd(match):
            entity_name = match.group(1)
            fields_text = match.group(2)
            
            # Parse fields: "- id (primary key)" -> "int id PK"
            erd_fields = []
            for line in fields_text.split('\n'):
                line = line.strip()
                if not line or not line.startswith('-'):
                    continue
                
                # Remove leading dash and whitespace
                field_text = line[1:].strip()
                
                # Extract field name and description
                # Pattern: "id (primary key)" or "username" or "user_id (foreign key references USER(id))"
                field_match = re.match(r'(\w+)(?:\s*\(([^)]+)\))?', field_text)
                if field_match:
                    field_name = field_match.group(1)
                    description = field_match.group(2) if field_match.group(2) else ""
                    
                    # Determine type (default to string/int based on field name)
                    field_type = "string"
                    if field_name.endswith("_id") or field_name == "id":
                        field_type = "int"
                    elif "date" in field_name.lower() or "time" in field_name.lower():
                        field_type = "datetime"
                    elif "boolean" in description.lower() or field_name.startswith("is_") or field_name.startswith("has_"):
                        field_type = "boolean"
                    
                    # Determine PK/FK
                    key_suffix = ""
                    if "primary key" in description.lower() or field_name == "id":
                        key_suffix = " PK"
                    elif "foreign key" in description.lower() or (field_name.endswith("_id") and field_name != "id"):
                        key_suffix = " FK"
                    
                    erd_fields.append(f"        {field_type} {field_name}{key_suffix}")
            
            # Return ERD format
            if erd_fields:
                return f"{entity_name} {{\n" + "\n".join(erd_fields) + "\n    }}"
            else:
                return f"{entity_name} {{\n        int id PK\n    }}"
        
        # Replace all class definitions with ERD format
        fixed = re.sub(class_pattern, convert_class_to_erd, content, flags=re.MULTILINE | re.DOTALL)
        
        # Also fix "CLASS ENTITY" (uppercase)
        class_pattern_upper = r'CLASS\s+(\w+)\s*\{([^}]+)\}'
        fixed = re.sub(class_pattern_upper, convert_class_to_erd, fixed, flags=re.MULTILINE | re.DOTALL)
        
        return fixed
    
    def _extract_mermaid_diagram(self, content: str) -> str:
        """
        Extract Mermaid diagram code from markdown code blocks or plain text.
        Removes any surrounding text and returns only the diagram code.
        """
        import re
        
        # Try to extract from markdown code blocks first
        mermaid_pattern = r'```(?:mermaid)?\s*\n(.*?)```'
        matches = re.findall(mermaid_pattern, content, re.DOTALL | re.IGNORECASE)
        if matches:
            # Return the first (and usually only) mermaid code block
            diagram = matches[0].strip()
            # Remove any leading/trailing whitespace and newlines
            return diagram.strip()
        
        # If no code block found, check if content already is mermaid code
        # Look for mermaid diagram type declarations
        diagram_types = [
            "erDiagram", "flowchart", "graph", "sequenceDiagram",
            "classDiagram", "stateDiagram", "gantt", "pie", "journey",
            "gitgraph", "mindmap", "timeline", "C4Context", "C4Container",
            "C4Component", "C4Deployment"
        ]
        
        # If content contains a diagram type, try to extract just the diagram
        for dt in diagram_types:
            if dt in content:
                idx = content.find(dt)
                # Extract from diagram type onwards
                diagram = content[idx:].strip()
                
                # Try to find the end of the diagram by looking for balanced braces
                # For most diagram types, we can find the last meaningful line
                lines = diagram.split('\n')
                diagram_lines = []
                brace_count = 0
                bracket_count = 0
                paren_count = 0
                
                for line in lines:
                    # Count braces/brackets to detect when diagram ends
                    brace_count += line.count('{') - line.count('}')
                    bracket_count += line.count('[') - line.count(']')
                    paren_count += line.count('(') - line.count(')')
                    
                    # Add line if it looks like diagram content
                    line_stripped = line.strip()
                    if line_stripped and not line_stripped.startswith('**') and not line_stripped.startswith('#'):
                        diagram_lines.append(line)
                    
                    # Stop if we hit explanatory text (common patterns)
                    if (line_stripped.startswith('**Explanation') or 
                        line_stripped.startswith('**Note') or
                        line_stripped.startswith('Explanation') or
                        (line_stripped.startswith('1.') and len(diagram_lines) > 5)):
                        break
                
                # If we collected lines, return them
                if diagram_lines:
                    extracted = '\n'.join(diagram_lines).strip()
                    # Remove any trailing markdown formatting
                    extracted = re.sub(r'\*\*.*?\*\*', '', extracted)  # Remove bold text
                    extracted = re.sub(r'^#+\s+.*$', '', extracted, flags=re.MULTILINE)  # Remove headers
                    return extracted.strip()
                
                # Fallback: return from diagram type to end (original behavior)
                return diagram
        
        # If no mermaid found, return original content (will fail validation)
        return content
    
    def _validate_mermaid(self, content: str) -> List[str]:
        """Validate Mermaid diagram syntax."""
        errors: List[str] = []
        warnings: List[str] = []
        
        # Extract clean mermaid diagram first
        clean_content = self._extract_mermaid_diagram(content)
        
        # Fix ERD syntax if it's using class diagram syntax
        if "erDiagram" in clean_content and ("class " in clean_content or "CLASS " in clean_content):
            clean_content = self._fix_erd_syntax(clean_content)
        
        # Check for Mermaid diagram type
        diagram_types = [
            "erDiagram", "flowchart", "graph", "sequenceDiagram",
            "classDiagram", "stateDiagram", "gantt", "pie", "journey",
            "gitgraph", "mindmap", "timeline", "C4Context", "C4Container",
            "C4Component", "C4Deployment"
        ]
        
        has_diagram_type = any(dt in clean_content for dt in diagram_types)
        if not has_diagram_type:
            errors.append("Missing Mermaid diagram type declaration")
        
        # Check for balanced brackets
        if clean_content.count('{') != clean_content.count('}'):
            errors.append("Unbalanced curly braces")
        
        if clean_content.count('[') != clean_content.count(']'):
            errors.append("Unbalanced square brackets")
        
        # Check for basic syntax
        if '-->' not in clean_content and '---' not in clean_content and '||' not in clean_content:
            if "erDiagram" not in clean_content and "gantt" not in clean_content and "pie" not in clean_content:
                warnings.append("No relationships/connections found")
        
        return errors
    
    def _validate_code(self, content: str) -> List[str]:
        """Validate code prototype."""
        errors: List[str] = []
        warnings: List[str] = []
        
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
        errors: List[str] = []
        warnings: List[str] = []
        
        # Check for API endpoints
        api_patterns = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        has_endpoints = any(pattern in content for pattern in api_patterns)
        
        if not has_endpoints:
            errors.append("No API endpoints found")
        
        # Check for paths
        if '/' not in content and 'api' not in content.lower():
            warnings.append("No API paths found")
        
        return errors
    
    def _validate_html(self, content: str) -> List[str]:
        """Validate HTML artifacts."""
        errors: List[str] = []
        warnings: List[str] = []
        
        # Check for basic HTML structure
        if '<html' not in content.lower() and '<div' not in content.lower() and '<body' not in content.lower():
            errors.append("No HTML structure found")
        
        # Check for balanced tags (basic)
        open_tags = content.count('<')
        close_tags = content.count('>')
        if open_tags != close_tags:
            warnings.append("Unbalanced HTML tags detected")
        
        # Check for common HTML elements
        has_elements = any(tag in content.lower() for tag in ['<div', '<span', '<button', '<input', '<form', '<table', '<ul', '<ol'])
        if not has_elements:
            warnings.append("No common HTML elements found")
        
        # Check for proper closing tags (basic check)
        if content.count('</div>') > 0 and content.count('<div') > content.count('</div>'):
            warnings.append("Some div tags may not be properly closed")
        
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


# =============================================================================
# Diagram Improvement Service
# =============================================================================
# NOTE: This was extracted from backend/api/ai.py to maintain proper separation
# of concerns. API routes should only coordinate; services should do the work.
# =============================================================================

@dataclass
class DiagramImprovementResult:
    """Result of a diagram improvement operation."""
    success: bool
    improved_code: str
    improvements_made: list
    error: Optional[str] = None
    model_used: Optional[str] = None


async def improve_mermaid_diagram(
    mermaid_code: str,
    diagram_type: str,
    improvement_focus: Optional[list] = None
) -> DiagramImprovementResult:
    """
    AI-powered diagram improvement service.
    
    Extracted from API layer to maintain separation of concerns.
    The API route should only coordinate; this service does the actual work.
    
    Args:
        mermaid_code: The Mermaid diagram code to improve
        diagram_type: The type of diagram (e.g., 'mermaid_erd', 'mermaid_flowchart')
        improvement_focus: List of areas to focus on (e.g., ['syntax', 'colors'])
    
    Returns:
        DiagramImprovementResult with success status, improved code, and details
    """
    from backend.services.model_service import get_service as get_model_service
    from backend.services.enhanced_generation import get_enhanced_service
    from rag.filters import sanitize_prompt_input
    
    try:
        logger.info(f"🔧 [DIAGRAM_IMPROVE] Starting improvement: type={diagram_type}")
        
        # Get model routing
        model_service = get_model_service()
        routing = model_service.get_routing_for_artifact(diagram_type)
        
        # Build improvement areas
        improvement_areas = ", ".join(improvement_focus or ["syntax", "colors"])
        
        # Detect diagram type from code
        diagram_start = _detect_diagram_type(mermaid_code)
        
        # Sanitize input to prevent prompt injection
        safe_code = sanitize_prompt_input(mermaid_code, max_length=8000)
        
        # Build improvement prompt
        prompt = f"""You are a Mermaid diagram expert. Improve this diagram while preserving its structure and meaning.

INPUT DIAGRAM:
{safe_code}

IMPROVEMENT FOCUS: {improvement_areas}

RULES:
1. Fix any syntax errors (missing quotes, brackets, etc.)
2. Keep all existing nodes and relationships
3. Add colors using classDef if not present
4. Do NOT add explanations or comments
5. Do NOT wrap in markdown code blocks
6. Start output directly with "{diagram_start or 'the diagram keyword'}"

OUTPUT (improved Mermaid code only):"""
        
        # Call AI generation service
        generation_service = get_enhanced_service()
        result = await generation_service.generate_with_fallback(
            prompt=prompt,
            model_routing=routing,
            temperature=0.3
        )
        
        if not result.success or not result.content or len(result.content.strip()) < 10:
            logger.warning(f"⚠️ [DIAGRAM_IMPROVE] AI generation failed")
            return DiagramImprovementResult(
                success=False,
                improved_code=mermaid_code,
                improvements_made=[],
                error=result.error or "AI returned empty response"
            )
        
        # Extract clean diagram code
        from backend.services.artifact_cleaner import get_cleaner
        cleaner = get_cleaner()
        improved_code = cleaner.clean_mermaid(result.content)
        
        if not improved_code or len(improved_code.strip()) < 10:
            logger.warning(f"⚠️ [DIAGRAM_IMPROVE] Extraction resulted in empty content")
            return DiagramImprovementResult(
                success=False,
                improved_code=mermaid_code,
                improvements_made=[],
                error="AI returned incomplete diagram"
            )
        
        # Validate diagram type consistency
        improved_lower = improved_code.lower().strip()
        if diagram_start and not improved_lower.startswith(diagram_start.lower()):
            improved_code = _fix_diagram_type(improved_code, diagram_start)
        
        logger.info(f"✅ [DIAGRAM_IMPROVE] Successfully improved diagram")
        return DiagramImprovementResult(
            success=True,
            improved_code=improved_code,
            improvements_made=["Syntax fixed", "Structure validated"],
            model_used=getattr(result, 'model_used', None)
        )
        
    except Exception as e:
        logger.error(f"❌ [DIAGRAM_IMPROVE] Error: {e}", exc_info=True)
        return DiagramImprovementResult(
            success=False,
            improved_code=mermaid_code,
            improvements_made=[],
            error=str(e)
        )


def _detect_diagram_type(mermaid_code: str) -> str:
    """Detect the diagram type from Mermaid code."""
    code_lower = mermaid_code.lower().strip()
    
    diagram_types = [
        ("erdiagram", "erDiagram"),
        ("graph", "graph"),
        ("flowchart", "flowchart"),
        ("sequencediagram", "sequenceDiagram"),
        ("classdiagram", "classDiagram"),
        ("statediagram", "stateDiagram-v2"),
        ("gantt", "gantt"),
        ("pie", "pie"),
        ("journey", "journey"),
        ("gitgraph", "gitgraph"),
        ("mindmap", "mindmap"),
        ("timeline", "timeline"),
    ]
    
    for prefix, proper_name in diagram_types:
        if code_lower.startswith(prefix):
            return proper_name
    
    return ""


def _fix_diagram_type(improved_code: str, expected_type: str) -> str:
    """Fix diagram type if it's missing or incorrect."""
    improved_lower = improved_code.lower().strip()
    
    diagram_keywords = [
        "erDiagram", "flowchart", "graph", "sequenceDiagram",
        "classDiagram", "stateDiagram", "gantt", "pie", "journey",
        "gitgraph", "mindmap", "timeline"
    ]
    
    for dt in diagram_keywords:
        if dt.lower() in improved_lower:
            idx = improved_lower.find(dt.lower())
            return improved_code[idx:].strip()
    
    return improved_code



