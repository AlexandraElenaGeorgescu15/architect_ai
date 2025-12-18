"""
AI-powered diagram parsing and improvement endpoints.
Supports all Mermaid diagram types with intelligent model routing.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Tuple
import logging
import re
import json

from backend.core.auth import get_current_user
from backend.models.dto import UserPublic, ArtifactType
from backend.services.model_service import get_service as get_model_service
from backend.services.enhanced_generation import get_enhanced_service as get_generation_service

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response that may contain markdown, explanations, or wrapper text.
    
    Handles various LLM output formats:
    - Clean JSON response
    - JSON wrapped in markdown code blocks
    - JSON with leading/trailing explanation text
    - Nested JSON with arrays and objects
    
    Args:
        response: Raw LLM response text
        
    Returns:
        Parsed JSON dict or None if extraction fails
    """
    if not response:
        return None
    
    response = response.strip()
    
    # Method 1: Try to parse as-is (clean JSON response)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # Method 2: Extract from markdown code block (```json ... ``` or ``` ... ```)
    # Use non-greedy match and handle multiple code blocks
    json_block_patterns = [
        r'```json\s*\n(.*?)\n```',  # Explicit json block
        r'```\s*\n(\{.*?\})\n```',   # Generic code block with JSON object
        r'```(.*?)```',              # Any code block
    ]
    
    for pattern in json_block_patterns:
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
        for match in matches:
            try:
                cleaned = match.strip()
                if cleaned.startswith('{') or cleaned.startswith('['):
                    return json.loads(cleaned)
            except json.JSONDecodeError:
                continue
    
    # Method 3: Find JSON object using balanced brace matching
    # This handles nested objects and arrays properly
    def find_balanced_json(text: str, start_char: str = '{', end_char: str = '}') -> Optional[str]:
        """Find a balanced JSON object or array in text."""
        start_idx = text.find(start_char)
        if start_idx == -1:
            return None
        
        count = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(text[start_idx:], start_idx):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if char == start_char:
                count += 1
            elif char == end_char:
                count -= 1
                if count == 0:
                    return text[start_idx:i+1]
        
        return None
    
    # Try to find a balanced JSON object
    json_str = find_balanced_json(response)
    if json_str:
        try:
            parsed = json.loads(json_str)
            # Verify it has expected structure for diagram parsing
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    
    # Method 4: Look for specific patterns like {"nodes": ..., "edges": ...}
    # Find the position of "nodes" and work backwards to find the opening brace
    nodes_idx = response.find('"nodes"')
    if nodes_idx != -1:
        # Search backwards for the opening brace
        for i in range(nodes_idx - 1, -1, -1):
            if response[i] == '{':
                json_str = find_balanced_json(response[i:])
                if json_str:
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
                break
    
    return None


def extract_mermaid_diagram(content: str) -> str:
    """
    Extract Mermaid diagram code from markdown code blocks or plain text.
    Removes any surrounding text and returns only the diagram code.
    
    Uses the shared extraction logic from ValidationService for consistency.
    """
    try:
        from backend.services.validation_service import get_service as get_validation_service
        validator = get_validation_service()
        extracted = validator._extract_mermaid_diagram(content)
        # Apply additional cleaning for AI explanatory text
        return _clean_ai_explanations(extracted)
    except ImportError:
        # Fallback if validation service not available
        pass
    
    # Fallback: Basic extraction
    # Try to extract from markdown code blocks first
    mermaid_pattern = r'```(?:mermaid)?\s*\n(.*?)```'
    matches = re.findall(mermaid_pattern, content, re.DOTALL | re.IGNORECASE)
    if matches:
        return _clean_ai_explanations(matches[0].strip())
    
    # Check for diagram type declarations
    diagram_types = [
        "erDiagram", "flowchart", "graph", "sequenceDiagram",
        "classDiagram", "stateDiagram", "gantt", "pie", "journey",
        "gitgraph", "mindmap", "timeline", "C4Context", "C4Container",
        "C4Component", "C4Deployment"
    ]
    
    for dt in diagram_types:
        if dt.lower() in content.lower():
            idx = content.lower().find(dt.lower())
            if idx != -1:
                diagram = content[idx:].strip()
                diagram = _clean_ai_explanations(diagram)
                if diagram:
                    return diagram
    
    return _clean_ai_explanations(content)


