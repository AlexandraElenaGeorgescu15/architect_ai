"""
Export Service - Handles artifact export in various formats.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import base64
import io

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Optional imports for export formats
try:
    from PIL import Image
    import svgwrite
    PILLOW_AVAILABLE = True
    SVGWRITE_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    SVGWRITE_AVAILABLE = False
    logger.warning("PIL or svgwrite not available. Some export formats may be limited.")


class ExportService:
    """
    Service for exporting artifacts in various formats.
    
    Features:
    - PNG export (for diagrams)
    - SVG export (for diagrams)
    - PDF export
    - Markdown export
    - Code export (for code prototypes)
    """
    
    def __init__(self):
        """Initialize Export Service."""
        logger.info("Export Service initialized")
    
    async def export_artifact(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        export_format: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Export an artifact in the specified format.
        
        Args:
            artifact_id: Artifact identifier
            artifact_type: Type of artifact
            content: Artifact content
            export_format: Format to export (png, svg, pdf, markdown, code)
            options: Optional export options
        
        Returns:
            Dictionary with export data and metadata
        """
        options = options or {}
        
        try:
            if export_format == "png":
                return await self._export_png(artifact_id, artifact_type, content, options)
            elif export_format == "svg":
                return await self._export_svg(artifact_id, artifact_type, content, options)
            elif export_format == "pdf":
                return await self._export_pdf(artifact_id, artifact_type, content, options)
            elif export_format == "markdown":
                return await self._export_markdown(artifact_id, artifact_type, content, options)
            elif export_format == "code":
                return await self._export_code(artifact_id, artifact_type, content, options)
            elif export_format == "confluence":
                return await self._export_confluence(artifact_id, artifact_type, content, options)
            elif export_format == "jira":
                return await self._export_jira(artifact_id, artifact_type, content, options)
            else:
                return {"error": f"Unsupported export format: {export_format}"}
        except Exception as e:
            logger.error(f"Error exporting artifact {artifact_id}: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _export_png(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Export as PNG (for diagrams)."""
        # For Mermaid diagrams, would need to render to image
        # For now, return placeholder
        return {
            "format": "png",
            "filename": f"{artifact_id}.png",
            "data": None,  # Would be base64 encoded image data
            "note": "PNG export requires diagram rendering. Use SVG or Markdown for now."
        }
    
    async def _export_svg(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Export as SVG (for diagrams)."""
        # For Mermaid diagrams, would convert to SVG
        # For now, return Mermaid content wrapped in SVG
        if artifact_type.startswith("mermaid_"):
            svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg">
  <foreignObject width="100%" height="100%">
    <div xmlns="http://www.w3.org/1999/xhtml">
      <pre>{content}</pre>
    </div>
  </foreignObject>
</svg>"""
            return {
                "format": "svg",
                "filename": f"{artifact_id}.svg",
                "data": svg_content,
                "mime_type": "image/svg+xml"
            }
        else:
            return {"error": "SVG export only supported for Mermaid diagrams"}
    
    async def _export_pdf(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Export as PDF."""
        # Would use reportlab or similar to generate PDF
        # For now, return placeholder
        return {
            "format": "pdf",
            "filename": f"{artifact_id}.pdf",
            "data": None,
            "note": "PDF export requires PDF generation library. Use Markdown for now."
        }
    
    async def _export_markdown(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Export as Markdown."""
        metadata = options.get("metadata", {})
        
        markdown = f"""# {artifact_id}

**Type:** {artifact_type}  
**Generated:** {metadata.get('generated_at', datetime.now().isoformat())}  
**Model:** {metadata.get('model_used', 'unknown')}  
**Score:** {metadata.get('validation_score', 'N/A')}

---

## Content

"""
        
        if artifact_type.startswith("mermaid_"):
            markdown += f"```mermaid\n{content}\n```\n"
        elif artifact_type.startswith("html_"):
            markdown += f"```html\n{content}\n```\n"
        else:
            markdown += f"```\n{content}\n```\n"
        
        return {
            "format": "markdown",
            "filename": f"{artifact_id}.md",
            "data": markdown,
            "mime_type": "text/markdown"
        }
    
    async def _export_code(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Export as code file."""
        language = options.get("language", "text")
        extension = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "java": "java",
            "go": "go",
            "rust": "rs",
            "php": "php"
        }.get(language, "txt")
        
        return {
            "format": "code",
            "filename": f"{artifact_id}.{extension}",
            "data": content,
            "mime_type": f"text/plain",
            "language": language
        }

    async def _export_confluence(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Simulate pushing content to Confluence."""
        space_key = options.get("space_key", "ARCH")
        page_title = options.get("page_title", artifact_id.replace('_', ' ').title())
        logger.info("Simulated Confluence export for %s to space %s (page %s)", artifact_id, space_key, page_title)
        return {
            "format": "confluence",
            "metadata": {
                "space_key": space_key,
                "page_title": page_title,
                "status": "queued",
            },
            "message": f"Pretend sent '{artifact_type}' to Confluence space {space_key} / {page_title}.",
        }

    async def _export_jira(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Simulate creating/updating a Jira issue."""
        project_key = options.get("project_key", "ARCH")
        issue_type = options.get("issue_type", "Task")
        summary = options.get("summary", f"{artifact_type} for {artifact_id}")
        logger.info("Simulated Jira export for %s to project %s (%s)", artifact_id, project_key, issue_type)
        return {
            "format": "jira",
            "metadata": {
                "project_key": project_key,
                "issue_type": issue_type,
                "summary": summary,
            },
            "message": f"Pretend created Jira {project_key} issue '{summary}'.",
        }


# Global service instance
_export_service: Optional[ExportService] = None


def get_export_service() -> ExportService:
    """Get or create global Export Service instance."""
    global _export_service
    if _export_service is None:
        _export_service = ExportService()
    return _export_service

