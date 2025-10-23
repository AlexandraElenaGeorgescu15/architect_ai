"""
Diagram Validator - Ensures Mermaid diagrams are syntactically correct
"""

import re
from typing import Tuple, List

class DiagramValidator:
    """Validates and cleans Mermaid diagram syntax"""
    
    VALID_DIAGRAM_TYPES = {
        'graph', 'flowchart', 'sequenceDiagram', 'classDiagram', 
        'stateDiagram', 'erDiagram', 'gantt', 'pie', 'journey'
    }
    
    VALID_GRAPH_DIRECTIONS = {'TD', 'TB', 'BT', 'RL', 'LR'}
    
    @staticmethod
    def validate_and_clean(content: str, diagram_name: str = "diagram") -> Tuple[bool, str, List[str]]:
        """
        Validate and clean a Mermaid diagram.
        
        Returns:
            (is_valid, cleaned_content, errors)
        """
        errors = []
        cleaned = content.strip()
        
        if not cleaned:
            return False, "", ["Empty diagram content"]
        
        # Step 1: Remove any markdown code fences
        cleaned = re.sub(r'^```mermaid\s*\n?', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()
        
        # Step 2: Check for diagram type declaration
        lines = [l.strip() for l in cleaned.split('\n') if l.strip()]
        if not lines:
            return False, "", ["No content after cleaning"]
        
        first_line = lines[0]
        
        # Detect diagram type
        diagram_type = None
        for dtype in DiagramValidator.VALID_DIAGRAM_TYPES:
            if first_line.startswith(dtype):
                diagram_type = dtype
                break
        
        if not diagram_type:
            errors.append(f"No valid diagram type found. First line: '{first_line}'")
            # Try to infer and fix
            if any(keyword in cleaned.lower() for keyword in ['participant', 'actor', '->']):
                cleaned = f"sequenceDiagram\n{cleaned}"
                diagram_type = 'sequenceDiagram'
            elif any(keyword in cleaned.lower() for keyword in ['class', 'interface']):
                cleaned = f"classDiagram\n{cleaned}"
                diagram_type = 'classDiagram'
            else:
                # Default to flowchart
                cleaned = f"graph TD\n{cleaned}"
                diagram_type = 'graph'
            errors.append(f"Auto-fixed: Added '{diagram_type}' declaration")
        
        # Step 3: Ensure only ONE diagram type declaration
        lines = cleaned.split('\n')
        type_count = sum(1 for line in lines if any(line.strip().startswith(dt) for dt in DiagramValidator.VALID_DIAGRAM_TYPES))
        
        if type_count > 1:
            # Keep only the first declaration
            kept_first = False
            new_lines = []
            for line in lines:
                is_type_line = any(line.strip().startswith(dt) for dt in DiagramValidator.VALID_DIAGRAM_TYPES)
                if is_type_line:
                    if not kept_first:
                        new_lines.append(line)
                        kept_first = True
                    # else skip duplicate
                else:
                    new_lines.append(line)
            cleaned = '\n'.join(new_lines)
            errors.append(f"Removed {type_count - 1} duplicate diagram type declarations")
        
        # Step 4: Fix double braces {{...}} -> {...}
        original_cleaned = cleaned
        cleaned = re.sub(r'\{\{([^}]+)\}\}', r'{\1}', cleaned)
        if cleaned != original_cleaned:
            errors.append("Normalized double braces {{...}} to {...}")
        
        # Step 5: Remove any trailing/leading whitespace per line
        lines = [line.rstrip() for line in cleaned.split('\n')]
        cleaned = '\n'.join(lines).strip()
        
        # Step 6: Basic syntax checks
        if diagram_type in ['graph', 'flowchart']:
            # Check for direction
            first_line = lines[0] if lines else ""
            if diagram_type == 'graph':
                parts = first_line.split()
                if len(parts) < 2 or parts[1] not in DiagramValidator.VALID_GRAPH_DIRECTIONS:
                    errors.append(f"Graph missing valid direction (TD/LR/etc). Found: '{first_line}'")
        
        # Step 7: Check for common syntax errors
        for i, line in enumerate(lines[1:], start=2):  # Skip first line (diagram type)
            line = line.strip()
            if not line or line.startswith('%%'):  # Empty or comment
                continue
            
            # Check for unmatched brackets
            open_brackets = line.count('[') + line.count('(') + line.count('{')
            close_brackets = line.count(']') + line.count(')') + line.count('}')
            if open_brackets != close_brackets:
                errors.append(f"Line {i}: Unmatched brackets - '{line[:50]}'")
        
        # Validation result
        is_valid = len([e for e in errors if not e.startswith("Auto-fixed") and not e.startswith("Normalized") and not e.startswith("Removed")]) == 0
        
        return is_valid, cleaned, errors
    
    @staticmethod
    def validate_diagram_set(diagrams: dict) -> Tuple[dict, List[str]]:
        """
        Validate and clean a set of diagrams.
        
        Returns:
            (cleaned_diagrams, all_errors)
        """
        cleaned_diagrams = {}
        all_errors = []
        
        for name, content in diagrams.items():
            is_valid, cleaned, errors = DiagramValidator.validate_and_clean(content, name)
            cleaned_diagrams[name] = cleaned
            
            if errors:
                all_errors.append(f"[{name}] " + "; ".join(errors))
        
        return cleaned_diagrams, all_errors


def get_diagram_validator():
    """Get diagram validator instance"""
    return DiagramValidator()

