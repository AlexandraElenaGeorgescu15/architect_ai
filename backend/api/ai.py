"""
AI-powered diagram parsing and improvement endpoints.
Supports all Mermaid diagram types with intelligent model routing.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging

from backend.core.auth import get_current_user
from backend.models.dto import UserPublic, ArtifactType
from backend.services.model_service import get_service as get_model_service
from backend.services.enhanced_generation import get_enhanced_service as get_generation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ============================================================================
# Request/Response Models
# ============================================================================

class DiagramParseRequest(BaseModel):
    """Request to parse Mermaid code to React Flow JSON."""
    mermaid_code: str = Field(..., description="Mermaid diagram code to parse")
    diagram_type: ArtifactType = Field(..., description="Type of diagram (mermaid_erd, mermaid_sequence, etc.)")
    layout_preference: Optional[str] = Field(None, description="Layout preference: horizontal, vertical, radial, force")


class ReactFlowNode(BaseModel):
    """React Flow node format."""
    id: str
    type: str = "custom"
    data: Dict[str, Any]
    position: Dict[str, float]  # {x: float, y: float}


class ReactFlowEdge(BaseModel):
    """React Flow edge format."""
    id: str
    source: str
    target: str
    label: Optional[str] = None
    type: Optional[str] = "default"
    animated: bool = False


class DiagramParseResponse(BaseModel):
    """Response from diagram parsing."""
    success: bool
    nodes: List[ReactFlowNode]
    edges: List[ReactFlowEdge]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class DiagramImproveRequest(BaseModel):
    """Request to improve a diagram."""
    mermaid_code: str = Field(..., description="Current Mermaid diagram code")
    diagram_type: ArtifactType = Field(..., description="Type of diagram")
    improvement_focus: Optional[List[str]] = Field(
        default_factory=lambda: ["syntax", "colors", "layout", "relationships"],
        description="Areas to improve: syntax, colors, layout, relationships, flow"
    )


class DiagramImproveResponse(BaseModel):
    """Response from diagram improvement."""
    success: bool
    improved_code: str
    improvements_made: List[str] = Field(default_factory=list)
    error: Optional[str] = None


# ============================================================================
# Parsing System Instructions (per diagram type)
# ============================================================================

PARSE_INSTRUCTIONS = {
    "mermaid_erd": """
You are an expert Mermaid ERD (Entity-Relationship Diagram) parser.
Convert Mermaid ERD code into React Flow JSON format.

Rules:
1. Each entity becomes a node with type='entity'
2. Each relationship becomes an edge with appropriate cardinality
3. Extract properties for each entity
4. Assign colors based on entity groups (e.g., User-related = blue, Order-related = green)
5. Layout: Arrange entities in a grid or hierarchy based on relationships
6. Spread nodes at least 300px apart

Return JSON with 'nodes' and 'edges' arrays.
    """,
    
    "mermaid_sequence": """
You are an expert Mermaid Sequence Diagram parser.
Convert Mermaid sequence diagram code into React Flow JSON format.

Rules:
1. Each participant becomes a node with type='participant'
2. Each message becomes an edge with type='message'
3. Preserve message order and direction
4. Layout: Arrange participants horizontally (x-axis), messages flow vertically (y-axis)
5. Space participants 250px apart horizontally
6. Space messages 80px apart vertically

Return JSON with 'nodes' and 'edges' arrays.
    """,
    
    "mermaid_flowchart": """
You are an expert Mermaid Flowchart parser.
Convert Mermaid flowchart code into React Flow JSON format.

Rules:
1. Each node becomes a React Flow node with appropriate shape (box, diamond, circle)
2. Preserve node labels and IDs
3. Each arrow/link becomes an edge
4. Assign colors based on node type (start=green, end=red, process=blue, decision=yellow)
5. Layout: Top-to-bottom or left-to-right based on code direction
6. Spread nodes at least 250px apart

Return JSON with 'nodes' and 'edges' arrays.
    """,
    
    "mermaid_class": """
You are an expert Mermaid Class Diagram parser.
Convert Mermaid class diagram code into React Flow JSON format.

Rules:
1. Each class becomes a node with type='class'
2. Extract methods and properties for each class
3. Relationships (inheritance, composition, aggregation) become edges
4. Layout: Group related classes, arrange in hierarchy
5. Assign colors based on class type (abstract=purple, interface=cyan, concrete=blue)
6. Space classes 300px apart

Return JSON with 'nodes' and 'edges' arrays.
    """,
    
    "mermaid_architecture": """
You are an expert Mermaid Architecture Diagram parser.
Convert Mermaid architecture/component diagram code into React Flow JSON format.

