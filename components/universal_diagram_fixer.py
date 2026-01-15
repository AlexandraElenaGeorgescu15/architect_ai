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
        'journey': 'journey',
        'gitgraph': 'gitGraph',
        'mindmap': 'mindmap',
        'timeline': 'timeline'
    }
    
    def __init__(self):
        self.current_type = None
        self.errors_fixed = []
    
    def fix_diagram(self, content: str, max_passes: int = 3) -> Tuple[str, List[str]]:
        """
        Fix any Mermaid diagram syntax issues with MULTIPLE validation passes.
        
        Args:
            content: Raw Mermaid diagram content (possibly with errors)
            max_passes: Maximum number of correction passes (default: 3 for aggressive fixing)
            
        Returns:
            Tuple of (fixed_content, list_of_fixes_applied)
        """
        self.errors_fixed = []
        previous_content = None
        
        # MULTIPLE PASSES for stubborn syntax errors
        for pass_num in range(max_passes):
            if content == previous_content:
                # No changes in this pass, we're done
                if pass_num > 0:
                    self.errors_fixed.append(f"Converged after {pass_num + 1} passes")
                break
            
            previous_content = content
            pass_fixes = []
            
            # Step 1: Clean markdown wrappers
            content = self._remove_markdown_blocks(content)
            
            # Step 2: Detect diagram type
            diagram_type = self._detect_diagram_type(content)
            self.current_type = diagram_type
            
            if not diagram_type:
                pass_fixes.append(f"[Pass {pass_num + 1}] Could not detect diagram type - added default flowchart header")
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
            elif diagram_type == 'gitgraph':
                content = self._fix_gitgraph_diagram(content)
            elif diagram_type == 'mindmap':
                content = self._fix_mindmap_diagram(content)
            elif diagram_type == 'timeline':
                content = self._fix_timeline_diagram(content)
            
            # Step 4: General cleanup
            content = self._general_cleanup(content)
            
            # Collect fixes from this pass
            if pass_num == max_passes - 1 or content != previous_content:
                pass_fixes.extend(self.errors_fixed)
            self.errors_fixed = pass_fixes
        
        if len(self.errors_fixed) > 0:
            print(f"[MERMAID_FIX] Applied {len(self.errors_fixed)} fixes across {min(pass_num + 1, max_passes)} passes")
        
        return content, self.errors_fixed
    
    def _remove_markdown_blocks(self, content: str) -> str:
        """Remove markdown code blocks (```mermaid, ```html, etc.) and RAG context pollution"""
        import re
        content = content.strip()
        
        # Remove ALL common LLM artifacts and explanatory text patterns
        explanatory_patterns = [
            r'Here is the corrected.*?:',
            r'Here\'s the.*?:',
            r'I\'ve corrected.*?:',
            r'The corrected.*?:',
            r'This diagram shows.*?:',
            r'This is the.*?:',
            r'Here is.*?:',
            r'Here\'s.*?:',
            r'The following.*?:',
            r'Below is.*?:',
            r'Above is.*?:',
            r'Generated.*?:',
            r'Output.*?:',
            r'Result.*?:',
            r'Corrected.*?:',
            r'Fixed.*?:',
            r'Updated.*?:',
            r'Here you go.*?:',
            r'As requested.*?:',
        ]
        for pattern in explanatory_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
        
        # Remove numbered explanations: "1. The generated...", "2. Otherwise...", etc.
        content = re.sub(r'^\d+\.\s+[A-Z][^:]*:.*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
        content = re.sub(r'^\d+\.\s+[A-Z].*$', '', content, flags=re.MULTILINE)
        
        # Remove ALL stray HTML closing tags (anywhere in content)
        html_tag_patterns = [
            r'</div>\s*',
            r'</p>\s*',
            r'</span>\s*',
            r'</body>\s*',
            r'</html>\s*',
            r'</head>\s*',
            r'</script>\s*',
            r'</style>\s*',
            r'</\w+>',  # Any closing tag
        ]
        for pattern in html_tag_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
        
        # Remove HTML opening tags that shouldn't be in diagrams
        content = re.sub(r'<div[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'<p[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'<span[^>]*>', '', content, flags=re.IGNORECASE)
        
        # Remove duplicate content (common with local models)
        # Split by diagram declaration and keep only first occurrence
        lines = content.split('\n')
        seen_declarations = set()
        cleaned_lines = []
        skip_until_next_diagram = False
        
        for line in lines:
            line_lower = line.strip().lower()
            # Check if this is a diagram declaration
            if any(line_lower.startswith(dt) for dt in ['erdiagram', 'flowchart', 'graph', 'sequencediagram', 'classdiagram', 'statediagram']):
                if line in seen_declarations:
                    # Duplicate found, skip everything after this
                    skip_until_next_diagram = True
                    self.errors_fixed.append(f"Removed duplicate diagram section starting with: {line}")
                    break
                seen_declarations.add(line)
                skip_until_next_diagram = False
            
            if not skip_until_next_diagram:
                cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines)
        
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
        
        # Remove ALL markdown code blocks (```mermaid, ```, etc.)
        content = re.sub(r'```[\w\-]*\s*\n?', '', content, flags=re.MULTILINE)
        content = re.sub(r'\n?```\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'```', '', content)
        
        return content.strip()
    
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
        """Fix ERD diagram syntax with comprehensive error handling"""
        import re
        lines = content.strip().split('\n')
        fixed_lines = []
        entities = {}
        relationships = []
        current_entity = None
        current_entity_fields = []
        
        # Pre-process: Fix common ERD syntax errors
        processed_lines = []
        for line in lines:
            original_line = line
            line = line.strip()
            
            if not line or line.startswith('```'):
                continue
            
            # Fix: Convert classDiagram-style syntax to ERD
            # "class USER { - id (pk) }" -> "USER { int id PK }"
            if line.lower().startswith('class ') and '{' not in line:
                line = line.replace('class ', '').replace('CLASS ', '')
                self.errors_fixed.append("Converted class declaration to ERD entity")
            
            # Fix: Convert invalid relationship markers
            # "USER -> ORDER" should be "USER ||--o{ ORDER"
            if ' -> ' in line and '||' not in line and '{' not in line:
                parts = line.split(' -> ')
                if len(parts) == 2:
                    line = f'{parts[0].strip()} ||--o{{ {parts[1].strip()} : has'
                    self.errors_fixed.append("Converted -> to ERD relationship")
            
            # Fix: ERD entities can't have quoted names
            if '{' in line and '"' in line:
                # Remove quotes from entity names
                line = re.sub(r'"(\w+)"(\s*\{)', r'\1\2', line)
                self.errors_fixed.append("Removed quotes from entity name")
            
            # Fix: Field type must come first in ERD
            # "id int PK" should be "int id PK"
            field_match = re.match(r'^(\s*)(\w+)\s+(int|string|varchar|text|date|datetime|boolean|decimal|float|timestamp)\s*(PK|FK)?', line)
            if field_match:
                indent = field_match.group(1)
                field_name = field_match.group(2)
                field_type = field_match.group(3)
                key = field_match.group(4) or ''
                line = f'{indent}{field_type} {field_name} {key}'.strip()
                self.errors_fixed.append(f"Reordered field definition: {field_name}")
            
            # Fix: Invalid characters in entity/field names
            if '{' in line or any(rel in line for rel in ['||', '}|', '|{', 'o{']):
                # Clean up entity names (before {)
                if '{' in line and '||' not in line:
                    parts = line.split('{')
                    entity_part = re.sub(r'[^\w\s]', '', parts[0]).strip()
                    if entity_part:
                        line = f'{entity_part} {{{parts[1]}' if len(parts) > 1 else f'{entity_part} {{'
            
            processed_lines.append(line)
        
        # Main processing loop
        for line in processed_lines:
            line = line.strip()
            
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
                # Clean entity name
                entity_name = re.sub(r'[^\w]', '', entity_name)
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
            
            # Detect field definition (with type)
            if current_entity:
                # Try to parse as field: "type name KEY" or just "type name"
                field_match = re.match(r'^(int|string|varchar|text|date|datetime|boolean|decimal|float|timestamp|uuid|bigint)\s+(\w+)\s*(PK|FK)?', line, re.IGNORECASE)
                if field_match:
                    field_type = field_match.group(1).lower()
                    field_name = field_match.group(2)
                    key = f' {field_match.group(3)}' if field_match.group(3) else ''
                    current_entity_fields.append(f'        {field_type} {field_name}{key}')
                    continue
                # Also accept lines that look like fields (have underscores, typical field names)
                elif re.match(r'^\w+(_\w+)*$', line):
                    # Guess field type based on name
                    field_type = 'string'
                    if line.endswith('_id') or line == 'id':
                        field_type = 'int'
                    elif 'date' in line.lower() or 'time' in line.lower():
                        field_type = 'datetime'
                    elif line.startswith('is_') or line.startswith('has_'):
                        field_type = 'boolean'
                    
                    key = ' PK' if line == 'id' else (' FK' if line.endswith('_id') else '')
                    current_entity_fields.append(f'        {field_type} {line}{key}')
                    self.errors_fixed.append(f"Inferred type for field: {line}")
                    continue
            
            # Detect relationship with more flexible matching
            relationship_patterns = [
                r'(\w+)\s*([\|\}o\{]+--[\|\}o\{]+)\s*(\w+)\s*:\s*(.+)',  # Full: A ||--o{ B : label
                r'(\w+)\s*([\|\}o\{]+--[\|\}o\{]+)\s*(\w+)',  # Without label: A ||--o{ B
            ]
            
            is_relationship = False
            for pattern in relationship_patterns:
                rel_match = re.match(pattern, line)
                if rel_match:
                    entity1 = rel_match.group(1)
                    rel_type = rel_match.group(2)
                    entity2 = rel_match.group(3)
                    label = rel_match.group(4) if len(rel_match.groups()) > 3 else 'relates'
                    relationships.append(f'    {entity1} {rel_type} {entity2} : {label}')
                    is_relationship = True
                    break
            
            if is_relationship:
                continue
        
        # Handle case where entity wasn't closed
        if current_entity and current_entity_fields:
            entities[current_entity] = current_entity_fields
            self.errors_fixed.append(f"Auto-closed entity: {current_entity}")
        
        # Build fixed ERD
        if not entities and not relationships:
            self.errors_fixed.append("ERD appears empty - added sample structure")
            return """erDiagram
    ENTITY {
        int id PK
        string name
    }"""
        
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
        import re
        lines = content.strip().split('\n')
        fixed_lines = []
        seen_header = False
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and markdown blocks
            if not line or line.startswith('```'):
                continue
            
            # Skip duplicate flowchart/graph declarations
            line_lower = line.lower()
            if ('flowchart' in line_lower or 'graph' in line_lower):
                if seen_header:
                    self.errors_fixed.append(f"Removed duplicate header: {line}")
                    continue
                else:
                    fixed_lines.append(line)
                    seen_header = True
                    continue
            
            # Add header if missing
            if not seen_header:
                fixed_lines.append('flowchart TD')
                seen_header = True
                self.errors_fixed.append("Added missing flowchart TD header")
            
            # Fix common syntax issues
            # Issue 1: Fix INVALID arrow syntax -->|label|> should be -->|label|
            # This is a CRITICAL fix - the |> at the end is invalid Mermaid syntax
            if '|>' in line:
                original_line = line
                line = re.sub(r'\|>', '', line)  # Remove all |> occurrences
                if line != original_line:
                    self.errors_fixed.append("Fixed invalid arrow syntax (removed trailing |>)")
            
            # Issue 1b: Fix reversed |> arrow to proper --> syntax
            # A|>B should become A --> B  
            line = re.sub(r'(\w+)\s*\|>\s*(\w+)', r'\1 --> \2', line)
            
            # Issue 2: Missing quotes in labels with spaces
            if '[' in line and ']' in line:
                match = re.search(r'\[([^\]]+)\]', line)
                if match:
                    label = match.group(1)
                    if ' ' in label and not (label.startswith('"') or label.startswith("'")):
                        line = line.replace(f'[{label}]', f'["{label}"]')
                        self.errors_fixed.append("Added quotes to labels with spaces")
            
            # Issue 2b: Fix unbalanced quotes in labels
            if '[' in line and ']' in line:
                # Count quotes inside brackets
                bracket_content = re.search(r'\[([^\]]*)\]', line)
                if bracket_content:
                    inside = bracket_content.group(1)
                    quote_count = inside.count('"')
                    if quote_count % 2 != 0:
                        # Unbalanced quotes - remove them all
                        fixed_inside = inside.replace('"', '')
                        line = line.replace(f'[{inside}]', f'[{fixed_inside}]')
                        self.errors_fixed.append("Fixed unbalanced quotes in label")
            
            # Issue 3: Fix arrow syntax
            line = re.sub(r'--+>', '-->', line)  # Multiple dashes to standard arrow
            line = re.sub(r'==+>', '==>', line)  # Bold arrows
            
            # Issue 3b: Fix malformed arrows like -.- or -..- to -.->
            line = re.sub(r'-\.-(?!>)', '-.->', line)
            
            # Issue 3c: Fix double arrow heads --> --> to single -->
            line = re.sub(r'-->\s*-->', '-->', line)
            
            # Issue 4: Fix node definition with missing closing bracket
            # A[Start -> B should become A[Start] --> B
            if re.search(r'\[[^\]]*$', line):
                # Line has unclosed bracket - try to fix
                line = re.sub(r'\[([^\]]*?)(\s*-+>)', r'[\1]\2', line)
                self.errors_fixed.append("Fixed unclosed bracket in node definition")
            
            # Issue 4: Remove explanatory text lines (comprehensive patterns)
            explanatory_line_patterns = [
                r'^[A-Z][a-z].*:$',  # "Start:", "Here is:", etc. (ending with colon)
                r'^This diagram.*',  # "This diagram shows..."
                r'^The following.*',  # "The following..."
                r'^Below is.*',  # "Below is..."
                r'^Above is.*',  # "Above is..."
                r'^Generated.*',  # "Generated..."
                r'^Output.*',  # "Output..."
                r'^Result.*',  # "Result..."
                r'^Corrected.*',  # "Corrected..."
                r'^Fixed.*',  # "Fixed..."
                r'^Updated.*',  # "Updated..."
                r'^\d+\.\s+[A-Z]',  # "1. The generated...", "2. Otherwise..."
                r'^Let me know.*',  # "Let me know if..."
                r'^Hope this helps.*',  # "Hope this helps!"
                r'^Feel free.*',  # "Feel free to..."
                r'^I\'ve made.*',  # "I've made the following..."
                r'^Here\'s.*',  # "Here's the..."
                r'^Here are.*',  # "Here are the..."
                r'^Here is.*',  # "Here is the..."
            ]
            is_explanatory = any(re.match(pattern, line, re.IGNORECASE) for pattern in explanatory_line_patterns)
            if is_explanatory:
                self.errors_fixed.append(f"Removed explanatory text: {line[:50]}...")
                continue
            
            # Issue 5: Fix node IDs (remove special characters)
            if '-->' in line or '---' in line or '-.>' in line or '[' in line:
                if not line.startswith('    '):
                    line = '    ' + line
                fixed_lines.append(line)
            elif line and not line.startswith(('flowchart', 'graph', 'classDef', 'class ')):
                # Include classDef and class statements without indentation check
                if line.startswith('classDef') or line.startswith('class '):
                    if not line.startswith('    '):
                        line = '    ' + line
                    fixed_lines.append(line)
                elif not line.startswith('    '):
                    line = '    ' + line
                    fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
        
        if len(fixed_lines) <= 1:
            self.errors_fixed.append("Flowchart appears empty - added sample node")
            fixed_lines.append('    A[Start] --> B[End]')
        
        return '\n'.join(fixed_lines)
    
    def _fix_sequence_diagram(self, content: str) -> str:
        """Fix sequence diagram syntax with comprehensive error handling"""
        import re
        lines = content.strip().split('\n')
        fixed_lines = []
        participants = set()
        
        # Ensure header
        if not lines[0].strip().lower().startswith('sequencediagram'):
            fixed_lines.append('sequenceDiagram')
            self.errors_fixed.append("Added missing sequenceDiagram header")
        else:
            fixed_lines.append('sequenceDiagram')
        
        # Pre-process to extract participants from arrows
        for line in lines:
            # Match arrow patterns to find participants
            arrow_match = re.search(r'(\w+)\s*(->>|-->>|->|-->)\s*(\w+)', line)
            if arrow_match:
                participants.add(arrow_match.group(1))
                participants.add(arrow_match.group(3))
        
        # Process interactions
        for line in lines[1:] if fixed_lines else lines:
            original_line = line
            line = line.strip()
            
            if not line or line.startswith('```') or line.lower().startswith('sequencediagram'):
                continue
            
            # Fix: Invalid arrow syntax
            # "A -> B" should be "A->>B" or "A->>B: message"
            if ' -> ' in line and '->>' not in line and '-->' not in line:
                line = line.replace(' -> ', '->>').replace('->> ', '->>')
                self.errors_fixed.append("Fixed arrow syntax: -> to ->>")
            
            # Fix: Missing colon in message
            # "A->>B Hello" should be "A->>B: Hello"
            arrow_without_colon = re.match(r'^(\w+\s*->>-?\s*\w+)\s+([^:].+)$', line)
            if arrow_without_colon:
                line = f'{arrow_without_colon.group(1)}: {arrow_without_colon.group(2)}'
                self.errors_fixed.append("Added missing colon after arrow")
            
            # Fix: Participant with unquoted alias containing spaces
            # "participant A as User Service" -> "participant A as UserService"
            participant_alias_match = re.match(r'^participant\s+(\w+)\s+as\s+(.+)$', line, re.IGNORECASE)
            if participant_alias_match:
                alias = participant_alias_match.group(2)
                if ' ' in alias and not (alias.startswith('"') or alias.startswith("'")):
                    # Wrap in quotes
                    line = f'participant {participant_alias_match.group(1)} as "{alias}"'
                    self.errors_fixed.append("Quoted participant alias with spaces")
            
            # Fix: Actor with spaces in name
            actor_match = re.match(r'^actor\s+(.+)$', line, re.IGNORECASE)
            if actor_match:
                name = actor_match.group(1).strip()
                if ' ' in name and not (name.startswith('"') or name.startswith("'")):
                    line = f'actor "{name}"'
                    self.errors_fixed.append("Quoted actor name with spaces")
            
            # Fix: Note syntax
            # "Note: some text" -> "Note right of A: some text"
            if line.lower().startswith('note:') or line.lower().startswith('note '):
                if 'right of' not in line.lower() and 'left of' not in line.lower() and 'over' not in line.lower():
                    # Need to add positioning - use first participant
                    if participants:
                        first_participant = sorted(participants)[0]
                        note_text = re.sub(r'^note:?\s*', '', line, flags=re.IGNORECASE)
                        line = f'Note right of {first_participant}: {note_text}'
                        self.errors_fixed.append("Added note positioning")
            
            # Fix: Activate/Deactivate without participant
            if line.lower().startswith('activate') or line.lower().startswith('deactivate'):
                parts = line.split()
                if len(parts) == 1:
                    # No participant specified - skip or use first one
                    if participants:
                        line = f'{parts[0]} {sorted(participants)[0]}'
                        self.errors_fixed.append(f"Added participant to {parts[0]}")
            
            # Fix: Loop/Alt/Opt without proper label
            for keyword in ['loop', 'alt', 'opt', 'par']:
                if line.lower().startswith(keyword) and ':' not in line and len(line.split()) == 1:
                    line = f'{keyword} [condition]'
                    self.errors_fixed.append(f"Added placeholder condition to {keyword}")
            
            # Add participant declarations
            if line.lower().startswith('participant') or line.lower().startswith('actor'):
                fixed_lines.append('    ' + line)
            # Arrows
            elif '->' in line or '-->>' in line or '-->' in line:
                fixed_lines.append('    ' + line)
            # Notes
            elif line.lower().startswith('note'):
                fixed_lines.append('    ' + line)
            # Control flow
            elif any(kw in line.lower() for kw in ['loop', 'alt', 'opt', 'par', 'end', 'activate', 'deactivate', 'rect', 'else']):
                fixed_lines.append('    ' + line)
            # Unknown line
            else:
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
        
        # Collect defined class names for validation
        defined_classes = set()
        
        # First pass: collect class definitions
        for line in lines:
            line_stripped = line.strip()
            # Match "class ClassName" or "class ClassName {"
            class_match = re.match(r'^class\s+(\w+)', line_stripped)
            if class_match:
                defined_classes.add(class_match.group(1))
        
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
            
            # Fix invalid relationship syntax
            original_line = line
            
            # Fix mixed inheritance/composition: <|--* should be <|-- or *--
            line = re.sub(r'<\|--\*', '<|--', line)
            line = re.sub(r'\*--<\|', '<|--', line)
            
            # Fix triple arrows: *---> should be *-->
            line = re.sub(r'\*---+>', '*-->', line)
            line = re.sub(r'o---+>', 'o-->', line)
            line = re.sub(r'---+>', '-->', line)
            
            # Fix reversed triple arrows
            line = re.sub(r'<---+\*', '<--*', line)
            line = re.sub(r'<---+o', '<--o', line)
            line = re.sub(r'<---+', '<--', line)
            
            # Fix invalid dependency arrows: ..-> should be ..>
            line = re.sub(r'\.\.+->+', '..>', line)
            line = re.sub(r'<-+\.\.+', '<..', line)
            
            # Fix missing spaces around relationships
            # But be careful not to break valid syntax
            
            if original_line != line:
                self.errors_fixed.append(f"Fixed invalid class relationship syntax: {original_line} -> {line}")
            
            # Class definitions
            if line.startswith('class ') or ('{' in line and '}' not in line):
                fixed_lines.append('    ' + line)
            # Class body content (inside braces)
            elif line.startswith('-') or line.startswith('+') or line.startswith('#') or line.startswith('}'):
                fixed_lines.append('    ' + line)
            # Relationships - check if both classes exist, but still include invalid ones (they might render)
            elif any(rel in line for rel in ['<|--', '*--', 'o--', '-->', '<..', '..>', '--', '<|', '|>']):
                fixed_lines.append('    ' + line)
            # classDef statements
            elif line.startswith('classDef'):
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
        """Fix user journey diagram syntax."""
        lines = content.strip().split('\n')
        fixed_lines = ['journey']
        
        for line in lines[1:]:
            line = line.strip()
            if not line or line.startswith('```') or line.lower() == 'journey':
                continue
            fixed_lines.append('    ' + line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_gitgraph_diagram(self, content: str) -> str:
        """Fix Git Graph diagram syntax issues, especially label syntax."""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Fix invalid label syntax: A[label="text"] -> just remove the invalid assignment
            # Git graph commits don't use label="text" syntax like flowcharts
            if re.match(r'^\s*[A-Z]\[.*label=.*\]', line):
                # This is invalid - Git Graph uses id: "label" or just commit statements
                # Remove these standalone label assignments
                self.errors_fixed.append(f"Removed invalid Git Graph label assignment: {line_stripped[:50]}")
                continue
            
            # Fix missing equals in label syntax: K[label"text"] -> skip entirely
            if re.search(r'\[label"[^"]+"\]', line):
                self.errors_fixed.append(f"Removed invalid Git Graph label (missing =): {line_stripped[:50]}")
                continue
            
            # Proper Git Graph syntax examples:
            # commit id: \"Initial Commit\"
            # branch develop
            # checkout develop
            # commit id: \"Feature A\"
            # merge develop
            
            cleaned_lines.append(line)
        
        return '\\n'.join(cleaned_lines)
    
    def _fix_mindmap_diagram(self, content: str) -> str:
        """Fix Mindmap diagram syntax issues."""
        # Mindmap is relatively simple, just ensure proper indentation
        return content
    
    def _fix_timeline_diagram(self, content: str) -> str:
        """Fix Timeline diagram syntax issues."""
        # Timeline uses section-based syntax, minimal fixes needed
        return content
    
    def _general_cleanup(self, content: str) -> str:
        """Apply general cleanup to all diagram types"""
        import re
        lines = content.split('\n')
        cleaned_lines = []
        
        # COMPREHENSIVE patterns for AI explanatory text that should be removed
        # These patterns match at line start
        explanatory_patterns = [
            # Common AI conversation phrases
            r'^Let me know.*',
            r'^Hope this helps.*',
            r'^Feel free.*',
            r'^I\'ve made.*',
            r'^I\'ve updated.*',
            r'^I\'ve improved.*',
            r'^I\'ve fixed.*',
            r'^I\'ve added.*',
            r'^I\'ve corrected.*',
            r'^Here\'s the.*',
            r'^Here are the.*',
            r'^Here is the.*',
            r'^Here you go.*',
            r'^This should.*',
            r'^This diagram.*',
            r'^This shows.*',
            r'^The diagram.*',
            r'^The above.*',
            r'^Above is.*',
            r'^Below is.*',
            r'^Please let me know.*',
            r'^If you need.*',
            r'^If you have.*',
            r'^If you\'d like.*',
            r'^As requested.*',
            r'^As you can see.*',
            # Markdown formatting
            r'^---+$',  # Markdown horizontal rule
            r'^#+\s+.*',  # Markdown headers
            r'^\*\*.*\*\*:?$',  # Bold text lines
            # Numbered explanations
            r'^\d+\.\s+[A-Z].*',  # "1. The diagram..."
            # Explanation markers
            r'^Explanation:.*',
            r'^Note:.*',
            r'^Notes?:.*',
            r'^Key (changes|improvements|features|points):.*',
            r'^Changes (made|include):.*',
            r'^Improvements (made|include):.*',
            r'^Summary:.*',
            r'^Output:.*',
            r'^Result:.*',
        ]
        
        # Also detect where diagram content ENDS (for truncation)
        # These patterns indicate end of diagram, start of explanation
        end_of_diagram_patterns = [
            r'^Let me know',
            r'^Hope this',
            r'^Feel free',
            r'^I\'ve (made|updated|improved|fixed|added)',
            r'^This (diagram|should|shows)',
            r'^The (diagram|above)',
            r'^Explanation:',
            r'^\*\*Explanation',
            r'^\*\*Note',
            r'^\*\*Key',
            r'^---',
            r'^Key improvements',
            r'^Changes made',
            r'^Improvements:',
        ]
        
        diagram_ended = False
        
        for line in lines:
            # Remove trailing whitespace
            line = line.rstrip()
            
            # Skip completely empty lines at start/end
            if not cleaned_lines and not line.strip():
                continue
            
            line_stripped = line.strip()
            
            # Check if we've hit end-of-diagram marker
            if not diagram_ended:
                for pattern in end_of_diagram_patterns:
                    if re.match(pattern, line_stripped, re.IGNORECASE):
                        diagram_ended = True
                        self.errors_fixed.append(f"Truncated at explanatory text: {line_stripped[:30]}...")
                        break
            
            if diagram_ended:
                continue  # Skip all lines after diagram ends
            
            # Check if line is explanatory AI text
            is_explanatory = any(re.match(pattern, line_stripped, re.IGNORECASE) for pattern in explanatory_patterns)
            if is_explanatory:
                self.errors_fixed.append(f"Removed AI text: {line_stripped[:40]}...")
                continue
            
            cleaned_lines.append(line)
        
        # Remove trailing empty lines
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()
        
        # Final pass: remove trailing AI text even if it's multi-line
        if cleaned_lines:
            # Check last few lines for AI text
            lines_to_check = min(5, len(cleaned_lines))
            for _ in range(lines_to_check):
                if not cleaned_lines:
                    break
                last_line = cleaned_lines[-1].strip()
                should_remove = False
                
                for pattern in explanatory_patterns:
                    if re.match(pattern, last_line, re.IGNORECASE):
                        should_remove = True
                        break
                
                # Also check for lines that look like explanations (sentence-like)
                if not should_remove and last_line:
                    # Lines ending with ! or ? that aren't part of diagram
                    if last_line.endswith('!') or last_line.endswith('?'):
                        if not any(kw in last_line for kw in ['-->',  '---', '|||', '{', '}']):
                            should_remove = True
                
                if should_remove:
                    cleaned_lines.pop()
                    self.errors_fixed.append(f"Removed trailing AI text")
                else:
                    break  # Stop if we find a valid diagram line
        
        return '\n'.join(cleaned_lines)


# Global instance
universal_diagram_fixer = UniversalDiagramFixer()


def fix_any_diagram(content: str, max_passes: int = 3) -> Tuple[str, List[str]]:
    """
    Convenience function to fix any Mermaid diagram with AGGRESSIVE multi-pass correction.
    
    Args:
        content: Raw diagram content
        max_passes: Number of correction passes (default: 3 for stubborn syntax errors)
        
    Returns:
        Tuple of (fixed_content, list_of_fixes_applied)
    """
    return universal_diagram_fixer.fix_diagram(content, max_passes=max_passes)