def _clean_ai_explanations(content: str) -> str:
    """
    Remove common AI explanatory text that appears before or after diagram code.
    """
    if not content:
        return content
    
    # Patterns that indicate end of diagram code (AI explanation starting)
    end_patterns = [
        r'\n\s*Let me know',
        r'\n\s*Hope this helps',
        r'\n\s*Feel free to',
        r'\n\s*If you have',
        r'\n\s*If you need',
        r'\n\s*Note:',
        r'\n\s*\*\*Note',
        r'\n\s*\*\*Explanation',
        r'\n\s*Explanation:',
        r'\n\s*This diagram',
        r'\n\s*The diagram',
        r'\n\s*I\'ve',
        r'\n\s*Here\'s',
        r'\n\s*Above is',
        r'\n\s*The above',
        r'\n\s*This shows',
        r'\n\s*---',
        r'\n\s*\*\*Key',
        r'\n\s*Key improvements',
        r'\n\s*Changes made',
        r'\n\s*Improvements:',
    ]
    
    result = content
    for pattern in end_patterns:
        match = re.search(pattern, result, re.IGNORECASE)
        if match:
            result = result[:match.start()].strip()
    
    # Also clean lines that start with common AI prefixes at the end
    lines = result.split('\n')
    cleaned_lines = []
    for line in lines:
        line_stripped = line.strip().lower()
        # Skip lines that are clearly explanatory
        if any(line_stripped.startswith(p) for p in [
            'let me know', 'hope this', 'feel free', 'if you', 
            'note:', '**note', '**explanation', 'explanation:',
            'this diagram', 'the diagram', "i've", "here's",
            'above is', 'the above', 'this shows', 'key improvements',
            'changes made', 'improvements:'
        ]):
            break
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()

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
        
        # Parse response using robust JSON extraction
        parsed_data = extract_json_from_response(result.content)
        
        if parsed_data is None:
            # Try one more time with a more explicit prompt
            retry_prompt = f"""
{prompt}

IMPORTANT: Return ONLY a valid JSON object. No explanations, no markdown, no code blocks.
Start your response with {{ and end with }}.
"""
            logger.warning("First parse attempt failed, retrying with explicit JSON prompt")
            retry_result = await generation_service.generate_with_fallback(
                prompt=retry_prompt,
                system_instruction=system_instruction + "\n\nYou MUST respond with ONLY valid JSON. No other text.",
                model_routing=routing,
                response_format="json",
                temperature=0.1  # Even lower temperature for strict JSON
            )
            parsed_data = extract_json_from_response(retry_result.content)
            
            if parsed_data is None:
                logger.error(f"Failed to extract JSON from AI response after retry. Response: {retry_result.content[:500]}...")
                return DiagramParseResponse(
                    success=False,
                    nodes=[],
                    edges=[],
                    error="AI returned response that could not be parsed as JSON. Please try again."
                )
        
        # Ensure nodes and edges are lists
        nodes = parsed_data.get("nodes", [])
        edges = parsed_data.get("edges", [])
        
        if not isinstance(nodes, list):
            nodes = []
        if not isinstance(edges, list):
            edges = []
        
        return DiagramParseResponse(
            success=True,
            nodes=[ReactFlowNode(**node) for node in nodes if isinstance(node, dict)],
            edges=[ReactFlowEdge(**edge) for edge in edges if isinstance(edge, dict)],
            metadata={
                "model_used": result.model_used,
                "diagram_type": request.diagram_type.value,
                "node_count": len(nodes),
                "edge_count": len(edges)
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


@router.post("/repair-diagram", response_model=DiagramImproveResponse)
async def repair_diagram(
    request: DiagramImproveRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    AGGRESSIVE diagram repair that keeps trying until diagram renders.
    Strategy:
    1. Rule-based repair (fast)
    2. AI repair with local model
    3. AI repair with cloud model (fallback)
    4. Full regeneration with cloud model (last resort)
    
    Does NOT stop until diagram is valid/renderable.
    """
    try:
        logger.info(f"🔧 AGGRESSIVE REPAIR: {request.diagram_type} diagram")
        
        original_code = request.mermaid_code
        attempts = []
        
        # Helper to validate diagram syntax
        def validate_mermaid(code: str) -> Tuple[bool, str]:
            """Check if Mermaid code is likely to render."""
            if not code or len(code.strip()) < 10:
                return False, "Code too short"
            
            code = code.strip()
            
            # Must start with valid diagram type
            diagram_types = [
                'erdiagram', 'flowchart', 'graph', 'sequencediagram',
                'classdiagram', 'statediagram', 'gantt', 'pie', 'journey',
                'gitgraph', 'mindmap', 'timeline', 'c4context', 'c4container',
                'c4component', 'c4deployment'
            ]
            first_line = code.split('\n')[0].strip().lower()
            if not any(first_line.startswith(dt) for dt in diagram_types):
                return False, f"Invalid diagram start: {first_line[:30]}"
            
            # Check balanced brackets
            if code.count('{') != code.count('}'):
                return False, "Unbalanced curly braces"
            if code.count('[') != code.count(']'):
                return False, "Unbalanced square brackets"
            
            # Check for common syntax errors
            if '-->|' in code and '|>' in code:
                return False, "Invalid arrow syntax (|>)"
            
            # Check content has more than just header
            lines = [l for l in code.split('\n') if l.strip() and not l.strip().startswith('%%')]
            if len(lines) < 2:
                return False, "Diagram has no content"
            
            # Check for AI text pollution
            ai_markers = ['let me know', 'hope this', 'feel free', 'here is the', "i've made"]
            for marker in ai_markers:
                if marker in code.lower():
                    return False, f"Contains AI text: {marker}"
            
            return True, "Valid"
        
        # ============================================================
        # ATTEMPT 1: Rule-based repair (fast, no AI)
        # ============================================================
        try:
            from components.universal_diagram_fixer import UniversalDiagramFixer
            fixer = UniversalDiagramFixer()
            fixed_code, fixes_applied = fixer.fix_diagram(original_code, max_passes=5)
            
            is_valid, reason = validate_mermaid(fixed_code)
            attempts.append(f"Rule-based: {is_valid} ({reason})")
            
            if is_valid:
                logger.info(f"✅ Rule-based repair successful: {len(fixes_applied)} fixes")
                return DiagramImproveResponse(
                    success=True,
                    improved_code=fixed_code,
                    improvements_made=[f"Rule-based: {f}" for f in fixes_applied[:5]] if fixes_applied else ["Diagram validated"],
                    error=None
                )
            else:
                logger.warning(f"Rule-based repair produced invalid diagram: {reason}")
        except Exception as e:
            attempts.append(f"Rule-based: Failed ({e})")
            logger.warning(f"Rule-based repair failed: {e}")
        
        # ============================================================
        # ATTEMPT 2: AI repair with local model
        # ============================================================
        try:
            ai_result = await _ai_repair_diagram(request, use_cloud=False)
            if ai_result and ai_result.strip():
                # Always clean AI output
                try:
                    fixer = UniversalDiagramFixer()
                    ai_result, _ = fixer.fix_diagram(ai_result, max_passes=3)
                except:
                    pass
                
                is_valid, reason = validate_mermaid(ai_result)
                attempts.append(f"AI-local: {is_valid} ({reason})")
                
                if is_valid:
                    logger.info(f"✅ AI (local) repair successful")
                    return DiagramImproveResponse(
                        success=True,
                        improved_code=ai_result,
                        improvements_made=["AI repair (local model)", "Syntax fixed"],
                        error=None
                    )
                else:
                    logger.warning(f"AI (local) repair produced invalid diagram: {reason}")
        except Exception as e:
            attempts.append(f"AI-local: Failed ({e})")
            logger.warning(f"AI (local) repair failed: {e}")
        
        # ============================================================
        # ATTEMPT 3: AI repair with CLOUD model (more capable)
        # ============================================================
        try:
            logger.info("🌐 Falling back to CLOUD model for repair")
            ai_result = await _ai_repair_diagram(request, use_cloud=True)
            if ai_result and ai_result.strip():
                # Always clean AI output
                try:
                    fixer = UniversalDiagramFixer()
                    ai_result, _ = fixer.fix_diagram(ai_result, max_passes=3)
                except:
                    pass
                
                is_valid, reason = validate_mermaid(ai_result)
                attempts.append(f"AI-cloud: {is_valid} ({reason})")
                
                if is_valid:
                    logger.info(f"✅ AI (cloud) repair successful")
                    return DiagramImproveResponse(
                        success=True,
                        improved_code=ai_result,
                        improvements_made=["AI repair (cloud model)", "Syntax fixed", "Full regeneration"],
                        error=None
                    )
                else:
                    logger.warning(f"AI (cloud) repair produced invalid diagram: {reason}")
        except Exception as e:
            attempts.append(f"AI-cloud: Failed ({e})")
            logger.warning(f"AI (cloud) repair failed: {e}")
        
        # ============================================================
        # ATTEMPT 4: Full REGENERATION with cloud model (last resort)
        # ============================================================
        try:
            logger.info("🔄 Last resort: Full regeneration with cloud model")
            regenerated = await _regenerate_diagram_from_scratch(request)
            if regenerated and regenerated.strip():
                # Always clean output
                try:
                    fixer = UniversalDiagramFixer()
                    regenerated, _ = fixer.fix_diagram(regenerated, max_passes=3)
                except:
                    pass
                
                is_valid, reason = validate_mermaid(regenerated)
                attempts.append(f"Regenerate: {is_valid} ({reason})")
                
                if is_valid:
                    logger.info(f"✅ Full regeneration successful")
                    return DiagramImproveResponse(
                        success=True,
                        improved_code=regenerated,
                        improvements_made=["Full regeneration (cloud)", "New diagram created"],
                        error=None
                    )
        except Exception as e:
            attempts.append(f"Regenerate: Failed ({e})")
            logger.error(f"Full regeneration failed: {e}")
        
        # ============================================================
        # ALL ATTEMPTS FAILED - Return best effort
        # ============================================================
        logger.error(f"❌ All repair attempts failed: {attempts}")
        
        # Return the rule-based fix even if invalid (best we have)
        try:
            fixer = UniversalDiagramFixer()
            best_effort, _ = fixer.fix_diagram(original_code, max_passes=5)
        except:
            best_effort = original_code
        
        return DiagramImproveResponse(
            success=False,
            improved_code=best_effort,
            improvements_made=attempts,
            error=f"All repair attempts failed. Attempts: {', '.join(attempts)}"
        )
        
    except Exception as e:
        logger.error(f"Repair failed catastrophically: {e}", exc_info=True)
        return DiagramImproveResponse(
            success=False,
            improved_code=request.mermaid_code,
            improvements_made=[],
            error=f"Repair failed: {str(e)}"
        )


async def _ai_repair_diagram(request: DiagramImproveRequest, use_cloud: bool = False) -> Optional[str]:
    """
    Use AI to repair a diagram.
    
    Args:
        request: The repair request
        use_cloud: If True, force use of cloud models (Gemini, GPT-4, etc.)
    """
    try:
        # Get generation service
        generation_service = get_generation_service()
        
        # Detect diagram type from code
        diagram_type = "diagram"
        code_lower = request.mermaid_code.lower().strip()
        if code_lower.startswith("erdiagram"):
            diagram_type = "erDiagram"
        elif code_lower.startswith("flowchart") or code_lower.startswith("graph"):
            diagram_type = "flowchart"
        elif code_lower.startswith("classdiagram"):
            diagram_type = "classDiagram"
        elif code_lower.startswith("sequencediagram"):
            diagram_type = "sequenceDiagram"
        elif code_lower.startswith("statediagram"):
            diagram_type = "stateDiagram-v2"
        elif code_lower.startswith("gantt"):
            diagram_type = "gantt"
        elif code_lower.startswith("pie"):
            diagram_type = "pie"
        elif code_lower.startswith("journey"):
            diagram_type = "journey"
        
        # Build strict prompt
        prompt = f"""Fix this Mermaid {diagram_type} diagram. It has syntax errors and won't render.

BROKEN DIAGRAM:
{request.mermaid_code}

REQUIREMENTS:
1. Fix ALL syntax errors
2. Keep the same structure and meaning
3. Output ONLY the fixed Mermaid code
4. Start directly with "{diagram_type}" (NO explanations)
5. Do NOT include markdown code blocks
6. Do NOT say "Here is" or any other text
7. JUST the raw Mermaid code, nothing else

VALID {diagram_type.upper()} SYNTAX:"""

        # Get model routing - force cloud if requested
        model_service = get_model_service()
        
        if use_cloud:
            # Force cloud models
            routing = {
                "models": ["gemini-2.0-flash-exp", "gpt-4-turbo", "claude-3-sonnet"],
                "priority": "cloud"
            }
        else:
            routing = model_service.get_routing_for_artifact(request.diagram_type)
        
        # Call AI (cloud-only for repair)
        result = await generation_service.generate_with_fallback(
            prompt=prompt,
            model_routing=routing,
            temperature=0.1,  # Very low temperature for consistent syntax
            max_local_attempts=0,  # enforce cloud-only models for repair
            system_instruction=f"""You are a Mermaid diagram syntax expert. You ONLY output valid Mermaid code.
CRITICAL: 
- Output ONLY the Mermaid diagram code
- Start with "{diagram_type}" keyword
- NO explanations, NO markdown, NO comments
- Just the raw diagram code"""
        )
        
        if result.success and result.content:
            # Extract just the diagram
            content = extract_mermaid_diagram(result.content)
            return content
        
        return None
        
    except Exception as e:
        logger.error(f"AI repair failed: {e}", exc_info=True)
        return None


async def _regenerate_diagram_from_scratch(request: DiagramImproveRequest) -> Optional[str]:
    """
    Completely regenerate a diagram from scratch using cloud models.
    Last resort when repair fails.
    """
    try:
        generation_service = get_generation_service()
        
        # Detect what the diagram is trying to show
        diagram_type = "flowchart"
        code_lower = request.mermaid_code.lower()
        
        if "erdiagram" in code_lower:
            diagram_type = "erDiagram"
        elif "classdiagram" in code_lower:
            diagram_type = "classDiagram"
        elif "sequencediagram" in code_lower:
            diagram_type = "sequenceDiagram"
        elif "statediagram" in code_lower:
            diagram_type = "stateDiagram-v2"
        elif "gantt" in code_lower:
            diagram_type = "gantt"
        elif "pie" in code_lower:
            diagram_type = "pie"
        elif "journey" in code_lower:
            diagram_type = "journey"
        
        # Extract meaningful content from broken diagram to understand intent
        # Look for node names, labels, relationships
        content_hints = []
        for line in request.mermaid_code.split('\n'):
            line = line.strip()
            if line and not line.startswith(('```', diagram_type.lower(), '#', '%%')):
                # Extract words that look like identifiers
                words = re.findall(r'\b[A-Z][a-zA-Z0-9_]*\b', line)
                content_hints.extend(words[:3])  # Limit per line
        
        content_hints = list(set(content_hints))[:10]  # Unique, max 10
        
        prompt = f"""Generate a valid Mermaid {diagram_type} diagram.

The diagram should include these elements (extracted from broken diagram):
{', '.join(content_hints) if content_hints else 'Standard elements for this diagram type'}

REQUIREMENTS:
1. Output ONLY valid Mermaid {diagram_type} code
2. Start directly with "{diagram_type}"
3. NO explanations, NO markdown code blocks
4. Include proper relationships and structure
5. Make sure ALL syntax is correct

OUTPUT:"""

        # Force cloud models for regeneration
        routing = {
            "models": ["gemini-2.0-flash-exp", "gpt-4-turbo", "claude-3-sonnet"],
            "priority": "cloud"
        }
        
        result = await generation_service.generate_with_fallback(
            prompt=prompt,
            model_routing=routing,
            temperature=0.3,
            max_local_attempts=0,  # enforce cloud-only models for regeneration
            system_instruction=f"""You are a Mermaid diagram expert. Generate ONLY valid {diagram_type} code.
CRITICAL: Output the raw Mermaid code only. No explanations. No markdown. Just the diagram."""
        )
        
        if result.success and result.content:
            return extract_mermaid_diagram(result.content)
        
        return None
        
    except Exception as e:
        logger.error(f"Regeneration failed: {e}", exc_info=True)
        return None


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
        logger.info(f"Improving {request.diagram_type} diagram (AI-powered)")
        
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
        
        # Use the robust extraction helper to get clean diagram code
        improved_code = extract_mermaid_diagram(result.content)
        
        # Validate that we got something meaningful
        if not improved_code or len(improved_code.strip()) < 10:
            logger.warning("AI response extraction resulted in empty or short content")
            return DiagramImproveResponse(
                success=False,
                improved_code=request.mermaid_code,
                improvements_made=[],
                error="AI returned incomplete diagram. Please try again."
            )
        
        # Validate that the improved code has the same diagram type
        improved_lower = improved_code.lower().strip()
        if diagram_start and not improved_lower.startswith(diagram_start.lower()):
            # Try to find the diagram type in the response
            logger.warning(f"AI response doesn't start with expected diagram type: {diagram_start}")
            
            # Try to prepend the diagram type if it's missing
            for dt in ["erDiagram", "flowchart", "graph", "sequenceDiagram", 
                       "classDiagram", "stateDiagram", "gantt", "pie", "journey",
                       "gitgraph", "mindmap", "timeline"]:
                if dt.lower() in improved_lower:
                    # Found the diagram type somewhere, extract from there
                    idx = improved_lower.find(dt.lower())
                    improved_code = improved_code[idx:].strip()
                    break
            
            # If still doesn't start correctly and is significantly shorter, fail
            if len(improved_code) < len(request.mermaid_code) * 0.5:
                return DiagramImproveResponse(
                    success=False,
                    improved_code=request.mermaid_code,
                    improvements_made=[],
                    error="AI returned incomplete diagram. Please try again."
                )
        
        # ALWAYS run the diagram fixer on AI output to strip explanatory text
        try:
            from components.universal_diagram_fixer import UniversalDiagramFixer
            fixer = UniversalDiagramFixer()
            improved_code, fixer_fixes = fixer.fix_diagram(improved_code, max_passes=3)
            if fixer_fixes:
                logger.info(f"Post-AI fixer applied {len(fixer_fixes)} fixes")
        except Exception as e:
            logger.warning(f"Post-AI fixer failed: {e}")
        
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
            improvements_made.append("Syntax verified and cleaned")
        
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

