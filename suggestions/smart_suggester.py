"""
Smart Suggestion System

Analyzes meeting notes and project context to intelligently suggest
which artifacts to generate. Provides context-aware recommendations
and quick-generate shortcuts.

Features:
- Keyword-based analysis
- Pattern matching for common scenarios
- Priority scoring for suggestions
- Quick-generate shortcuts
- Customizable suggestion rules
"""

from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class Suggestion:
    """
    Represents a single artifact generation suggestion.
    
    Attributes:
        artifact_type: Type of artifact to generate (erd, jira, etc.)
        priority: Priority score (0-100, higher = more important)
        reason: Why this artifact is suggested
        keywords_matched: Keywords that triggered this suggestion
        quick_generate: Whether to enable quick-generate button
        dependencies: Other artifacts that should be generated first
    """
    artifact_type: str
    priority: float
    reason: str
    keywords_matched: List[str]
    quick_generate: bool = True
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class SmartSuggester:
    """
    Analyzes meeting notes and suggests relevant artifacts to generate.
    
    Uses keyword matching, pattern detection, and heuristics to provide
    intelligent recommendations.
    """
    
    def __init__(self):
        """Initialize suggester with keyword patterns"""
        
        # Keyword patterns for each artifact type
        self.patterns = {
            'erd': {
                'keywords': [
                    'database', 'table', 'schema', 'entity', 'relationship',
                    'foreign key', 'primary key', 'model', 'data model',
                    'store', 'persist', 'record', 'column', 'field'
                ],
                'phrases': [
                    r'need to store',
                    r'save.*data',
                    r'database.*design',
                    r'data.*model',
                    r'table.*structure'
                ],
                'priority_base': 80
            },
            
            'architecture': {
                'keywords': [
                    'architecture', 'system', 'component', 'service',
                    'microservice', 'layer', 'tier', 'infrastructure',
                    'scalability', 'design', 'structure', 'flow'
                ],
                'phrases': [
                    r'system.*design',
                    r'how.*work',
                    r'architecture.*diagram',
                    r'component.*interaction',
                    r'high.*level'
                ],
                'priority_base': 90
            },
            
            'api_docs': {
                'keywords': [
                    'api', 'endpoint', 'rest', 'graphql', 'http',
                    'request', 'response', 'route', 'controller',
                    'integration', 'webhook', 'authentication'
                ],
                'phrases': [
                    r'api.*endpoint',
                    r'rest.*api',
                    r'http.*method',
                    r'authentication.*api',
                    r'external.*integration'
                ],
                'priority_base': 85
            },
            
            'jira': {
                'keywords': [
                    'task', 'story', 'epic', 'sprint', 'backlog',
                    'implementation', 'todo', 'deliverable', 'milestone',
                    'acceptance criteria', 'user story'
                ],
                'phrases': [
                    r'need to implement',
                    r'user story',
                    r'acceptance criteria',
                    r'tasks.*required',
                    r'sprint.*planning'
                ],
                'priority_base': 95
            },
            
            'workflows': {
                'keywords': [
                    'deployment', 'ci/cd', 'pipeline', 'docker',
                    'kubernetes', 'build', 'test', 'deploy',
                    'workflow', 'automation', 'devops'
                ],
                'phrases': [
                    r'deploy.*process',
                    r'ci.*cd',
                    r'build.*pipeline',
                    r'deployment.*strategy',
                    r'automated.*workflow'
                ],
                'priority_base': 70
            },
            
            'code_prototype': {
                'keywords': [
                    'implement', 'code', 'develop', 'build', 'create',
                    'function', 'class', 'method', 'algorithm',
                    'prototype', 'proof of concept', 'poc'
                ],
                'phrases': [
                    r'need to code',
                    r'implement.*feature',
                    r'build.*prototype',
                    r'proof of concept',
                    r'working.*example'
                ],
                'priority_base': 85
            },
            
            'visual_prototype_dev': {
                'keywords': [
                    'ui', 'ux', 'interface', 'design', 'mockup',
                    'wireframe', 'screen', 'page', 'view', 'form',
                    'dashboard', 'visual', 'layout'
                ],
                'phrases': [
                    r'user.*interface',
                    r'ui.*design',
                    r'visual.*mockup',
                    r'screen.*layout',
                    r'dashboard.*view'
                ],
                'priority_base': 80
            },
            
            'all_diagrams': {
                'keywords': [
                    'diagram', 'visualization', 'flowchart', 'sequence',
                    'visual', 'chart', 'graph', 'overview'
                ],
                'phrases': [
                    r'need.*diagram',
                    r'visual.*overview',
                    r'flowchart.*showing',
                    r'sequence.*diagram',
                    r'diagram.*flow'
                ],
                'priority_base': 75
            }
        }
        
        # Dependency chains (artifact A suggests artifact B)
        self.dependencies = {
            'code_prototype': ['architecture', 'api_docs'],
            'visual_prototype_dev': ['architecture'],
            'workflows': ['code_prototype'],
            'api_docs': ['architecture']
        }
        
        # Artifact display names
        self.display_names = {
            'erd': 'ERD Diagram',
            'architecture': 'System Architecture',
            'api_docs': 'API Documentation',
            'jira': 'JIRA Tasks',
            'workflows': 'Deployment Workflows',
            'code_prototype': 'Code Prototype',
            'visual_prototype_dev': 'Visual Prototype',
            'all_diagrams': 'All Diagrams'
        }
    
    # =========================================================================
    # Core Suggestion Logic
    # =========================================================================
    
    def analyze_and_suggest(
        self,
        meeting_notes: str,
        existing_artifacts: List[str] = None
    ) -> List[Suggestion]:
        """
        Analyze meeting notes and generate suggestions.
        
        Args:
            meeting_notes: Raw meeting notes text
            existing_artifacts: List of already generated artifacts (to avoid duplicates)
        
        Returns:
            List of Suggestion objects, sorted by priority (high to low)
        """
        if existing_artifacts is None:
            existing_artifacts = []
        
        notes_lower = meeting_notes.lower()
        suggestions = []
        
        # Analyze each artifact type
        for artifact_type, patterns in self.patterns.items():
            # Skip if already generated
            if artifact_type in existing_artifacts:
                continue
            
            # Calculate match score
            matched_keywords = []
            keyword_matches = 0
            phrase_matches = 0
            
            # Check keywords
            for keyword in patterns['keywords']:
                if keyword in notes_lower:
                    matched_keywords.append(keyword)
                    keyword_matches += 1
            
            # Check phrases (regex patterns)
            for phrase_pattern in patterns['phrases']:
                if re.search(phrase_pattern, notes_lower, re.IGNORECASE):
                    phrase_matches += 1
            
            # Calculate priority
            if keyword_matches > 0 or phrase_matches > 0:
                priority = self._calculate_priority(
                    patterns['priority_base'],
                    keyword_matches,
                    phrase_matches,
                    len(meeting_notes)
                )
                
                reason = self._generate_reason(
                    artifact_type,
                    keyword_matches,
                    phrase_matches,
                    matched_keywords
                )
                
                # Check dependencies
                deps = self.dependencies.get(artifact_type, [])
                missing_deps = [d for d in deps if d not in existing_artifacts]
                
                suggestion = Suggestion(
                    artifact_type=artifact_type,
                    priority=priority,
                    reason=reason,
                    keywords_matched=matched_keywords,
                    quick_generate=True,
                    dependencies=missing_deps
                )
                
                suggestions.append(suggestion)
        
        # Sort by priority (descending)
        suggestions.sort(key=lambda s: s.priority, reverse=True)
        
        return suggestions
    
    def get_quick_suggestions(
        self,
        meeting_notes: str,
        max_suggestions: int = 3
    ) -> List[Suggestion]:
        """
        Get top N quick suggestions for fast generation.
        
        Args:
            meeting_notes: Meeting notes text
            max_suggestions: Maximum number of suggestions to return
        
        Returns:
            Top N suggestions sorted by priority
        """
        all_suggestions = self.analyze_and_suggest(meeting_notes)
        return all_suggestions[:max_suggestions]
    
    def suggest_next(
        self,
        meeting_notes: str,
        generated_artifacts: List[str]
    ) -> Optional[Suggestion]:
        """
        Suggest the next artifact to generate based on what's already done.
        
        This uses dependency chains and context to recommend the most
        logical next step.
        
        Args:
            meeting_notes: Meeting notes text
            generated_artifacts: List of already generated artifacts
        
        Returns:
            Next suggested artifact or None
        """
        suggestions = self.analyze_and_suggest(meeting_notes, generated_artifacts)
        
        # Filter for suggestions with no missing dependencies
        ready_suggestions = [
            s for s in suggestions
            if len(s.dependencies) == 0
        ]
        
        if ready_suggestions:
            return ready_suggestions[0]  # Highest priority
        
        # If all have dependencies, return highest priority anyway
        if suggestions:
            return suggestions[0]
        
        return None
    
    # =========================================================================
    # Scoring & Reasoning
    # =========================================================================
    
    def _calculate_priority(
        self,
        base_priority: float,
        keyword_matches: int,
        phrase_matches: int,
        notes_length: int
    ) -> float:
        """
        Calculate priority score based on matches and context.
        
        Formula:
        - Base priority (artifact type importance)
        - +5 points per keyword match (max +20)
        - +10 points per phrase match (max +30)
        - Boost if multiple matches in short notes (high density)
        
        Returns:
            Priority score (0-100)
        """
        priority = base_priority
        
        # Keyword boost (max +20)
        priority += min(keyword_matches * 5, 20)
        
        # Phrase boost (max +30)
        priority += min(phrase_matches * 10, 30)
        
        # Density boost (more matches in shorter notes = higher confidence)
        if notes_length > 0:
            match_density = (keyword_matches + phrase_matches * 2) / (notes_length / 100)
            if match_density > 0.5:
                priority += 10
        
        # Cap at 100
        return min(priority, 100)
    
    def _generate_reason(
        self,
        artifact_type: str,
        keyword_matches: int,
        phrase_matches: int,
        matched_keywords: List[str]
    ) -> str:
        """Generate human-readable reason for suggestion"""
        
        display_name = self.display_names.get(artifact_type, artifact_type)
        
        if phrase_matches > 0 and keyword_matches > 0:
            keywords_str = ', '.join(matched_keywords[:3])
            return f"Found {phrase_matches} relevant phrase(s) and keywords: {keywords_str}"
        
        elif phrase_matches > 0:
            return f"Found {phrase_matches} relevant phrase(s) indicating need for {display_name}"
        
        elif keyword_matches > 0:
            keywords_str = ', '.join(matched_keywords[:3])
            return f"Found {keyword_matches} relevant keyword(s): {keywords_str}"
        
        else:
            return f"Suggested based on project context"
    
    # =========================================================================
    # Pattern Detection
    # =========================================================================
    
    def detect_scenarios(self, meeting_notes: str) -> Dict[str, bool]:
        """
        Detect common development scenarios in meeting notes.
        
        Returns dict with scenario flags:
        - new_feature: Building a new feature
        - refactoring: Refactoring existing code
        - bug_fix: Fixing bugs
        - api_integration: Integrating with external API
        - database_migration: Database changes
        - ui_redesign: UI/UX changes
        """
        notes_lower = meeting_notes.lower()
        
        scenarios = {
            'new_feature': any(phrase in notes_lower for phrase in [
                'new feature', 'build', 'implement', 'create', 'add functionality'
            ]),
            'refactoring': any(phrase in notes_lower for phrase in [
                'refactor', 'restructure', 'cleanup', 'improve', 'optimize'
            ]),
            'bug_fix': any(phrase in notes_lower for phrase in [
                'bug', 'fix', 'issue', 'error', 'problem', 'broken'
            ]),
            'api_integration': any(phrase in notes_lower for phrase in [
                'api', 'integration', 'external service', 'webhook', 'third party'
            ]),
            'database_migration': any(phrase in notes_lower for phrase in [
                'database', 'migration', 'schema change', 'add table', 'modify column'
            ]),
            'ui_redesign': any(phrase in notes_lower for phrase in [
                'ui', 'redesign', 'mockup', 'wireframe', 'user interface', 'screen'
            ])
        }
        
        return scenarios
    
    def get_scenario_recommendations(
        self,
        meeting_notes: str
    ) -> Dict[str, List[str]]:
        """
        Get artifact recommendations based on detected scenarios.
        
        Returns dict mapping scenarios to recommended artifacts.
        """
        scenarios = self.detect_scenarios(meeting_notes)
        
        recommendations = {
            'new_feature': ['jira', 'architecture', 'api_docs', 'code_prototype', 'visual_prototype_dev'],
            'refactoring': ['architecture', 'code_prototype', 'jira'],
            'bug_fix': ['jira', 'code_prototype'],
            'api_integration': ['api_docs', 'architecture', 'code_prototype'],
            'database_migration': ['erd', 'architecture', 'jira'],
            'ui_redesign': ['visual_prototype_dev', 'jira', 'architecture']
        }
        
        result = {}
        for scenario, is_detected in scenarios.items():
            if is_detected:
                result[scenario] = recommendations.get(scenario, [])
        
        return result
    
    # =========================================================================
    # Statistics & Insights
    # =========================================================================
    
    def get_suggestion_stats(
        self,
        suggestions: List[Suggestion]
    ) -> Dict:
        """
        Get statistics about suggestions.
        
        Returns:
            Dict with stats: total, high_priority, medium_priority, low_priority, etc.
        """
        if not suggestions:
            return {
                'total': 0,
                'high_priority': 0,
                'medium_priority': 0,
                'low_priority': 0,
                'with_dependencies': 0
            }
        
        high_priority = sum(1 for s in suggestions if s.priority >= 80)
        medium_priority = sum(1 for s in suggestions if 60 <= s.priority < 80)
        low_priority = sum(1 for s in suggestions if s.priority < 60)
        with_deps = sum(1 for s in suggestions if s.dependencies)
        
        return {
            'total': len(suggestions),
            'high_priority': high_priority,
            'medium_priority': medium_priority,
            'low_priority': low_priority,
            'with_dependencies': with_deps,
            'avg_priority': sum(s.priority for s in suggestions) / len(suggestions)
        }

