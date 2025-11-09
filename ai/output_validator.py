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
    
    def _extract_feature_keywords(self, meeting_notes: str) -> List[str]:
        """
        Extract key feature terms from meeting notes for semantic validation.
        
        Args:
            meeting_notes: Meeting notes text
            
        Returns:
            List of important keywords/phrases that should appear in generated content
        """
        if not meeting_notes:
            return []
        
        keywords = []
        content_lower = meeting_notes.lower()
        
        # Extract entity names (PascalCase or multi-word phrases)
        # Look for patterns like "PhoneSwapRequest", "Phone Swap Request", "swap request"
        common_patterns = [
            r'\b([A-Z][a-z]+){2,}\b',  # PascalCase: PhoneSwapRequest
            r'\b(phone\s*swap|swap\s*request|swap\s*modal)\b',  # Multi-word features
            r'/api/[\w\-/]+',  # API endpoints
            r'\bPOST\s+/[\w\-/]+',  # HTTP methods + endpoints
            r'\b([A-Z][a-z]+Modal|[A-Z][a-z]+Request|[A-Z][a-z]+Service)\b',  # Component patterns
        ]
        
        for pattern in common_patterns:
            matches = re.findall(pattern, content_lower)
            keywords.extend(matches)
        
        # Add known terms from common feature descriptions
        feature_terms = [
            'swap', 'phone swap', 'swap request', 'request phone',
            'exchange', 'offer phone', 'phone exchange'
        ]
        
        for term in feature_terms:
            if term in content_lower:
                keywords.append(term)
        
        # Extract specific entities mentioned in implementation details
        if 'phoneswap' in content_lower or 'phone-swap' in content_lower or 'phone_swap' in content_lower:
            keywords.extend(['phoneswap', 'phone-swap', 'phone_swap', 'swap'])
        
        if '/api/phone-swaps' in content_lower or 'phone-swaps' in content_lower:
            keywords.extend(['phone-swaps', 'swaps'])
        
        return list(set(keywords))  # Remove duplicates
    
    def _check_semantic_relevance(self, content: str, required_keywords: List[str]) -> Tuple[bool, int]:
        """
        Check if content is semantically relevant to the feature being implemented.
        
        Args:
            content: Generated content to check
            required_keywords: Keywords that should appear in content
            
        Returns:
            Tuple of (is_relevant: bool, keyword_match_count: int)
        """
        if not required_keywords:
            return True, 0
        
        content_lower = content.lower()
        matches = 0
        
        for keyword in required_keywords:
            if isinstance(keyword, tuple):
                keyword = keyword[0] if keyword else ''
            
            if keyword and keyword.lower() in content_lower:
                matches += 1
        
        # Consider relevant if at least 30% of keywords match
        threshold = max(1, len(required_keywords) * 0.3)
        is_relevant = matches >= threshold
        
        return is_relevant, matches
    
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
            # Return moderate default score to allow cloud fallback if quality is poor
            return ValidationResult.PASS, [], 70
        
        return validator(content)
    
    # ============================================================
    # Artifact-Specific Validators
    # ============================================================
    
    def _validate_erd(self, content: str) -> Tuple[ValidationResult, List[str], int]:
        """Validate Mermaid ERD diagram"""
        issues = []
        score = 100
        
        # SEMANTIC VALIDATION: Check if content is about the NEW feature
        meeting_notes = self._current_context.get('meeting_notes', '')
        if meeting_notes:
            feature_keywords = self._extract_feature_keywords(meeting_notes)
            is_relevant, keyword_matches = self._check_semantic_relevance(content, feature_keywords)
            
            if not is_relevant:
                issues.append(f"Content appears to be about existing codebase, not the new feature (only {keyword_matches}/{len(feature_keywords)} keywords matched)")
                score -= 40
            
            # Check for generic entities that suggest it's about existing code
            generic_indicators = ['user', 'phone', 'weatherforecast', 'forecast', 'userscontroller']
            swap_indicators = ['swap', 'phoneswap', 'swapmodal', 'swaprequest', 'phone-swap', 'phone_swap']
            
            content_lower = content.lower()
            has_generic = any(indicator in content_lower for indicator in generic_indicators)
            has_swap = any(indicator in content_lower for indicator in swap_indicators)
            
            if has_generic and not has_swap:
                issues.append("ERD contains generic entities (User, Phone, WeatherForecast) without swap-related context")
                score -= 30
        
        # SYNTACTIC VALIDATION (original checks)
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
        
        # SEMANTIC VALIDATION: Check if content is about the NEW feature
        meeting_notes = self._current_context.get('meeting_notes', '')
        if meeting_notes:
            feature_keywords = self._extract_feature_keywords(meeting_notes)
            is_relevant, keyword_matches = self._check_semantic_relevance(content, feature_keywords)
            
            if not is_relevant:
                issues.append(f"Architecture appears to be about existing system, not the new feature (only {keyword_matches}/{len(feature_keywords)} keywords matched)")
                score -= 40
            
            # Check for generic components that suggest it's about existing code
            generic_indicators = ['userscontroller', 'weathercontroller', 'forecastcontroller', 'userservice']
            swap_indicators = ['swapmodal', 'swapcontroller', 'swapservice', 'swapapi', 'phone-swap', 'phoneswap']
            
            content_lower = content.lower()
            has_generic = any(indicator in content_lower for indicator in generic_indicators)
            has_swap = any(indicator in content_lower for indicator in swap_indicators)
            
            if has_generic and not has_swap:
                issues.append("Architecture contains generic components (UsersController, WeatherForecast) without swap-related context")
                score -= 30
        
        # SYNTACTIC VALIDATION (original checks)
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
        
        # SEMANTIC VALIDATION: Check if content is about the NEW feature
        meeting_notes = self._current_context.get('meeting_notes', '')
        if meeting_notes:
            feature_keywords = self._extract_feature_keywords(meeting_notes)
            is_relevant, keyword_matches = self._check_semantic_relevance(content, feature_keywords)
            
            if not is_relevant:
                issues.append(f"Sequence diagram appears to be about existing flows, not the new feature (only {keyword_matches}/{len(feature_keywords)} keywords matched)")
                score -= 40
            
            # Check for swap-specific participants and messages
            swap_indicators = ['swap', 'phoneswap', 'swapcontroller', 'swapservice', 'swapmodal', 'phone-swap']
            content_lower = content.lower()
            has_swap = any(indicator in content_lower for indicator in swap_indicators)
            
            if not has_swap:
                issues.append("Sequence diagram doesn't contain swap-related participants or interactions")
                score -= 30
        
        # SYNTACTIC VALIDATION (original checks)
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
        
        # SEMANTIC VALIDATION: Check if content is about the NEW feature
        meeting_notes = self._current_context.get('meeting_notes', '')
        if meeting_notes:
            feature_keywords = self._extract_feature_keywords(meeting_notes)
            is_relevant, keyword_matches = self._check_semantic_relevance(content, feature_keywords)
            
            if not is_relevant:
                issues.append(f"Class diagram appears to be about existing classes, not the new feature (only {keyword_matches}/{len(feature_keywords)} keywords matched)")
                score -= 40
            
            # Check for swap-specific classes
            swap_class_indicators = ['swap', 'phoneswap', 'swaprequest', 'swapmodal', 'swapservice', 'swapcontroller', 'phone-swap']
            content_lower = content.lower()
            has_swap_classes = any(indicator in content_lower for indicator in swap_class_indicators)
            
            if not has_swap_classes:
                issues.append("Class diagram doesn't contain swap-related classes (SwapRequest, SwapModal, SwapService, etc.)")
                score -= 30
        
        # SYNTACTIC VALIDATION (original checks)
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
        
        # SEMANTIC VALIDATION: Check if content is about the NEW feature
        meeting_notes = self._current_context.get('meeting_notes', '')
        if meeting_notes:
            feature_keywords = self._extract_feature_keywords(meeting_notes)
            is_relevant, keyword_matches = self._check_semantic_relevance(content, feature_keywords)
            
            if not is_relevant:
                issues.append(f"State diagram appears to be about existing states, not the new feature (only {keyword_matches}/{len(feature_keywords)} keywords matched)")
                score -= 40
            
            # Check for swap-specific states
            swap_state_indicators = ['pending', 'approved', 'rejected', 'cancelled', 'swap', 'request']
            content_lower = content.lower()
            swap_state_count = sum(1 for indicator in swap_state_indicators if indicator in content_lower)
            
            if swap_state_count < 2:
                issues.append("State diagram doesn't contain swap-related states (Pending, Approved, Rejected, Cancelled)")
                score -= 30
        
        # SYNTACTIC VALIDATION (original checks)
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
        
        # SEMANTIC VALIDATION: Check if content is about the NEW feature
        meeting_notes = self._current_context.get('meeting_notes', '')
        if meeting_notes:
            feature_keywords = self._extract_feature_keywords(meeting_notes)
            is_relevant, keyword_matches = self._check_semantic_relevance(content, feature_keywords)
            
            if not is_relevant:
                issues.append(f"Code appears to be about existing features, not the new feature (only {keyword_matches}/{len(feature_keywords)} keywords matched)")
                score -= 40
            
            # Check for swap-specific code elements
            swap_code_indicators = [
                'swap', 'phoneswap', 'swaprequest', 'swapmodal', 'swapservice', 'swapcontroller',
                'phone-swap', 'phone_swap', 'createswap', 'processswap', 'requestswap'
            ]
            content_lower = content.lower()
            has_swap_code = any(indicator in content_lower for indicator in swap_code_indicators)
            
            if not has_swap_code:
                issues.append("Code doesn't contain swap-related classes, methods, or variables")
                score -= 30
        
        # SYNTACTIC VALIDATION (original checks)
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
        
        # SEMANTIC VALIDATION: Check if content is about the NEW feature
        meeting_notes = self._current_context.get('meeting_notes', '')
        if meeting_notes:
            feature_keywords = self._extract_feature_keywords(meeting_notes)
            is_relevant, keyword_matches = self._check_semantic_relevance(content, feature_keywords)
            
            if not is_relevant:
                issues.append(f"HTML appears to be about existing UI, not the new feature (only {keyword_matches}/{len(feature_keywords)} keywords matched)")
                score -= 40
            
            # Check for swap-specific UI elements
            swap_ui_indicators = ['swap', 'swapmodal', 'phone-swap', 'request-phone', 'exchange']
            content_lower = content.lower()
            has_swap_ui = any(indicator in content_lower for indicator in swap_ui_indicators)
            
            if not has_swap_ui:
                issues.append("HTML doesn't contain swap-related UI components (modal, buttons, forms)")
                score -= 30
        
        # SYNTACTIC VALIDATION (original checks)
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
        
        # SEMANTIC VALIDATION: Check if content is about the NEW feature
        meeting_notes = self._current_context.get('meeting_notes', '')
        if meeting_notes:
            feature_keywords = self._extract_feature_keywords(meeting_notes)
            is_relevant, keyword_matches = self._check_semantic_relevance(content, feature_keywords)
            
            if not is_relevant:
                issues.append(f"API docs appear to be about existing endpoints, not the new feature (only {keyword_matches}/{len(feature_keywords)} keywords matched)")
                score -= 40
            
            # Check for swap-specific API endpoints
            swap_api_indicators = ['/api/phone-swaps', '/phone-swaps', 'swap', 'phone-swap', 'phoneswap']
            content_lower = content.lower()
            has_swap_api = any(indicator in content_lower for indicator in swap_api_indicators)
            
            if not has_swap_api:
                issues.append("API docs don't mention phone swap endpoints")
                score -= 30
        
        # SYNTACTIC VALIDATION (original checks)
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
        
        # SEMANTIC VALIDATION: Check if content is about the NEW feature
        meeting_notes = self._current_context.get('meeting_notes', '')
        if meeting_notes:
            feature_keywords = self._extract_feature_keywords(meeting_notes)
            is_relevant, keyword_matches = self._check_semantic_relevance(content, feature_keywords)
            
            if not is_relevant:
                issues.append(f"JIRA story appears to be about existing features, not the new phone swap feature (only {keyword_matches}/{len(feature_keywords)} keywords matched)")
                score -= 40
        
        # SYNTACTIC VALIDATION (original checks)
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
        
        # SEMANTIC VALIDATION: Check if content is about the NEW feature
        meeting_notes = self._current_context.get('meeting_notes', '')
        if meeting_notes:
            feature_keywords = self._extract_feature_keywords(meeting_notes)
            is_relevant, keyword_matches = self._check_semantic_relevance(content, feature_keywords)
            
            if not is_relevant:
                issues.append(f"Workflow appears to be about existing processes, not the new phone swap feature (only {keyword_matches}/{len(feature_keywords)} keywords matched)")
                score -= 40
        
        # SYNTACTIC VALIDATION (original checks)
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
