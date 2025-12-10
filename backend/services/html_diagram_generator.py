"""
HTML Diagram Generator Service - Converts Mermaid diagrams to interactive HTML visualizations.

For every Mermaid diagram type, there should be a corresponding HTML version.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import re

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.models.dto import ArtifactType

logger = logging.getLogger(__name__)

# Optional imports
try:
    from components.mermaid_html_renderer import MermaidHTMLRenderer
    HTML_RENDERER_AVAILABLE = True
except ImportError:
    HTML_RENDERER_AVAILABLE = False
    logger.warning("MermaidHTMLRenderer not available. HTML generation will be limited.")


class HTMLDiagramGenerator:
    """
    Generates HTML visualizations for Mermaid diagrams.
    
    Features:
    - Converts Mermaid syntax to interactive HTML
    - Supports all Mermaid diagram types
    - Context-aware generation using AI
    - Fallback to static rendering if AI unavailable
    """
    
    # Mapping from Mermaid artifact types to HTML artifact types
    MERMAID_TO_HTML_MAP = {
        ArtifactType.MERMAID_ERD: ArtifactType.HTML_ERD,
        ArtifactType.MERMAID_ARCHITECTURE: ArtifactType.HTML_ARCHITECTURE,
        ArtifactType.MERMAID_SEQUENCE: ArtifactType.HTML_SEQUENCE,
        ArtifactType.MERMAID_CLASS: ArtifactType.HTML_CLASS,
        ArtifactType.MERMAID_STATE: ArtifactType.HTML_STATE,
        ArtifactType.MERMAID_FLOWCHART: ArtifactType.HTML_FLOWCHART,
        ArtifactType.MERMAID_DATA_FLOW: ArtifactType.HTML_DATA_FLOW,
        ArtifactType.MERMAID_USER_FLOW: ArtifactType.HTML_USER_FLOW,
        ArtifactType.MERMAID_COMPONENT: ArtifactType.HTML_COMPONENT,
        ArtifactType.MERMAID_SYSTEM_OVERVIEW: ArtifactType.HTML_SYSTEM_OVERVIEW,
        ArtifactType.MERMAID_API_SEQUENCE: ArtifactType.HTML_API_SEQUENCE,
        ArtifactType.MERMAID_UML: ArtifactType.HTML_UML,
        ArtifactType.MERMAID_GANTT: ArtifactType.HTML_GANTT,
        ArtifactType.MERMAID_PIE: ArtifactType.HTML_PIE,
        ArtifactType.MERMAID_JOURNEY: ArtifactType.HTML_JOURNEY,
        ArtifactType.MERMAID_MINDMAP: ArtifactType.HTML_MINDMAP,
        ArtifactType.MERMAID_GIT_GRAPH: ArtifactType.HTML_GIT_GRAPH,
        ArtifactType.MERMAID_TIMELINE: ArtifactType.HTML_TIMELINE,
        ArtifactType.MERMAID_C4_CONTEXT: ArtifactType.HTML_C4_CONTEXT,
        ArtifactType.MERMAID_C4_CONTAINER: ArtifactType.HTML_C4_CONTAINER,
        ArtifactType.MERMAID_C4_COMPONENT: ArtifactType.HTML_C4_COMPONENT,
        ArtifactType.MERMAID_C4_DEPLOYMENT: ArtifactType.HTML_C4_DEPLOYMENT,
    }
    
    def __init__(self):
        """Initialize HTML Diagram Generator."""
        self.renderer = MermaidHTMLRenderer() if HTML_RENDERER_AVAILABLE else None
        logger.info("HTML Diagram Generator initialized")
    
    def get_html_artifact_type(self, mermaid_artifact_type: ArtifactType) -> Optional[ArtifactType]:
        """
        Get corresponding HTML artifact type for a Mermaid artifact type.
        
        Args:
            mermaid_artifact_type: Mermaid artifact type
        
        Returns:
            Corresponding HTML artifact type or None
        """
        return self.MERMAID_TO_HTML_MAP.get(mermaid_artifact_type)
    
    async def generate_html_directly(
        self,
        html_artifact_type: ArtifactType,
        meeting_notes: str,
        rag_context: str = "",
        use_ai: bool = True
    ) -> str:
        """
        Generate HTML diagram directly from meeting notes (without Mermaid).
        
        Args:
            html_artifact_type: HTML artifact type (e.g., HTML_ERD, HTML_FLOWCHART)
            meeting_notes: Meeting notes/requirements
            rag_context: RAG context for AI generation
            use_ai: Whether to use AI for generation
        
        Returns:
            HTML content
        """
        if not self.renderer:
            logger.warning("HTML renderer not available, cannot generate HTML directly")
            return self._create_basic_html("", html_artifact_type)
        
        # Map HTML artifact type to diagram type
        html_to_diagram_type = {
            ArtifactType.HTML_ERD: "erd",
            ArtifactType.HTML_ARCHITECTURE: "architecture",
            ArtifactType.HTML_SEQUENCE: "sequence",
            ArtifactType.HTML_CLASS: "class",
            ArtifactType.HTML_STATE: "state",
            ArtifactType.HTML_FLOWCHART: "flowchart",
            ArtifactType.HTML_DATA_FLOW: "data_flow",
            ArtifactType.HTML_USER_FLOW: "user_flow",
            ArtifactType.HTML_COMPONENT: "component",
            ArtifactType.HTML_SYSTEM_OVERVIEW: "system_overview",
            ArtifactType.HTML_API_SEQUENCE: "api_sequence",
            ArtifactType.HTML_UML: "uml",
            ArtifactType.HTML_GANTT: "gantt",
            ArtifactType.HTML_PIE: "pie",
            ArtifactType.HTML_JOURNEY: "journey",
            ArtifactType.HTML_MINDMAP: "mindmap",
            ArtifactType.HTML_GIT_GRAPH: "git_graph",
            ArtifactType.HTML_TIMELINE: "timeline",
            ArtifactType.HTML_C4_CONTEXT: "c4_context",
            ArtifactType.HTML_C4_CONTAINER: "c4_container",
            ArtifactType.HTML_C4_COMPONENT: "c4_component",
            ArtifactType.HTML_C4_DEPLOYMENT: "c4_deployment",
        }
        
        diagram_type = html_to_diagram_type.get(html_artifact_type, "flowchart")
        
        try:
            if use_ai and meeting_notes:
                # Generate HTML directly from meeting notes (no Mermaid needed)
                html_content = await self.renderer.generate_html_visualization_with_gemini(
                    mermaid_content="",  # Empty - we're generating directly
                    meeting_notes=meeting_notes,
                    diagram_type=diagram_type,
                    rag_context=rag_context
                )
                logger.info(f"✅ [HTML_GEN] Generated HTML diagram directly: type={html_artifact_type.value}, diagram_type={diagram_type}")
                return html_content
            else:
                logger.warning("AI generation required for direct HTML generation")
                return self._create_basic_html("", html_artifact_type)
        except Exception as e:
            logger.error(f"Error generating HTML directly: {e}")
            return self._create_basic_html("", html_artifact_type)
    
    async def generate_html_from_mermaid(
        self,
        mermaid_content: str,
        mermaid_artifact_type: ArtifactType,
        meeting_notes: str = "",
        rag_context: str = "",
        use_ai: bool = True
    ) -> str:
        """
        Generate HTML visualization from Mermaid diagram.
        
        Args:
            mermaid_content: Mermaid diagram code
            mermaid_artifact_type: Type of Mermaid diagram
            meeting_notes: Meeting notes for context
            rag_context: RAG context for AI generation
            use_ai: Whether to use AI for context-aware generation
        
        Returns:
            HTML content as string
        """
        if not self.renderer:
            # Fallback: basic HTML wrapper
            return self._create_basic_html(mermaid_content, mermaid_artifact_type)
        
        # Determine diagram type for renderer
        diagram_type_map = {
            ArtifactType.MERMAID_ERD: "erd",
            ArtifactType.MERMAID_ARCHITECTURE: "architecture",
            ArtifactType.MERMAID_SEQUENCE: "sequence",
            ArtifactType.MERMAID_CLASS: "class",
            ArtifactType.MERMAID_STATE: "state",
            ArtifactType.MERMAID_FLOWCHART: "flowchart",
            ArtifactType.MERMAID_DATA_FLOW: "data_flow",
            ArtifactType.MERMAID_USER_FLOW: "user_flow",
            ArtifactType.MERMAID_COMPONENT: "component",
            ArtifactType.MERMAID_GANTT: "gantt",
            ArtifactType.MERMAID_PIE: "pie",
            ArtifactType.MERMAID_JOURNEY: "journey",
            ArtifactType.MERMAID_MINDMAP: "mindmap",
            ArtifactType.MERMAID_GIT_GRAPH: "git_graph",
            ArtifactType.MERMAID_TIMELINE: "timeline",
            ArtifactType.MERMAID_SYSTEM_OVERVIEW: "system_overview",
            ArtifactType.MERMAID_API_SEQUENCE: "api_sequence",
            ArtifactType.MERMAID_UML: "uml",
            # C4 Diagrams - individual types
            ArtifactType.MERMAID_C4_CONTEXT: "c4_context",
            ArtifactType.MERMAID_C4_CONTAINER: "c4_container",
            ArtifactType.MERMAID_C4_COMPONENT: "c4_component",
            ArtifactType.MERMAID_C4_DEPLOYMENT: "c4_deployment",
        }
        
        diagram_type = diagram_type_map.get(mermaid_artifact_type, "flowchart")
        
        try:
            if use_ai and meeting_notes:
                # Use AI for context-aware generation
                html_content = await self.renderer.generate_html_visualization_with_gemini(
                    mermaid_content=mermaid_content,
                    meeting_notes=meeting_notes,
                    diagram_type=diagram_type,
                    rag_context=rag_context
                )
            else:
                # Use static rendering
                html_content = self.renderer.render_mermaid_as_html(
                    mermaid_content=mermaid_content,
                    diagram_id=f"{diagram_type}_diagram"
                )
            
            return html_content
        except Exception as e:
            logger.error(f"Error generating HTML from Mermaid: {e}")
            # Fallback to basic HTML
            return self._create_basic_html(mermaid_content, mermaid_artifact_type)
    
    def _create_basic_html(self, mermaid_content: str, artifact_type: ArtifactType) -> str:
        """Create basic HTML wrapper for Mermaid diagram."""
        diagram_type = artifact_type.value.replace("mermaid_", "")
        
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{diagram_type.replace('_', ' ').title()} Diagram</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
        }}
        h1 {{
            color: #667eea;
            margin-bottom: 30px;
            text-align: center;
        }}
        .diagram-container {{
            background: #f9f9f9;
            padding: 30px;
            border-radius: 8px;
            margin: 20px 0;
            overflow-x: auto;
        }}
        .mermaid {{
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{diagram_type.replace('_', ' ').title()} Diagram</h1>
        <div class="diagram-container">
            <div class="mermaid">
{mermaid_content}
            </div>
        </div>
    </div>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            themeVariables: {{
                primaryColor: '#667eea',
                primaryTextColor: '#fff',
                primaryBorderColor: '#764ba2',
                lineColor: '#667eea',
                secondaryColor: '#f0f0f0',
                tertiaryColor: '#f9f9f9'
            }}
        }});
    </script>
</body>
</html>"""
        return html_template
    
    def validate_mermaid_syntax(self, mermaid_content: str) -> tuple[bool, Optional[str], List[str]]:
        """
        Validate Mermaid syntax and attempt to fix common errors.
        
        Args:
            mermaid_content: Mermaid diagram code
        
        Returns:
            Tuple of (is_valid, corrected_content, errors)
        """
        errors = []
        corrected = mermaid_content
        
        # Basic validation
        if not mermaid_content or len(mermaid_content.strip()) < 10:
            errors.append("Mermaid content too short")
            return False, None, errors
        
        # Check for common diagram type declarations
        diagram_types = [
            "erDiagram", "graph", "flowchart", "sequenceDiagram",
            "classDiagram", "stateDiagram", "gantt", "pie", "journey",
            "gitGraph", "mindmap", "timeline", "C4Context", "C4Container"
        ]
        
        has_diagram_type = any(diagram_type in mermaid_content for diagram_type in diagram_types)
        if not has_diagram_type:
            errors.append("No diagram type declaration found")
            # Try to infer and add
            if "Entity" in mermaid_content or "entity" in mermaid_content.lower():
                corrected = "erDiagram\n" + corrected
            elif "->" in mermaid_content or "Node" in mermaid_content:
                corrected = "graph TD\n" + corrected
        
        # Check for balanced brackets
        open_brackets = mermaid_content.count('{')
        close_brackets = mermaid_content.count('}')
        if open_brackets != close_brackets:
            errors.append(f"Unbalanced brackets: {open_brackets} open, {close_brackets} close")
        
        is_valid = len(errors) == 0
        return is_valid, corrected if is_valid else mermaid_content, errors


# Global generator instance
_html_generator: Optional[HTMLDiagramGenerator] = None

def get_generator() -> HTMLDiagramGenerator:
    """Get or create global HTML Diagram Generator instance."""
    global _html_generator
    if _html_generator is None:
        _html_generator = HTMLDiagramGenerator()
    return _html_generator

