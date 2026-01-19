"""
Validation API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import List, Dict, Any
import logging
import re

from backend.models.dto import (
    ValidationResultDTO, ArtifactType
)
from backend.services.validation_service import get_service
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/validation", tags=["validation"])


@router.post("/validate", response_model=ValidationResultDTO)
@limiter.limit("30/minute")
async def validate_artifact(
    request: Request,
    body: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Validate an artifact.
    
    Request body:
    {
        "artifact_type": "mermaid_erd",
        "content": "erDiagram\n...",
        "meeting_notes": "Optional meeting notes for context"
    }
    """
    artifact_type_str = body.get("artifact_type")
    content = body.get("content", "")
    meeting_notes = body.get("meeting_notes")
    
    if not artifact_type_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="artifact_type is required"
        )
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="content is required"
        )
    
    try:
        artifact_type = ArtifactType(artifact_type_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid artifact_type: {artifact_type_str}"
        )
    
    service = get_service()
    result = await service.validate_artifact(
        artifact_type=artifact_type,
        content=content,
        meeting_notes=meeting_notes
    )
    
    return result


@router.post("/validate-batch", response_model=List[ValidationResultDTO])
@limiter.limit("10/minute")
async def validate_batch(
    request: Request,
    body: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Validate multiple artifacts in batch.
    
    Request body:
    {
        "artifacts": [
            {
                "type": "mermaid_erd",
                "content": "...",
                "meeting_notes": "..."
            },
            ...
        ]
    }
    """
    artifacts = body.get("artifacts", [])
    
    if not artifacts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="artifacts list is required"
        )
    
    if len(artifacts) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 artifacts per batch"
        )
    
    service = get_service()
    results = service.validate_batch(artifacts)
    
    return results


@router.get("/stats", response_model=Dict[str, Any])
async def get_validation_stats(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get validation service statistics."""
    # Placeholder for validation stats
    return {
        "total_validations": 0,
        "average_score": 0.0,
        "validation_rate": 0.0
    }


@router.post("/mermaid", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def validate_mermaid(
    request: Request,
    body: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Comprehensive Mermaid diagram validation with detailed error reporting.
    
    Request body:
    {
        "content": "erDiagram\n...",
        "diagram_type": "mermaid_erd"  // optional, will auto-detect if not provided
    }
    
    Response:
    {
        "is_valid": true,
        "score": 85.0,
        "errors": ["error1", ...],
        "warnings": ["warning1", ...],
        "suggestions": ["suggestion1", ...],
        "detected_type": "erDiagram",
        "stats": {
            "entities_count": 5,
            "relationships_count": 3,
            ...
        }
    }
    """
    content = body.get("content", "")
    diagram_type = body.get("diagram_type")
    
    if not content or len(content.strip()) < 5:
        return {
            "is_valid": False,
            "score": 0.0,
            "errors": ["Content is empty or too short"],
            "warnings": [],
            "suggestions": ["Provide a valid Mermaid diagram"],
            "detected_type": None,
            "stats": {}
        }
    
    errors = []
    warnings = []
    suggestions = []
    stats = {}
    score = 100.0
    
    # Remove markdown code blocks if present
    clean_content = content.strip()
    if clean_content.startswith("```"):
        lines = clean_content.split('\n')
        clean_lines = []
        in_code = False
        for line in lines:
            if line.startswith("```") and not in_code:
                in_code = True
                continue
            elif line.startswith("```") and in_code:
                break
            elif in_code:
                clean_lines.append(line)
        if clean_lines:
            clean_content = '\n'.join(clean_lines)
    
    # Detect diagram type
    diagram_types = {
        'erDiagram': 'ERD',
        'flowchart': 'Flowchart',
        'graph': 'Graph',
        'sequenceDiagram': 'Sequence',
        'classDiagram': 'Class',
        'stateDiagram': 'State',
        'gantt': 'Gantt',
        'pie': 'Pie',
        'journey': 'Journey',
        'gitgraph': 'Git Graph',
        'mindmap': 'Mind Map',
        'timeline': 'Timeline'
    }
    
    detected_type = None
    for dt_key, dt_name in diagram_types.items():
        if dt_key.lower() in clean_content.lower():
            detected_type = dt_key
            break
    
    if not detected_type:
        errors.append("Missing Mermaid diagram type declaration (erDiagram, flowchart, etc.)")
        suggestions.append("Start your diagram with a type declaration like 'erDiagram' or 'flowchart TD'")
        score -= 30.0
    
    # Check for balanced brackets
    open_curly = clean_content.count('{')
    close_curly = clean_content.count('}')
    if open_curly != close_curly:
        errors.append(f"Unbalanced curly braces: {open_curly} opening, {close_curly} closing")
        score -= 20.0
    
    open_square = clean_content.count('[')
    close_square = clean_content.count(']')
    if open_square != close_square:
        errors.append(f"Unbalanced square brackets: {open_square} opening, {close_square} closing")
        score -= 20.0
    
    open_paren = clean_content.count('(')
    close_paren = clean_content.count(')')
    if open_paren != close_paren:
        warnings.append(f"Possibly unbalanced parentheses: {open_paren} opening, {close_paren} closing")
        score -= 5.0
    
    # ERD-specific validation
    if detected_type == 'erDiagram':
        # Check for class diagram syntax in ERD
        if 'class ' in clean_content or 'CLASS ' in clean_content:
            warnings.append("ERD diagram contains class diagram syntax - may cause rendering issues")
            suggestions.append("Use proper ERD entity syntax: ENTITY_NAME { type attribute_name PK/FK }")
            score -= 10.0
        
        # Count entities (lines with { that aren't relationships)
        entities = re.findall(r'^(\w+)\s*\{', clean_content, re.MULTILINE)
        stats["entities_count"] = len(entities)
        
        # Count relationships
        relationships = re.findall(r'\|\|--|--\|\||--o\{|--\|\{|\}o--|--o--|o--o', clean_content)
        stats["relationships_count"] = len(relationships)
        
        if len(entities) == 0:
            warnings.append("No entities found in ERD diagram")
            suggestions.append("Define at least one entity: ENTITY_NAME { int id PK }")
            score -= 15.0
        
        # Check for empty entities
        empty_entities = re.findall(r'(\w+)\s*\{\s*\}', clean_content)
        if empty_entities:
            warnings.append(f"Empty entity definitions found: {', '.join(empty_entities)}")
            suggestions.append("Add attributes to your entities")
            score -= 5.0
    
    # Flowchart-specific validation
    elif detected_type in ['flowchart', 'graph']:
        # Check for direction
        if detected_type == 'flowchart' and not any(d in clean_content.upper() for d in ['TD', 'TB', 'BT', 'LR', 'RL']):
            warnings.append("Flowchart missing direction declaration")
            suggestions.append("Add a direction after 'flowchart', e.g., 'flowchart TD' (top-down)")
            score -= 5.0
        
        # Count nodes (simple heuristic)
        nodes = re.findall(r'(\w+)\[', clean_content)
        stats["nodes_count"] = len(nodes)
        
        # Count connections
        arrows = clean_content.count('-->') + clean_content.count('---') + clean_content.count('==>') + clean_content.count('-.->') 
        stats["connections_count"] = arrows
    
    # Sequence diagram validation
    elif detected_type == 'sequenceDiagram':
        participants = re.findall(r'participant\s+(\w+)', clean_content, re.IGNORECASE)
        stats["participants_count"] = len(participants)
        
        messages = clean_content.count('->>') + clean_content.count('-->>') + clean_content.count('->')
        stats["messages_count"] = messages
        
        if len(participants) == 0:
            warnings.append("No participants declared in sequence diagram")
            suggestions.append("Declare participants: participant UserA")
            score -= 10.0
    
    # Check for common syntax issues
    lines = clean_content.split('\n')
    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()
        if line_stripped and not line_stripped.startswith('%%'):
            # Check for unmatched quotes
            quote_count = line_stripped.count('"') + line_stripped.count("'")
            if quote_count % 2 != 0:
                errors.append(f"Line {i}: Unmatched quotes")
                score -= 10.0
    
    # Calculate final score
    score = max(0.0, min(100.0, score))
    is_valid = len(errors) == 0 and score >= 60.0
    
    # Add general suggestions if score is low
    if score < 80.0 and len(suggestions) == 0:
        suggestions.append("Consider using the AI Repair feature to fix syntax issues")
    
    return {
        "is_valid": is_valid,
        "score": score,
        "errors": errors,
        "warnings": warnings,
        "suggestions": suggestions,
        "detected_type": detected_type,
        "stats": stats
    }



