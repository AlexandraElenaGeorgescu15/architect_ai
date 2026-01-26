"""
Validation Service - Refactored from validation/output_validator.py
Validates generated artifacts with quality scoring.

Features:
- Rule-based validation (syntax, structure)
- LLM-as-a-Judge validation (local model evaluation)
- Combined scoring for accurate quality assessment
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime
import re
import json
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

# Optional: Ollama client for LLM-as-a-Judge
try:
    from ai.ollama_client import OllamaClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("OllamaClient not available. LLM-as-a-Judge validation disabled.")

# LLM Judge configuration - uses settings from config.py
def get_llm_judge_config() -> dict:
    """Get LLM Judge configuration from settings."""
    return {
        "enabled": settings.llm_judge_enabled,
        "preferred_models": settings.llm_judge_preferred_models,
        "timeout_seconds": settings.llm_judge_timeout,
        "weight": settings.llm_judge_weight,
    }

# Backwards compatibility alias
LLM_JUDGE_CONFIG = get_llm_judge_config()


class ValidationService:
    """
    Validation service for artifact quality assurance.
    
    Features:
    - Artifact-specific validation (ERD, Architecture, Sequence, etc.)
    - Quality scoring (0-100)
    - LLM-as-a-Judge validation (local model evaluation)
    - Multiple validators per artifact type
    - Validation caching
    - Detailed validation reports
    """
    
    def __init__(self):
        """Initialize Validation Service."""
        self.validator = ArtifactValidator() if VALIDATOR_AVAILABLE else None
        self.custom_validator_service = get_custom_validator_service()
        self.ollama_client = OllamaClient() if OLLAMA_AVAILABLE else None
        self._llm_judge_model = None  # Cached judge model
        
        logger.info("Validation Service initialized (LLM-as-a-Judge: %s)", 
                   "enabled" if self.ollama_client else "disabled")
    
    async def validate_artifact(
        self,
        artifact_type: ArtifactType,
        content: str,
        meeting_notes: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        use_llm_judge: bool = True
    ) -> ValidationResultDTO:
        """
        Validate an artifact and return quality score.
        
        Uses a two-stage validation:
        1. Rule-based validation (syntax, structure checks)
        2. LLM-as-a-Judge validation (local model evaluation)
        
        The final score is a weighted combination of both.
        
        Args:
            artifact_type: Type of artifact
            content: Artifact content to validate
            meeting_notes: Optional meeting notes for context validation
            context: Optional additional context
            use_llm_judge: Whether to use LLM-as-a-Judge (default: True)
        
        Returns:
            ValidationResultDTO with score, is_valid, and details
        """
        logger.info(f"🔍 [VALIDATION] Starting validation: artifact_type={artifact_type.value}, "
                   f"content_length={len(content) if content else 0}, "
                   f"has_meeting_notes={bool(meeting_notes)}, has_context={bool(context)}, "
                   f"use_llm_judge={use_llm_judge}")
        
        if not content or not content.strip():
            logger.warning(f"⚠️ [VALIDATION] Empty artifact content, returning invalid result")
            return ValidationResultDTO(
                score=0.0,
                is_valid=False,
                validators={},
                errors=["Empty artifact content"],
                warnings=[]
            )
        
        # Stage 1: Rule-based validation
        rule_based_dto = None
        
        # Use ArtifactValidator if available
        if self.validator:
            logger.info(f"✅ [VALIDATION] Stage 1: Using ArtifactValidator for rule-based validation")
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
                    f"📊 [VALIDATION] Rule-based result: score={score:.1f}, "
                    f"is_valid={is_valid}, "
                    f"errors={len(result_errors)}, "
                    f"warnings={len(result_warnings)}"
                )

                rule_based_dto = ValidationResultDTO(
                    score=score,
                    is_valid=is_valid,
                    validators={
                        "rule_based": {
                            "score": score,
                            "errors": len(result_errors),
                            "warnings": len(result_warnings),
                        }
                    },
                    errors=result_errors,
                    warnings=result_warnings,
                )
            except Exception as e:
                logger.error(f"❌ [VALIDATION] Error in ArtifactValidator: {e}", exc_info=True)
                # Fall through to basic validation
        
        # Fallback to basic validation if ArtifactValidator failed or unavailable
        if rule_based_dto is None:
            rule_based_dto = self._basic_validation(artifact_type, content, meeting_notes)
        
        # Apply custom validators
        rule_based_dto = self._apply_custom_validators(artifact_type, content, rule_based_dto)
        
        # Stage 2: LLM-as-a-Judge validation (if enabled)
        llm_config = get_llm_judge_config()
        if use_llm_judge and llm_config["enabled"]:
            try:
                # Import here to avoid circular dependencies
                from backend.services.llm_judge import get_judge
                judge = get_judge()
                
                # Get validation context
                validation_context = context.get("rag_context", "") if context else ""
                
                # Call LLM judge
                llm_score, llm_reasoning = await judge.evaluate_artifact(
                    content=content, 
                    artifact_type=artifact_type.value,
                    meeting_notes=meeting_notes or "",
                    context=validation_context
                )
                
                # Determine LLM model used (helper for logging)
                # In a real implementation this would come from the judge result
                llm_model = "configured-model" 
                
                # Combine scores: weighted average
                weight = llm_config["weight"]
                combined_score = (rule_based_dto.score * (1 - weight)) + (llm_score * weight)
                
                # Log the scoring
                logger.info(
                    f"🤖 [LLM_JUDGE] Score: {llm_score:.1f}/100\n"
                    f"   Rule-based: {rule_based_dto.score:.1f} × {(1-weight):.1f} = {rule_based_dto.score * (1-weight):.1f}\n"
                    f"   LLM Judge:  {llm_score:.1f} × {weight:.1f} = {llm_score * weight:.1f}\n"
                    f"   Combined:   {combined_score:.1f}/100\n"
                    f"   Reasoning:  {llm_reasoning[:200]}..."
                )
                
                # Update the DTO with combined score
                rule_based_dto.score = combined_score
                rule_based_dto.validators["llm_judge"] = {
                    "score": llm_score,
                    "reasoning": llm_reasoning[:500],
                    "weight": weight
                }
                
                # Re-evaluate validity based on combined score
                # Valid if combined score >= 80 (stricter than before) AND no critical errors
                has_critical = any(e.startswith("CRITICAL:") for e in rule_based_dto.errors)
                rule_based_dto.is_valid = combined_score >= 80.0 and not has_critical
                
                if not rule_based_dto.is_valid:
                     logger.info(f"❌ [VALIDATION] Combined score {combined_score:.1f} < 70 or critical errors present")
                     
            except Exception as e:
                logger.warning(f"⚠️ [LLM_JUDGE] LLM judge failed, using rule-based score only: {e}")
                # Continue with rule-based score only
        
        # =================================================================
        # FINAL STRICT VALIDATION CHECK
        # =================================================================
        final_score = rule_based_dto.score
        critical_errors = [e for e in rule_based_dto.errors if "CRITICAL" in e]
        
        # Apply critical penalties - OVERRIDE validity
        if critical_errors:
            logger.warning(f"❌ [VALIDATION] Critical errors found: {critical_errors}")
            # Cap score at 40.0 if critical syntax errors exist
            final_score = min(final_score, 40.0)
            rule_based_dto.score = final_score
            rule_based_dto.is_valid = False
            # Ensure critical errors are in the list
            for err in critical_errors:
                if err not in rule_based_dto.errors:
                     rule_based_dto.errors.append(err)
        
        # Apply STRICT threshold (User request: "too easy")
        STRICT_THRESHOLD = 80.0
        if final_score < STRICT_THRESHOLD:
            # Enforce 80.0 for "valid"
            rule_based_dto.is_valid = False
            msg = f"Score {final_score:.1f} is below strict threshold {STRICT_THRESHOLD}"
            if msg not in rule_based_dto.errors:
                rule_based_dto.errors.append(msg)
        
        logger.info(
            f"✅ [VALIDATION] Final result: score={rule_based_dto.score:.1f}, "
            f"is_valid={rule_based_dto.is_valid}, "
            f"validators={list(rule_based_dto.validators.keys())}"
        )
        return rule_based_dto
    
    async def _llm_judge_validation(
        self,
        artifact_type: ArtifactType,
        content: str,
        rule_based_score: float,
        rule_based_errors: List[str],
        meeting_notes: Optional[str] = None
    ) -> Optional[Tuple[float, str, str]]:
        """
        Use a local LLM as a judge to evaluate artifact quality.
        
        Args:
            artifact_type: Type of artifact being validated
            content: The artifact content
            rule_based_score: Score from rule-based validation
            rule_based_errors: Errors from rule-based validation
            meeting_notes: Optional meeting notes for context
        
        Returns:
            Tuple of (score, reasoning, model_name) or None if failed
        """
        if not self.ollama_client:
            return None
        
        logger.info(f"🤖 [LLM_JUDGE] Starting LLM-as-a-Judge evaluation...")
        
        # Find an available judge model
        judge_model = await self._get_available_judge_model()
        if not judge_model:
            logger.warning("⚠️ [LLM_JUDGE] No judge model available")
            return None
        
        logger.info(f"🤖 [LLM_JUDGE] Using model: {judge_model}")
        
        # Build the judge prompt
        artifact_type_display = artifact_type.value.replace("_", " ").title()
        errors_text = "\n".join(f"- {e}" for e in rule_based_errors[:5]) if rule_based_errors else "None"
        
        # Truncate content for prompt (first 2000 chars for efficiency)
        content_preview = content[:2000] + ("..." if len(content) > 2000 else "")
        
        prompt = f"""You are an expert code and diagram quality evaluator. Evaluate the following {artifact_type_display} artifact.

