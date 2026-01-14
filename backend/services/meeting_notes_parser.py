"""
Meeting Notes Analysis Service

Structured extraction and analysis of meeting notes content.
Identifies and extracts:
- Feature specifications
- Database entities and relationships
- API endpoint definitions
- UI component requirements
- Action items with assignees
- Technical requirements and constraints
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """A database entity extracted from notes."""
    name: str
    fields: List[Dict[str, str]]  # {"name": "fieldName", "type": "inferred_type", "constraints": "PK/FK/etc"}
    relationships: List[str]
    confidence: float


@dataclass
class ExtractedEndpoint:
    """An API endpoint extracted from notes."""
    method: str  # GET, POST, PUT, DELETE
    path: str
    description: str
    request_body: Optional[List[str]]
    response: Optional[str]
    confidence: float


@dataclass
class ExtractedUIComponent:
    """A UI component extracted from notes."""
    component_type: str  # modal, form, button, dropdown, etc.
    description: str
    fields: List[str]
    actions: List[str]
    confidence: float


@dataclass
class ExtractedActionItem:
    """An action item extracted from notes."""
    task: str
    assignee: Optional[str]
    deadline: Optional[str]
    priority: str  # high, medium, low


@dataclass
class ParsedMeetingNotes:
    """Fully parsed meeting notes structure."""
    # Metadata
    feature_name: str
    feature_description: str
    meeting_date: Optional[str]
    attendees: List[str]
    
    # Technical extractions
    entities: List[ExtractedEntity]
    endpoints: List[ExtractedEndpoint]
    ui_components: List[ExtractedUIComponent]
    
    # Project management
    action_items: List[ExtractedActionItem]
    user_stories: List[str]
    acceptance_criteria: List[str]
    
    # Additional context
    technologies_mentioned: List[str]
    risks_concerns: List[str]
    decisions_made: List[str]
    
    # Quality
    parsing_confidence: float
    suggestions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        return result


class MeetingNotesParser:
    """
    Intelligent parser for meeting notes.
    
    Extracts structured information to improve artifact generation quality.
    Uses pattern matching and heuristics to identify:
    - Database entities and relationships
    - API endpoints
    - UI components
    - Action items
    - User stories
    """
    
    def __init__(self):
        # Patterns for different extractions
        self.entity_patterns = [
            r'(?:table|entity|model)\s+(?:called|named)?\s*["\']?(\w+)["\']?',
            r'(\w+)\s+(?:table|entity|model)',
            r'store\s+(?:in|into)\s+["\']?(\w+)["\']?',
            r'(\w+)\s+(?:will have|has|contains)\s+(?:columns?|fields?)',
        ]
        
        self.endpoint_patterns = [
            r'(POST|GET|PUT|DELETE|PATCH)\s+(/[\w\-/{}]+)',
            r'(?:endpoint|api|route)\s+(?:for|to)?\s*["\']?(/[\w\-/{}]+)["\']?',
            r'(POST|GET|PUT|DELETE)\s+(?:request|call)\s+(?:to)?\s*["\']?(/[\w\-/]+)["\']?',
        ]
        
        self.ui_patterns = {
            'modal': [r'modal\s+(?:for|with|containing)?', r'popup', r'dialog'],
            'form': [r'form\s+(?:with|containing)?', r'input\s+fields?'],
            'button': [r'button\s+(?:labeled|called|for)?["\']?(\w+)["\']?'],
            'dropdown': [r'dropdown\s+(?:list|menu)?', r'select\s+(?:box|list)?'],
            'table': [r'(?:data\s+)?table\s+(?:showing|displaying)?'],
        }
        
        self.action_patterns = [
            r'(?:action\s+item|task|todo)[:\s]+(.+?)(?:\.|$)',
            r'(\w+\s+team)[:\s]+(.+?)(?:\.|$)',
            r'(\w+)\s+will\s+(.+?)(?:\.|$)',
        ]
    
    def parse(self, meeting_notes: str) -> ParsedMeetingNotes:
        """
        Parse meeting notes and extract structured information.
        
        Args:
            meeting_notes: Raw meeting notes text
            
        Returns:
            ParsedMeetingNotes with extracted information
        """
        logger.info(f"Parsing meeting notes ({len(meeting_notes)} chars)")
        
        # Basic metadata extraction
        feature_name = self._extract_feature_name(meeting_notes)
        feature_description = self._extract_feature_description(meeting_notes)
        meeting_date = self._extract_date(meeting_notes)
        attendees = self._extract_attendees(meeting_notes)
        
        # Technical extractions
        entities = self._extract_entities(meeting_notes)
        endpoints = self._extract_endpoints(meeting_notes)
        ui_components = self._extract_ui_components(meeting_notes)
        
        # PM extractions
        action_items = self._extract_action_items(meeting_notes)
        user_stories = self._extract_user_stories(meeting_notes)
        acceptance_criteria = self._extract_acceptance_criteria(meeting_notes)
        
        # Additional context
        technologies = self._extract_technologies(meeting_notes)
        risks = self._extract_risks(meeting_notes)
        decisions = self._extract_decisions(meeting_notes)
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            entities, endpoints, ui_components, action_items
        )
        
        # Generate suggestions
        suggestions = self._generate_suggestions(
            entities, endpoints, ui_components, meeting_notes
        )
        
        result = ParsedMeetingNotes(
            feature_name=feature_name,
            feature_description=feature_description,
            meeting_date=meeting_date,
            attendees=attendees,
            entities=entities,
            endpoints=endpoints,
            ui_components=ui_components,
            action_items=action_items,
            user_stories=user_stories,
            acceptance_criteria=acceptance_criteria,
            technologies_mentioned=technologies,
            risks_concerns=risks,
            decisions_made=decisions,
            parsing_confidence=confidence,
            suggestions=suggestions
        )
        
        logger.info(f"Parsed: {len(entities)} entities, {len(endpoints)} endpoints, "
                   f"{len(ui_components)} UI components, confidence={confidence:.2f}")
        
        return result
    
    def _extract_feature_name(self, text: str) -> str:
        """Extract the feature name from notes."""
        # Look for explicit feature name
        patterns = [
            r'(?:feature|project|epic)[:\s]+["\']?(.+?)["\']?(?:\n|$)',
            r'^#\s*(.+?)(?:\n|$)',  # Markdown header
            r'(?:implement|build|create)\s+(?:a|the)?\s*(.+?)\s+(?:feature|functionality)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        # Fallback: first line that looks like a title
        lines = text.strip().split('\n')
        for line in lines[:5]:
            line = line.strip()
            if line and len(line) < 100 and not line.startswith(('Date', 'Attendees', '-')):
                return re.sub(r'^[#\-\*\s]+', '', line)
        
        return "Unnamed Feature"
    
    def _extract_feature_description(self, text: str) -> str:
        """Extract feature description."""
        # Look for background/overview section
        patterns = [
            r'(?:background|overview|description|objective)[:\s]+(.+?)(?:\n\n|$)',
            r'(?:the team agreed|we will|this feature)[:\s]+(.+?)(?:\n\n|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                desc = match.group(1).strip()
                return desc[:500] if len(desc) > 500 else desc
        
        # Fallback: first paragraph after title
        paragraphs = text.split('\n\n')
        if len(paragraphs) > 1:
            return paragraphs[1].strip()[:500]
        
        return ""
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract meeting date."""
        patterns = [
            r'(?:date|on)[:\s]+(\w+\s+\d{1,2},?\s+\d{4})',
            r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
            r'(\w+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_attendees(self, text: str) -> List[str]:
        """Extract attendees."""
        pattern = r'(?:attendees|participants|present)[:\s]+(.+?)(?:\n\n|\n[A-Z]|$)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        
        if match:
            attendees_text = match.group(1)
            # Split by comma, newline, or "and"
            attendees = re.split(r'[,\n]|\band\b', attendees_text)
            return [a.strip() for a in attendees if a.strip() and len(a.strip()) < 50]
        
        return []
    
    def _extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract database entities from notes."""
        entities = []
        text_lower = text.lower()
        
        # Find entity names
        entity_names = set()
        for pattern in self.entity_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entity_names.update(m if isinstance(m, str) else m[0] for m in matches)
        
        # Also look for PascalCase words that might be entities
        pascal_words = re.findall(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b', text)
        entity_names.update(pascal_words)
        
        # Filter and analyze each entity
        for name in entity_names:
            if len(name) < 3 or name.lower() in ['the', 'and', 'for', 'with']:
                continue
            
            # Try to find fields for this entity
            fields = self._extract_fields_for_entity(name, text)
            relationships = self._extract_relationships_for_entity(name, text)
            
            confidence = 0.5
            if fields:
                confidence += 0.3
            if relationships:
                confidence += 0.2
            
            entities.append(ExtractedEntity(
                name=name,
                fields=fields,
                relationships=relationships,
                confidence=min(confidence, 1.0)
            ))
        
        return entities
    
    def _extract_fields_for_entity(self, entity_name: str, text: str) -> List[Dict[str, str]]:
        """Extract fields for a specific entity."""
        fields = []
        
        # Look for field definitions near entity name
        patterns = [
            rf'{entity_name}[^.]*(?:has|contains|includes)[^.]*:\s*([^.]+)',
            rf'{entity_name}[^.]*(?:columns?|fields?)[^.]*:\s*([^.]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                field_text = match.group(1)
                # Parse individual fields
                field_items = re.split(r'[,;]|\band\b', field_text)
                for item in field_items:
                    item = item.strip()
                    if item and len(item) < 50:
                        # Try to determine type
                        field_type = self._infer_field_type(item)
                        constraints = self._infer_constraints(item)
                        fields.append({
                            "name": re.sub(r'\s+', '_', item.split()[0] if item.split() else item),
                            "type": field_type,
                            "constraints": constraints
                        })
        
        # Common fields based on entity type
        if not fields:
            fields = [{"name": "id", "type": "int", "constraints": "PK"}]
        
        return fields
    
    def _extract_relationships_for_entity(self, entity_name: str, text: str) -> List[str]:
        """Extract relationships for an entity."""
        relationships = []
        
        patterns = [
            rf'{entity_name}[^.]*(?:belongs to|has many|has one|references)[^.]*(\w+)',
            rf'(\w+)[^.]*(?:belongs to|has many|has one|references)[^.]*{entity_name}',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            relationships.extend(matches)
        
        return list(set(relationships))
    
    def _infer_field_type(self, field_text: str) -> str:
        """Infer data type from field description."""
        field_lower = field_text.lower()
        
        if any(kw in field_lower for kw in ['id', 'count', 'number', 'quantity', 'amount']):
            return 'int'
        if any(kw in field_lower for kw in ['date', 'time', 'created', 'updated', 'at']):
            return 'datetime'
        if any(kw in field_lower for kw in ['price', 'cost', 'total', 'decimal']):
            return 'decimal'
        if any(kw in field_lower for kw in ['is_', 'has_', 'active', 'enabled', 'flag']):
            return 'boolean'
        
        return 'string'
    
    def _infer_constraints(self, field_text: str) -> str:
        """Infer constraints from field description."""
        field_lower = field_text.lower()
        
        if 'primary' in field_lower or field_lower.strip() == 'id':
            return 'PK'
        if 'foreign' in field_lower or field_lower.endswith('_id'):
            return 'FK'
        if 'unique' in field_lower:
            return 'UK'
        if 'required' in field_lower or 'not null' in field_lower:
            return 'NOT NULL'
        
        return ''
    
    def _extract_endpoints(self, text: str) -> List[ExtractedEndpoint]:
        """Extract API endpoints from notes."""
        endpoints = []
        
        for pattern in self.endpoint_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    method, path = match
                else:
                    method = "POST"  # Default
                    path = match
                
                # Find description near the endpoint mention
                desc = self._find_endpoint_description(path, text)
                
                endpoints.append(ExtractedEndpoint(
                    method=method.upper(),
                    path=path,
                    description=desc,
                    request_body=None,
                    response=None,
                    confidence=0.7
                ))
        
        return endpoints
    
    def _find_endpoint_description(self, path: str, text: str) -> str:
        """Find description for an endpoint."""
        pattern = rf'{re.escape(path)}[^.]*(?:will|to|for)[^.]*([^.]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()[:200]
        return f"Handle {path}"
    
    def _extract_ui_components(self, text: str) -> List[ExtractedUIComponent]:
        """Extract UI components from notes."""
        components = []
        
        for comp_type, patterns in self.ui_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    # Find context around the component
                    match = re.search(rf'({pattern})[^.]*\.', text, re.IGNORECASE)
                    desc = match.group(0) if match else f"A {comp_type} component"
                    
                    # Extract fields if it's a form/modal
                    fields = []
                    if comp_type in ['form', 'modal']:
                        fields = self._extract_form_fields(text)
                    
                    components.append(ExtractedUIComponent(
                        component_type=comp_type,
                        description=desc[:200],
                        fields=fields,
                        actions=self._extract_component_actions(desc),
                        confidence=0.6
                    ))
        
        return components
    
    def _extract_form_fields(self, text: str) -> List[str]:
        """Extract form field names."""
        patterns = [
            r'(?:field|input|select|dropdown)[:\s]+["\']?(\w+)["\']?',
            r'["\'](\w+)["\']?\s+(?:field|input)',
        ]
        
        fields = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            fields.extend(matches)
        
        return list(set(fields))
    
    def _extract_component_actions(self, text: str) -> List[str]:
        """Extract actions/buttons for a component."""
        patterns = [
            r'(?:button|action)[:\s]+["\']?(\w+)["\']?',
            r'["\'](\w+)["\']?\s+button',
        ]
        
        actions = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            actions.extend(matches)
        
        return list(set(actions))
    
    def _extract_action_items(self, text: str) -> List[ExtractedActionItem]:
        """Extract action items from notes."""
        items = []
        
        # Look for action items section
        section_match = re.search(r'action\s+items?[:\s]+(.+?)(?:\n\n|\Z)', text, re.IGNORECASE | re.DOTALL)
        if section_match:
            section = section_match.group(1)
            
            # Parse individual items
            item_lines = re.split(r'\n\-|\n\*|\n\d+\.', section)
            for line in item_lines:
                line = line.strip()
                if line:
                    assignee = self._extract_assignee(line)
                    deadline = self._extract_deadline(line)
                    
                    items.append(ExtractedActionItem(
                        task=line[:200],
                        assignee=assignee,
                        deadline=deadline,
                        priority="medium"
                    ))
        
        return items
    
    def _extract_assignee(self, text: str) -> Optional[str]:
        """Extract assignee from action item text."""
        pattern = r'(\w+\s+team|\w+)\s*[:\-]'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def _extract_deadline(self, text: str) -> Optional[str]:
        """Extract deadline from action item text."""
        patterns = [
            r'by\s+(\w+\s+\d{1,2})',
            r'due[:\s]+(\w+\s+\d{1,2})',
            r'EOD[,\s]+(\w+\s+\d{1,2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_user_stories(self, text: str) -> List[str]:
        """Extract user stories from notes."""
        stories = []
        
        # Look for "As a... I want... so that..." pattern
        pattern = r'["\']?as\s+a[n]?\s+(\w+)[,\s]+i\s+want[^"\']+["\']?'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        # Also look for explicit user story mentions
        story_pattern = r'user\s+story[:\s]+["\']?(.+?)["\']?(?:\n|$)'
        story_matches = re.findall(story_pattern, text, re.IGNORECASE)
        
        stories.extend([f"As a {m}" for m in matches])
        stories.extend(story_matches)
        
        return stories
    
    def _extract_acceptance_criteria(self, text: str) -> List[str]:
        """Extract acceptance criteria."""
        criteria = []
        
        # Look for acceptance criteria section
        section_match = re.search(r'acceptance\s+criteria[:\s]+(.+?)(?:\n\n|\Z)', text, re.IGNORECASE | re.DOTALL)
        if section_match:
            section = section_match.group(1)
            items = re.split(r'\n\-|\n\*|\n\d+\.', section)
            criteria.extend([i.strip() for i in items if i.strip()])
        
        return criteria
    
    def _extract_technologies(self, text: str) -> List[str]:
        """Extract mentioned technologies."""
        tech_keywords = [
            'angular', 'react', 'vue', 'typescript', 'javascript',
            '.net', 'c#', 'python', 'java', 'node',
            'sql', 'postgresql', 'mongodb', 'redis',
            'rest', 'graphql', 'grpc', 'websocket',
            'docker', 'kubernetes', 'aws', 'azure',
        ]
        
        found = []
        text_lower = text.lower()
        for tech in tech_keywords:
            if tech in text_lower:
                found.append(tech)
        
        return found
    
    def _extract_risks(self, text: str) -> List[str]:
        """Extract risks and concerns."""
        risks = []
        
        patterns = [
            r'(?:risk|concern|issue|problem)[:\s]+(.+?)(?:\n|$)',
            r'(?:worried about|careful with)[:\s]+(.+?)(?:\n|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            risks.extend(matches)
        
        return risks
    
    def _extract_decisions(self, text: str) -> List[str]:
        """Extract decisions made."""
        decisions = []
        
        patterns = [
            r'(?:decided|agreed|decision)[:\s]+(.+?)(?:\n|$)',
            r'(?:will|we will)[:\s]+(.+?)(?:\n|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            decisions.extend([m for m in matches if len(m) > 10])
        
        return decisions[:10]  # Limit to top 10
    
    def _calculate_confidence(
        self,
        entities: List[ExtractedEntity],
        endpoints: List[ExtractedEndpoint],
        ui_components: List[ExtractedUIComponent],
        action_items: List[ExtractedActionItem]
    ) -> float:
        """Calculate overall parsing confidence."""
        score = 0.3  # Base score
        
        if entities:
            score += 0.2
        if endpoints:
            score += 0.2
        if ui_components:
            score += 0.15
        if action_items:
            score += 0.15
        
        return min(score, 1.0)
    
    def _generate_suggestions(
        self,
        entities: List[ExtractedEntity],
        endpoints: List[ExtractedEndpoint],
        ui_components: List[ExtractedUIComponent],
        text: str
    ) -> List[str]:
        """Generate suggestions based on parsing results."""
        suggestions = []
        
        if not entities:
            suggestions.append("Consider defining database entities/tables explicitly")
        
        if not endpoints:
            suggestions.append("Consider specifying API endpoints (e.g., 'POST /api/feature')")
        
        if not ui_components:
            suggestions.append("Consider describing UI components (modal, form, etc.)")
        
        if len(text) < 200:
            suggestions.append("More detailed notes would improve artifact generation quality")
        
        return suggestions


# Singleton instance
_meeting_notes_parser: Optional[MeetingNotesParser] = None


def get_meeting_notes_parser() -> MeetingNotesParser:
    """Get or create meeting notes parser singleton."""
    global _meeting_notes_parser
    if _meeting_notes_parser is None:
        _meeting_notes_parser = MeetingNotesParser()
    return _meeting_notes_parser
