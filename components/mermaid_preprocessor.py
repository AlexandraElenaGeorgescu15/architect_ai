"""
Aggressive Mermaid Diagram Preprocessor
Fixes common syntax errors BEFORE validation and rendering
"""

import re
from typing import Tuple, List


def aggressive_mermaid_preprocessing(diagram_text: str) -> str:
    """
    Aggressive preprocessing to fix common Mermaid syntax errors BEFORE validation.
    
    Fixes:
    1. Multiple diagram declarations on same line (flowchart TDgraph TD)
    2. Markdown fences inside diagram content (```mermaid inside diagram)
    3. Invalid characters in node IDs (.NET, C#, etc.)
    4. Duplicate diagram headers
    5. Malformed ERD entities
    6. Sequence diagram format issues
    
    Args:
        diagram_text: Raw Mermaid diagram text (possibly with errors)
    
    Returns:
        Cleaned diagram text ready for validation
    """
    if not diagram_text:
        return "flowchart TD\n"
    
    # Strip outer markdown fences first
    diagram_text = diagram_text.strip()
    if diagram_text.startswith("```mermaid"):
        diagram_text = diagram_text[10:].strip()
    if diagram_text.startswith("```"):
        diagram_text = diagram_text[3:].strip()
    if diagram_text.endswith("```"):
        diagram_text = diagram_text[:-3:].strip()
    
    # Remove ANY remaining ``` fences (they shouldn't be inside the diagram)
    diagram_text = diagram_text.replace("```mermaid", "").replace("```", "")
    
    lines = diagram_text.split("\n")
    fixed_lines = []
    diagram_type_declared = False
    in_erd_entity = False
    
    for i, line in enumerate(lines):
        original_line = line
        line = line.strip()
        
        # Skip empty lines at the start
        if not line and not fixed_lines:
            continue
        
        # Fix: Multiple diagram declarations on same line
        # Example: "flowchart TDgraph TD" -> "flowchart TD"
        if re.match(r'(flowchart|graph)\s+(TD|TB|LR|RL|BT)', line):
            # Extract just the first valid declaration
            match = re.match(r'(flowchart|graph)\s+(TD|TB|LR|RL|BT)', line)
            if match and not diagram_type_declared:
                fixed_lines.append(f"{match.group(1)} {match.group(2)}")
                diagram_type_declared = True
            continue
        elif re.match(r'^(sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|journey)$', line, re.IGNORECASE):
            # Keep diagram type declarations, but only first one
            if not diagram_type_declared:
                fixed_lines.append(line)
                diagram_type_declared = True
            continue
        
        # Fix: Node IDs with special characters like .NET, C#, etc.
        # Example: API[Registration API (.NET)] -> API["Registration API (dotNET)"]
        # Replace problematic characters in node labels
        line = line.replace("(.NET)", "(dotNET)")
        line = line.replace(".NET", "dotNET")
        line = line.replace("C#", "CSharp")
        line = line.replace("F#", "FSharp")
        line = line.replace("Node.js", "NodeJS")
        line = line.replace("Vue.js", "VueJS")
        line = line.replace("React.js", "ReactJS")
        
        # Fix: ERD malformed entities
        # Detect ERD entity start
        if re.match(r'^\s*[A-Z_][A-Z0-9_]*\s*\{', line):
            # Entity declaration - ensure proper format
            entity_name = line.split("{")[0].strip()
            fixed_lines.append(f"    {entity_name} {{")
            in_erd_entity = True
            continue
        
        # ERD entity end
        if line == "}" and in_erd_entity:
            fixed_lines.append("    }")
            in_erd_entity = False
            continue
        
        # ERD entity attribute
        if in_erd_entity and line and not line.startswith("{") and not line.startswith("}"):
            # Entity attribute - ensure proper indentation and format
            # Format should be: type name [constraints]
            parts = line.split()
            if len(parts) >= 2:
                # Looks like a valid attribute
                fixed_lines.append(f"        {line}")
                continue
        
        # Fix: Sequence diagram issues
        # Remove "par" without proper block structure
        if line.startswith("par") and not line.endswith(":"):
            # Invalid par usage - skip it
            continue
        
        # Keep the line (possibly modified)
        if line:
            fixed_lines.append(line)
    
    result = "\n".join(fixed_lines).strip()
    
    # Ensure diagram has a type declaration
    if not diagram_type_declared:
        result = "flowchart TD\n" + result
    
    return result


def validate_and_fix_mermaid(diagram_text: str) -> Tuple[str, List[str]]:
    """
    Validate and fix Mermaid diagram with aggressive preprocessing.
    
    Args:
        diagram_text: Raw Mermaid diagram
    
    Returns:
        Tuple of (fixed_diagram, list_of_fixes_applied)
    """
    fixes_applied = []
    
    # 1. Check for markdown fences
    if "```mermaid" in diagram_text or "```" in diagram_text:
        fixes_applied.append("Removed markdown fences")
    
    # 2. Check for multiple diagram declarations
    if re.search(r'(flowchart|graph)\s+(TD|TB|LR|RL|BT).+(flowchart|graph)\s+(TD|TB|LR|RL|BT)', diagram_text):
        fixes_applied.append("Fixed multiple diagram declarations on same line")
    
    # 3. Check for invalid characters
    if any(char in diagram_text for char in [".NET", "C#", "F#", "Node.js"]):
        fixes_applied.append("Replaced special characters in node labels")
    
    # 4. Apply preprocessing
    fixed_diagram = aggressive_mermaid_preprocessing(diagram_text)
    
    # 5. Validate result
    lines = fixed_diagram.split("\n")
    valid_types = ["flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram", 
                   "erDiagram", "gantt", "pie", "journey"]
    
    if not any(lines[0].strip().startswith(t) for t in valid_types):
        fixes_applied.append("Added missing diagram type declaration")
        fixed_diagram = "flowchart TD\n" + fixed_diagram
    
    return fixed_diagram, fixes_applied


# Global instance
_preprocessor_enabled = True

def enable_preprocessing():
    """Enable aggressive Mermaid preprocessing globally"""
    global _preprocessor_enabled
    _preprocessor_enabled = True

def disable_preprocessing():
    """Disable aggressive Mermaid preprocessing"""
    global _preprocessor_enabled
    _preprocessor_enabled = False

def preprocess_if_enabled(diagram_text: str) -> str:
    """Apply preprocessing only if enabled"""
    if _preprocessor_enabled:
        return aggressive_mermaid_preprocessing(diagram_text)
    return diagram_text

