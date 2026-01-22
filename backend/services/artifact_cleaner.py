"""
Artifact Cleaner Service - Cleans and extracts artifact content from AI responses.
Handles both programmatic cleaning and AI-assisted cleanup.
"""

import re
import logging
import json
import os
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# #region agent log
def _debug_log_artifact(location: str, message: str, data: dict, hypothesis_id: str):
    """Write debug log entry to debug.log file"""
    try:
        log_path = os.path.join(os.path.dirname(__file__), '..', '..', '.cursor', 'debug.log')
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        entry = {
            "location": location,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "sessionId": "debug-session",
            "hypothesisId": hypothesis_id
        }
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception:
        pass
# #endregion


class ArtifactCleaner:
    """
    Cleans artifacts by removing noise, markdown wrappers, and explanatory text.
    Works for Mermaid diagrams, HTML, code, and other artifact types.
    """
    
    @staticmethod
    def clean_mermaid(content: str) -> str:
        """
        Extract clean Mermaid diagram code from content.
        Removes markdown code blocks, explanations, and other noise.
        AGGRESSIVELY strips AI explanatory text.
        """
        if not content:
            return content
        
        original_length = len(content)
        
        # #region agent log
        _debug_log_artifact(
            "artifact_cleaner.py:clean_mermaid:entry",
            "Mermaid cleaning started",
            {"contentLength": original_length, "contentPreview": content[:500]},
            "H2"
        )
        # #endregion
        
        # Step 1: Try to extract from markdown code blocks
        mermaid_pattern = r'```(?:mermaid)?\s*\n(.*?)```'
        matches = re.findall(mermaid_pattern, content, re.DOTALL | re.IGNORECASE)
        if matches:
            # Take the first match that looks like a diagram
            for match in matches:
                match = match.strip()
                if any(dt in match for dt in ["erDiagram", "flowchart", "graph", "sequenceDiagram",
                                               "classDiagram", "stateDiagram", "gantt", "pie", "journey",
                                               "gitgraph", "mindmap", "timeline", "C4"]):
                    content = match
                    break
        
        # Step 2: If no code block, look for diagram type declaration
        diagram_types = [
            "erDiagram", "flowchart", "graph ", "graph\n", "sequenceDiagram",
            "classDiagram", "stateDiagram", "stateDiagram-v2", "gantt", "pie", 
            "journey", "gitgraph", "mindmap", "timeline",
            "C4Context", "C4Container", "C4Component", "C4Deployment"
        ]
        
        for dt in diagram_types:
            if dt in content:
                idx = content.find(dt)
                # Extract from diagram type onwards
                diagram = content[idx:].strip()
                
                # COMPREHENSIVE list of explanatory text markers
                end_markers = [
                    'explanation:', 'note:', 'this diagram', 'the above',
                    '**explanation', '**note', '## explanation', '## note',
                    'here\'s what', 'this shows', 'the diagram above',
                    'let me know', 'hope this', 'feel free', 'if you need',
                    'if you have', 'i\'ve made', 'i\'ve updated', 'i\'ve improved',
                    'i\'ve fixed', 'i\'ve added', 'here is the', 'here\'s the',
                    'as requested', 'key improvements', 'changes made',
                    'improvements:', 'summary:', 'output:', 'result:',
                ]
                
                # Remove trailing explanations
                lines = diagram.split('\n')
                clean_lines = []
                
                for line in lines:
                    stripped = line.strip().lower()
                    
                    # Stop at explanatory text markers
                    if any(marker in stripped for marker in end_markers):
                        break
                    
                    # Stop at markdown headers that indicate end of diagram
                    if line.strip().startswith('##') or (line.strip().startswith('**') and ':' in line):
                        if len(clean_lines) > 3:  # Only if we have some content
                            break
                    
                    # Stop at numbered explanations (1. The diagram..., 2. This shows...)
                    if re.match(r'^\d+\.\s+[A-Z]', line.strip()):
                        if len(clean_lines) > 3:
                            break
                    
                    clean_lines.append(line)
                
                # Remove trailing empty lines
                while clean_lines and not clean_lines[-1].strip():
                    clean_lines.pop()
                
                if clean_lines:
                    content = '\n'.join(clean_lines).strip()
                    break
        
        # Step 3: Fix common ERD issues
        if "erDiagram" in content:
            content = ArtifactCleaner._fix_erd_syntax(content)
        
        # Step 4: Remove any remaining markdown artifacts
        content = re.sub(r'\*\*[^*]+\*\*\s*:', '', content)  # Remove bold markers with colons
        content = re.sub(r'^#+\s+.*$', '', content, flags=re.MULTILINE)  # Remove headers
        
        # Step 5: AGGRESSIVE cleanup of trailing AI text
        # Remove lines that look like AI explanations at the end
        lines = content.split('\n')
        while lines:
            last_line = lines[-1].strip().lower()
            should_remove = False
            
            # Check for AI conversation patterns
            ai_patterns = [
                'let me know', 'hope this', 'feel free', 'if you',
                'i\'ve', 'here\'s', 'this should', 'please', 
                'note:', 'explanation:', 'summary:'
            ]
            for pattern in ai_patterns:
                if last_line.startswith(pattern):
                    should_remove = True
                    break
            
            # Lines ending with ! or ? that aren't diagram content
            if not should_remove and (last_line.endswith('!') or last_line.endswith('?')):
                if not any(kw in last_line for kw in ['-->', '---', '|||', '{', '}']):
                    should_remove = True
            
            # Empty lines at end
            if not should_remove and not last_line:
                should_remove = True
            
            if should_remove:
                lines.pop()
            else:
                break
        
        content = '\n'.join(lines).strip()
        
        chars_removed = original_length - len(content)
        # Only log if significant content was removed (not just whitespace trimming)
        # Threshold of 10+ chars to reduce log spam from minor cleanups
        if chars_removed >= 10:
            logger.info(f"🧹 [CLEANER] Cleaned Mermaid: removed {chars_removed} chars")
        
        # #region agent log
        _debug_log_artifact(
            "artifact_cleaner.py:clean_mermaid:exit",
            "Mermaid cleaning complete",
            {"originalLength": original_length, "cleanedLength": len(content), "charsRemoved": chars_removed, "cleanedContent": content[:800]},
            "H2"
        )
        # #endregion
        
        return content
    
    @staticmethod
    def _fix_erd_syntax(content: str) -> str:
        """Fix ERD diagrams that use class diagram syntax incorrectly."""
        # Pattern to match class diagram syntax: class ENTITY { - field }
        class_pattern = r'class\s+(\w+)\s*\{([^}]+)\}'
        
        def convert_class_to_erd(match):
            entity_name = match.group(1)
            fields_text = match.group(2)
            
            erd_fields = []
            for line in fields_text.split('\n'):
                line = line.strip()
                if not line or not line.startswith('-'):
                    continue
                
                field_text = line[1:].strip()
                field_match = re.match(r'(\w+)(?:\s*\(([^)]+)\))?', field_text)
                if field_match:
                    field_name = field_match.group(1)
                    description = field_match.group(2) or ""
                    
                    # Determine type
                    field_type = "string"
                    if field_name.endswith("_id") or field_name == "id":
                        field_type = "int"
                    elif "date" in field_name.lower() or "time" in field_name.lower():
                        field_type = "datetime"
                    
                    # Determine key
                    key_suffix = ""
                    if "primary" in description.lower() or field_name == "id":
                        key_suffix = " PK"
                    elif "foreign" in description.lower() or (field_name.endswith("_id") and field_name != "id"):
                        key_suffix = " FK"
                    
                    erd_fields.append(f"        {field_type} {field_name}{key_suffix}")
            
            if erd_fields:
                return f"{entity_name} {{\n" + "\n".join(erd_fields) + "\n    }}"
            return f"{entity_name} {{\n        int id PK\n    }}"
        
        fixed = re.sub(class_pattern, convert_class_to_erd, content, flags=re.MULTILINE | re.DOTALL)
        fixed = re.sub(r'CLASS\s+', 'class ', fixed, flags=re.IGNORECASE)
        fixed = re.sub(class_pattern, convert_class_to_erd, fixed, flags=re.MULTILINE | re.DOTALL)
        
        return fixed
    
    @staticmethod
    def clean_html(content: str) -> str:
        """
        Extract clean HTML from content.
        Removes markdown wrappers and explanatory text.
        """
        if not content:
            return content
        
        original_length = len(content)
        
        # Step 1: Try to extract from markdown code blocks
        html_pattern = r'```(?:html)?\s*\n(.*?)```'
        matches = re.findall(html_pattern, content, re.DOTALL | re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if '<' in match and '>' in match:
                    content = match
                    break
        
        # Step 2: Look for HTML doctype or html tag
        if '<!DOCTYPE' in content or '<html' in content.lower():
            # Find start of HTML
            doctype_idx = content.find('<!DOCTYPE')
            html_idx = content.lower().find('<html')
            start_idx = min(
                doctype_idx if doctype_idx >= 0 else len(content),
                html_idx if html_idx >= 0 else len(content)
            )
            
            if start_idx < len(content):
                # Find end of HTML
                html_close_idx = content.lower().rfind('</html>')
                if html_close_idx > start_idx:
                    content = content[start_idx:html_close_idx + 7].strip()
                else:
                    content = content[start_idx:].strip()
        
        # Step 3: If just HTML fragments, clean up
        elif '<div' in content.lower() or '<body' in content.lower():
            # Look for first tag
            first_tag_idx = content.find('<')
            if first_tag_idx > 0:
                # Check if there's explanatory text before
                before = content[:first_tag_idx].strip()
                if before and not before.startswith('<!'):
                    content = content[first_tag_idx:].strip()
            
            # Remove trailing explanations
            last_tag_idx = content.rfind('>')
            if last_tag_idx > 0 and last_tag_idx < len(content) - 1:
                after = content[last_tag_idx + 1:].strip()
                if after and not after.startswith('<'):
                    content = content[:last_tag_idx + 1].strip()
        
        if len(content) < original_length:
            logger.info(f"🧹 [CLEANER] Cleaned HTML: removed {original_length - len(content)} chars")
        
        return content
    
    @staticmethod
    def clean_code(content: str, language: str = "python") -> str:
        """
        Extract clean code from content.
        Removes markdown wrappers and explanatory comments at start/end.
        """
        if not content:
            return content
        
        original_length = len(content)
        
        # Step 1: Try to extract from markdown code blocks
        code_pattern = rf'```(?:{language})?\s*\n(.*?)```'
        matches = re.findall(code_pattern, content, re.DOTALL | re.IGNORECASE)
        if matches:
            # Join all code blocks if multiple
            content = '\n\n'.join(m.strip() for m in matches)
        else:
            # Remove leading/trailing markdown
            content = re.sub(r'^```\w*\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
        
        if len(content) < original_length:
            logger.info(f"🧹 [CLEANER] Cleaned code: removed {original_length - len(content)} chars")
        
        return content.strip()
    
    @staticmethod
    def clean_artifact(content: str, artifact_type: str) -> str:
        """
        Clean artifact based on its type.
        
        Args:
            content: Raw artifact content
            artifact_type: Type of artifact (e.g., "mermaid_erd", "html_prototype")
        
        Returns:
            Cleaned artifact content
        """
        if not content:
            return content
        
        # #region agent log
        _debug_log_artifact(
            "artifact_cleaner.py:clean_artifact:entry",
            "Artifact cleaning requested",
            {"artifactType": artifact_type, "contentLength": len(content), "rawPreview": content[:300]},
            "H2"
        )
        # #endregion
        
        result = content
        if artifact_type.startswith("mermaid_"):
            result = ArtifactCleaner.clean_mermaid(content)
        elif artifact_type.startswith("html_") or artifact_type in ["dev_visual_prototype", "html_prototype"]:
            result = ArtifactCleaner.clean_html(content)
        elif artifact_type == "code_prototype":
            result = ArtifactCleaner.clean_code(content)
        elif artifact_type == "api_docs":
            # API docs can be markdown, minimal cleaning
            result = content.strip()
        else:
            # Default: just strip whitespace
            result = content.strip()
        
        # #region agent log
        _debug_log_artifact(
            "artifact_cleaner.py:clean_artifact:exit",
            "Artifact cleaning complete",
            {"artifactType": artifact_type, "resultLength": len(result), "cleanedPreview": result[:300]},
            "H2"
        )
        # #endregion
        
        return result


# Global singleton
_cleaner: Optional[ArtifactCleaner] = None


def get_cleaner() -> ArtifactCleaner:
    """Get or create global ArtifactCleaner instance."""
    global _cleaner
    if _cleaner is None:
        _cleaner = ArtifactCleaner()
    return _cleaner

