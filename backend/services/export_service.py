"""
Export Service - Handles artifact export in various formats.
Supports PNG, PDF, SVG, Markdown, and code exports.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import base64
import io
import subprocess
import tempfile
import os

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Optional imports for export formats
PILLOW_AVAILABLE = False
CAIROSVG_AVAILABLE = False
REPORTLAB_AVAILABLE = False

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    logger.warning("PIL not available. Image manipulation limited.")

try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except ImportError:
    logger.warning("cairosvg not available. PNG export will use fallback method.")

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    logger.warning("reportlab not available. PDF export will be limited.")


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
        """Export as PNG (for diagrams).
        
        Uses Mermaid CLI if available, otherwise falls back to cairosvg.
        """
        if not artifact_type.startswith("mermaid_") and not artifact_type.startswith("html_"):
            return {"error": "PNG export only supported for diagram artifacts"}
        
        try:
            # Method 1: Try Mermaid CLI (mmdc) if available
            png_data = await self._render_mermaid_to_png(content, artifact_id)
            
            if png_data:
                return {
                    "format": "png",
                    "filename": f"{artifact_id}.png",
                    "data": png_data,
                    "mime_type": "image/png"
                }
            
            # Method 2: Generate a simple PNG with text representation
            if PILLOW_AVAILABLE:
                png_data = await self._generate_text_png(content, artifact_id, artifact_type)
                return {
                    "format": "png",
                    "filename": f"{artifact_id}.png",
                    "data": png_data,
                    "mime_type": "image/png"
                }
            
            # Fallback: Return error with instructions
            return {
                "format": "png",
                "filename": f"{artifact_id}.png",
                "data": None,
                "error": "PNG export requires Mermaid CLI or Pillow. Install with: npm install -g @mermaid-js/mermaid-cli"
            }
            
        except Exception as e:
            logger.error(f"PNG export failed: {e}")
            return {"error": f"PNG export failed: {str(e)}"}
    
    async def _render_mermaid_to_png(self, content: str, artifact_id: str) -> Optional[bytes]:
        """Render Mermaid diagram to PNG using mmdc CLI."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                input_file = Path(tmpdir) / "input.mmd"
                output_file = Path(tmpdir) / "output.png"
                
                # Write Mermaid content
                input_file.write_text(content, encoding='utf-8')
                
                # Try to run mmdc (Mermaid CLI)
                result = subprocess.run(
                    ["mmdc", "-i", str(input_file), "-o", str(output_file), "-b", "white"],
                    capture_output=True,
                    timeout=30
                )
                
                if result.returncode == 0 and output_file.exists():
                    return output_file.read_bytes()
                else:
                    logger.warning(f"mmdc failed: {result.stderr.decode()}")
                    return None
                    
        except FileNotFoundError:
            logger.debug("mmdc (Mermaid CLI) not found, trying fallback")
            return None
        except Exception as e:
            logger.warning(f"Mermaid CLI render failed: {e}")
            return None
    
    async def _generate_text_png(self, content: str, artifact_id: str, artifact_type: str) -> bytes:
        """Generate a PNG image with text content using Pillow."""
        from PIL import Image, ImageDraw, ImageFont
        
        # Create image
        width, height = 1200, 800
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a monospace font
        try:
            font = ImageFont.truetype("consola.ttf", 12)
            title_font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
            title_font = font
        
        # Draw title
        title = f"{artifact_type.replace('_', ' ').title()}"
        draw.text((20, 20), title, fill='black', font=title_font)
        
        # Draw content (wrapped)
        y = 60
        lines = content.split('\n')
        for line in lines[:50]:  # Limit to first 50 lines
            if y > height - 40:
                draw.text((20, y), "... (content truncated)", fill='gray', font=font)
                break
            draw.text((20, y), line[:120], fill='black', font=font)
            y += 16
        
        # Draw footer
        draw.text((20, height - 30), f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}", fill='gray', font=font)
        
        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
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
        """Export as PDF using reportlab."""
        
        if REPORTLAB_AVAILABLE:
            try:
                pdf_data = await self._generate_pdf_reportlab(artifact_id, artifact_type, content, options)
                return {
                    "format": "pdf",
                    "filename": f"{artifact_id}.pdf",
                    "data": pdf_data,
                    "mime_type": "application/pdf"
                }
            except Exception as e:
                logger.error(f"PDF generation failed: {e}")
                return {"error": f"PDF generation failed: {str(e)}"}
        
        # Fallback: Generate a simple text-based PDF representation
        try:
            pdf_data = await self._generate_simple_pdf(artifact_id, artifact_type, content)
            return {
                "format": "pdf",
                "filename": f"{artifact_id}.pdf",
                "data": pdf_data,
                "mime_type": "application/pdf"
            }
        except Exception as e:
            return {
                "format": "pdf",
                "filename": f"{artifact_id}.pdf",
                "data": None,
                "error": "PDF export requires reportlab. Install with: pip install reportlab"
            }
    
    async def _generate_pdf_reportlab(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        options: Dict[str, Any]
    ) -> bytes:
        """Generate PDF using reportlab."""
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.enums import TA_LEFT
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        subtitle_style = styles['Heading2']
        
        # Create code style for monospace content
        code_style = ParagraphStyle(
            'Code',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=8,
            leading=10,
            leftIndent=10,
            rightIndent=10,
            spaceAfter=10,
            backColor='#f5f5f5'
        )
        
        story = []
        
        # Title
        story.append(Paragraph(f"Artifact: {artifact_id}", title_style))
        story.append(Spacer(1, 12))
        
        # Metadata
        metadata = options.get("metadata", {})
        meta_text = f"""
        <b>Type:</b> {artifact_type}<br/>
        <b>Generated:</b> {metadata.get('generated_at', datetime.now().isoformat())}<br/>
        <b>Score:</b> {metadata.get('validation_score', 'N/A')}
        """
        story.append(Paragraph(meta_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Content section
        story.append(Paragraph("Content", subtitle_style))
        story.append(Spacer(1, 12))
        
        # Add content as preformatted text (code-like)
        # Split content into chunks to avoid overflow
        lines = content.split('\n')
        chunk_size = 50  # Lines per chunk
        
        for i in range(0, len(lines), chunk_size):
            chunk = '\n'.join(lines[i:i+chunk_size])
            # Escape special characters for reportlab
            chunk = chunk.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Preformatted(chunk, code_style))
            story.append(Spacer(1, 6))
        
        doc.build(story)
        return buffer.getvalue()
    
    async def _generate_simple_pdf(self, artifact_id: str, artifact_type: str, content: str) -> bytes:
        """Generate a minimal PDF without reportlab (using basic PDF structure)."""
        # Create a minimal valid PDF with the content as text
        # This is a very basic PDF that most readers can open
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        text_content = f"""Artifact: {artifact_id}
Type: {artifact_type}
Exported: {timestamp}

{'='*50}

{content}
"""
        
        # Minimal PDF structure
        pdf_lines = [
            "%PDF-1.4",
            "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
            "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
            "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj",
        ]
        
        # Escape and encode content for PDF
        escaped_content = text_content.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        # Limit content length for simple PDF
        if len(escaped_content) > 10000:
            escaped_content = escaped_content[:10000] + "\n\n... [Content truncated for PDF export]"
        
        # Content stream
        stream_content = f"BT /F1 10 Tf 50 750 Td ({escaped_content[:500]}) Tj ET"
        stream_length = len(stream_content)
        
        pdf_lines.extend([
            f"4 0 obj << /Length {stream_length} >> stream",
            stream_content,
            "endstream endobj",
            "5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Courier >> endobj",
            "xref",
            "0 6",
            "0000000000 65535 f ",
            "0000000009 00000 n ",
            "0000000058 00000 n ",
            "0000000115 00000 n ",
            f"0000000270 00000 n ",
            f"0000000{270 + stream_length + 50:03d} 00000 n ",
            "trailer << /Size 6 /Root 1 0 R >>",
            "startxref",
            f"{400 + stream_length}",
            "%%EOF"
        ])
        
        return '\n'.join(pdf_lines).encode('latin-1')
    
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

