"""
Universal Diagram Syntax Fixer
Fixes syntax issues in ALL Mermaid diagram types (ERD, Flowchart, Sequence, Class, State, etc.)
"""

import re
from typing import Dict, List, Tuple, Optional


class UniversalDiagramFixer:
    """
    Comprehensive Mermaid diagram syntax fixer that handles all diagram types.
    
    Supports:
    - ERD (Entity Relationship Diagrams)
    - Flowcharts (flowchart TD/LR, graph TD/LR)
    - Sequence Diagrams
    - Class Diagrams
    - State Diagrams
    - Gantt Charts
    - Pie Charts
    - User Journey
    """
    
    DIAGRAM_TYPES = {
        'erdiagram': 'erDiagram',
        'flowchart': 'flowchart TD',
        'graph': 'graph TD',
        'sequencediagram': 'sequenceDiagram',
        'classdiagram': 'classDiagram',
        'statediagram': 'stateDiagram-v2',
        'gantt': 'gantt',
        'pie': 'pie',
        'journey': 'journey'
    }
    
    def __init__(self):
        self.current_type = None
        self.errors_fixed = []
    
    def fix_diagram(self, content: str) -> Tuple[str, List[str]]:
        """
        Fix any Mermaid diagram syntax issues.
        
        Args:
            content: Raw Mermaid diagram content (possibly with errors)
            
        Returns:
            Tuple of (fixed_content, list_of_fixes_applied)
        """
        self.errors_fixed = []
        
        # Step 1: Clean markdown wrappers
        content = self._remove_markdown_blocks(content)
        
        # Step 2: Detect diagram type
        diagram_type = self._detect_diagram_type(content)
        self.current_type = diagram_type
        
        if not diagram_type:
            self.errors_fixed.append("Could not detect diagram type - added default flowchart header")
            content = "flowchart TD\n" + content
            diagram_type = 'flowchart'
            self.current_type = 'flowchart'
        
        # Step 3: Apply type-specific fixes
        if diagram_type == 'erdiagram':
            content = self._fix_erd_diagram(content)
        elif diagram_type in ['flowchart', 'graph']:
            content = self._fix_flowchart_diagram(content)
        elif diagram_type == 'sequencediagram':
            content = self._fix_sequence_diagram(content)
        elif diagram_type == 'classdiagram':
            content = self._fix_class_diagram(content)
        elif diagram_type == 'statediagram':
            content = self._fix_state_diagram(content)
        elif diagram_type == 'gantt':
            content = self._fix_gantt_diagram(content)
        elif diagram_type == 'pie':
            content = self._fix_pie_diagram(content)
        elif diagram_type == 'journey':
            content = self._fix_journey_diagram(content)
        
        # Step 4: General cleanup
        content = self._general_cleanup(content)
        
        return content, self.errors_fixed
    
    def _remove_markdown_blocks(self, content: str) -> str:
        """Remove markdown code blocks (```mermaid, ```html, etc.) and RAG context pollution"""
        content = content.strip()
        
        # CRITICAL: Remove RAG context pollution that local models sometimes include
        # Look for common RAG pollution patterns
        rag_markers = [
            "RAG RETRIEVED CONTEXT:",
            "USER REQUEST:",
            "FILE:",
            "SECTION:",
            "Language:",
            "--- Chunk",
            "Score:",
        ]
        
        # Find the first actual diagram line
        lines = content.split('\n')
        diagram_start_idx = 0
        
        for i, line in enumerate(lines):
            # Check if this line starts a diagram
            line_lower = line.strip().lower()
            if any(line_lower.startswith(dt) for dt in ['erdiagram', 'flowchart', 'graph', 'sequencediagram', 'classdiagram', 'statediagram', 'gantt', 'pie', 'journey']):
                diagram_start_idx = i
                break
            # Or check if line contains diagram syntax
            elif '-->' in line or '||' in line or '|o' in line or '{' in line and '}' in line:
                # This looks like diagram content, backtrack to find header
                for j in range(i-1, -1, -1):
                    check_line = lines[j].strip().lower()
                    if any(check_line.startswith(dt) for dt in ['erdiagram', 'flowchart', 'graph', 'sequencediagram', 'classdiagram', 'statediagram', 'gantt', 'pie', 'journey']):
                        diagram_start_idx = j
                        break
                break
        
        # If we found diagram content after junk, trim the junk
        if diagram_start_idx > 0:
            content = '\n'.join(lines[diagram_start_idx:])
            self.errors_fixed.append(f"Removed {diagram_start_idx} lines of RAG context pollution before diagram")
        
        # Remove opening markdown blocks
        if content.startswith('```'):
            lines = content.split('\n')
            # Remove first line if it's a code block marker
            if lines[0].startswith('```'):
                content = '\n'.join(lines[1:])
                self.errors_fixed.append("Removed opening markdown code block")
        
        # Remove closing markdown blocks
        if content.endswith('```'):
            content = content[:-3].strip()
            self.errors_fixed.append("Removed closing markdown code block")
        
        return content
    
    def _detect_diagram_type(self, content: str) -> Optional[str]:
        """Detect the type of Mermaid diagram"""
        first_line = content.split('\n')[0].strip().lower()
        
        for key, value in self.DIAGRAM_TYPES.items():
            if first_line.startswith(key):
                return key
        
        # Check if it's a variant (e.g., "graph LR" instead of "graph TD")
        if first_line.startswith('graph '):
            return 'graph'
        if first_line.startswith('flowchart '):
            return 'flowchart'
        if first_line.startswith('statediagram'):
            return 'statediagram'
        
        return None
    
    def _fix_erd_diagram(self, content: str) -> str:
        """Fix ERD diagram syntax"""
        lines = content.strip().split('\n')
        fixed_lines = []
        entities = {}
        relationships = []
        current_entity = None
        current_entity_fields = []
        
        for line in lines:
            line = line.strip()
            
            if not line or line.startswith('```'):
                continue
            
            # Ensure first line is erDiagram
            if not fixed_lines:
                if not line.startswith('erDiagram'):
                    fixed_lines.append('erDiagram')
                    if line and line != 'erDiagram':
                        # Process this line again
                        pass
                    else:
                        continue
                else:
                    fixed_lines.append('erDiagram')
                    continue
            
            # Detect entity definition start
            if '{' in line and not ('||' in line or '}}' in line or line.count('{') > 1):
                entity_name = line.split('{')[0].strip()
                if entity_name:
                    current_entity = entity_name
                    current_entity_fields = []
                continue
            
            # Detect entity definition end
            if line.startswith('}') and current_entity:
                entities[current_entity] = current_entity_fields
                current_entity = None
                current_entity_fields = []
                continue
            
            # Detect field definition
            if current_entity and any(t in line for t in ['int ', 'string ', 'date ', 'decimal ', 'boolean ', 'text ', 'varchar ', 'timestamp ']):
                current_entity_fields.append('        ' + line)
                continue
            
            # Detect relationship
            if any(rel in line for rel in ['||--', '}}--', 'o{', '|{', '{|', 'o|']):
                relationships.append('    ' + line)
                continue
        
        # Build fixed ERD
        if not entities and not relationships:
            self.errors_fixed.append("ERD appears empty - added sample structure")
            return """erDiagram
    ENTITY {{
        int id PK
        string name
    }}"""
        
        # Add entities
        for entity_name, fields in entities.items():
            fixed_lines.append(f'    {entity_name} {{')
            if fields:
                fixed_lines.extend(fields)
            else:
                # Add placeholder if no fields
                fixed_lines.append('        int id PK')
                self.errors_fixed.append(f"Added placeholder fields to entity {entity_name}")
            fixed_lines.append('    }')
        
        # Add relationships
        fixed_lines.extend(relationships)
        
        if entities:
            self.errors_fixed.append(f"Fixed ERD structure: {len(entities)} entities, {len(relationships)} relationships")
        
        return '\n'.join(fixed_lines)
    
    def _fix_flowchart_diagram(self, content: str) -> str:
        """Fix flowchart/graph diagram syntax"""
        lines = content.strip().split('\n')
        fixed_lines = []
        
        first_line = lines[0].strip()
        
        # Ensure proper header
        if first_line.startswith('flowchart '):
            fixed_lines.append(first_line)
        elif first_line.startswith('graph '):
            fixed_lines.append(first_line)
        else:
            fixed_lines.append('flowchart TD')
            self.errors_fixed.append("Added missing flowchart header")
        
        # Process nodes and connections
        for i, line in enumerate(lines[1:] if fixed_lines else lines):
            line = line.strip()
            
            if not line or line.startswith('```'):
                continue
            
            # Fix common syntax issues
            # Issue 1: Missing quotes in labels with spaces
            if '[' in line and ']' in line:
                # Check if label has spaces but no quotes
                match = re.search(r'\[([^\]]+)\]', line)
                if match:
                    label = match.group(1)
                    if ' ' in label and not (label.startswith('"') or label.startswith("'")):
                        line = line.replace(f'[{label}]', f'["{label}"]')
                        if i == 0:  # Only log once
                            self.errors_fixed.append("Added quotes to labels with spaces")
            
            # Issue 2: Fix arrow syntax
            line = re.sub(r'--+>', '-->', line)  # Multiple dashes to standard arrow
            line = re.sub(r'==+>', '==>', line)  # Bold arrows
            
            # Issue 3: Fix node IDs (remove special characters)
            # This is complex, so we'll just validate it exists
            if '-->' in line or '---' in line:
                fixed_lines.append('    ' + line)
            elif line and not line.startswith(('flowchart', 'graph')):
                fixed_lines.append('    ' + line)
        
        if len(fixed_lines) <= 1:
            self.errors_fixed.append("Flowchart appears empty - added sample node")
            fixed_lines.append('    A[Start] --> B[End]')
        
        return '\n'.join(fixed_lines)
    
    def _fix_sequence_diagram(self, content: str) -> str:
        """Fix sequence diagram syntax"""
        lines = content.strip().split('\n')
        fixed_lines = []
        
        # Ensure header
        if not lines[0].strip().lower().startswith('sequencediagram'):
            fixed_lines.append('sequenceDiagram')
            self.errors_fixed.append("Added missing sequenceDiagram header")
        else:
            fixed_lines.append('sequenceDiagram')
        
        # Process interactions
        for line in lines[1:] if fixed_lines else lines:
            line = line.strip()
            
            if not line or line.startswith('```') or line.lower().startswith('sequencediagram'):
                continue
            
            # Fix participant declarations
            if line.lower().startswith('participant'):
                fixed_lines.append('    ' + line)
            # Fix arrows (->>, ->, -->>, -->)
            elif '->' in line or '-->>' in line:
                fixed_lines.append('    ' + line)
            # Fix notes
            elif line.lower().startswith('note'):
                fixed_lines.append('    ' + line)
            # Fix loops, alt, opt blocks
            elif any(kw in line.lower() for kw in ['loop', 'alt', 'opt', 'par', 'end']):
                fixed_lines.append('    ' + line)
            else:
                # Unknown line, but include it
                fixed_lines.append('    ' + line)
        
        if len(fixed_lines) <= 1:
            self.errors_fixed.append("Sequence diagram appears empty - added sample")
            fixed_lines.extend([
                '    participant A',
                '    participant B',
                '    A->>B: Hello'
            ])
        
        return '\n'.join(fixed_lines)
    
    def _fix_class_diagram(self, content: str) -> str:
        """Fix class diagram syntax"""
        lines = content.strip().split('\n')
        fixed_lines = []
        
        # Ensure header
        if not lines[0].strip().lower().startswith('classdiagram'):
            fixed_lines.append('classDiagram')
            self.errors_fixed.append("Added missing classDiagram header")
        else:
            fixed_lines.append('classDiagram')
        
        # Process class definitions and relationships
        for line in lines[1:] if fixed_lines else lines:
            line = line.strip()
            
            if not line or line.startswith('```') or line.lower().startswith('classdiagram'):
                continue
            
            # Class definitions
            if line.startswith('class ') or '{' in line:
                fixed_lines.append('    ' + line)
            # Relationships
            elif any(rel in line for rel in ['<|--', '*--', 'o--', '-->', '<..', '..>']):
                fixed_lines.append('    ' + line)
            else:
                fixed_lines.append('    ' + line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_state_diagram(self, content: str) -> str:
        """Fix state diagram syntax"""
        lines = content.strip().split('\n')
        fixed_lines = []
        
        # Ensure header
        if not lines[0].strip().lower().startswith('statediagram'):
            fixed_lines.append('stateDiagram-v2')
            self.errors_fixed.append("Added missing stateDiagram header")
        else:
            fixed_lines.append(lines[0].strip())
        
        # Process states and transitions
        for line in lines[1:] if fixed_lines else lines:
            line = line.strip()
            
            if not line or line.startswith('```') or line.lower().startswith('statediagram'):
                continue
            
            fixed_lines.append('    ' + line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_gantt_diagram(self, content: str) -> str:
        """Fix Gantt diagram syntax"""
        lines = content.strip().split('\n')
        fixed_lines = ['gantt']
        
        for line in lines[1:]:
            line = line.strip()
            if not line or line.startswith('```') or line.lower() == 'gantt':
                continue
            fixed_lines.append('    ' + line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_pie_diagram(self, content: str) -> str:
        """Fix pie chart syntax"""
        lines = content.strip().split('\n')
        fixed_lines = ['pie']
        
        for line in lines[1:]:
            line = line.strip()
            if not line or line.startswith('```') or line.lower() == 'pie':
                continue
            fixed_lines.append('    ' + line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_journey_diagram(self, content: str) -> str:
        """Fix user journey diagram syntax"""
        lines = content.strip().split('\n')
        fixed_lines = ['journey']
        
        for line in lines[1:]:
            line = line.strip()
            if not line or line.startswith('```') or line.lower() == 'journey':
                continue
            fixed_lines.append('    ' + line)
        
        return '\n'.join(fixed_lines)
    
    def _general_cleanup(self, content: str) -> str:
        """Apply general cleanup to all diagram types"""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove trailing whitespace
            line = line.rstrip()
            
            # Skip completely empty lines at start/end
            if not cleaned_lines and not line.strip():
                continue
            
            cleaned_lines.append(line)
        
        # Remove trailing empty lines
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()
        
        return '\n'.join(cleaned_lines)


# Global instance
universal_diagram_fixer = UniversalDiagramFixer()


def fix_any_diagram(content: str) -> Tuple[str, List[str]]:
    """
    Convenience function to fix any Mermaid diagram.
    
    Args:
        content: Raw diagram content
        
    Returns:
        Tuple of (fixed_content, list_of_fixes_applied)
    """
    return universal_diagram_fixer.fix_diagram(content)

