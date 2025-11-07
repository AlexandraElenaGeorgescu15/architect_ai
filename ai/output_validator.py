"""
Output Validation System
Validates local model outputs before accepting them.
Only falls back to cloud if local outputs fail quality checks.
"""

import re
from typing import Dict, List, Tuple
from enum import Enum
from ai.artifact_router import ArtifactType


class ValidationResult(Enum):
    """Validation result status"""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


class OutputValidator:
    """
    Validates artifact outputs from local models.
    
    Each artifact type has specific validation rules.
    Only accepts output if it meets quality thresholds.
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator.
        
        Args:
            strict_mode: If True, enforces stricter validation rules
        """
        self.strict_mode = strict_mode
        self.validation_stats = {}
        self._current_context = {}
    
    def validate(self, artifact_type: ArtifactType, content: str, context: Dict = None) -> Tuple[ValidationResult, List[str], int]:
        """
        Validate output for an artifact type.
        
        Args:
            artifact_type: Type of artifact
            content: Generated content to validate
            context: Optional context dict (e.g., meeting_notes, requirements)
            
        Returns:
            Tuple of (ValidationResult, list of issues, quality_score 0-100)
        """
        if not content or len(content.strip()) < 10:
            return ValidationResult.FAIL, ["Output too short or empty"], 0
        
        # Store context for validators that might need it
        self._current_context = context or {}
        
        # Route to specific validator
        validator_map = {
            ArtifactType.ERD: self._validate_erd,
            ArtifactType.ARCHITECTURE: self._validate_architecture,
            ArtifactType.SEQUENCE: self._validate_sequence,
            ArtifactType.CLASS_DIAGRAM: self._validate_class_diagram,
            ArtifactType.STATE_DIAGRAM: self._validate_state_diagram,
            ArtifactType.CODE_PROTOTYPE: self._validate_code,
            ArtifactType.HTML_PROTOTYPE: self._validate_html,
            ArtifactType.API_DOCS: self._validate_api_docs,
            ArtifactType.JIRA_STORIES: self._validate_jira,
            ArtifactType.WORKFLOWS: self._validate_workflow,
            ArtifactType.DOCUMENTATION: self._validate_documentation,
        }
        
        validator = validator_map.get(artifact_type)
        if not validator:
            # No specific validator, do basic check
            return ValidationResult.PASS, [], 70
        
        return validator(content)
    
    # ============================================================
    # Artifact-Specific Validators
    # ============================================================
    
    def _validate_erd(self, content: str) -> Tuple[ValidationResult, List[str], int]:
        """Validate Mermaid ERD diagram"""
        issues = []
        score = 100
        
        # Must start with erDiagram
        if not content.strip().startswith("erDiagram"):
            issues.append("Missing 'erDiagram' declaration")
            score -= 30
        
        # Must have entities (tables)
        entity_pattern = r'\w+\s+\{'
        entities = re.findall(entity_pattern, content)
        if len(entities) < 2:
            issues.append(f"Too few entities ({len(entities)}), expected at least 2")
            score -= 25
        
        # Must have relationships
        relationship_pattern = r'\w+\s+[\|\}][\|\}o]--[o\|][\|\{]\s+\w+'
        relationships = re.findall(relationship_pattern, content)
        if len(relationships) < 1:
            issues.append("No relationships defined")
            score -= 25
        
        # Must have attributes
        attribute_pattern = r'\w+\s+\w+\s+(PK|FK|UK)?'
        attributes = re.findall(attribute_pattern, content)
        if len(attributes) < 3:
            issues.append(f"Too few attributes ({len(attributes)})")
            score -= 20
        
        # Determine result
        if score >= 70:
            result = ValidationResult.PASS
        elif score >= 50:
            result = ValidationResult.WARN
        else:
            result = ValidationResult.FAIL
        
        return result, issues, max(0, score)
    
    def _validate_architecture(self, content: str) -> Tuple[ValidationResult, List[str], int]:
        """Validate architecture diagram"""
        issues = []
        score = 100
        
        # Must be a flowchart or graph
        if not any(keyword in content.lower() for keyword in ["flowchart", "graph"]):
            issues.append("Not a valid flowchart/graph")
            score -= 40
        
        # Must have nodes
        node_pattern = r'\w+\[.+?\]'
        nodes = re.findall(node_pattern, content)
        if len(nodes) < 3:
            issues.append(f"Too few nodes ({len(nodes)}), expected at least 3")
            score -= 30
        
        # Must have connections
        connection_pattern = r'-->'
        connections = content.count('-->')
        if connections < 2:
            issues.append(f"Too few connections ({connections})")
            score -= 30
        
        if score >= 70:
            result = ValidationResult.PASS
        elif score >= 50:
            result = ValidationResult.WARN
        else:
            result = ValidationResult.FAIL
        
        return result, issues, max(0, score)
    
    def _validate_sequence(self, content: str) -> Tuple[ValidationResult, List[str], int]:
        """Validate sequence diagram"""
        issues = []
        score = 100
        
        if not content.strip().startswith("sequenceDiagram"):
            issues.append("Missing 'sequenceDiagram' declaration")
            score -= 40
        
        # Must have messages
        message_pattern = r'->>'
        messages = content.count('->>')
        if messages < 2:
            issues.append(f"Too few messages ({messages})")
            score -= 30
        
        # Must have participants
        participant_pattern = r'participant\s+\w+'
        participants = re.findall(participant_pattern, content)
        if len(participants) < 2 and messages >= 2:
            # Implicit participants are OK if messages exist
            pass
        
        if score >= 70:
            result = ValidationResult.PASS
        elif score >= 50:
            result = ValidationResult.WARN
        else:
            result = ValidationResult.FAIL
        
        return result, issues, max(0, score)
    
    def _validate_class_diagram(self, content: str) -> Tuple[ValidationResult, List[str], int]:
        """Validate class diagram"""
        issues = []
        score = 100
        
        if not content.strip().startswith("classDiagram"):
            issues.append("Missing 'classDiagram' declaration")
            score -= 40
        
        # Must have classes
        class_pattern = r'class\s+\w+\s+\{'
        classes = re.findall(class_pattern, content)
        if len(classes) < 2:
            issues.append(f"Too few classes ({len(classes)})")
            score -= 30
        
        if score >= 70:
            result = ValidationResult.PASS
        elif score >= 50:
            result = ValidationResult.WARN
        else:
            result = ValidationResult.FAIL
        
        return result, issues, max(0, score)
    
    def _validate_state_diagram(self, content: str) -> Tuple[ValidationResult, List[str], int]:
        """Validate state diagram"""
        issues = []
        score = 100
        
        if not "stateDiagram" in content:
            issues.append("Missing 'stateDiagram' declaration")
            score -= 40
        
        # Must have states
        state_pattern = r'-->'
        transitions = content.count('-->')
        if transitions < 2:
            issues.append(f"Too few state transitions ({transitions})")
            score -= 30
        
        if score >= 70:
            result = ValidationResult.PASS
        elif score >= 50:
            result = ValidationResult.WARN
        else:
            result = ValidationResult.FAIL
        
        return result, issues, max(0, score)
    
    def _validate_code(self, content: str) -> Tuple[ValidationResult, List[str], int]:
        """Validate code prototype"""
        issues = []
        score = 100
        
        # Must have code structure
        has_class = "class " in content
        has_function = "function " in content or "def " in content or "public " in content
        has_import = "import " in content or "using " in content
        
        if not (has_class or has_function):
            issues.append("No class or function definitions found")
            score -= 40
        
        if not has_import and len(content) > 200:
            issues.append("No import statements (may be incomplete)")
            score -= 10
        
        # Check for common patterns
        if len(content) < 50:
            issues.append("Code too short")
            score -= 30
        
        if score >= 70:
            result = ValidationResult.PASS
        elif score >= 50:
            result = ValidationResult.WARN
        else:
            result = ValidationResult.FAIL
        
        return result, issues, max(0, score)
    
    def _validate_html(self, content: str) -> Tuple[ValidationResult, List[str], int]:
        """Validate HTML prototype"""
        issues = []
        score = 100
        
        # Must have basic HTML structure
        has_doctype = "<!DOCTYPE" in content or "<!doctype" in content
        has_html = "<html" in content.lower()
        has_body = "<body" in content.lower()
        
        if not has_html:
            issues.append("Missing <html> tag")
            score -= 30
        
        if not has_body:
            issues.append("Missing <body> tag")
            score -= 30
        
        if not has_doctype:
            issues.append("Missing DOCTYPE declaration")
            score -= 10
        
        # Check for actual content
        if content.count("<") < 5:
            issues.append("Too few HTML elements")
            score -= 30
        
        if score >= 70:
            result = ValidationResult.PASS
        elif score >= 50:
            result = ValidationResult.WARN
        else:
            result = ValidationResult.FAIL
        
        return result, issues, max(0, score)
    
    def _validate_api_docs(self, content: str) -> Tuple[ValidationResult, List[str], int]:
        """Validate API documentation"""
        issues = []
        score = 100
        
        # Check for OpenAPI/Swagger
        has_openapi = "openapi:" in content.lower()
        has_swagger = "swagger:" in content.lower()
        
        if not (has_openapi or has_swagger):
            # Might be markdown docs
            has_endpoints = "GET" in content or "POST" in content or "PUT" in content
            if not has_endpoints:
                issues.append("No API spec or endpoint documentation found")
                score -= 40
        
        if len(content) < 100:
            issues.append("Documentation too short")
            score -= 30
        
        if score >= 70:
            result = ValidationResult.PASS
        elif score >= 50:
            result = ValidationResult.WARN
        else:
            result = ValidationResult.FAIL
        
        return result, issues, max(0, score)
    
    def _validate_jira(self, content: str) -> Tuple[ValidationResult, List[str], int]:
        """Validate JIRA stories"""
        issues = []
        score = 100
        
        # Must have user story format
        has_user_story = "as a" in content.lower() or "as an" in content.lower()
        has_acceptance = "acceptance" in content.lower() or "criteria" in content.lower()
        
        if not has_user_story:
            issues.append("Missing user story format (As a...)")
            score -= 30
        
        if not has_acceptance and self.strict_mode:
            issues.append("Missing acceptance criteria")
            score -= 20
        
        if len(content) < 50:
            issues.append("Story too short")
            score -= 20
        
        if score >= 70:
            result = ValidationResult.PASS
        elif score >= 50:
            result = ValidationResult.WARN
        else:
            result = ValidationResult.FAIL
        
        return result, issues, max(0, score)
    
    def _validate_workflow(self, content: str) -> Tuple[ValidationResult, List[str], int]:
        """Validate workflow documentation"""
        issues = []
        score = 100
        
        # Must have steps
        has_numbered_steps = bool(re.search(r'\d+\.', content))
        has_bullet_points = '*' in content or '-' in content
        
        if not (has_numbered_steps or has_bullet_points):
            issues.append("No clear workflow steps found")
            score -= 30
        
        if len(content) < 100:
            issues.append("Workflow too short")
            score -= 20
        
        if score >= 70:
            result = ValidationResult.PASS
        elif score >= 50:
            result = ValidationResult.WARN
        else:
            result = ValidationResult.FAIL
        
        return result, issues, max(0, score)
    
    def _validate_documentation(self, content: str) -> Tuple[ValidationResult, List[str], int]:
        """Validate general documentation"""
        issues = []
        score = 100
        
        # Basic checks
        if len(content) < 100:
            issues.append("Documentation too short")
            score -= 30
        
        # Should have some structure
        has_headers = bool(re.search(r'^#{1,6}\s+', content, re.MULTILINE))
        if not has_headers and len(content) > 200:
            issues.append("No markdown headers found")
            score -= 10
        
        if score >= 70:
            result = ValidationResult.PASS
        elif score >= 50:
            result = ValidationResult.WARN
        else:
            result = ValidationResult.FAIL
        
        return result, issues, max(0, score)


# Global validator instance
_validator: OutputValidator | None = None


def get_validator(strict_mode: bool = False) -> OutputValidator:
    """Get or create global validator instance"""
    global _validator
    if _validator is None:
        _validator = OutputValidator(strict_mode)
    return _validator
