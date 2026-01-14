"""
Artifact Suggestions Service

Provides intelligent recommendations for artifact generation workflow.
Analyzes existing artifacts and meeting notes to suggest optimal next steps
using artifact relationship patterns and dependency analysis.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class SuggestionPriority(str, Enum):
    """Priority level for suggestions."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ArtifactSuggestion:
    """A suggested artifact to generate next."""
    artifact_type: str
    reason: str
    priority: SuggestionPriority
    context: str  # Why this suggestion makes sense
    estimated_value: str  # What the user gains
    dependencies: List[str]  # What should exist first
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "priority": self.priority.value
        }


# Artifact generation flow patterns - what naturally follows what
ARTIFACT_FLOW_PATTERNS = {
    # After ERD, these make sense
    "mermaid_erd": [
        ("mermaid_sequence", "Sequence diagram showing data flow between entities", SuggestionPriority.HIGH),
        ("api_docs", "API documentation for CRUD operations on these entities", SuggestionPriority.HIGH),
        ("code_prototype", "Backend code scaffold for entity models", SuggestionPriority.MEDIUM),
        ("mermaid_class", "Class diagram showing entity relationships", SuggestionPriority.MEDIUM),
    ],
    
    # After Architecture diagram
    "mermaid_architecture": [
        ("mermaid_component", "Component diagram with more detail", SuggestionPriority.HIGH),
        ("mermaid_sequence", "Sequence diagram showing component interactions", SuggestionPriority.HIGH),
        ("api_docs", "API documentation for service interfaces", SuggestionPriority.MEDIUM),
        ("mermaid_data_flow", "Data flow diagram showing information movement", SuggestionPriority.MEDIUM),
    ],
    
    # After Sequence diagram
    "mermaid_sequence": [
        ("api_docs", "API documentation for the endpoints in this flow", SuggestionPriority.HIGH),
        ("code_prototype", "Implementation code for this flow", SuggestionPriority.HIGH),
        ("mermaid_state", "State diagram for entities involved", SuggestionPriority.MEDIUM),
    ],
    
    # After API docs
    "api_docs": [
        ("code_prototype", "Backend implementation with these endpoints", SuggestionPriority.HIGH),
        ("dev_visual_prototype", "Frontend UI to consume these APIs", SuggestionPriority.HIGH),
        ("mermaid_api_sequence", "API sequence diagram showing endpoint calls", SuggestionPriority.MEDIUM),
    ],
    
    # After Code prototype
    "code_prototype": [
        ("dev_visual_prototype", "UI prototype to interact with this code", SuggestionPriority.HIGH),
        ("jira", "JIRA stories for implementation tasks", SuggestionPriority.MEDIUM),
        ("workflows", "Workflow documentation for the feature", SuggestionPriority.LOW),
    ],
    
    # After Visual prototype
    "dev_visual_prototype": [
        ("mermaid_user_flow", "User flow diagram showing interaction paths", SuggestionPriority.MEDIUM),
        ("jira", "JIRA stories for frontend tasks", SuggestionPriority.MEDIUM),
        ("personas", "User personas who will use this UI", SuggestionPriority.LOW),
    ],
    
    # After JIRA stories
    "jira": [
        ("workflows", "Detailed workflow documentation", SuggestionPriority.MEDIUM),
        ("estimations", "Time and effort estimations", SuggestionPriority.MEDIUM),
        ("backlog", "Full product backlog organization", SuggestionPriority.LOW),
    ],
    
    # After Class diagram
    "mermaid_class": [
        ("code_prototype", "Implementation of these classes", SuggestionPriority.HIGH),
        ("mermaid_sequence", "Sequence diagram showing class interactions", SuggestionPriority.MEDIUM),
    ],
    
    # After State diagram
    "mermaid_state": [
        ("mermaid_sequence", "Sequence diagram showing state transitions", SuggestionPriority.MEDIUM),
        ("code_prototype", "State machine implementation", SuggestionPriority.MEDIUM),
    ],
    
    # After Component diagram
    "mermaid_component": [
        ("mermaid_sequence", "Sequence showing component communication", SuggestionPriority.HIGH),
        ("mermaid_c4_component", "C4 component diagram with more detail", SuggestionPriority.MEDIUM),
    ],
    
    # After C4 diagrams
    "mermaid_c4_context": [
        ("mermaid_c4_container", "C4 Container diagram - zoom into the system", SuggestionPriority.HIGH),
    ],
    "mermaid_c4_container": [
        ("mermaid_c4_component", "C4 Component diagram - zoom into containers", SuggestionPriority.HIGH),
    ],
    "mermaid_c4_component": [
        ("code_prototype", "Implementation of these components", SuggestionPriority.HIGH),
        ("mermaid_c4_deployment", "Deployment diagram showing infrastructure", SuggestionPriority.MEDIUM),
    ],
}

