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
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize the diagram fixer.
        
        Args:
            strict_mode: If True, aggressively removes invalid lines.
                        If False, tries to preserve more content with minimal fixes.
        """
        self.current_type = None
        self.errors_fixed = []
        self.strict_mode = strict_mode
    
    def fix_diagram(self, content: str, max_passes: int = 3, lenient: bool = False) -> Tuple[str, List[str]]:
        """
        Fix any Mermaid diagram syntax issues with MULTIPLE validation passes.
        
        Args:
            content: Raw Mermaid diagram content (possibly with errors)
            max_passes: Maximum number of correction passes (default: 3 for aggressive fixing)
            lenient: If True, apply minimal fixes only (less aggressive)
            
        Returns:
            Tuple of (fixed_content, list_of_fixes_applied)
        """
        self.errors_fixed = []
        
        # LENIENT MODE: Apply minimal fixes only
        if lenient:
            return self._fix_diagram_lenient(content)
        
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
    
    def _fix_diagram_lenient(self, content: str) -> Tuple[str, List[str]]:
        """
        Apply MINIMAL fixes to a diagram - preserves most content.
        
        Only fixes critical issues:
        - Removes markdown code blocks
        - Removes AI preambles
        - Fixes |> arrow syntax
        - Removes lines with 'depend' for Gantt
        - Fixes very basic syntax issues
        
        Args:
            content: Raw diagram content
            
        Returns:
            Tuple of (fixed_content, list_of_fixes)
        """
        import re
        fixes = []
        original_content = content
        
        # Step 1: Remove markdown blocks
        content = re.sub(r'^```(?:mermaid)?\s*\n?', '', content, flags=re.MULTILINE)
        content = re.sub(r'\n?```\s*$', '', content)
        content = content.strip()
        if content != original_content:
            fixes.append("Removed markdown code blocks")
        
        # Step 2: Remove AI preambles (single line at start)
        ai_preambles = [
            r'^Here(?:\'s| is).*?:\s*\n',
            r'^Sure(?:,| thing)?.*?:\s*\n',
            r'^Of course.*?:\s*\n',
            r'^I\'ve.*?:\s*\n',
            r'^The (?:corrected|fixed).*?:\s*\n',
        ]
        for pattern in ai_preambles:
            before = content
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
            if content != before:
                fixes.append("Removed AI preamble")
                break
        
        # Step 3: Remove trailing AI explanations
        explanation_patterns = [
            r'\n\n+\*{2}(?:Explanation|Note|Key).*$',
            r'\n\n+(?:Explanation|Note):.*$',
        ]
        for pattern in explanation_patterns:
            before = content
            content = re.sub(pattern, '', content, flags=re.DOTALL)
            if content != before:
                fixes.append("Removed trailing explanation")
                break
        
        # Step 4: Fix |> arrow syntax (very common error)
        if '|>' in content:
            content = content.replace('|>', '>')
            fixes.append("Fixed |> arrow syntax")
        
        # Step 5: For Gantt diagrams, remove "depend" lines
        if 'gantt' in content.lower():
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                if 'depend' in line.lower() and not line.strip().lower().startswith('section'):
                    fixes.append("Removed invalid 'depend' line")
                    continue
                new_lines.append(line)
            content = '\n'.join(new_lines)
        
        # Step 6: Fix -.- to -.- (dotted arrows sometimes malformed)
        content = re.sub(r'-\.-+', '-.-', content)
        
        # Step 7: Ensure diagram type declaration exists
        diagram_types = [
            'erdiagram', 'flowchart', 'graph', 'sequencediagram',
            'classdiagram', 'statediagram', 'gantt', 'pie', 'journey',
            'gitgraph', 'mindmap', 'timeline'
        ]
        first_line = content.split('\n')[0].strip().lower() if content else ''
        has_type = any(first_line.startswith(dt) for dt in diagram_types)
        
        if not has_type:
            # Try to detect from content
            if '||' in content or '}o' in content or 'o{' in content:
                content = 'erDiagram\n' + content
                fixes.append("Added erDiagram header")
            elif '-->' in content or '---' in content:
                content = 'flowchart TD\n' + content
                fixes.append("Added flowchart TD header")
            elif '->>' in content or 'participant' in content.lower():
                content = 'sequenceDiagram\n' + content
                fixes.append("Added sequenceDiagram header")
        
        self.errors_fixed = fixes
        return content.strip(), fixes
    
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
        """Fix ERD diagram syntax with STRICT validation.
        
        Valid ERD syntax:
        - erDiagram (header)
        - EntityA ||--o{ EntityB : relationship
        - EntityA { type field_name KEY }
        
        Relationship symbols:
        - ||--|| : one to one
        - ||--o{ : one to many  
        - }o--o{ : many to many
        - ||--o| : one to zero or one
        
        REMOVES any line that doesn't match valid patterns.
        """
        import re
        lines = content.strip().split('\n')
        fixed_lines = ['erDiagram']
        entities = {}
        relationships = []
        current_entity = None
        current_entity_fields = []
        seen_header = False
        
        # Valid ERD field types
        valid_field_types = [
            'int', 'integer', 'bigint', 'smallint', 'tinyint',
            'string', 'varchar', 'text', 'char', 'nvarchar',
            'date', 'datetime', 'timestamp', 'time',
            'boolean', 'bool', 'bit',
            'decimal', 'float', 'double', 'real', 'numeric',
            'uuid', 'guid', 'binary', 'blob', 'json', 'enum'
        ]
        
        # Valid relationship patterns
        relationship_regex = re.compile(
            r'^(\w+)\s*([\|\}o\{]+--[\|\}o\{]+)\s*(\w+)\s*(?::\s*(.+))?$'
        )
        
        for line in lines:
            original_line = line
            line_stripped = line.strip()
            
            # Skip empty, markdown
            if not line_stripped or line_stripped.startswith('```'):
                continue
            
            # Skip duplicate headers
            if line_stripped.lower() == 'erdiagram':
                if seen_header:
                    continue
                seen_header = True
                continue
            
            # REJECT AI explanatory text
            ai_text_patterns = [
                r'^(This|The|Here|Below|Above|I\'ve|Let me|Hope|Feel free|As requested|Sure|Certainly|Of course)',
                r'^[A-Z][a-z]+.*:\s*$',
                r'^\d+\.\s+[A-Z]',
            ]
            is_ai_junk = any(re.match(p, line_stripped, re.IGNORECASE) for p in ai_text_patterns)
            if is_ai_junk:
                self.errors_fixed.append(f"Removed AI text: {line_stripped[:40]}...")
                continue
            
            # Fix: Convert " -> " to ERD relationship (common AI mistake)
            if ' -> ' in line_stripped and '||' not in line_stripped and '{' not in line_stripped:
                parts = line_stripped.split(' -> ')
                if len(parts) == 2:
                    line_stripped = f'{parts[0].strip()} ||--o{{ {parts[1].strip()} : has'
                    self.errors_fixed.append("Converted -> to ERD relationship")
            
            # Handle entity definition end
            if line_stripped == '}' and current_entity:
                entities[current_entity] = current_entity_fields
                current_entity = None
                current_entity_fields = []
                continue
            
            # Handle entity definition start
            entity_start = re.match(r'^(\w+)\s*\{$', line_stripped)
            if entity_start:
                current_entity = entity_start.group(1)
                current_entity_fields = []
                continue
            
            # Handle inline entity definition: ENTITY { field... }
            inline_entity = re.match(r'^(\w+)\s*\{(.+)\}$', line_stripped)
            if inline_entity:
                entity_name = inline_entity.group(1)
                field_content = inline_entity.group(2).strip()
                # Parse fields
                fields = []
                for field_def in field_content.split(','):
                    field_def = field_def.strip()
                    if field_def:
                        fields.append(f'        {field_def}')
                if fields:
                    entities[entity_name] = fields
                continue
            
            # Handle field definitions inside entity
            if current_entity:
                # Try to parse as field: "type name KEY"
                field_match = re.match(
                    r'^(' + '|'.join(valid_field_types) + r')\s+(\w+)\s*(PK|FK|UK)?',
                    line_stripped, re.IGNORECASE
                )
                if field_match:
                    field_type = field_match.group(1).lower()
                    field_name = field_match.group(2)
                    key = f' {field_match.group(3).upper()}' if field_match.group(3) else ''
                    current_entity_fields.append(f'        {field_type} {field_name}{key}')
                    continue
                
                # Try reversed order: "name type KEY" -> fix to "type name KEY"
                reversed_match = re.match(
                    r'^(\w+)\s+(' + '|'.join(valid_field_types) + r')\s*(PK|FK|UK)?',
                    line_stripped, re.IGNORECASE
                )
                if reversed_match:
                    field_name = reversed_match.group(1)
                    field_type = reversed_match.group(2).lower()
                    key = f' {reversed_match.group(3).upper()}' if reversed_match.group(3) else ''
                    current_entity_fields.append(f'        {field_type} {field_name}{key}')
                    self.errors_fixed.append(f"Fixed field order: {line_stripped[:30]}...")
                    continue
                
                # Accept simple field names and infer types
                if re.match(r'^\w+(_\w+)*$', line_stripped):
                    field_type = 'string'
                    key = ''
                    if line_stripped.endswith('_id') or line_stripped == 'id':
                        field_type = 'int'
                        key = ' PK' if line_stripped == 'id' else ' FK'
                    elif 'date' in line_stripped.lower() or 'time' in line_stripped.lower():
                        field_type = 'datetime'
                    elif line_stripped.startswith('is_') or line_stripped.startswith('has_'):
                        field_type = 'boolean'
                    current_entity_fields.append(f'        {field_type} {line_stripped}{key}')
                    continue
                
                # Reject invalid field line
                self.errors_fixed.append(f"Removed invalid field: {line_stripped[:40]}...")
                continue
            
            # Handle relationships
            rel_match = relationship_regex.match(line_stripped)
            if rel_match:
                entity1 = rel_match.group(1)
                rel_type = rel_match.group(2)
                entity2 = rel_match.group(3)
                label = rel_match.group(4) if rel_match.group(4) else 'relates'
                relationships.append(f'    {entity1} {rel_type} {entity2} : {label}')
                continue
            
            # Reject anything else outside entity definition
            self.errors_fixed.append(f"Removed invalid ERD line: {line_stripped[:40]}...")
        
        # Handle unclosed entity
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
                fixed_lines.append('        int id PK')
                self.errors_fixed.append(f"Added placeholder fields to entity {entity_name}")
            fixed_lines.append('    }')
        
        # Add relationships
        fixed_lines.extend(relationships)
        
        return '\n'.join(fixed_lines)
    
    def _fix_flowchart_diagram(self, content: str) -> str:
        """Fix flowchart/graph diagram syntax with STRICT validation.
        
        Valid flowchart syntax:
        - flowchart TD|LR|TB|BT|RL (direction)
        - graph TD|LR|TB|BT|RL (direction)
        - A[Label] --> B[Label]
        - A{Decision} -->|Yes| B
        - subgraph name ... end
        - classDef/class statements
        
        REMOVES any line that doesn't match valid patterns.
        """
        import re
        lines = content.strip().split('\n')
        fixed_lines = []
        seen_header = False
        in_subgraph = 0  # Track subgraph nesting
        
        # Valid flowchart line patterns (strict)
        valid_patterns = [
            r'^(flowchart|graph)\s+(TD|LR|TB|BT|RL)',  # Header
            r'^\s*subgraph\s+',  # Subgraph start
            r'^\s*end\s*$',  # Subgraph end
            r'^\s*classDef\s+',  # Class definition
            r'^\s*class\s+\w+',  # Class application
            r'^\s*style\s+',  # Style definition
            r'^\s*linkStyle\s+',  # Link style
            r'^\s*direction\s+',  # Direction override
            r'^\s*%%',  # Comments
            # Node definitions and connections - the core patterns
            r'^\s*\w+[\[\(\{\<]',  # Node with shape: A[, A(, A{, A<
            r'^\s*\w+\s*--',  # Connection starting: A --
            r'^\s*\w+\s*-\.', # Dotted line: A -.
            r'^\s*\w+\s*==',  # Thick line: A ==
            r'^\s*\w+\s*~~~', # Invisible link
            r'^\s*\w+\s*\|',  # A | text
        ]
        
        for line in lines:
            original_line = line
            line_stripped = line.strip()
            
            # Skip empty lines and markdown blocks
            if not line_stripped or line_stripped.startswith('```'):
                continue
            
            # Handle header
            line_lower = line_stripped.lower()
            if line_lower.startswith('flowchart') or line_lower.startswith('graph'):
                if seen_header:
                    self.errors_fixed.append(f"Removed duplicate header: {line_stripped}")
                    continue
                # Ensure valid direction
                if not re.match(r'^(flowchart|graph)\s+(TD|LR|TB|BT|RL)', line_stripped, re.IGNORECASE):
                    line_stripped = 'flowchart TD'
                    self.errors_fixed.append("Fixed flowchart header direction")
                fixed_lines.append(line_stripped)
                seen_header = True
                continue
            
            # Add header if missing
            if not seen_header:
                fixed_lines.append('flowchart TD')
                seen_header = True
                self.errors_fixed.append("Added missing flowchart TD header")
            
            # Track subgraph nesting
            if line_stripped.lower().startswith('subgraph'):
                in_subgraph += 1
            elif line_stripped.lower() == 'end':
                in_subgraph = max(0, in_subgraph - 1)
                fixed_lines.append('    ' + line_stripped)
                continue
            
            # Fix INVALID |> syntax (critical error source)
            if '|>' in line_stripped:
                line_stripped = line_stripped.replace('|>', '')
                self.errors_fixed.append("Removed invalid |> syntax")
            
            # Fix double arrows
            line_stripped = re.sub(r'-->\s*-->', '-->', line_stripped)
            line_stripped = re.sub(r'--+>', '-->', line_stripped)
            line_stripped = re.sub(r'==+>', '==>', line_stripped)
            
            # Fix unclosed brackets
            open_brackets = line_stripped.count('[') + line_stripped.count('(') + line_stripped.count('{')
            close_brackets = line_stripped.count(']') + line_stripped.count(')') + line_stripped.count('}')
            if open_brackets > close_brackets:
                # Add missing closing brackets
                diff = open_brackets - close_brackets
                for _ in range(diff):
                    if '[' in line_stripped and line_stripped.count('[') > line_stripped.count(']'):
                        line_stripped += ']'
                    elif '(' in line_stripped and line_stripped.count('(') > line_stripped.count(')'):
                        line_stripped += ')'
                    elif '{' in line_stripped and line_stripped.count('{') > line_stripped.count('}'):
                        line_stripped += '}'
                self.errors_fixed.append("Fixed unclosed brackets")
            
            # REJECT explanatory text (AI-generated junk)
            ai_text_patterns = [
                r'^(This|The|Here|Below|Above|I\'ve|Let me|Hope|Feel free|As requested)',
                r'^[A-Z][a-z]+.*:\s*$',  # "Something:" on its own
                r'^\d+\.\s+[A-Z]',  # Numbered list
            ]
            is_ai_junk = any(re.match(p, line_stripped, re.IGNORECASE) for p in ai_text_patterns)
            if is_ai_junk:
                self.errors_fixed.append(f"Removed AI text: {line_stripped[:40]}...")
                continue
            
            # Check if line matches any valid pattern
            is_valid = any(re.match(p, line_stripped, re.IGNORECASE) for p in valid_patterns)
            
            # Also accept lines that look like diagram content
            has_arrow = any(x in line_stripped for x in ['-->', '---', '-.', '==>', '~~~'])
            has_node = re.search(r'\w+[\[\(\{\<]', line_stripped)
            
            if is_valid or has_arrow or has_node or in_subgraph > 0:
                # Ensure proper indentation
                if not line_stripped.startswith(' '):
                    line_stripped = '    ' + line_stripped
                fixed_lines.append(line_stripped)
            else:
                self.errors_fixed.append(f"Removed invalid flowchart line: {line_stripped[:40]}...")
        
        if len(fixed_lines) <= 1:
            self.errors_fixed.append("Flowchart appears empty - added sample node")
            fixed_lines.append('    A[Start] --> B[End]')
        
        return '\n'.join(fixed_lines)
    
    def _fix_sequence_diagram(self, content: str) -> str:
        """Fix sequence diagram syntax with STRICT validation.
        
        Valid sequence diagram syntax:
        - sequenceDiagram (header)
        - participant A as Alias
        - actor A as Alias
        - A->>B: Message (solid arrow with arrowhead)
        - A-->>B: Message (dotted arrow with arrowhead)
        - A->B: Message (solid arrow without arrowhead)
        - A-->B: Message (dotted arrow without arrowhead)
        - Note right/left of A: Text
        - Note over A,B: Text
        - loop/alt/opt/par/rect/critical ... end
        - activate/deactivate A
        
        REMOVES any line that doesn't match valid patterns.
        """
        import re
        lines = content.strip().split('\n')
        fixed_lines = ['sequenceDiagram']
        participants = set()
        in_block = 0  # Track nested blocks (loop, alt, etc.)
        seen_header = False
        
        # Valid sequence diagram line patterns (strict)
        valid_keywords = [
            'participant', 'actor', 'note', 'loop', 'alt', 'else', 'opt', 'par', 
            'and', 'critical', 'break', 'rect', 'activate', 'deactivate', 'end',
            'autonumber', 'box', 'title', 'links', 'link'
        ]
        
        # First pass: extract participants from arrows
        for line in lines:
            arrow_match = re.search(r'(\w+)\s*(->>|-->>|->|-->)\s*(\w+)', line)
            if arrow_match:
                participants.add(arrow_match.group(1))
                participants.add(arrow_match.group(3))
        
        for line in lines:
            original_line = line
            line_stripped = line.strip()
            
            # Skip empty, markdown, duplicate headers
            if not line_stripped or line_stripped.startswith('```'):
                continue
            if line_stripped.lower() == 'sequencediagram':
                if seen_header:
                    continue
                seen_header = True
                continue  # Already added header
            
            # Track block nesting
            line_lower = line_stripped.lower()
            if any(line_lower.startswith(kw) for kw in ['loop', 'alt', 'opt', 'par', 'rect', 'critical', 'box']):
                in_block += 1
            elif line_lower == 'end':
                in_block = max(0, in_block - 1)
                fixed_lines.append('    end')
                continue
            
            # REJECT explanatory AI text
            ai_text_patterns = [
                r'^(This|The|Here|Below|Above|I\'ve|Let me|Hope|Feel free|As requested|Sure|Certainly|Of course)',
                r'^[A-Z][a-z]+.*:\s*$',
                r'^\d+\.\s+[A-Z]',
            ]
            is_ai_junk = any(re.match(p, line_stripped, re.IGNORECASE) for p in ai_text_patterns)
            if is_ai_junk:
                self.errors_fixed.append(f"Removed AI text: {line_stripped[:40]}...")
                continue
            
            # Fix invalid arrow syntax: " -> " should be "->>" for sequence diagrams
            if ' -> ' in line_stripped and '->>' not in line_stripped and '-->' not in line_stripped:
                line_stripped = line_stripped.replace(' -> ', '->>')
                self.errors_fixed.append("Fixed -> to ->> for sequence diagram")
            
            # Check if line is a valid keyword line
            is_keyword_line = any(line_lower.startswith(kw) for kw in valid_keywords)
            
            # Check if line is an arrow/message
            has_arrow = any(x in line_stripped for x in ['->>', '-->>',  '->', '-->', '-x', '--x'])
            
            # Check if it's a valid participant/actor declaration
            participant_match = re.match(r'^(participant|actor)\s+\w+', line_stripped, re.IGNORECASE)
            
            # Check if it's a note
            note_match = re.match(r'^note\s+(right\s+of|left\s+of|over)\s+\w+', line_stripped, re.IGNORECASE)
            
            # Accept valid lines
            if is_keyword_line or has_arrow or participant_match or note_match or in_block > 0:
                # Fix missing colon in message
                if has_arrow:
                    arrow_without_colon = re.match(r'^(\w+\s*(?:->>|-->>|->|-->|-x|--x)\s*\w+)\s+([^:].+)$', line_stripped)
                    if arrow_without_colon:
                        line_stripped = f'{arrow_without_colon.group(1)}: {arrow_without_colon.group(2)}'
                        self.errors_fixed.append("Added missing colon after arrow")
                
                # Fix participant alias with spaces
                if participant_match:
                    alias_match = re.match(r'^(participant|actor)\s+(\w+)\s+as\s+(.+)$', line_stripped, re.IGNORECASE)
                    if alias_match:
                        alias = alias_match.group(3)
                        if ' ' in alias and not (alias.startswith('"') or alias.startswith("'")):
                            line_stripped = f'{alias_match.group(1)} {alias_match.group(2)} as "{alias}"'
                            self.errors_fixed.append("Quoted alias with spaces")
                
                # Ensure indentation
                if not line_stripped.startswith(' '):
                    line_stripped = '    ' + line_stripped
                fixed_lines.append(line_stripped)
            else:
                self.errors_fixed.append(f"Removed invalid sequence line: {line_stripped[:40]}...")
        
        # Ensure we have content
        if len(fixed_lines) <= 1:
            self.errors_fixed.append("Sequence diagram appears empty - added sample")
            fixed_lines.extend([
                '    participant A',
                '    participant B',
                '    A->>B: Hello'
            ])
        
        return '\n'.join(fixed_lines)
    
    def _fix_class_diagram(self, content: str) -> str:
        """Fix class diagram syntax with STRICT validation.
        
        Valid class diagram syntax:
        - classDiagram (header)
        - class ClassName { ... }
        - ClassName : +method()
        - ClassName : -attribute
        - ClassA <|-- ClassB (inheritance)
        - ClassA *-- ClassB (composition)
        - ClassA o-- ClassB (aggregation)
        - ClassA --> ClassB (association)
        - ClassA ..> ClassB (dependency)
        - ClassA <.. ClassB (reverse dependency)
        - <<interface>> ClassName
        - note "text"
        
        REMOVES any line that doesn't match valid patterns.
        """
        import re
        lines = content.strip().split('\n')
        fixed_lines = ['classDiagram']
        in_class_body = False
        seen_header = False
        
        # Valid class diagram patterns
        valid_patterns = [
            r'^class\s+\w+',  # Class declaration
            r'^<<\w+>>\s*\w+',  # Stereotype
            r'^[\+\-\#\~]',  # Visibility markers for members
            r'^\w+\s+:\s+[\+\-\#\~]',  # ClassName : +method()
            r'^\w+\s*<\|--\s*\w+',  # Inheritance
            r'^\w+\s*\*--\s*\w+',  # Composition  
            r'^\w+\s*o--\s*\w+',  # Aggregation
            r'^\w+\s*-->?\s*\w+',  # Association
            r'^\w+\s*\.\.>?\s*\w+',  # Dependency
            r'^\w+\s*<\.\.?\s*\w+',  # Reverse dependency
            r'^\w+\s*--\s*\w+',  # Link
            r'^note\s+',  # Note
            r'^link\s+',  # Link
            r'^direction\s+',  # Direction
            r'^namespace\s+',  # Namespace
            r'^\}',  # Closing brace
            r'^\{',  # Opening brace (on separate line)
            r'^%%',  # Comment
        ]
        
        for line in lines:
            original_line = line
            line_stripped = line.strip()
            
            # Skip empty, markdown
            if not line_stripped or line_stripped.startswith('```'):
                continue
            
            # Skip duplicate headers
            if line_stripped.lower() == 'classdiagram':
                if seen_header:
                    continue
                seen_header = True
                continue
            
            # Track class body
            if '{' in line_stripped and not '}' in line_stripped:
                in_class_body = True
            elif '}' in line_stripped:
                in_class_body = False
                fixed_lines.append('    }')
                continue
            
            # REJECT AI explanatory text
            ai_text_patterns = [
                r'^(This|The|Here|Below|Above|I\'ve|Let me|Hope|Feel free|As requested|Sure|Certainly|Of course)',
                r'^[A-Z][a-z]+.*:\s*$',
                r'^\d+\.\s+[A-Z]',
            ]
            is_ai_junk = any(re.match(p, line_stripped, re.IGNORECASE) for p in ai_text_patterns)
            if is_ai_junk:
                self.errors_fixed.append(f"Removed AI text: {line_stripped[:40]}...")
                continue
            
            # Fix common relationship syntax errors
            line_stripped = re.sub(r'<\|--\*', '<|--', line_stripped)
            line_stripped = re.sub(r'\*--<\|', '<|--', line_stripped)
            line_stripped = re.sub(r'---+>', '-->', line_stripped)
            line_stripped = re.sub(r'<---+', '<--', line_stripped)
            line_stripped = re.sub(r'\.\.+->+', '..>', line_stripped)
            
            if original_line.strip() != line_stripped:
                self.errors_fixed.append(f"Fixed relationship syntax: {original_line.strip()[:30]}...")
            
            # Check if line matches valid patterns or is inside class body
            is_valid = any(re.match(p, line_stripped, re.IGNORECASE) for p in valid_patterns)
            has_relationship = any(x in line_stripped for x in ['<|--', '*--', 'o--', '-->', '..>', '<..', '--'])
            
            if is_valid or has_relationship or in_class_body:
                if not line_stripped.startswith(' '):
                    line_stripped = '    ' + line_stripped
                fixed_lines.append(line_stripped)
            else:
                self.errors_fixed.append(f"Removed invalid class line: {line_stripped[:40]}...")
        
        # Ensure we have content
        if len(fixed_lines) <= 1:
            self.errors_fixed.append("Class diagram appears empty - added sample")
            fixed_lines.extend([
                '    class SampleClass {',
                '        +method()',
                '    }'
            ])
        
        return '\n'.join(fixed_lines)
    
    def _fix_state_diagram(self, content: str) -> str:
        """Fix state diagram syntax with STRICT validation.
        
        Valid state diagram syntax:
        - stateDiagram-v2 (header)
        - [*] --> StateA (start)
        - StateA --> [*] (end)
        - StateA --> StateB : transition
        - state "Description" as StateA
        - state StateA { ... } (composite)
        - note right/left of StateA
        
        REMOVES any line that doesn't match valid patterns.
        """
        import re
        lines = content.strip().split('\n')
        fixed_lines = ['stateDiagram-v2']
        in_state_body = 0
        seen_header = False
        
        # Valid state diagram patterns
        valid_patterns = [
            r'^\[\*\]\s*-->\s*\w+',  # Start state
            r'^\w+\s*-->\s*\[\*\]',  # End state
            r'^\w+\s*-->\s*\w+',  # Transition
            r'^state\s+',  # State declaration
            r'^note\s+(right|left)\s+of\s+',  # Notes
            r'^direction\s+',  # Direction
            r'^\[\*\]',  # Start/end marker
            r'^\}',  # Closing brace
            r'^\{',  # Opening brace
            r'^--',  # Comment or divider
            r'^%%',  # Mermaid comment
        ]
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip empty, markdown
            if not line_stripped or line_stripped.startswith('```'):
                continue
            
            # Skip duplicate headers
            if line_stripped.lower().startswith('statediagram'):
                if seen_header:
                    continue
                seen_header = True
                continue
            
            # Track composite state nesting
            if '{' in line_stripped and 'state' in line_stripped.lower():
                in_state_body += 1
            elif line_stripped == '}':
                in_state_body = max(0, in_state_body - 1)
                fixed_lines.append('    }')
                continue
            
            # REJECT AI explanatory text
            ai_text_patterns = [
                r'^(This|The|Here|Below|Above|I\'ve|Let me|Hope|Feel free|As requested|Sure|Certainly|Of course)',
                r'^[A-Z][a-z]+.*:\s*$',
                r'^\d+\.\s+[A-Z]',
            ]
            is_ai_junk = any(re.match(p, line_stripped, re.IGNORECASE) for p in ai_text_patterns)
            if is_ai_junk:
                self.errors_fixed.append(f"Removed AI text: {line_stripped[:40]}...")
                continue
            
            # Check if line matches valid patterns
            is_valid = any(re.match(p, line_stripped, re.IGNORECASE) for p in valid_patterns)
            has_transition = '-->' in line_stripped
            
            if is_valid or has_transition or in_state_body > 0:
                if not line_stripped.startswith(' '):
                    line_stripped = '    ' + line_stripped
                fixed_lines.append(line_stripped)
            else:
                self.errors_fixed.append(f"Removed invalid state line: {line_stripped[:40]}...")
        
        # Ensure we have content
        if len(fixed_lines) <= 1:
            self.errors_fixed.append("State diagram appears empty - added sample")
            fixed_lines.extend([
                '    [*] --> StateA',
                '    StateA --> StateB : action',
                '    StateB --> [*]'
            ])
        
        return '\n'.join(fixed_lines)
    
    def _fix_gantt_diagram(self, content: str) -> str:
        """Fix Gantt diagram syntax with AGGRESSIVE validation.
        
        Valid Gantt syntax ONLY:
        - gantt (header)
        - title Project Title
        - dateFormat YYYY-MM-DD
        - section Section Name
        - Task Name :taskId, 2024-01-01, 5d
        - Task Name :taskId, after task1, 3d
        
        REMOVES anything that doesn't match these patterns exactly.
        """
        import re
        lines = content.strip().split('\n')
        fixed_lines = ['gantt']
        seen_header = False
        task_counter = 1
        
        def make_task_id(name):
            """Create a valid task ID from a name"""
            clean = re.sub(r'[^a-zA-Z0-9]', '', name.lower())[:10]
            return clean if clean else f'task{task_counter}'
        
        def is_valid_duration(s):
            """Check if string looks like a valid duration (e.g., 1d, 2w, 3h)"""
            return bool(re.match(r'^\d+[dwmh]?$', s.strip()))
        
        def is_valid_task_data(data):
            """Check if task data is valid Gantt format"""
            data = data.strip()
            # Valid patterns:
            # taskId, 1d
            # taskId, 2024-01-01, 1d  
            # taskId, after otherId, 1d
            # active, taskId, 1d
            # crit, taskId, 1d
            parts = [p.strip() for p in data.split(',')]
            if not parts:
                return False
            # Last part should be a duration OR a date
            last = parts[-1]
            if not (is_valid_duration(last) or re.match(r'^\d{4}-\d{2}-\d{2}$', last)):
                return False
            # Check for "after" keyword (valid dependency reference)
            for part in parts:
                if part.lower().startswith('after '):
                    return True
            return True
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip empty lines, markdown blocks, comments
            if not line_stripped or line_stripped.startswith('```') or line_stripped.startswith('%%'):
                continue
            
            # Skip duplicate gantt headers
            if line_stripped.lower() == 'gantt':
                if seen_header:
                    continue
                seen_header = True
                continue  # Already added gantt header
            
            # REJECT any line containing "depend" - this is NEVER valid Gantt syntax
            if 'depend' in line_stripped.lower():
                self.errors_fixed.append(f"Removed invalid 'depend' line: {line_stripped[:50]}...")
                continue
            
            # REJECT any line with "dependencies:" header - invalid
            if re.match(r'^dependencies\s*:', line_stripped, re.IGNORECASE):
                self.errors_fixed.append(f"Removed invalid 'dependencies:' line")
                continue
            
            # Valid: section headers
            if line_stripped.lower().startswith('section'):
                section_match = re.match(r'^section\s+(.+)$', line_stripped, re.IGNORECASE)
                if section_match:
                    section_name = section_match.group(1).strip()
                    # Section name should not contain colons or task-like patterns
                    if ':' not in section_name:
                        fixed_lines.append(f'    section {section_name}')
                        continue
                self.errors_fixed.append(f"Removed malformed section: {line_stripped[:40]}...")
                continue
            
            # Valid: directives (title, dateFormat, etc.)
            directive_match = re.match(r'^(title|dateformat|excludes|todaymarker|axisformat|tickinterval)\s+(.+)$', line_stripped, re.IGNORECASE)
            if directive_match:
                directive = directive_match.group(1).lower()
                value = directive_match.group(2).strip()
                fixed_lines.append(f'    {directive} {value}')
                continue
            
            # Valid: task with proper format: "Task Name :taskData"
            # taskData must be: id, duration OR id, date, duration OR id, after other, duration
            task_match = re.match(r'^(.+?)\s*:\s*(.+)$', line_stripped)
            if task_match:
                task_name = task_match.group(1).strip()
                task_data = task_match.group(2).strip()
                
                # Reject if task_name contains invalid patterns
                if 'depend' in task_name.lower():
                    self.errors_fixed.append(f"Removed task with 'depend' in name: {line_stripped[:40]}...")
                    continue
                
                # Validate task_data format
                if is_valid_task_data(task_data):
                    fixed_lines.append(f'    {task_name} :{task_data}')
                    task_counter += 1
                    continue
                else:
                    # Try to fix simple cases: "Task Name: 1d" -> "Task Name :taskid, 1d"
                    if is_valid_duration(task_data):
                        task_id = make_task_id(task_name)
                        fixed_lines.append(f'    {task_name} :{task_id}, {task_data}')
                        self.errors_fixed.append(f"Fixed task format: {line_stripped[:30]}...")
                        task_counter += 1
                        continue
                    else:
                        self.errors_fixed.append(f"Removed invalid task data: {line_stripped[:40]}...")
                        continue
            
            # If line doesn't match any valid pattern, REMOVE it
            self.errors_fixed.append(f"Removed non-matching line: {line_stripped[:40]}...")
        
        # Ensure we have at least some content after gantt header
        if len(fixed_lines) <= 1:
            # Add a placeholder task if diagram is empty
            fixed_lines.append('    title Gantt Chart')
            fixed_lines.append('    dateFormat YYYY-MM-DD')
            fixed_lines.append('    section Tasks')
            fixed_lines.append('    Placeholder :task1, 1d')
            self.errors_fixed.append("Added placeholder content for empty Gantt")
        
        return '\n'.join(fixed_lines)
    
    def _fix_pie_diagram(self, content: str) -> str:
        """Fix pie chart syntax with STRICT validation.
        
        Valid pie syntax:
        - pie (header)
        - pie showData (header with data display)
        - title Chart Title
        - "Label" : value
        
        REMOVES any line that doesn't match valid patterns.
        """
        import re
        lines = content.strip().split('\n')
        fixed_lines = []
        seen_header = False
        
        # Valid pie patterns
        valid_patterns = [
            r'^pie\s*(showdata)?',  # Header
            r'^title\s+',  # Title
            r'^"[^"]+"\s*:\s*[\d\.]+',  # Data entry: "Label" : 100
            r'^%%',  # Comment
        ]
        
        for line in lines:
            line_stripped = line.strip()
            
            if not line_stripped or line_stripped.startswith('```'):
                continue
            
            # Handle header
            if line_stripped.lower().startswith('pie'):
                if seen_header:
                    continue
                fixed_lines.append(line_stripped)
                seen_header = True
                continue
            
            if not seen_header:
                fixed_lines.append('pie')
                seen_header = True
            
            # REJECT AI explanatory text
            ai_text_patterns = [
                r'^(This|The|Here|Below|Above|I\'ve|Let me|Hope|Feel free|As requested|Sure|Certainly|Of course)',
                r'^\d+\.\s+[A-Z]',
            ]
            is_ai_junk = any(re.match(p, line_stripped, re.IGNORECASE) for p in ai_text_patterns)
            if is_ai_junk:
                self.errors_fixed.append(f"Removed AI text: {line_stripped[:40]}...")
                continue
            
            # Check if valid pie data format
            is_valid = any(re.match(p, line_stripped, re.IGNORECASE) for p in valid_patterns)
            has_data = re.match(r'^"[^"]+"\s*:\s*\d', line_stripped)
            
            if is_valid or has_data or line_stripped.lower().startswith('title'):
                if not line_stripped.startswith(' '):
                    line_stripped = '    ' + line_stripped
                fixed_lines.append(line_stripped)
            else:
                self.errors_fixed.append(f"Removed invalid pie line: {line_stripped[:40]}...")
        
        if len(fixed_lines) <= 1:
            self.errors_fixed.append("Pie chart appears empty - added sample")
            fixed_lines.extend([
                '    title Sample Chart',
                '    "Category A" : 40',
                '    "Category B" : 60'
            ])
        
        return '\n'.join(fixed_lines)
    
    def _fix_journey_diagram(self, content: str) -> str:
        """Fix user journey diagram syntax with STRICT validation.
        
        Valid journey syntax:
        - journey (header)
        - title Journey Title
        - section Section Name
        - Task Name: score: actor1, actor2
        
        REMOVES any line that doesn't match valid patterns.
        """
        import re
        lines = content.strip().split('\n')
        fixed_lines = ['journey']
        seen_header = False
        
        # Valid journey patterns
        valid_patterns = [
            r'^title\s+',  # Title
            r'^section\s+',  # Section
            r'^[^:]+:\s*\d+:\s*',  # Task: score: actors
            r'^%%',  # Comment
        ]
        
        for line in lines:
            line_stripped = line.strip()
            
            if not line_stripped or line_stripped.startswith('```'):
                continue
            
            if line_stripped.lower() == 'journey':
                if seen_header:
                    continue
                seen_header = True
                continue
            
            # REJECT AI explanatory text
            ai_text_patterns = [
                r'^(This|The|Here|Below|Above|I\'ve|Let me|Hope|Feel free|As requested|Sure|Certainly|Of course)',
                r'^\d+\.\s+[A-Z]',
            ]
            is_ai_junk = any(re.match(p, line_stripped, re.IGNORECASE) for p in ai_text_patterns)
            if is_ai_junk:
                self.errors_fixed.append(f"Removed AI text: {line_stripped[:40]}...")
                continue
            
            # Check if valid
            is_valid = any(re.match(p, line_stripped, re.IGNORECASE) for p in valid_patterns)
            is_task = re.match(r'^[^:]+:\s*\d', line_stripped)
            is_section = line_stripped.lower().startswith('section')
            is_title = line_stripped.lower().startswith('title')
            
            if is_valid or is_task or is_section or is_title:
                if not line_stripped.startswith(' '):
                    line_stripped = '    ' + line_stripped
                fixed_lines.append(line_stripped)
            else:
                self.errors_fixed.append(f"Removed invalid journey line: {line_stripped[:40]}...")
        
        if len(fixed_lines) <= 1:
            self.errors_fixed.append("Journey appears empty - added sample")
            fixed_lines.extend([
                '    title Sample Journey',
                '    section Start',
                '    First step: 5: User'
            ])
        
        return '\n'.join(fixed_lines)
    
    def _fix_gitgraph_diagram(self, content: str) -> str:
        """Fix Git Graph diagram syntax with STRICT validation.
        
        Valid gitgraph syntax:
        - gitGraph (header)
        - commit id: "message" tag: "v1.0"
        - branch branchName
        - checkout branchName
        - merge branchName
        
        REMOVES any line that doesn't match valid patterns.
        """
        import re
        lines = content.strip().split('\n')
        fixed_lines = ['gitGraph']
        seen_header = False
        
        # Valid gitgraph patterns
        valid_patterns = [
            r'^commit\s*',  # Commit
            r'^branch\s+\w+',  # Branch
            r'^checkout\s+\w+',  # Checkout
            r'^merge\s+\w+',  # Merge
            r'^cherry-pick\s+',  # Cherry-pick
            r'^options\s*$',  # Options block
            r'^end\s*$',  # End options
            r'^%%',  # Comment
        ]
        
        for line in lines:
            line_stripped = line.strip()
            
            if not line_stripped or line_stripped.startswith('```'):
                continue
            
            if line_stripped.lower() == 'gitgraph':
                if seen_header:
                    continue
                seen_header = True
                continue
            
            # REJECT invalid label syntax from flowchart (common AI mistake)
            if re.match(r'^\s*[A-Z]\[.*label=.*\]', line_stripped):
                self.errors_fixed.append(f"Removed invalid label syntax: {line_stripped[:40]}...")
                continue
            
            # REJECT AI explanatory text
            ai_text_patterns = [
                r'^(This|The|Here|Below|Above|I\'ve|Let me|Hope|Feel free|As requested|Sure|Certainly|Of course)',
                r'^\d+\.\s+[A-Z]',
            ]
            is_ai_junk = any(re.match(p, line_stripped, re.IGNORECASE) for p in ai_text_patterns)
            if is_ai_junk:
                self.errors_fixed.append(f"Removed AI text: {line_stripped[:40]}...")
                continue
            
            # Check if valid
            is_valid = any(re.match(p, line_stripped, re.IGNORECASE) for p in valid_patterns)
            
            if is_valid:
                if not line_stripped.startswith(' '):
                    line_stripped = '    ' + line_stripped
                fixed_lines.append(line_stripped)
            else:
                self.errors_fixed.append(f"Removed invalid gitgraph line: {line_stripped[:40]}...")
        
        if len(fixed_lines) <= 1:
            self.errors_fixed.append("Gitgraph appears empty - added sample")
            fixed_lines.extend([
                '    commit',
                '    branch develop',
                '    commit',
                '    checkout main',
                '    merge develop'
            ])
        
        return '\n'.join(fixed_lines)
    
    def _fix_mindmap_diagram(self, content: str) -> str:
        """Fix Mindmap diagram syntax with STRICT validation.
        
        Valid mindmap syntax:
        - mindmap (header)
        - root((Root))
        - Indented children with proper spacing
        
        REMOVES any line that doesn't match valid patterns.
        """
        import re
        lines = content.strip().split('\n')
        fixed_lines = ['mindmap']
        seen_header = False
        has_root = False
        
        for line in lines:
            line_stripped = line.strip()
            original_indent = len(line) - len(line.lstrip())
            
            if not line_stripped or line_stripped.startswith('```'):
                continue
            
            if line_stripped.lower() == 'mindmap':
                if seen_header:
                    continue
                seen_header = True
                continue
            
            # REJECT AI explanatory text
            ai_text_patterns = [
                r'^(This|The|Here|Below|Above|I\'ve|Let me|Hope|Feel free|As requested|Sure|Certainly|Of course)',
                r'^\d+\.\s+[A-Z]',
            ]
            is_ai_junk = any(re.match(p, line_stripped, re.IGNORECASE) for p in ai_text_patterns)
            if is_ai_junk:
                self.errors_fixed.append(f"Removed AI text: {line_stripped[:40]}...")
                continue
            
            # First content line should be root
            if not has_root:
                if line_stripped.lower().startswith('root'):
                    fixed_lines.append('    ' + line_stripped)
                    has_root = True
                else:
                    # Make it a root
                    fixed_lines.append(f'    root(({line_stripped}))')
                    has_root = True
                    self.errors_fixed.append("Converted first line to root node")
            else:
                # Preserve indentation for children
                indent = '    ' + '  ' * (original_indent // 2)
                fixed_lines.append(indent + line_stripped)
        
        if len(fixed_lines) <= 1:
            self.errors_fixed.append("Mindmap appears empty - added sample")
            fixed_lines.extend([
                '    root((Main Topic))',
                '      Child 1',
                '      Child 2'
            ])
        
        return '\n'.join(fixed_lines)
    
    def _fix_timeline_diagram(self, content: str) -> str:
        """Fix Timeline diagram syntax with STRICT validation.
        
        Valid timeline syntax:
        - timeline (header)
        - title Timeline Title
        - section Period Name
        - Event : Description
        
        REMOVES any line that doesn't match valid patterns.
        """
        import re
        lines = content.strip().split('\n')
        fixed_lines = ['timeline']
        seen_header = False
        
        # Valid timeline patterns
        valid_patterns = [
            r'^title\s+',  # Title
            r'^section\s+',  # Section/Period
            r'^[^:]+\s*:\s*',  # Event : description
            r'^\d{4}',  # Year-based entry
            r'^%%',  # Comment
        ]
        
        for line in lines:
            line_stripped = line.strip()
            
            if not line_stripped or line_stripped.startswith('```'):
                continue
            
            if line_stripped.lower() == 'timeline':
                if seen_header:
                    continue
                seen_header = True
                continue
            
            # REJECT AI explanatory text
            ai_text_patterns = [
                r'^(This|The|Here|Below|Above|I\'ve|Let me|Hope|Feel free|As requested|Sure|Certainly|Of course)',
                r'^\d+\.\s+[A-Z]',
            ]
            is_ai_junk = any(re.match(p, line_stripped, re.IGNORECASE) for p in ai_text_patterns)
            if is_ai_junk:
                self.errors_fixed.append(f"Removed AI text: {line_stripped[:40]}...")
                continue
            
            # Check if valid
            is_valid = any(re.match(p, line_stripped, re.IGNORECASE) for p in valid_patterns)
            is_section = line_stripped.lower().startswith('section')
            is_title = line_stripped.lower().startswith('title')
            
            if is_valid or is_section or is_title or ':' in line_stripped:
                if not line_stripped.startswith(' '):
                    line_stripped = '    ' + line_stripped
                fixed_lines.append(line_stripped)
            else:
                self.errors_fixed.append(f"Removed invalid timeline line: {line_stripped[:40]}...")
        
        if len(fixed_lines) <= 1:
            self.errors_fixed.append("Timeline appears empty - added sample")
            fixed_lines.extend([
                '    title Sample Timeline',
                '    section 2024',
                '    Event : Description'
            ])
        
        return '\n'.join(fixed_lines)
    
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