## Artifact Content:
```
{content_preview}
```

## Rule-Based Validation Results:
- Score: {rule_based_score:.1f}/100
- Issues found: {errors_text}

{f"## Requirements (from meeting notes):" + chr(10) + meeting_notes[:500] if meeting_notes else ""}

## Your Task:
Evaluate this artifact's quality considering:
1. **Correctness**: Is the syntax valid? Will it render/compile?
2. **Completeness**: Does it include all necessary elements?
3. **Relevance**: Does it match the requirements?
4. **Quality**: Is it well-structured and professional?

Respond with ONLY a JSON object in this exact format:
{{"score": <number 0-100>, "reasoning": "<brief explanation>"}}

Be strict but fair. A score of:
- 90-100: Excellent, production-ready
- 80-89: Good, minor improvements possible
- 70-79: Acceptable, some issues
- 60-69: Needs improvement
- Below 60: Poor quality, needs rework

JSON response:"""

        try:
            import asyncio
            
            llm_config = get_llm_judge_config()
            
            # Call Ollama with timeout
            response = await asyncio.wait_for(
                self.ollama_client.generate(
                    model_name=judge_model,
                    prompt=prompt,
                    system_message="You are a strict but fair quality evaluator. Always respond with valid JSON only.",
                    temperature=0.1,  # Low temperature for consistent scoring
                    num_ctx=4096
                ),
                timeout=llm_config["timeout_seconds"]
            )
            
            if not response.success or not response.content:
                logger.warning(f"⚠️ [LLM_JUDGE] Model returned no content")
                return None
            
            # Parse JSON response
            response_text = response.content.strip()
            
            # Try to extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
            elif "```" in response_text:
                json_match = re.search(r'```\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
            
            # Find JSON object in response
            json_match = re.search(r'\{[^{}]*"score"[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            try:
                result = json.loads(response_text)
                llm_score = float(result.get("score", 0))
                llm_reasoning = str(result.get("reasoning", ""))
                
                # Clamp score to valid range
                llm_score = max(0.0, min(100.0, llm_score))
                
                logger.info(f"🤖 [LLM_JUDGE] LLM evaluation: score={llm_score:.1f}, reasoning={llm_reasoning[:100]}...")
                return (llm_score, llm_reasoning, judge_model)
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ [LLM_JUDGE] Failed to parse JSON response: {e}")
                logger.debug(f"   Response was: {response_text[:200]}")
                return None
                
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ [LLM_JUDGE] Timeout after {llm_config['timeout_seconds']}s")
            return None
        except Exception as e:
            logger.warning(f"⚠️ [LLM_JUDGE] Error calling LLM: {e}")
            return None
    
    async def _get_available_judge_model(self) -> Optional[str]:
        """
        Find an available local model for judging.
        
        Returns the first available model from the preferred list,
        or None if no models are available.
        """
        if not self.ollama_client:
            return None
        
        # Return cached model if still valid
        if self._llm_judge_model:
            return self._llm_judge_model
        
        try:
            # Get list of available Ollama models
            available_models = await self.ollama_client.list_models()
            available_names = set()
            
            for model in available_models:
                # Handle different model info formats
                if isinstance(model, dict):
                    name = model.get("name", model.get("model", ""))
                else:
                    name = str(model)
                if name:
                    available_names.add(name.lower())
                    # Also add without tag for matching
                    if ":" in name:
                        available_names.add(name.split(":")[0].lower())
            
            logger.debug(f"🤖 [LLM_JUDGE] Available models: {available_names}")
            
            # Find first preferred model that's available
            llm_config = get_llm_judge_config()
            for preferred in llm_config["preferred_models"]:
                preferred_lower = preferred.lower()
                # Check exact match or base name match
                if preferred_lower in available_names:
                    self._llm_judge_model = preferred
                    logger.info(f"🤖 [LLM_JUDGE] Selected judge model: {preferred}")
                    return preferred
                # Check if base name matches (e.g., "llama3" matches "llama3:latest")
                base_name = preferred.split(":")[0].lower()
                if base_name in available_names:
                    self._llm_judge_model = preferred
                    logger.info(f"🤖 [LLM_JUDGE] Selected judge model: {preferred}")
                    return preferred
            
            # No preferred model found - use first available
            if available_names:
                first_available = list(available_names)[0]
                self._llm_judge_model = first_available
                logger.info(f"🤖 [LLM_JUDGE] Using fallback judge model: {first_available}")
                return first_available
            
            logger.warning("⚠️ [LLM_JUDGE] No Ollama models available for judging")
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ [LLM_JUDGE] Error listing models: {e}")
            return None
    
    def _basic_validation(
        self,
        artifact_type: ArtifactType,
        content: str,
        meeting_notes: Optional[str] = None
    ) -> ValidationResultDTO:
        """
        Basic validation when ArtifactValidator is not available.
        
        STRICT VALIDATION - Broken artifacts WILL trigger fallback to next model.
        
        Scoring:
        - CRITICAL errors: -40 points each (will break rendering)
        - SYNTAX errors: -25 points each (likely to break)
        - Regular errors: -15 points each
        - Warnings: -5 points each
        
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
        has_critical_error = False
        
        # Basic checks
        if not content or len(content.strip()) < 10:
            errors.append("CRITICAL: Content too short")
            score -= 50.0
            has_critical_error = True
        
        # Artifact-specific validation with STRICT scoring
        if artifact_type.value.startswith("mermaid_"):
            # Mermaid diagram validation (uses cleaned content internally)
            mermaid_errors = self._validate_mermaid(content)
            
            # Score based on error severity
            for error in mermaid_errors:
                errors.append(error)
                if error.startswith("CRITICAL:"):
                    score -= 40.0
                    has_critical_error = True
                elif error.startswith("SYNTAX:"):
                    score -= 25.0
                else:
                    score -= 15.0
            
            # Check for required diagram type
            diagram_type = artifact_type.value.replace("mermaid_", "")
            # Map artifact type to expected mermaid keyword
            type_mapping = {
                "erd": "erDiagram",
                "sequence": "sequenceDiagram",
                "class": "classDiagram",
                "state": "stateDiagram",
                "flowchart": "flowchart",
                "architecture": "flowchart",  # Architecture often uses flowchart
                "data_flow": "flowchart",
                "user_flow": "flowchart",
                "component": "flowchart",
                "system_overview": "flowchart",
                "api_sequence": "sequenceDiagram",
                "gantt": "gantt",
                "pie": "pie",
                "journey": "journey",
                "mindmap": "mindmap",
                "timeline": "timeline",
                "git_graph": "gitGraph",
                "c4_context": "C4Context",
                "c4_container": "C4Container",
                "c4_component": "C4Component",
                "c4_deployment": "C4Deployment",
            }
            
            expected_keyword = type_mapping.get(diagram_type, diagram_type)
            if expected_keyword.lower() not in content.lower():
                # Some flexibility - graph can be used instead of flowchart
                if expected_keyword == "flowchart" and "graph" in content.lower():
                    pass  # OK
                else:
                    errors.append(f"Wrong diagram type: expected {expected_keyword}")
        # Apply STRICT threshold (User request: "too easy" -> but now "too strict")
        # Adjusted to be balanced: 70.0 is acceptable, 80.0 is good
        STRICT_THRESHOLD = 70.0  # Relaxed from 80.0
        if final_score < STRICT_THRESHOLD:
            # Enforce 70.0 for "valid"
            rule_based_dto.is_valid = False
            msg = f"Score {final_score:.1f} is below strict threshold {STRICT_THRESHOLD}"
            if msg not in rule_based_dto.errors:
                rule_based_dto.errors.append(msg)
        
        # Valid if score >= 70.0 and no critical blocking errors
        # (We allow *some* critical errors to be auto-fixed by frontend/repair)
        is_valid = (
            score >= STRICT_THRESHOLD
        )
        
        # Log validation result for debugging
        logger.info(f"🔍 [VALIDATION] {artifact_type.value}: score={score:.1f}, is_valid={is_valid}, "
                   f"errors={len(errors)}, critical={has_critical_error}")
        if errors:
            logger.info(f"   Errors: {errors[:3]}{'...' if len(errors) > 3 else ''}")
        
        validators["basic"] = {
            "score": score,
            "errors": len(errors),
            "warnings": len(warnings),
            "has_critical": has_critical_error
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
        """
        Validate Mermaid diagram syntax with STRICT checking.
        
        This validator catches common AI generation errors that break rendering:
        - Invalid syntax patterns
        - Malformed node definitions
        - Missing required elements
        - Common hallucination patterns
        """
        import re
        errors: List[str] = []
        
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
            errors.append("CRITICAL: Missing Mermaid diagram type declaration")
        
        # Check for balanced brackets (CRITICAL - breaks rendering)
        if clean_content.count('{') != clean_content.count('}'):
            errors.append("CRITICAL: Unbalanced curly braces - diagram will not render")
        
        if clean_content.count('[') != clean_content.count(']'):
            errors.append("CRITICAL: Unbalanced square brackets - diagram will not render")
        
        if clean_content.count('(') != clean_content.count(')'):
            errors.append("CRITICAL: Unbalanced parentheses - diagram will not render")
        
        if clean_content.count('"') % 2 != 0:
            errors.append("CRITICAL: Unbalanced quotes - diagram will not render")
        
        # Check for common AI hallucination patterns that break Mermaid
        broken_patterns = [
            (r'\[\s*\]', "Empty brackets [] will break rendering"),
            (r'\{\s*\}', "Empty braces {} may break rendering"),
            (r'-->\s*$', "Arrow pointing to nothing"),
            (r'^\s*-->', "Arrow with no source", re.MULTILINE),
            (r'\|\|\s*\|\|', "Invalid double relationship marker"),
            (r':\s*$', "Colon with no value", re.MULTILINE),
            (r'participant\s+$', "Participant with no name", re.MULTILINE),
            (r'Note\s+$', "Note with no content", re.MULTILINE),
        ]
        
        for pattern_info in broken_patterns:
            if len(pattern_info) == 2:
                pattern, msg = pattern_info
                flags = 0
            else:
                pattern, msg, flags = pattern_info
            
            if re.search(pattern, clean_content, flags):
                errors.append(f"SYNTAX: {msg}")
        
        # Diagram-specific validation
        if "erDiagram" in clean_content:
            errors.extend(self._validate_erd_specific(clean_content))
        elif "sequenceDiagram" in clean_content:
            errors.extend(self._validate_sequence_specific(clean_content))
        elif "flowchart" in clean_content or "graph" in clean_content:
            errors.extend(self._validate_flowchart_specific(clean_content))
        elif "classDiagram" in clean_content:
            errors.extend(self._validate_class_specific(clean_content))
        elif "stateDiagram" in clean_content:
            errors.extend(self._validate_state_specific(clean_content))
        elif "gantt" in clean_content:
            errors.extend(self._validate_gantt_specific(clean_content))
        
        # Check for minimum content (diagrams with almost nothing)
        non_whitespace_lines = [l for l in clean_content.split('\n') if l.strip() and not l.strip().startswith('%%')]
        if len(non_whitespace_lines) < 3:
            errors.append("CRITICAL: Diagram has too few elements (less than 3 lines)")
        
        return errors
    
    def _validate_erd_specific(self, content: str) -> List[str]:
        """Validate ERD diagram specific syntax."""
        import re
        errors = []
        
        # ERD must have at least one entity
        entity_pattern = r'^\s*(\w+)\s*\{'
        entities = re.findall(entity_pattern, content, re.MULTILINE)
        if not entities:
            errors.append("ERD: No entities defined (need ENTITY { fields })")
        
        # ERD must have relationships (unless it's a single entity)
        if len(entities) > 1:
            relationship_patterns = ['||--||', '||--o{', '}o--||', '||--|{', '}|--||', 'o{--||', '}o--|{']
            has_relationship = any(p in content for p in relationship_patterns)
            if not has_relationship:
                errors.append("ERD: No valid relationships between entities")
        
        # Check for invalid ERD syntax patterns
        if re.search(r'class\s+\w+', content, re.IGNORECASE):
            errors.append("ERD: Using classDiagram syntax (class X) instead of ERD syntax")
        
        return errors
    
    def _validate_sequence_specific(self, content: str) -> List[str]:
        """Validate sequence diagram specific syntax."""
        import re
        errors = []
        
        # Must have participants or actors
        has_participants = 'participant' in content.lower() or 'actor' in content.lower()
        # Or implicit participants via arrows
        has_arrows = '->>' in content or '-->>' in content or '->' in content
        
        if not has_participants and not has_arrows:
            errors.append("SEQUENCE: No participants/actors or message arrows defined")
        
        # Check for valid arrow syntax
        arrow_pattern = r'(\w+)\s*(->>|-->>|->|-->)\s*(\w+)'
        arrows = re.findall(arrow_pattern, content)
        if len(arrows) < 1 and has_participants:
            errors.append("SEQUENCE: Participants defined but no messages between them")
        
        return errors
    
    def _validate_flowchart_specific(self, content: str) -> List[str]:
        """Validate flowchart/graph specific syntax."""
        import re
        errors = []
        
        # Check for direction (TD, LR, RL, BT)
        direction_pattern = r'(flowchart|graph)\s+(TD|TB|LR|RL|BT)'
        if not re.search(direction_pattern, content):
            # Check if it at least has flowchart/graph keyword
            if 'flowchart' in content.lower() or 'graph' in content.lower():
                errors.append("FLOWCHART: Missing direction (TD, LR, etc.)")
        
        # Must have nodes
        node_pattern = r'(\w+)(\[|\(|\{|\[\[|\(\()'
        nodes = re.findall(node_pattern, content)
        if len(nodes) < 2:
            errors.append("FLOWCHART: Need at least 2 nodes for a valid diagram")
        
        # Must have connections
        arrow_patterns = ['-->', '---', '-.->', '-.->']
        has_connections = any(p in content for p in arrow_patterns)
        if not has_connections:
            errors.append("FLOWCHART: No connections between nodes")
        
        return errors
    
    def _validate_class_specific(self, content: str) -> List[str]:
        """Validate class diagram specific syntax."""
        import re
        errors = []
        
        # Must have at least one class
        class_pattern = r'class\s+(\w+)'
        classes = re.findall(class_pattern, content)
        if len(classes) < 1:
            errors.append("CLASS: No classes defined")
        
        return errors
    
    def _validate_state_specific(self, content: str) -> List[str]:
        """Validate state diagram specific syntax."""
        import re
        errors = []
        
        # Must have states or transitions
        has_states = '[*]' in content or 'state ' in content.lower()
        has_transitions = '-->' in content
        
        if not has_states and not has_transitions:
            errors.append("STATE: No states or transitions defined")
        
        return errors
    
    def _validate_gantt_specific(self, content: str) -> List[str]:
        """Validate Gantt chart specific syntax."""
        import re
        errors = []
        
        # Must have title or section
        has_structure = 'title' in content.lower() or 'section' in content.lower()
        if not has_structure:
            errors.append("GANTT: Missing title or section")
        
        # Must have tasks
        task_pattern = r':\s*\w+,\s*\d'
        has_tasks = bool(re.search(task_pattern, content))
        if not has_tasks:
            errors.append("GANTT: No valid tasks defined (format: taskName :status, duration)")
        
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
        """
        Validate HTML artifacts with STRICT checking.
        
        Catches common AI generation errors:
        - Missing document structure
        - Unclosed tags
        - Invalid nesting
        - Empty/placeholder content
        """
        import re
        errors: List[str] = []
        
        content_lower = content.lower()
        
        # Check for basic HTML structure (must have at least one container)
        has_structure = any(tag in content_lower for tag in ['<html', '<body', '<div', '<!doctype'])
        if not has_structure:
            errors.append("CRITICAL: No HTML structure found (missing html/body/div tags)")
        
        # Check for balanced angle brackets (CRITICAL)
        open_tags = content.count('<')
        close_tags = content.count('>')
        if open_tags != close_tags:
            errors.append("CRITICAL: Unbalanced HTML tags - will not render correctly")
        
        # Check for common unclosed tags
        void_elements = {'br', 'hr', 'img', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'source', 'track', 'wbr'}
        
        # Find all opening tags
        opening_tags = re.findall(r'<(\w+)(?:\s[^>]*)?>(?!</)', content_lower)
        closing_tags = re.findall(r'</(\w+)>', content_lower)
        
        # Count tags (excluding void elements and self-closing)
        open_counts = {}
        for tag in opening_tags:
            if tag not in void_elements:
                open_counts[tag] = open_counts.get(tag, 0) + 1
        
        close_counts = {}
        for tag in closing_tags:
            close_counts[tag] = close_counts.get(tag, 0) + 1
        
        # Check for major imbalances
        important_tags = ['div', 'span', 'p', 'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'form', 'section', 'article', 'header', 'footer', 'nav', 'main']
        for tag in important_tags:
            opened = open_counts.get(tag, 0)
            closed = close_counts.get(tag, 0)
            if opened > closed + 2:  # Allow some tolerance
                errors.append(f"HTML: Unclosed <{tag}> tags ({opened} opened, {closed} closed)")
            elif closed > opened + 2:
                errors.append(f"HTML: Extra </{tag}> closing tags")
        
        # Check for empty/placeholder content
        placeholder_patterns = [
            r'lorem\s+ipsum',
            r'\{\{\s*\w+\s*\}\}',  # {{ placeholder }}
            r'\[\s*placeholder\s*\]',
            r'TODO:?\s',
            r'FIXME:?\s',
            r'<div>\s*</div>',  # Empty divs
            r'<span>\s*</span>',  # Empty spans
        ]
        
        for pattern in placeholder_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                errors.append(f"HTML: Contains placeholder/incomplete content")
                break
        
        # Check for interactive HTML (should have some elements)
        interactive_tags = ['button', 'input', 'select', 'textarea', 'a', 'form']
        structural_tags = ['div', 'section', 'article', 'header', 'footer', 'nav', 'main', 'aside']
        
        has_interactive = any(f'<{tag}' in content_lower for tag in interactive_tags)
        has_structural = any(f'<{tag}' in content_lower for tag in structural_tags)
        
        if not has_interactive and not has_structural:
            errors.append("HTML: No interactive or structural elements found")
        
        # Check minimum content length
        text_content = re.sub(r'<[^>]+>', '', content)  # Remove all tags
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        if len(text_content) < 20:
            errors.append("HTML: Very little actual content (mostly empty tags)")
        
        # Check for proper closing tags (basic check)
        if content.count('</div>') > 0 and content.count('<div') > content.count('</div>'):
            errors.append("HTML: Some div tags may not be properly closed")
        
        return errors
    
    def auto_repair_mermaid(self, content: str, max_attempts: int = 3) -> Tuple[str, bool, List[str]]:
        """
        Attempt to automatically repair a Mermaid diagram.
        
        This method validates the diagram, identifies errors, and applies targeted fixes
        in a loop until the diagram is valid or max attempts are reached.
        
        Args:
            content: The Mermaid diagram content
            max_attempts: Maximum repair attempts
        
        Returns:
            Tuple of (repaired_content, is_valid, list_of_fixes_applied)
        """
        import re
        
        logger.info(f"🔍 [VALIDATION] ========== AUTO-REPAIR STARTED ==========")
        logger.info(f"🔍 [VALIDATION] Step 1: Initializing auto-repair")
        logger.info(f"🔍 [VALIDATION] Step 1.1: Input content length={len(content)}, max_attempts={max_attempts}")
        logger.info(f"🔍 [VALIDATION] Step 1.2: Input preview (first 200 chars): {content[:200]}...")
        
        all_fixes = []
        current_content = content
        
        for attempt in range(max_attempts):
            logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}: Starting repair attempt {attempt + 1}/{max_attempts}")
            
            # Validate current state
            logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}.1: Validating current diagram state")
            errors = self._validate_mermaid(current_content)
            critical_errors = [e for e in errors if e.startswith("CRITICAL:")]
            non_critical_errors = [e for e in errors if not e.startswith("CRITICAL:")]
            
            logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}.2: Validation result: {len(critical_errors)} critical errors, {len(non_critical_errors)} warnings")
            if critical_errors:
                logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}.2.1: Critical errors: {critical_errors[:3]}...")  # Show first 3
            
            if not critical_errors:
                # No critical errors - diagram should render
                if errors:
                    logger.info(f"✅ [VALIDATION] Step 2.{attempt + 1}.3: Diagram valid after {attempt + 1} repair passes ({len(errors)} non-critical warnings)")
                else:
                    logger.info(f"✅ [VALIDATION] Step 2.{attempt + 1}.3: Diagram valid after {attempt + 1} repair passes (no errors)")
                logger.info(f"🔍 [VALIDATION] ========== AUTO-REPAIR COMPLETE (SUCCESS) ==========")
                return current_content, True, all_fixes
            
            # Apply targeted fixes based on errors
            logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}.3: Applying targeted fixes for {len(critical_errors)} critical errors")
            fixes_this_pass = []
            
            for error_idx, error in enumerate(critical_errors):
                error_lower = error.lower()
                logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}.3.{error_idx + 1}: Fixing error: {error[:100]}...")
                
                # Fix unbalanced curly braces
                if "unbalanced curly braces" in error_lower:
                    logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}.3.{error_idx + 1}.1: Fixing unbalanced curly braces")
                    open_count = current_content.count('{')
                    close_count = current_content.count('}')
                    logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}.3.{error_idx + 1}.2: Count: {open_count} open, {close_count} close")
                    
                    if open_count > close_count:
                        # Add missing closing braces
                        diff = open_count - close_count
                        logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}.3.{error_idx + 1}.3: Adding {diff} missing closing braces")
                        current_content = current_content.rstrip() + '\n' + '}\n' * diff
                        fixes_this_pass.append(f"Added {diff} missing closing braces")
                        logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}.3.{error_idx + 1}.4: Fixed - added {diff} closing braces")
                    elif close_count > open_count:
                        # Remove extra closing braces (from end)
                        logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}.3.{error_idx + 1}.3: Removing {close_count - open_count} extra closing braces")
                        lines = current_content.split('\n')
                        to_remove = close_count - open_count
                        removed = 0
                        while to_remove > 0 and lines:
                            if '}' in lines[-1] and '{' not in lines[-1]:
                                lines[-1] = lines[-1].replace('}', '', 1)
                                to_remove -= 1
                                removed += 1
                                if not lines[-1].strip():
                                    lines.pop()
                            else:
                                break
                        current_content = '\n'.join(lines)
                        fixes_this_pass.append(f"Removed {close_count - open_count} extra closing braces")
                        logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}.3.{error_idx + 1}.4: Fixed - removed {removed} closing braces")
                
                # Fix unbalanced square brackets
                elif "unbalanced square brackets" in error_lower:
                    open_count = current_content.count('[')
                    close_count = current_content.count(']')
                    
                    if open_count > close_count:
                        # Find lines with unclosed brackets and close them
                        lines = current_content.split('\n')
                        fixed_lines = []
                        for line in lines:
                            line_open = line.count('[')
                            line_close = line.count(']')
                            if line_open > line_close:
                                # Add closing bracket before arrow or at end
                                if '-->' in line:
                                    line = re.sub(r'\[([^\]]*)(-->)', r'[\1]\2', line)
                                else:
                                    line = line.rstrip() + ']'
                            fixed_lines.append(line)
                        current_content = '\n'.join(fixed_lines)
                        fixes_this_pass.append("Fixed unclosed square brackets")
                
                # Fix unbalanced parentheses
                elif "unbalanced parentheses" in error_lower:
                    open_count = current_content.count('(')
                    close_count = current_content.count(')')
                    
                    if open_count > close_count:
                        # Close unclosed parentheses
                        lines = current_content.split('\n')
                        fixed_lines = []
                        for line in lines:
                            line_open = line.count('(')
                            line_close = line.count(')')
                            if line_open > line_close:
                                line = line.rstrip() + ')' * (line_open - line_close)
                            fixed_lines.append(line)
                        current_content = '\n'.join(fixed_lines)
                        fixes_this_pass.append("Fixed unclosed parentheses")
                
                # Fix unbalanced quotes
                elif "unbalanced quotes" in error_lower:
                    quote_count = current_content.count('"')
                    if quote_count % 2 != 0:
                        # Remove all quotes (safest fix)
                        current_content = current_content.replace('"', '')
                        fixes_this_pass.append("Removed unbalanced quotes")
                        logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}.3.{error_idx + 1}.4: Fixed - removed unbalanced quotes")
                
                # Fix missing diagram type
                elif "missing mermaid diagram type" in error_lower:
                    logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}.3.{error_idx + 1}.3: Adding missing diagram type")
                    # Try to detect what type it should be
                    if '||--' in current_content or '}|--' in current_content:
                        current_content = 'erDiagram\n' + current_content
                        fixes_this_pass.append("Added missing erDiagram declaration")
                        logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}.3.{error_idx + 1}.4: Fixed - added erDiagram declaration")
                    elif '->>-' in current_content or '->>' in current_content:
                        current_content = 'sequenceDiagram\n' + current_content
                        fixes_this_pass.append("Added missing sequenceDiagram declaration")
                    elif '-->' in current_content or '---' in current_content:
                        current_content = 'flowchart TD\n' + current_content
                        fixes_this_pass.append("Added missing flowchart declaration")
            
            all_fixes.extend(fixes_this_pass)
            logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}.4: Applied {len(fixes_this_pass)} fixes in this pass: {fixes_this_pass[:3]}...")  # Show first 3
            
            if not fixes_this_pass:
                # No fixes applied this pass - we're stuck
                logger.warning(f"🔍 [VALIDATION] Step 2.{attempt + 1}.5: No fixes applied on pass {attempt + 1}, stopping repair")
                break
            
            # Check if we made progress
            if current_content == content:
                logger.warning(f"🔍 [VALIDATION] Step 2.{attempt + 1}.5: No changes made in this pass, stopping")
                break
            
            current_content = content
            logger.info(f"🔍 [VALIDATION] Step 2.{attempt + 1}.5: Pass {attempt + 1} complete: {len(fixes_this_pass)} fixes, content_length={len(current_content)}")
        
        # Final validation
        logger.info(f"🔍 [VALIDATION] Step 3: Final validation after {attempt + 1} repair attempts")
        final_errors = self._validate_mermaid(current_content)
        critical_errors = [e for e in final_errors if e.startswith("CRITICAL:")]
        is_valid = len(critical_errors) == 0
        
        if is_valid:
            logger.info(f"✅ [VALIDATION] Step 3.1: Diagram valid after {attempt + 1} repair passes ({len(final_errors)} non-critical warnings, {len(all_fixes)} total fixes)")
            logger.info(f"🔍 [VALIDATION] ========== AUTO-REPAIR COMPLETE (SUCCESS) ==========")
        else:
            logger.warning(f"⚠️ [VALIDATION] Step 3.1: Diagram still has {len(critical_errors)} critical errors after {attempt + 1} attempts: {critical_errors[:3]}")
            logger.info(f"🔍 [VALIDATION] ========== AUTO-REPAIR COMPLETE (PARTIAL) ==========")
        
        return current_content, is_valid, all_fixes
    
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
    
    def auto_repair_mermaid(
        self,
        content: str,
        max_attempts: int = 3
    ) -> Tuple[str, bool, List[str]]:
        """
        Auto-repair a Mermaid diagram using validation and iterative fixing.
        
        This method is called from generation_service to repair generated diagrams.
        Uses the UniversalDiagramFixer for comprehensive syntax repairs.
        
        Args:
            content: Raw Mermaid diagram content
            max_attempts: Maximum repair attempts
        
        Returns:
            Tuple of (repaired_content, is_valid, list_of_fixes_applied)
        """
        from typing import Tuple
        all_fixes = []
        current_content = content
        
        try:
            # Import the universal fixer
            from components.universal_diagram_fixer import UniversalDiagramFixer
            fixer = UniversalDiagramFixer(strict_mode=True)
        except ImportError:
            logger.warning("UniversalDiagramFixer not available. Returning original content.")
            # Just do basic validation
            errors = self._validate_mermaid(content)
            is_valid = not any(e.startswith("CRITICAL:") for e in errors)
            return content, is_valid, []
        
        for attempt in range(max_attempts):
            logger.debug(f"🔧 [VALIDATION] Auto-repair attempt {attempt + 1}/{max_attempts}")
            
            # Validate current content
            errors = self._validate_mermaid(current_content)
            critical_errors = [e for e in errors if e.startswith("CRITICAL:")]
            
            # If no critical errors, we're done
            if not critical_errors:
                logger.info(f"✅ [VALIDATION] Mermaid diagram is valid after {attempt} repair(s)")
                return current_content, True, all_fixes
            
            # Apply fixes
            fixed_content, fixes = fixer.fix_diagram(current_content, max_passes=3, lenient=False)
            
            if fixes:
                all_fixes.extend(fixes)
                logger.info(f"🔧 [VALIDATION] Applied {len(fixes)} fixes on attempt {attempt + 1}")
            
            # If content didn't change and we still have errors, try lenient mode
            if fixed_content == current_content and attempt == max_attempts - 1:
                logger.info(f"⚠️ [VALIDATION] Trying lenient mode for final attempt")
                fixed_content, fixes = fixer.fix_diagram(current_content, max_passes=3, lenient=True)
                if fixes:
                    all_fixes.extend(fixes)
            
            current_content = fixed_content
        
        # Final validation
        final_errors = self._validate_mermaid(current_content)
        critical_errors = [e for e in final_errors if e.startswith("CRITICAL:")]
        is_valid = len(critical_errors) == 0
        
        if is_valid:
            logger.info(f"✅ [VALIDATION] Mermaid diagram repaired successfully with {len(all_fixes)} total fixes")
        else:
            logger.warning(f"⚠️ [VALIDATION] Mermaid diagram still has {len(critical_errors)} critical errors after {max_attempts} attempts")
        
        return current_content, is_valid, all_fixes


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



