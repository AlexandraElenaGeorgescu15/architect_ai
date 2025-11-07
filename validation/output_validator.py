"""
Output Validation System

Automatically validates generated artifacts to ensure quality and completeness.
Provides validation rules for different artifact types and supports auto-retry
on failure.

Features:
- Type-specific validation rules
- Quality scoring (0-100)
- Auto-retry with feedback
- Detailed error reporting
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class ValidationResult:
    """
    Result of artifact validation.
    
    Attributes:
        is_valid: Whether the artifact passes validation
        score: Quality score from 0-100
        errors: List of validation errors
        warnings: List of non-critical issues
        suggestions: List of improvement suggestions
    """
    is_valid: bool
    score: float  # 0-100
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    
    def __str__(self) -> str:
        status = "✅ VALID" if self.is_valid else "❌ INVALID"
        return f"{status} (Score: {self.score:.1f}/100)"


class ArtifactValidator:
    """
    Validates generated artifacts based on type-specific rules.
    
    Each artifact type has its own validation criteria to ensure
    quality and completeness.
    """
    
    def __init__(self):
        """Initialize validator with type-specific rules"""
        self.min_passing_score = 60.0  # Minimum score to pass validation
        self.validators = {
            'erd': self.validate_erd,
            'architecture': self.validate_architecture,
            'api_docs': self.validate_api_docs,
            'jira': self.validate_jira,
            'workflows': self.validate_workflows,
            'all_diagrams': self.validate_diagrams,
            'code_prototype': self.validate_code,
            'visual_prototype_dev': self.validate_html,
        }
    
    def validate(self, artifact_type: str, content: str, context: Dict = None) -> ValidationResult:
        """
        Validate artifact based on its type.
        
        Args:
            artifact_type: Type of artifact (erd, architecture, etc.)
            content: The generated content to validate
            context: Optional context (meeting notes, RAG data, etc.)
        
        Returns:
            ValidationResult with score, errors, warnings, suggestions
        """
        # Get appropriate validator
        validator = self.validators.get(artifact_type, self.validate_generic)
        
        # Run validation
        result = validator(content, context or {})
        
        # Determine if valid (score >= threshold and no critical errors)
        result.is_valid = (result.score >= self.min_passing_score and len(result.errors) == 0)
        
        return result
    
    # =========================================================================
    # Type-Specific Validators
    # =========================================================================
    
    def validate_erd(self, content: str, context: Dict) -> ValidationResult:
        """
        Validate ERD diagram (Mermaid format).
        
        Checks:
        - Is valid Mermaid syntax
        - Has entities and relationships
        - Entities have attributes
        - Relationships are properly defined
        """
        errors = []
        warnings = []
        suggestions = []
        score = 100.0
        
        # Check if empty
        if not content or len(content.strip()) < 50:
            errors.append("ERD diagram is too short or empty")
            score -= 50
            return ValidationResult(False, max(0, score), errors, warnings, suggestions)
        
        # Check for Mermaid ERD syntax
        if 'erDiagram' not in content and 'graph' not in content:
            errors.append("Missing Mermaid ERD/graph syntax")
            score -= 30
        
        # Check for entities (at least 2)
        entities = re.findall(r'\b[A-Z][A-Za-z0-9_]+\s*\{', content)
        if len(entities) < 2:
            warnings.append(f"Only {len(entities)} entities found, expected at least 2")
            score -= 10
        
        # Check for relationships
        relationships = re.findall(r'\|\|--\||o\||<\||>|\}o--', content)
        if len(relationships) == 0:
            warnings.append("No relationships defined between entities")
            score -= 20
        
        # Check for attributes
        if '{' in content and '}' in content:
            attributes_count = len(re.findall(r'\w+\s+\w+', content))
            if attributes_count < 5:
                warnings.append(f"Only {attributes_count} attributes found")
                score -= 5
        else:
            warnings.append("Entities should have attributes defined")
            score -= 10
        
        # Suggestions
        if len(entities) < 5:
            suggestions.append("Consider adding more entities for completeness")
        if 'id' not in content.lower():
            suggestions.append("Ensure entities have primary key (id) fields")
        
        return ValidationResult(True, max(0, score), errors, warnings, suggestions)
    
    def validate_architecture(self, content: str, context: Dict) -> ValidationResult:
        """
        Validate architecture diagram.
        
        Checks:
        - Has components/nodes
        - Has connections/edges
        - Proper layer separation
        - Clear data flow
        """
        errors = []
        warnings = []
        suggestions = []
        score = 100.0
        
        if not content or len(content.strip()) < 50:
            errors.append("Architecture diagram is too short or empty")
            score -= 50
            return ValidationResult(False, max(0, score), errors, warnings, suggestions)
        
        # Check for Mermaid syntax
        if 'graph' not in content and 'flowchart' not in content:
            errors.append("Missing Mermaid graph syntax")
            score -= 30
        
        # Check for nodes (components)
        nodes = re.findall(r'\[.+?\]|\(.+?\)|\{.+?\}', content)
        if len(nodes) < 3:
            warnings.append(f"Only {len(nodes)} components found, expected at least 3")
            score -= 15
        
        # Check for connections
        connections = re.findall(r'-->|--->', content)
        if len(connections) == 0:
            errors.append("No connections between components")
            score -= 25
        
        # Check for layers (frontend, backend, database)
        has_layers = any(term in content.lower() for term in ['frontend', 'backend', 'database', 'ui', 'api', 'db'])
        if not has_layers:
            warnings.append("Consider showing architectural layers (UI, API, DB)")
            score -= 10
        
        # Suggestions
        if 'api' not in content.lower():
            suggestions.append("Consider showing API endpoints or services")
        if len(nodes) > 15:
            suggestions.append("Complex architecture - consider creating multiple diagrams")
        
        return ValidationResult(True, max(0, score), errors, warnings, suggestions)
    
    def validate_api_docs(self, content: str, context: Dict) -> ValidationResult:
        """
        Validate API documentation.
        
        Checks:
        - Has endpoints defined
        - Includes HTTP methods
        - Has request/response examples
        - Describes parameters
        """
        errors = []
        warnings = []
        suggestions = []
        score = 100.0
        
        if not content or len(content.strip()) < 100:
            errors.append("API documentation is too short")
            score -= 50
            return ValidationResult(False, max(0, score), errors, warnings, suggestions)
        
        # Check for HTTP methods
        http_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        found_methods = [m for m in http_methods if m in content]
        if len(found_methods) == 0:
            errors.append("No HTTP methods found")
            score -= 30
        
        # Check for endpoints
        endpoints = re.findall(r'/[\w/-]+', content)
        if len(endpoints) < 2:
            warnings.append(f"Only {len(endpoints)} endpoints found")
            score -= 15
        
        # Check for request/response
        has_request = 'request' in content.lower() or 'body' in content.lower()
        has_response = 'response' in content.lower() or 'returns' in content.lower()
        
        if not has_request:
            warnings.append("Missing request examples")
            score -= 10
        if not has_response:
            warnings.append("Missing response examples")
            score -= 10
        
        # Check for status codes
        status_codes = re.findall(r'\b[2345]\d{2}\b', content)
        if len(status_codes) == 0:
            warnings.append("Consider adding HTTP status codes")
            score -= 5
        
        # Check for authentication
        has_auth = any(term in content.lower() for term in ['auth', 'token', 'bearer', 'api key'])
        if not has_auth:
            suggestions.append("Consider documenting authentication requirements")
        
        return ValidationResult(True, max(0, score), errors, warnings, suggestions)
    
    def validate_jira(self, content: str, context: Dict) -> ValidationResult:
        """
        Validate JIRA tasks.
        
        Checks:
        - Has epics/stories/tasks
        - Includes acceptance criteria
        - Has clear descriptions
        - Proper structure
        """
        errors = []
        warnings = []
        suggestions = []
        score = 100.0
        
        if not content or len(content.strip()) < 100:
            errors.append("JIRA tasks are too short")
            score -= 50
            return ValidationResult(False, max(0, score), errors, warnings, suggestions)
        
        # Check for task structure
        has_epic = 'epic' in content.lower()
        has_story = 'story' in content.lower() or 'user story' in content.lower()
        has_task = 'task' in content.lower()
        
        if not (has_epic or has_story or has_task):
            errors.append("No JIRA task structure found (Epic/Story/Task)")
            score -= 30
        
        # Check for acceptance criteria
        has_acceptance = 'acceptance' in content.lower() or 'given when then' in content.lower()
        if not has_acceptance:
            warnings.append("Missing acceptance criteria")
            score -= 15
        
        # Check for numbered lists (tasks)
        numbered_items = len(re.findall(r'^\d+\.|\-\s', content, re.MULTILINE))
        if numbered_items < 3:
            warnings.append(f"Only {numbered_items} tasks found, expected more")
            score -= 10
        
        # Check for descriptions
        if len(content) < 300:
            warnings.append("Task descriptions seem brief")
            score -= 5
        
        # Suggestions
        if 'priority' not in content.lower():
            suggestions.append("Consider adding priority levels")
        if 'estimate' not in content.lower():
            suggestions.append("Consider adding story point estimates")
        
        return ValidationResult(True, max(0, score), errors, warnings, suggestions)
    
    def validate_workflows(self, content: str, context: Dict) -> ValidationResult:
        """
        Validate deployment workflows.
        
        Checks:
        - Has clear steps
        - Includes setup instructions
        - Has deployment commands
        - Error handling mentioned
        """
        errors = []
        warnings = []
        suggestions = []
        score = 100.0
        
        if not content or len(content.strip()) < 100:
            errors.append("Workflow documentation is too short")
            score -= 50
            return ValidationResult(False, max(0, score), errors, warnings, suggestions)
        
        # Check for steps/sections
        sections = len(re.findall(r'^#+\s', content, re.MULTILINE))
        if sections < 3:
            warnings.append(f"Only {sections} sections found")
            score -= 10
        
        # Check for commands/code blocks
        code_blocks = len(re.findall(r'```', content))
        if code_blocks < 2:
            warnings.append("Missing command examples")
            score -= 15
        
        # Check for deployment keywords
        deployment_terms = ['deploy', 'build', 'install', 'setup', 'configure']
        found_terms = [t for t in deployment_terms if t in content.lower()]
        if len(found_terms) < 2:
            warnings.append("Missing deployment steps")
            score -= 10
        
        # Check for environment setup
        if 'environment' not in content.lower() and 'env' not in content.lower():
            suggestions.append("Consider documenting environment variables")
        
        return ValidationResult(True, max(0, score), errors, warnings, suggestions)
    
    def validate_diagrams(self, content: str, context: Dict) -> ValidationResult:
        """
        Validate multiple diagrams.
        
        Checks:
        - Has multiple diagram types
        - Each is properly formatted
        - Sufficient complexity
        """
        errors = []
        warnings = []
        suggestions = []
        score = 100.0
        
        # For multiple diagrams, check if content is a dict
        if isinstance(content, dict):
            diagram_count = len(content)
            if diagram_count < 3:
                warnings.append(f"Only {diagram_count} diagrams generated")
                score -= 10
            
            # Validate each diagram
            for name, diagram_content in content.items():
                if len(diagram_content.strip()) < 50:
                    warnings.append(f"{name} diagram is too short")
                    score -= 5
        else:
            # Single content string
            if len(content.strip()) < 200:
                warnings.append("Combined diagrams seem insufficient")
                score -= 20
        
        return ValidationResult(True, max(0, score), errors, warnings, suggestions)
    
    def validate_code(self, content: str, context: Dict) -> ValidationResult:
        """
        Validate generated code prototype.
        
        Checks:
        - Has proper structure
        - Includes key functions/classes
        - No obvious syntax errors
        - Has comments/documentation
        """
        errors = []
        warnings = []
        suggestions = []
        score = 100.0
        
        if not content or len(content.strip()) < 100:
            errors.append("Code prototype is too short")
            score -= 50
            return ValidationResult(False, max(0, score), errors, warnings, suggestions)
        
        # Check for basic code structure
        has_functions = 'def ' in content or 'function ' in content or 'public ' in content
        has_classes = 'class ' in content or 'interface ' in content
        
        if not (has_functions or has_classes):
            errors.append("No functions or classes found")
            score -= 30
        
        # Check for comments
        comment_lines = len(re.findall(r'//|#|/\*|\*/', content))
        if comment_lines < 5:
            warnings.append("Insufficient code documentation")
            score -= 10
        
        # Check for error handling
        has_error_handling = any(term in content.lower() for term in ['try', 'catch', 'except', 'error'])
        if not has_error_handling:
            warnings.append("No error handling found")
            score -= 15
        
        # Suggestions
        if 'test' not in content.lower():
            suggestions.append("Consider generating unit tests")
        
        return ValidationResult(True, max(0, score), errors, warnings, suggestions)
    
    def validate_html(self, content: str, context: Dict) -> ValidationResult:
        """
        Validate HTML prototype.
        
        Checks:
        - Valid HTML structure
        - Has DOCTYPE
        - Includes CSS/styling
        - No broken tags
        """
        errors = []
        warnings = []
        suggestions = []
        score = 100.0
        
        if not content or len(content.strip()) < 100:
            errors.append("HTML prototype is too short")
            score -= 50
            return ValidationResult(False, max(0, score), errors, warnings, suggestions)
        
        # Check for DOCTYPE
        if '<!DOCTYPE' not in content and '<!doctype' not in content:
            warnings.append("Missing DOCTYPE declaration")
            score -= 5
        
        # Check for basic HTML structure
        required_tags = ['<html', '<head', '<body']
        missing_tags = [tag for tag in required_tags if tag not in content.lower()]
        if missing_tags:
            errors.append(f"Missing required tags: {', '.join(missing_tags)}")
            score -= 20
        
        # Check for styling
        has_css = '<style' in content or 'style=' in content or '<link' in content
        if not has_css:
            warnings.append("No styling found")
            score -= 15
        
        # Check for balanced tags
        open_tags = len(re.findall(r'<(\w+)', content))
        close_tags = len(re.findall(r'</(\w+)>', content))
        if abs(open_tags - close_tags) > 3:  # Allow some self-closing tags
            warnings.append(f"Possibly unbalanced tags (open: {open_tags}, close: {close_tags})")
            score -= 10
        
        # Check for content
        if '<body></body>' in content or len(content) < 300:
            errors.append("HTML body is empty or minimal")
            score -= 25
        
        # Suggestions
        if 'responsive' not in content.lower() and 'viewport' not in content.lower():
            suggestions.append("Consider adding responsive design (viewport meta tag)")
        
        return ValidationResult(True, max(0, score), errors, warnings, suggestions)
    
    def validate_generic(self, content: str, context: Dict) -> ValidationResult:
        """
        Generic validation for unknown artifact types.
        
        Basic checks:
        - Not empty
        - Reasonable length
        - Has structure
        """
        errors = []
        warnings = []
        suggestions = []
        score = 100.0
        
        if not content or len(content.strip()) < 50:
            errors.append("Content is too short or empty")
            score -= 50
        elif len(content.strip()) < 200:
            warnings.append("Content seems brief")
            score -= 15
        
        return ValidationResult(True, max(0, score), errors, warnings, suggestions)
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def should_retry(self, result: Optional[ValidationResult]) -> bool:
        """
        Determine if generation should be retried based on validation result.
        
        Retry if:
        - Score is below threshold (< 60)
        - Has critical errors
        - Content is too short
        
        Args:
            result: ValidationResult from validation
        
        Returns:
            True if should retry, False otherwise
        """
        if result is None:
            return True
        
        if not result.is_valid:
            return True
        
        if result.score < self.min_passing_score:
            return True
        
        # Check for critical errors
        critical_keywords = ['empty', 'too short', 'missing required', 'no http methods']
        has_critical = any(
            any(keyword in error.lower() for keyword in critical_keywords)
            for error in result.errors
        )
        
        return has_critical
    
    def get_retry_feedback(self, result: Optional[ValidationResult], artifact_type: str) -> str:
        """
        Generate feedback to send to AI for retry attempt.
        
        Includes errors, warnings, and suggestions to improve the output.
        
        Args:
            result: ValidationResult with issues
            artifact_type: Type of artifact that failed
        
        Returns:
            Feedback string for AI
        """
        if result is None:
            return (
                "The previous generation returned empty output. "
                f"Please regenerate a complete {artifact_type} that follows the repository conventions and meeting notes."
            )

        feedback_parts = [
            f"The generated {artifact_type} did not pass validation (score: {result.score:.1f}/100).",
            "",
            "Please regenerate with the following improvements:",
            ""
        ]
        
        if result.errors:
            feedback_parts.append("**Errors to fix:**")
            for error in result.errors:
                feedback_parts.append(f"- {error}")
            feedback_parts.append("")
        
        if result.warnings:
            feedback_parts.append("**Warnings to address:**")
            for warning in result.warnings:
                feedback_parts.append(f"- {warning}")
            feedback_parts.append("")
        
        if result.suggestions:
            feedback_parts.append("**Suggestions:**")
            for suggestion in result.suggestions:
                feedback_parts.append(f"- {suggestion}")
        
        return "\n".join(feedback_parts)