# What artifacts complement each other (should exist together)
ARTIFACT_COMPANIONS = {
    "mermaid_erd": ["api_docs", "code_prototype", "mermaid_sequence"],
    "mermaid_architecture": ["mermaid_component", "mermaid_data_flow"],
    "api_docs": ["code_prototype", "dev_visual_prototype"],
    "code_prototype": ["dev_visual_prototype", "jira"],
    "dev_visual_prototype": ["mermaid_user_flow", "personas"],
    "jira": ["workflows", "estimations", "backlog"],
}

# Starting suggestions when nothing exists
INITIAL_SUGGESTIONS = [
    ("mermaid_erd", "Start with data model - ERD shows your entities and relationships", SuggestionPriority.HIGH),
    ("mermaid_architecture", "Start with system overview - shows high-level components", SuggestionPriority.HIGH),
    ("jira", "Start with JIRA stories - break down requirements into tasks", SuggestionPriority.MEDIUM),
    ("dev_visual_prototype", "Start with UI prototype - visualize the user experience", SuggestionPriority.MEDIUM),
]


class SuggestionEngine:
    """
    Intelligent suggestion engine that recommends next artifacts to generate.
    
    Uses:
    - Artifact flow patterns (what naturally follows what)
    - Companion artifacts (what should exist together)
    - Meeting notes analysis (what's mentioned but not generated)
    - Gap detection (missing pieces in the workflow)
    """
    
    def __init__(self):
        self.flow_patterns = ARTIFACT_FLOW_PATTERNS
        self.companions = ARTIFACT_COMPANIONS
        self.initial_suggestions = INITIAL_SUGGESTIONS
    
    def get_suggestions(
        self,
        existing_artifacts: List[Dict[str, Any]],
        meeting_notes: str = "",
        max_suggestions: int = 5
    ) -> List[ArtifactSuggestion]:
        """
        Get smart suggestions for what to generate next.
        
        Args:
            existing_artifacts: List of already generated artifacts with 'type' field
            meeting_notes: Current meeting notes content
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            List of ArtifactSuggestion ordered by priority
        """
        suggestions: List[ArtifactSuggestion] = []
        existing_types: Set[str] = {a.get('type', '') for a in existing_artifacts}
        
        logger.info(f"Generating suggestions. Existing artifacts: {existing_types}")
        
        # Case 1: No artifacts yet - suggest starting points
        if not existing_types:
            suggestions = self._get_initial_suggestions(meeting_notes)
            return suggestions[:max_suggestions]
        
        # Case 2: Get flow-based suggestions (what follows existing artifacts)
        flow_suggestions = self._get_flow_suggestions(existing_types, meeting_notes)
        suggestions.extend(flow_suggestions)
        
        # Case 3: Get companion suggestions (what should exist alongside)
        companion_suggestions = self._get_companion_suggestions(existing_types)
        suggestions.extend(companion_suggestions)
        
        # Case 4: Analyze meeting notes for mentioned but not generated
        if meeting_notes:
            notes_suggestions = self._analyze_meeting_notes(meeting_notes, existing_types)
            suggestions.extend(notes_suggestions)
        
        # Deduplicate and sort by priority
        suggestions = self._deduplicate_and_sort(suggestions, existing_types)
        
        return suggestions[:max_suggestions]
    
    def _get_initial_suggestions(self, meeting_notes: str) -> List[ArtifactSuggestion]:
        """Get suggestions when no artifacts exist."""
        suggestions = []
        
        # Analyze meeting notes to prioritize initial suggestions
        notes_lower = meeting_notes.lower() if meeting_notes else ""
        
        for artifact_type, reason, priority in self.initial_suggestions:
            # Boost priority based on meeting notes content
            adjusted_priority = priority
            
            if artifact_type == "mermaid_erd" and any(kw in notes_lower for kw in ["database", "table", "entity", "field", "schema", "data"]):
                adjusted_priority = SuggestionPriority.HIGH
            elif artifact_type == "mermaid_architecture" and any(kw in notes_lower for kw in ["system", "component", "service", "architecture"]):
                adjusted_priority = SuggestionPriority.HIGH
            elif artifact_type == "dev_visual_prototype" and any(kw in notes_lower for kw in ["ui", "modal", "button", "form", "screen", "page"]):
                adjusted_priority = SuggestionPriority.HIGH
            elif artifact_type == "jira" and any(kw in notes_lower for kw in ["story", "task", "sprint", "backlog", "acceptance"]):
                adjusted_priority = SuggestionPriority.HIGH
            
            suggestions.append(ArtifactSuggestion(
                artifact_type=artifact_type,
                reason=reason,
                priority=adjusted_priority,
                context="Good starting point for your project",
                estimated_value="Foundation for other artifacts",
                dependencies=[]
            ))
        
        return suggestions
    
    def _get_flow_suggestions(
        self,
        existing_types: Set[str],
        meeting_notes: str
    ) -> List[ArtifactSuggestion]:
        """Get suggestions based on natural artifact flow."""
        suggestions = []
        
        for existing_type in existing_types:
            if existing_type in self.flow_patterns:
                for next_type, reason, priority in self.flow_patterns[existing_type]:
                    if next_type not in existing_types:
                        suggestions.append(ArtifactSuggestion(
                            artifact_type=next_type,
                            reason=reason,
                            priority=priority,
                            context=f"Natural next step after {self._format_type(existing_type)}",
                            estimated_value=f"Expands on your {self._format_type(existing_type)}",
                            dependencies=[existing_type]
                        ))
        
        return suggestions
    
    def _get_companion_suggestions(self, existing_types: Set[str]) -> List[ArtifactSuggestion]:
        """Get suggestions for companion artifacts that should exist together."""
        suggestions = []
        
        for existing_type in existing_types:
            if existing_type in self.companions:
                for companion_type in self.companions[existing_type]:
                    if companion_type not in existing_types:
                        suggestions.append(ArtifactSuggestion(
                            artifact_type=companion_type,
                            reason=f"Complements your {self._format_type(existing_type)}",
                            priority=SuggestionPriority.MEDIUM,
                            context=f"Often paired with {self._format_type(existing_type)}",
                            estimated_value="Completes your documentation set",
                            dependencies=[existing_type]
                        ))
        
        return suggestions
    
    def _analyze_meeting_notes(
        self,
        meeting_notes: str,
        existing_types: Set[str]
    ) -> List[ArtifactSuggestion]:
        """Analyze meeting notes for mentioned but not generated artifacts."""
        suggestions = []
        notes_lower = meeting_notes.lower()
        
        # Keywords that suggest specific artifact types
        keyword_mappings = {
            "mermaid_erd": ["database", "table", "entity", "field", "column", "schema", "foreign key", "primary key", "relationship"],
            "mermaid_sequence": ["flow", "process", "step", "sequence", "interaction", "call", "request", "response"],
            "mermaid_architecture": ["system", "component", "service", "layer", "module", "architecture"],
            "api_docs": ["api", "endpoint", "post", "get", "put", "delete", "rest", "http"],
            "code_prototype": ["implement", "code", "function", "method", "class", "controller", "service"],
            "dev_visual_prototype": ["ui", "ux", "modal", "button", "form", "page", "screen", "interface", "dropdown"],
            "jira": ["story", "task", "sprint", "ticket", "acceptance criteria", "user story"],
            "mermaid_state": ["state", "status", "transition", "pending", "approved", "rejected"],
            "mermaid_user_flow": ["user flow", "user journey", "click", "navigate", "submit"],
        }
        
        for artifact_type, keywords in keyword_mappings.items():
            if artifact_type not in existing_types:
                matches = [kw for kw in keywords if kw in notes_lower]
                if len(matches) >= 2:  # At least 2 keyword matches
                    suggestions.append(ArtifactSuggestion(
                        artifact_type=artifact_type,
                        reason=f"Your meeting notes mention: {', '.join(matches[:3])}",
                        priority=SuggestionPriority.HIGH,
                        context="Detected from meeting notes content",
                        estimated_value="Addresses topics discussed in your meeting",
                        dependencies=[]
                    ))
        
        return suggestions
    
    def _deduplicate_and_sort(
        self,
        suggestions: List[ArtifactSuggestion],
        existing_types: Set[str]
    ) -> List[ArtifactSuggestion]:
        """Remove duplicates and sort by priority."""
        seen_types: Set[str] = set()
        unique_suggestions: List[ArtifactSuggestion] = []
        
        # Priority order
        priority_order = {
            SuggestionPriority.HIGH: 0,
            SuggestionPriority.MEDIUM: 1,
            SuggestionPriority.LOW: 2,
        }
        
        # Sort by priority first
        sorted_suggestions = sorted(
            suggestions,
            key=lambda s: priority_order.get(s.priority, 99)
        )
        
        for suggestion in sorted_suggestions:
            if suggestion.artifact_type not in seen_types and suggestion.artifact_type not in existing_types:
                seen_types.add(suggestion.artifact_type)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions
    
    def _format_type(self, artifact_type: str) -> str:
        """Format artifact type for display."""
        return artifact_type.replace("mermaid_", "").replace("_", " ").title()
    
    def get_generation_roadmap(
        self,
        meeting_notes: str,
        target_artifacts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a full roadmap of artifacts to create.
        
        Returns ordered list of artifacts with dependencies.
        """
        if target_artifacts is None:
            # Default comprehensive roadmap
            target_artifacts = [
                "mermaid_erd",
                "mermaid_architecture", 
                "mermaid_sequence",
                "api_docs",
                "code_prototype",
                "dev_visual_prototype",
                "jira"
            ]
        
        roadmap = []
        completed: Set[str] = set()
        
        # Build dependency-ordered roadmap
        while len(completed) < len(target_artifacts):
            for artifact in target_artifacts:
                if artifact in completed:
                    continue
                
                # Check if dependencies are met
                deps = self._get_dependencies(artifact)
                deps_met = all(d in completed or d not in target_artifacts for d in deps)
                
                if deps_met:
                    roadmap.append({
                        "artifact_type": artifact,
                        "order": len(roadmap) + 1,
                        "dependencies": [d for d in deps if d in target_artifacts],
                        "description": self._get_artifact_description(artifact)
                    })
                    completed.add(artifact)
                    break
            else:
                # No progress - add remaining with warnings
                for artifact in target_artifacts:
                    if artifact not in completed:
                        roadmap.append({
                            "artifact_type": artifact,
                            "order": len(roadmap) + 1,
                            "dependencies": [],
                            "description": self._get_artifact_description(artifact),
                            "warning": "Circular dependency detected"
                        })
                        completed.add(artifact)
        
        return {
            "roadmap": roadmap,
            "total_artifacts": len(roadmap),
            "estimated_time_minutes": len(roadmap) * 2,  # ~2 min per artifact
        }
    
    def _get_dependencies(self, artifact_type: str) -> List[str]:
        """Get recommended dependencies for an artifact type."""
        deps_map = {
            "mermaid_sequence": ["mermaid_erd", "mermaid_architecture"],
            "api_docs": ["mermaid_erd"],
            "code_prototype": ["mermaid_erd", "api_docs"],
            "dev_visual_prototype": ["api_docs"],
            "mermaid_class": ["mermaid_erd"],
            "mermaid_state": ["mermaid_erd"],
            "jira": ["mermaid_architecture"],
        }
        return deps_map.get(artifact_type, [])
    
    def _get_artifact_description(self, artifact_type: str) -> str:
        """Get description for artifact type."""
        descriptions = {
            "mermaid_erd": "Entity-Relationship Diagram showing data models",
            "mermaid_architecture": "High-level system architecture diagram",
            "mermaid_sequence": "Sequence diagram showing interactions",
            "mermaid_class": "Class diagram showing code structure",
            "mermaid_state": "State diagram showing status transitions",
            "mermaid_component": "Component diagram showing modules",
            "mermaid_flowchart": "Flowchart showing process logic",
            "mermaid_user_flow": "User flow diagram showing UX paths",
            "mermaid_data_flow": "Data flow diagram showing information movement",
            "api_docs": "API documentation with endpoints and schemas",
            "code_prototype": "Backend code implementation scaffold",
            "dev_visual_prototype": "Frontend UI prototype",
            "jira": "JIRA stories with acceptance criteria",
            "workflows": "Workflow documentation",
            "estimations": "Time and effort estimations",
            "backlog": "Product backlog items",
            "personas": "User personas",
        }
        return descriptions.get(artifact_type, f"Generate {artifact_type}")


# Singleton instance
_artifact_suggestions_service: Optional[SuggestionEngine] = None


def get_suggestion_engine() -> SuggestionEngine:
    """Get or create artifact suggestions service singleton."""
    global _artifact_suggestions_service
    if _artifact_suggestions_service is None:
        _artifact_suggestions_service = SuggestionEngine()
    return _artifact_suggestions_service