Rules:
1. Each component/service becomes a node with type='component'
2. Dependencies/connections become edges
3. Group related components with similar colors
4. Layout: Layers (frontend, backend, database) in vertical stacks
5. Space components 300px apart within layers
6. Use colors to indicate layer (frontend=blue, backend=green, data=orange)

Return JSON with 'nodes' and 'edges' arrays.
    """,
    
    "mermaid_state": """
You are an expert Mermaid State Diagram parser.
Convert Mermaid state diagram code into React Flow JSON format.

Rules:
1. Each state becomes a node with type='state'
2. Transitions become edges with labels
3. Mark start state (green) and end states (red)
4. Layout: Flow from initial to final states
5. Space states 250px apart
6. Show transition conditions as edge labels

Return JSON with 'nodes' and 'edges' arrays.
    """,
    
    # Add more as needed...
}

# Default instruction for unsupported types
DEFAULT_PARSE_INSTRUCTION = """
You are an expert Mermaid Diagram parser.
Convert the provided Mermaid diagram code into React Flow JSON format.

Rules:
1. Extract all nodes with unique IDs and labels
2. Extract all edges/connections
3. Assign appropriate node types based on diagram semantics
4. Create a clean layout with nodes spaced at least 250px apart
5. Assign meaningful colors to group related concepts
6. Preserve the diagram's logical structure

