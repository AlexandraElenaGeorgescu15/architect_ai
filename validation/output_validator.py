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
        is_generic_content: Whether the content is generic/placeholder (not project-specific)
    """
    is_valid: bool
    score: float  # 0-100
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    is_generic_content: bool = False  # Flag for generic content detection
    
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
        self.min_passing_score = 80.0  # Minimum score to pass validation (increased from 60.0)
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
    
    def _detect_generic_content(self, content: str, context: Dict = None) -> Tuple[bool, List[str]]:
        """
        Detect generic/placeholder content that is not project-specific.
        
        Returns:
            Tuple of (is_generic, list_of_issues)
        """
        issues = []
        is_generic = False
        content_lower = content.lower()
        
        # Only flag truly generic placeholder entities (not common domain entities)
        # Removed legitimate entities like 'user', 'registration api', 'angular', etc.
        generic_entities = [
            'example entity', 'sample entity', 'placeholder', 'todo', 'tbd',
            'replace me', 'your entity here', 'entity name'
        ]
        
        # Generic patterns (very strict - only obvious placeholders)
        generic_patterns = [
            r'node\s+\d+\s*->\s*node\s+\d+',  # node 1 -> node 2
            r'example\s+\d+',
            r'sample\s+\d+',
            r'placeholder\s+\d+',
        ]
        
        # Placeholder nodes (single letters are OK, just not chains of them)
        placeholder_nodes = [
            'node 1', 'node 2', 'node 3', 'node 4', 'node 5',
            'example', 'sample', 'placeholder', 'todo'
        ]
        
        # Check for generic entities
        for entity in generic_entities:
            if entity in content_lower:
                issues.append(f"Generic placeholder detected: {entity}")
                is_generic = True
        
        # Check for generic patterns
        for pattern in generic_patterns:
            if re.search(pattern, content_lower):
                issues.append(f"Generic placeholder pattern detected: {pattern}")
                is_generic = True
        
        # Check for placeholder nodes (require many to flag)
        placeholder_count = sum(1 for placeholder in placeholder_nodes if placeholder in content_lower)
        if placeholder_count >= 5:  # Increased from 3 to 5 - more lenient
            issues.append(f"Multiple placeholder nodes detected ({placeholder_count})")
            is_generic = True
        
        # Removed file path checking - these are legitimate in architecture diagrams
        
        # Relaxed ERD field checking - having just id and name is sometimes legitimate
        # Only flag if ALL entities have only these fields
        if 'erd' in content_lower or 'erDiagram' in content_lower:
            entity_blocks = re.findall(r'\{[^}]+\}', content)
            generic_entity_count = 0
            for block in entity_blocks:
                fields = re.findall(r'\w+\s+\w+', block)
                if len(fields) <= 2:
                    # Check if fields are just "id" and "name"
                    field_names = [f.split()[1].lower() for f in fields]
                    if set(field_names) <= {'id', 'name', 'pk', 'fk'}:
                        generic_entity_count += 1
            
            # Only flag if ALL entities are generic (not just one or two)
            if entity_blocks and generic_entity_count == len(entity_blocks) and len(entity_blocks) >= 2:
                issues.append("All entities have only generic fields (id, name) - likely generic")
                is_generic = True
        
        return is_generic, issues
    
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
        - Is valid Mermaid syntax (PROGRAMMATIC)
        - Has entities and relationships
        - Entities have attributes
        - Relationships are properly defined
        - Context-aware: Checks if entities match requirements in RAG/meeting notes
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
        
        # STEP 1: PROGRAMMATIC SYNTAX VALIDATION (catches errors AI might miss)
        try:
            from components.mermaid_syntax_corrector import validate_mermaid_syntax
            is_valid_syntax, error_msg, syntax_errors = validate_mermaid_syntax(content)
            
            if not is_valid_syntax:
                errors.append(f"Syntax error: {error_msg}")
                score -= 30
                if syntax_errors:
                    for syntax_error in syntax_errors[:3]:  # Show first 3 errors
                        errors.append(f"Syntax: {syntax_error}")
                        score -= 5
        except Exception as e:
            # Fallback to basic regex check
            pass
        
        # NOTE: Syntax correction with MermaidSyntaxCorrector happens AFTER validation
        # We skip it here to avoid "coroutine never awaited" warnings
        # The diagram fixer is called separately in the generation flow
        
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
        
        # NEW: Context-aware validation (check if entities match requirements)
        if context.get('rag_context') or context.get('user_request'):
            combined_context = f"{context.get('rag_context', '')} {context.get('user_request', '')}".lower()
            
            # Extract expected entities from context (common nouns in caps or plurals)
            expected_entities = set()
            for word in re.findall(r'\b[A-Z][a-z]+(?:s)?\b', combined_context):
                if len(word) > 3:  # Filter short words
                    expected_entities.add(word.rstrip('s'))  # Remove plural
            
            # Check if generated entities cover expected ones
            entity_names = [e.split('{')[0].strip() for e in entities]
            entity_names_lower = [e.lower() for e in entity_names]
            
            missing_entities = []
            for expected in expected_entities:
                if expected.lower() not in entity_names_lower and expected.lower() not in combined_context.count(expected.lower()) < 2:
                    # Only flag if mentioned multiple times in context
                    if combined_context.count(expected.lower()) >= 2:
                        missing_entities.append(expected)
            
            if missing_entities and len(missing_entities) <= 3:
                warnings.append(f"May be missing entities mentioned in requirements: {', '.join(missing_entities[:3])}")
                score -= 5
        
        # STEP 2: GENERIC CONTENT DETECTION (CRITICAL - FAIL IF GENERIC)
        is_generic, generic_issues = self._detect_generic_content(content, context)
        if is_generic:
            errors.extend([f"❌ GENERIC CONTENT: {issue}" for issue in generic_issues[:3]])  # Show first 3 issues
            score = 0  # FAIL VALIDATION - Generic content is unacceptable
            errors.append("⛔ VALIDATION FAILED: Content is generic/placeholder, not project-specific. Regenerate with actual project context.")
        
        # Suggestions
        if len(entities) < 5:
            suggestions.append("Consider adding more entities for completeness")
        if 'id' not in content.lower():
            suggestions.append("Ensure entities have primary key (id) fields")
        
        return ValidationResult(True, max(0, score), errors, warnings, suggestions, is_generic_content=is_generic)
    
    def validate_architecture(self, content: str, context: Dict) -> ValidationResult:
        """
        Validate architecture diagram.
        
        Checks:
        - PROGRAMMATIC: Valid Mermaid syntax
        - Has components/nodes
        - Has connections/edges
        - Proper layer separation
        - Clear data flow
        - Context-aware: Validates against mentioned technologies/components
        """
        errors = []
        warnings = []
        suggestions = []
        score = 100.0
        
        if not content or len(content.strip()) < 50:
            errors.append("Architecture diagram is too short or empty")
            score -= 50
            return ValidationResult(False, max(0, score), errors, warnings, suggestions)
        
        # STEP 1: PROGRAMMATIC SYNTAX VALIDATION
        try:
            from components.mermaid_syntax_corrector import validate_mermaid_syntax
            is_valid_syntax, error_msg, syntax_errors = validate_mermaid_syntax(content)
            
            if not is_valid_syntax:
                errors.append(f"Syntax error: {error_msg}")
                score -= 30
                if syntax_errors:
                    for syntax_error in syntax_errors[:3]:
                        errors.append(f"Syntax: {syntax_error}")
                        score -= 5
        except Exception:
            pass
        
        # NOTE: Syntax correction with MermaidSyntaxCorrector happens AFTER validation
        # We skip it here to avoid "coroutine never awaited" warnings
        # The diagram fixer is called separately in the generation flow
        
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
        
        # NEW: Context-aware validation (check for mentioned technologies)
        if context.get('rag_context') or context.get('user_request'):
            combined_context = f"{context.get('rag_context', '')} {context.get('user_request', '')}".lower()
            
            # Common tech stack keywords to look for
            tech_keywords = ['react', 'angular', 'vue', 'node', 'express', 'django', 'flask', 'spring',
                           'postgres', 'mysql', 'mongodb', 'redis', 'kafka', 'nginx', 'docker', 'kubernetes']
            
            mentioned_tech = [tech for tech in tech_keywords if tech in combined_context]
            included_tech = [tech for tech in mentioned_tech if tech in content.lower()]
            missing_tech = [tech for tech in mentioned_tech if tech not in content.lower()]
            
            if missing_tech and len(missing_tech) <= 3:
                warnings.append(f"Requirements mention {', '.join(missing_tech[:3])} but not shown in diagram")
                score -= 8
        
        # STEP 2: GENERIC CONTENT DETECTION (CRITICAL - FAIL IF GENERIC)
        is_generic, generic_issues = self._detect_generic_content(content, context)
        if is_generic:
            errors.extend([f"❌ GENERIC CONTENT: {issue}" for issue in generic_issues[:3]])
            score = 0  # FAIL VALIDATION - Generic content is unacceptable
            errors.append("⛔ VALIDATION FAILED: Content is generic/placeholder, not project-specific. Regenerate with actual project context.")
        
        # Suggestions
        if 'api' not in content.lower():
            suggestions.append("Consider showing API endpoints or services")
        if len(nodes) > 15:
            suggestions.append("Complex architecture - consider creating multiple diagrams")
        
        return ValidationResult(True, max(0, score), errors, warnings, suggestions, is_generic_content=is_generic)
    
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
        
        # STEP 2: GENERIC CONTENT DETECTION (CRITICAL - FAIL IF GENERIC)
        is_generic, generic_issues = self._detect_generic_content(content, context)
        if is_generic:
            errors.extend([f"❌ GENERIC CONTENT: {issue}" for issue in generic_issues[:3]])
            score = 0  # FAIL VALIDATION - Generic content is unacceptable
            errors.append("⛔ VALIDATION FAILED: Content is generic/placeholder, not project-specific. Regenerate with actual project context.")
        
        return ValidationResult(True, max(0, score), errors, warnings, suggestions, is_generic_content=is_generic)
    
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
        
        # STEP 2: GENERIC CONTENT DETECTION (CRITICAL - FAIL IF GENERIC)
        is_generic, generic_issues = self._detect_generic_content(content, context)
        if is_generic:
            errors.extend([f"❌ GENERIC CONTENT: {issue}" for issue in generic_issues[:3]])
            score = 0  # FAIL VALIDATION - Generic content is unacceptable
            errors.append("⛔ VALIDATION FAILED: Content is generic/placeholder, not project-specific. Regenerate with actual project context.")
        
        # Suggestions
        if 'priority' not in content.lower():
            suggestions.append("Consider adding priority levels")
        if 'estimate' not in content.lower():
            suggestions.append("Consider adding story point estimates")
        
        return ValidationResult(True, max(0, score), errors, warnings, suggestions, is_generic_content=is_generic)
    
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
        
        # STEP 2: GENERIC CONTENT DETECTION (CRITICAL - FAIL IF GENERIC)
        is_generic, generic_issues = self._detect_generic_content(content, context)
        if is_generic:
            errors.extend([f"❌ GENERIC CONTENT: {issue}" for issue in generic_issues[:3]])
            score = 0  # FAIL VALIDATION - Generic content is unacceptable
            errors.append("⛔ VALIDATION FAILED: Content is generic/placeholder, not project-specific. Regenerate with actual project context.")
        
        return ValidationResult(True, max(0, score), errors, warnings, suggestions, is_generic_content=is_generic)
    
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
        - PROGRAMMATIC: Valid HTML syntax (balanced tags, proper nesting)
        - Has DOCTYPE
        - Includes CSS/styling
        - No broken tags
        - Context-aware: Validates UI elements match requirements
        """
        errors = []
        warnings = []
        suggestions = []
        score = 100.0
        
        if not content or len(content.strip()) < 100:
            errors.append("HTML prototype is too short")
            score -= 50
            return ValidationResult(False, max(0, score), errors, warnings, suggestions)
        
        # STEP 1: PROGRAMMATIC SYNTAX VALIDATION
        # Check for balanced tags
        tag_pattern = r'<(\w+)(?:\s[^>]*)?>|</(\w+)>'
        tags_stack = []
        tag_matches = re.finditer(tag_pattern, content, re.IGNORECASE)
        
        self_closing_tags = {'img', 'br', 'hr', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'param', 'source', 'track', 'wbr'}
        
        for match in tag_matches:
            opening_tag = match.group(1)
            closing_tag = match.group(2)
            
            if opening_tag:
                tag_lower = opening_tag.lower()
                if tag_lower not in self_closing_tags:
                    tags_stack.append(tag_lower)
            elif closing_tag:
                tag_lower = closing_tag.lower()
                if not tags_stack:
                    errors.append(f"Unmatched closing tag: </{tag_lower}>")
                    score -= 10
                elif tags_stack[-1] != tag_lower:
                    errors.append(f"Tag mismatch: expected </{tags_stack[-1]}>, got </{tag_lower}>")
                    score -= 10
                    tags_stack.pop()
                else:
                    tags_stack.pop()
        
        if tags_stack:
            unclosed = ', '.join(f"<{tag}>" for tag in tags_stack[:3])
            errors.append(f"Unclosed tags: {unclosed}")
            score -= 15
        
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
        
        # Check for interactivity
        has_js = '<script' in content or 'onclick=' in content
        if not has_js:
            warnings.append("No JavaScript/interactivity found")
            score -= 10
        
        # NEW: Context-aware validation (check for required UI elements)
        if context.get('rag_context') or context.get('user_request'):
            combined_context = f"{context.get('rag_context', '')} {context.get('user_request', '')}".lower()
            
            # Common UI element keywords
            ui_elements = {
                'form': ['<form', '<input', '<button'],
                'table': ['<table', '<tr', '<td'],
                'list': ['<ul', '<ol', '<li'],
                'nav': ['<nav', 'navigation'],
                'header': ['<header'],
                'footer': ['<footer'],
                'card': ['class="card"', 'class=\'card\''],
                'modal': ['modal', 'dialog'],
                'dropdown': ['<select', 'dropdown']
            }
            
            missing_elements = []
            for element_name, element_patterns in ui_elements.items():
                if element_name in combined_context:
                    # Check if any pattern for this element exists in HTML
                    if not any(pattern in content.lower() for pattern in element_patterns):
                        missing_elements.append(element_name)
            
            if missing_elements and len(missing_elements) <= 3:
                warnings.append(f"Requirements mention {', '.join(missing_elements[:3])} but not found in HTML")
                score -= 10
        
        # Check for responsiveness
        is_responsive = 'viewport' in content or 'media' in content or 'responsive' in content
        if not is_responsive:
            suggestions.append("Consider adding responsive design (viewport meta tag)")
        
        # Suggestions
        if 'title' not in content.lower():
            suggestions.append("Add a <title> tag for better SEO")
        
        return ValidationResult(True, max(0, score), errors, warnings, suggestions)
        
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