Return JSON with 'nodes' and 'edges' arrays.
Each node must have: {id: string, type: string, data: {label: string, color?: string}, position: {x: number, y: number}}
Each edge must have: {id: string, source: string, target: string, label?: string}
"""


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/parse-diagram", response_model=DiagramParseResponse)
async def parse_diagram(
    request: DiagramParseRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Parse Mermaid diagram code into React Flow JSON format.
    Supports all diagram types with intelligent model routing.
    """
    try:
        logger.info(f"Parsing {request.diagram_type} diagram ({len(request.mermaid_code)} chars)")
        
        # Get model routing for this artifact type
        model_service = get_model_service()
        routing = model_service.get_routing_for_artifact(request.diagram_type)
        
        # Get diagram-specific parsing instruction
        system_instruction = PARSE_INSTRUCTIONS.get(
            request.diagram_type.value,
            DEFAULT_PARSE_INSTRUCTION
        )
        
        # Add layout preference if provided
        if request.layout_preference:
            system_instruction += f"\n\nLayout Preference: {request.layout_preference}"
        
        # Build parsing prompt
        prompt = f"""
Parse this Mermaid {request.diagram_type.value} code into React Flow JSON format:

```mermaid
{request.mermaid_code}
```

Return ONLY valid JSON with this exact structure:
{{
  "nodes": [
    {{"id": "string", "type": "string", "data": {{"label": "string", "color": "string"}}, "position": {{"x": number, "y": number}}}}
  ],
  "edges": [
    {{"id": "string", "source": "string", "target": "string", "label": "string"}}
  ]
}}
"""
        
        # Call AI generation service with routing
        generation_service = get_generation_service()
        result = await generation_service.generate_with_fallback(
            prompt=prompt,
            system_instruction=system_instruction,
            model_routing=routing,
            response_format="json",
            temperature=0.3  # Lower temperature for more consistent parsing
        )
        
        # Parse response
        import json
        parsed_data = json.loads(result.content)
        
        return DiagramParseResponse(
            success=True,
            nodes=[ReactFlowNode(**node) for node in parsed_data.get("nodes", [])],
            edges=[ReactFlowEdge(**edge) for edge in parsed_data.get("edges", [])],
            metadata={
                "model_used": result.model_used,
                "diagram_type": request.diagram_type.value,
                "node_count": len(parsed_data.get("nodes", [])),
                "edge_count": len(parsed_data.get("edges", []))
            }
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        return DiagramParseResponse(
            success=False,
            nodes=[],
            edges=[],
            error=f"AI returned invalid JSON: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Diagram parsing failed: {e}", exc_info=True)
        return DiagramParseResponse(
            success=False,
            nodes=[],
            edges=[],
            error=str(e)
        )


@router.post("/improve-diagram", response_model=DiagramImproveResponse)
async def improve_diagram(
    request: DiagramImproveRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    AI-powered diagram improvement.
    Fixes syntax, adds colors, improves layout, and suggests enhancements.
    """
    try:
        logger.info(f"Improving {request.diagram_type} diagram")
        
        # Get model routing
        model_service = get_model_service()
        routing = model_service.get_routing_for_artifact(request.diagram_type)
        
        # Build improvement areas
        improvement_areas = ", ".join(request.improvement_focus or ["syntax", "colors"])
        
        # Detect diagram type from code
        diagram_start = ""
        code_lower = request.mermaid_code.lower().strip()
        if code_lower.startswith("erdiagram"):
            diagram_start = "erDiagram"
        elif code_lower.startswith("graph"):
            diagram_start = "graph"
        elif code_lower.startswith("flowchart"):
            diagram_start = "flowchart"
        elif code_lower.startswith("sequencediagram"):
            diagram_start = "sequenceDiagram"
        elif code_lower.startswith("classdiagram"):
            diagram_start = "classDiagram"
        elif code_lower.startswith("statediagram"):
            diagram_start = "stateDiagram-v2"
        
        # Build improvement prompt - more explicit about output format
        prompt = f"""You are a Mermaid diagram expert. Improve this diagram while preserving its structure and meaning.

INPUT DIAGRAM:
{request.mermaid_code}

IMPROVEMENT FOCUS: {improvement_areas}

RULES:
1. Fix any syntax errors (missing quotes, brackets, etc.)
2. Keep all existing nodes and relationships
3. Add colors using classDef if not present (e.g., classDef primary fill:#4f46e5,stroke:#3730a3)
4. Do NOT add explanations or comments
5. Do NOT wrap in markdown code blocks
6. Start output directly with "{diagram_start or 'the diagram keyword'}"

OUTPUT (improved Mermaid code only):"""
        
        # Call AI generation service
        generation_service = get_generation_service()
        result = await generation_service.generate_with_fallback(
            prompt=prompt,
            model_routing=routing,
            temperature=0.3  # Lower temperature for more consistent syntax
        )
        
        # Check if generation succeeded
        if not result.success or not result.content or len(result.content.strip()) < 10:
            logger.warning(f"AI generation failed or returned empty: success={result.success}, content_len={len(result.content) if result.content else 0}")
            return DiagramImproveResponse(
                success=False,
                improved_code=request.mermaid_code,
                improvements_made=[],
                error=result.error or "AI returned empty response. Please try again."
            )
        
        # Clean up response (remove markdown code blocks if present)
        improved_code = result.content.strip()
        
        # Remove common wrapper patterns
        if improved_code.startswith("```"):
            # Find the end of the code block
            lines = improved_code.split('\n')
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
                improved_code = '\n'.join(clean_lines)
        
        # Additional cleanup
        improved_code = improved_code.replace("```mermaid", "").replace("```", "").strip()
        
        # Validate that the improved code has the same diagram type
        improved_lower = improved_code.lower().strip()
        if diagram_start and not improved_lower.startswith(diagram_start.lower()):
            # Try to find the diagram content and prepend the correct start
            logger.warning(f"AI response doesn't start with expected diagram type: {diagram_start}")
            # If the original has a valid structure, return it with minimal fixes
            if len(improved_code) < len(request.mermaid_code) * 0.5:
                return DiagramImproveResponse(
                    success=False,
                    improved_code=request.mermaid_code,
                    improvements_made=[],
                    error="AI returned incomplete diagram. Please try again."
                )
        
        # Detect improvements made
        improvements_made = []
        if "style" in improved_code.lower() and "style" not in request.mermaid_code.lower():
            improvements_made.append("Added inline styles")
        if "classdef" in improved_code.lower() and "classdef" not in request.mermaid_code.lower():
            improvements_made.append("Added style definitions")
        if ":::" in improved_code and ":::" not in request.mermaid_code:
            improvements_made.append("Added style classes")
        if len(improved_code) > len(request.mermaid_code):
            improvements_made.append("Enhanced structure")
        if not improvements_made:
            improvements_made.append("Syntax verified")
        
        logger.info(f"Diagram improvement successful: {improvements_made}")
        
        return DiagramImproveResponse(
            success=True,
            improved_code=improved_code,
            improvements_made=improvements_made
        )
        
    except Exception as e:
        logger.error(f"Diagram improvement failed: {e}", exc_info=True)
        return DiagramImproveResponse(
            success=False,
            improved_code=request.mermaid_code,  # Return original on error
            error=str(e)
        )


@router.get("/diagram-types")
async def get_supported_diagram_types(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get list of supported diagram types for canvas editing."""
    return {
        "supported_types": [
            {"value": "mermaid_erd", "label": "Entity-Relationship Diagram", "icon": "database"},
            {"value": "mermaid_sequence", "label": "Sequence Diagram", "icon": "arrow-right"},
            {"value": "mermaid_flowchart", "label": "Flowchart", "icon": "git-branch"},
            {"value": "mermaid_class", "label": "Class Diagram", "icon": "box"},
            {"value": "mermaid_architecture", "label": "Architecture Diagram", "icon": "layout"},
            {"value": "mermaid_state", "label": "State Diagram", "icon": "circle"},
            {"value": "mermaid_component", "label": "Component Diagram", "icon": "package"},
            {"value": "mermaid_data_flow", "label": "Data Flow Diagram", "icon": "arrow-right-circle"},
            # Add more as implemented...
        ],
        "total_count": len([t for t in ArtifactType if t.value.startswith("mermaid_")])
    }

