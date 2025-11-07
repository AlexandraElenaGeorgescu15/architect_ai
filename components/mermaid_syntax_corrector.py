"""
Mermaid Syntax Correction System
AI-powered validation and auto-fix for Mermaid diagrams
"""

import re
import streamlit as st
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class DiagramType(Enum):
    """Supported Mermaid diagram types"""
    FLOWCHART = "flowchart"
    GRAPH = "graph"
    SEQUENCE = "sequenceDiagram"
    CLASS = "classDiagram"
    STATE = "stateDiagram"
    ER = "erDiagram"
    GANTT = "gantt"
    PIE = "pie"
    JOURNEY = "journey"


@dataclass
class SyntaxError:
    """Represents a syntax error in Mermaid diagram"""
    line_number: int
    error_type: str
    description: str
    suggested_fix: str
    severity: str  # 'error', 'warning', 'info'


@dataclass
class CorrectionResult:
    """Result of syntax correction"""
    is_valid: bool
    corrected_diagram: str
    errors_found: List[SyntaxError]
    warnings: List[str]
    corrections_applied: List[str]


class MermaidSyntaxCorrector:
    """AI-powered Mermaid syntax corrector"""
    
    def __init__(self):
        self.diagram_validators = {
            DiagramType.FLOWCHART: self._validate_flowchart,
            DiagramType.GRAPH: self._validate_graph,
            DiagramType.SEQUENCE: self._validate_sequence,
            DiagramType.CLASS: self._validate_class,
            DiagramType.STATE: self._validate_state,
            DiagramType.ER: self._validate_er,
            DiagramType.GANTT: self._validate_gantt,
            DiagramType.PIE: self._validate_pie,
            DiagramType.JOURNEY: self._validate_journey
        }
        
        # Common syntax patterns
        self.syntax_patterns = {
            'node_id': r'[A-Za-z][A-Za-z0-9_]*',
            'node_label': r'["\'].*?["\']',
            'arrow': r'-->|--|==>|==|-.->|-.->|~>|~',
            'direction': r'(TD|TB|BT|RL|LR)',
            'class_name': r'[A-Z][A-Za-z0-9_]*',
            'method_name': r'[a-z][a-zA-Z0-9_]*'
        }
    
    def _preprocess_content(self, diagram_content: str) -> str:
        """
        Strip markdown fences, BOMs, and apply aggressive preprocessing.
        
        Now uses the centralized mermaid_preprocessor module for consistency.
        """
        try:
            from .mermaid_preprocessor import aggressive_mermaid_preprocessing
            
            content = diagram_content or ""
            # Remove BOM if present
            if content.startswith("\ufeff"):
                content = content.lstrip("\ufeff")
            
            # Apply aggressive preprocessing (fixes 4 common error types)
            content = aggressive_mermaid_preprocessing(content)
            
            return content
        except Exception as e:
            # Fallback: original preprocessing logic
            content = diagram_content or ""
            if content.startswith("\ufeff"):
                content = content.lstrip("\ufeff")
            content = content.strip()

            lines = content.splitlines()
            if lines and lines[0].strip().lower().startswith("```mermaid"):
                lines = lines[1:]
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
            elif lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()

            return content

    def _ensure_header_line(self, content: str) -> str:
        """Ensure the first non-empty line declares a Mermaid diagram header."""
        if not content.strip():
            return "flowchart TD\n"

        detected = self._detect_diagram_type(content)
        if detected:
            lines = content.splitlines()
            first = lines[0].strip()
            if detected in (DiagramType.FLOWCHART, DiagramType.GRAPH):
                has_dir = (
                    any(first.endswith(dir_) for dir_ in ["TD", "TB", "BT", "RL", "LR"]) or
                    any(line.strip() in ["TD", "TB", "BT", "RL", "LR"] for line in lines[1:3])
                )
                if not has_dir:
                    lines[0] = f"{first} TD"
            return "\n".join(lines)

        lowered = content.lower()
        header = None
        if "erdiagram" in lowered:
            header = "erDiagram"
        elif "sequencediagram" in lowered:
            header = "sequenceDiagram"
        elif "classdiagram" in lowered:
            header = "classDiagram"
        elif "statediagram" in lowered:
            header = "stateDiagram"
        elif "gantt" in lowered:
            header = "gantt"
        elif " pie " in f" {lowered} ":
            header = "pie"
        elif "journey" in lowered:
            header = "journey"

        if header:
            return f"{header}\n{content}"

        return f"flowchart TD\n{content}"
    
    async def correct_diagram(self, diagram_content: str, diagram_name: str = "diagram") -> CorrectionResult:
        """
        Correct Mermaid diagram syntax using AI and pattern matching
        
        Args:
            diagram_content: Raw Mermaid diagram content
            diagram_name: Name of the diagram for context
            
        Returns:
            CorrectionResult with corrected diagram and error details
        """
        
        # Preprocess input (strip fences, ensure header)
        preprocessed = self._preprocess_content(diagram_content)
        preprocessed = self._ensure_header_line(preprocessed)

        # Step 1: Detect diagram type
        diagram_type = self._detect_diagram_type(preprocessed)
        
        # Step 2: Basic syntax validation
        basic_errors = self._validate_basic_syntax(preprocessed)
        
        # Step 3: Type-specific validation
        type_errors = []
        if diagram_type and diagram_type in self.diagram_validators:
            type_errors = self.diagram_validators[diagram_type](preprocessed)
        
        # Step 4: AI-powered correction
        ai_corrections = await self._ai_correct_syntax(preprocessed, diagram_type, basic_errors + type_errors)
        
        # Step 5: Apply corrections
        corrected_diagram, corrections_applied = self._apply_corrections(
            preprocessed, basic_errors + type_errors + ai_corrections
        )

        # Ensure header/direction after corrections
        corrected_diagram = self._ensure_header_line(corrected_diagram)
        
        # Step 6: Final validation
        final_errors = self._validate_basic_syntax(corrected_diagram)
        
        return CorrectionResult(
            is_valid=len(final_errors) == 0,
            corrected_diagram=corrected_diagram,
            errors_found=basic_errors + type_errors + ai_corrections,
            warnings=self._generate_warnings(corrected_diagram),
            corrections_applied=corrections_applied
        )
    
    def _detect_diagram_type(self, content: str) -> Optional[DiagramType]:
        """Detect the type of Mermaid diagram"""
        
        content_lower = content.lower().strip()
        
        if content_lower.startswith('flowchart'):
            return DiagramType.FLOWCHART
        elif content_lower.startswith('graph'):
            return DiagramType.GRAPH
        elif content_lower.startswith('sequencediagram'):
            return DiagramType.SEQUENCE
        elif content_lower.startswith('classdiagram'):
            return DiagramType.CLASS
        elif content_lower.startswith('statediagram'):
            return DiagramType.STATE
        elif content_lower.startswith('erdiagram'):
            return DiagramType.ER
        elif content_lower.startswith('gantt'):
            return DiagramType.GANTT
        elif content_lower.startswith('pie'):
            return DiagramType.PIE
        elif content_lower.startswith('journey'):
            return DiagramType.JOURNEY
        
        return None
    
    def _validate_basic_syntax(self, content: str) -> List[SyntaxError]:
        """Validate basic Mermaid syntax rules"""
        
        errors = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('%%'):
                continue
            
            # Check for common syntax issues
            if self._has_unmatched_quotes(line):
                errors.append(SyntaxError(
                    line_number=i,
                    error_type="unmatched_quotes",
                    description="Unmatched quotes in node label",
                    suggested_fix="Ensure all quotes are properly matched",
                    severity="error"
                ))
            
            if self._has_invalid_node_syntax(line):
                errors.append(SyntaxError(
                    line_number=i,
                    error_type="invalid_node",
                    description="Invalid node syntax",
                    suggested_fix="Use format: NodeID[Label] or NodeID --> NodeID",
                    severity="error"
                ))
            
            if self._has_invalid_arrow(line):
                errors.append(SyntaxError(
                    line_number=i,
                    error_type="invalid_arrow",
                    description="Invalid arrow syntax",
                    suggested_fix="Use valid arrows: -->, --, ==>, ==, -.->, ~>",
                    severity="error"
                ))
        
        return errors
    
    def _validate_flowchart(self, content: str) -> List[SyntaxError]:
        """Validate flowchart-specific syntax"""
        
        errors = []
        lines = content.split('\n')
        
        # Check for direction declaration
        has_direction = any(line.strip().startswith(('TD', 'TB', 'BT', 'RL', 'LR')) 
                           for line in lines)
        
        if not has_direction:
            errors.append(SyntaxError(
                line_number=1,
                error_type="missing_direction",
                description="Flowchart missing direction declaration",
                suggested_fix="Add direction (TD, TB, BT, RL, LR) after 'flowchart'",
                severity="error"
            ))
        
        # Check for valid node shapes
        for i, line in enumerate(lines, 1):
            if '[' in line and ']' in line:
                if not self._is_valid_node_shape(line):
                    errors.append(SyntaxError(
                        line_number=i,
                        error_type="invalid_shape",
                        description="Invalid node shape syntax",
                        suggested_fix="Use valid shapes: [Label], (Label), {Label}, [[Label]], etc.",
                        severity="warning"
                    ))
        
        return errors
    
    def _validate_graph(self, content: str) -> List[SyntaxError]:
        """Validate graph-specific syntax"""
        
        errors = []
        lines = content.split('\n')
        
        # Check for direction declaration
        has_direction = any(line.strip().startswith(('TD', 'TB', 'BT', 'RL', 'LR')) 
                           for line in lines)
        
        if not has_direction:
            errors.append(SyntaxError(
                line_number=1,
                error_type="missing_direction",
                description="Graph missing direction declaration",
                suggested_fix="Add direction (TD, TB, BT, RL, LR) after 'graph'",
                severity="error"
            ))
        
        return errors
    
    def _validate_sequence(self, content: str) -> List[SyntaxError]:
        """Validate sequence diagram syntax"""
        
        errors = []
        lines = content.split('\n')
        
        # Check for participant declarations
        has_participants = any(line.strip().startswith('participant') for line in lines)
        
        if not has_participants:
            errors.append(SyntaxError(
                line_number=1,
                error_type="missing_participants",
                description="Sequence diagram missing participant declarations",
                suggested_fix="Add participants: participant A, participant B",
                severity="error"
            ))
        
        # Check for valid message syntax
        for i, line in enumerate(lines, 1):
            if '->' in line or '-->' in line:
                if not self._is_valid_sequence_message(line):
                    errors.append(SyntaxError(
                        line_number=i,
                        error_type="invalid_message",
                        description="Invalid sequence message syntax",
                        suggested_fix="Use: A->>B: message or A-->>B: message",
                        severity="error"
                    ))
        
        return errors
    
    def _validate_class(self, content: str) -> List[SyntaxError]:
        """Validate class diagram syntax"""
        
        errors = []
        lines = content.split('\n')
        
        # Check for class declarations
        has_classes = any(line.strip().startswith('class') for line in lines)
        
        if not has_classes:
            errors.append(SyntaxError(
                line_number=1,
                error_type="missing_classes",
                description="Class diagram missing class declarations",
                suggested_fix="Add classes: class ClassName",
                severity="error"
            ))
        
        return errors
    
    def _validate_state(self, content: str) -> List[SyntaxError]:
        """Validate state diagram syntax"""
        
        errors = []
        lines = content.split('\n')
        
        # Check for state declarations
        has_states = any('[*]' in line or 'state' in line.lower() for line in lines)
        
        if not has_states:
            errors.append(SyntaxError(
                line_number=1,
                error_type="missing_states",
                description="State diagram missing state declarations",
                suggested_fix="Add states: [*] --> State1, state State1",
                severity="error"
            ))
        
        return errors
    
    def _validate_er(self, content: str) -> List[SyntaxError]:
        """Validate ER diagram syntax"""
        
        errors = []
        lines = content.split('\n')
        
        # Check for entity declarations
        has_entities = any('ENTITY' in line.upper() or 'entity' in line.lower() for line in lines)
        
        if not has_entities:
            errors.append(SyntaxError(
                line_number=1,
                error_type="missing_entities",
                description="ER diagram missing entity declarations",
                suggested_fix="Add entities: ENTITY EntityName { attribute }",
                severity="error"
            ))
        
        return errors
    
    def _validate_gantt(self, content: str) -> List[SyntaxError]:
        """Validate Gantt chart syntax"""
        
        errors = []
        lines = content.split('\n')
        
        # Check for title and dateFormat
        has_title = any(line.strip().startswith('title') for line in lines)
        has_dateformat = any(line.strip().startswith('dateFormat') for line in lines)
        
        if not has_title:
            errors.append(SyntaxError(
                line_number=1,
                error_type="missing_title",
                description="Gantt chart missing title",
                suggested_fix="Add: title Gantt Chart Title",
                severity="error"
            ))
        
        if not has_dateformat:
            errors.append(SyntaxError(
                line_number=1,
                error_type="missing_dateformat",
                description="Gantt chart missing dateFormat",
                suggested_fix="Add: dateFormat YYYY-MM-DD",
                severity="error"
            ))
        
        return errors
    
    def _validate_pie(self, content: str) -> List[SyntaxError]:
        """Validate pie chart syntax"""
        
        errors = []
        lines = content.split('\n')
        
        # Check for title
        has_title = any(line.strip().startswith('title') for line in lines)
        
        if not has_title:
            errors.append(SyntaxError(
                line_number=1,
                error_type="missing_title",
                description="Pie chart missing title",
                suggested_fix="Add: title Pie Chart Title",
                severity="error"
            ))
        
        # Check for data
        has_data = any(':' in line and line.strip() not in ['title', 'pie'] for line in lines)
        
        if not has_data:
            errors.append(SyntaxError(
                line_number=1,
                error_type="missing_data",
                description="Pie chart missing data",
                suggested_fix="Add data: \"Label\" : value",
                severity="error"
            ))
        
        return errors
    
    def _validate_journey(self, content: str) -> List[SyntaxError]:
        """Validate journey diagram syntax"""
        
        errors = []
        lines = content.split('\n')
        
        # Check for title
        has_title = any(line.strip().startswith('title') for line in lines)
        
        if not has_title:
            errors.append(SyntaxError(
                line_number=1,
                error_type="missing_title",
                description="Journey diagram missing title",
                suggested_fix="Add: title Journey Title",
                severity="error"
            ))
        
        # Check for sections
        has_sections = any(line.strip().startswith('section') for line in lines)
        
        if not has_sections:
            errors.append(SyntaxError(
                line_number=1,
                error_type="missing_sections",
                description="Journey diagram missing sections",
                suggested_fix="Add sections: section Section Name",
                severity="error"
            ))
        
        return errors
    
    async def _ai_correct_syntax(self, content: str, diagram_type: Optional[DiagramType], 
                                errors: List[SyntaxError]) -> List[SyntaxError]:
        """Use AI to correct syntax errors"""
        
        if not errors:
            return []
        
        # Import agent here to avoid circular imports
        from agents.universal_agent import UniversalArchitectAgent
        
        agent = UniversalArchitectAgent()
        
        # Create error description
        error_descriptions = []
        for error in errors:
            error_descriptions.append(f"Line {error.line_number}: {error.description}")
        
        prompt = f"""
        Fix these Mermaid diagram syntax errors:
        
        DIAGRAM TYPE: {diagram_type.value if diagram_type else 'Unknown'}
        
        ORIGINAL DIAGRAM:
        ```
        {content}
        ```
        
        ERRORS FOUND:
        {chr(10).join(error_descriptions)}
        
        Please provide the corrected Mermaid diagram with:
        1. All syntax errors fixed
        2. Proper formatting
        3. Valid Mermaid syntax
        4. Same logical structure as original
        
        Output ONLY the corrected Mermaid diagram code, no explanations.
        """
        
        try:
            # Guard against long-running AI calls
            import asyncio as _aio
            corrected = await _aio.wait_for(
                agent._call_ai(
                    prompt,
                    "You are a Mermaid syntax expert. Fix all syntax errors."
                ),
                timeout=12
            )
            
            # Parse the corrected diagram
            corrected_lines = corrected.strip().split('\n')
            original_lines = content.split('\n')
            
            # Create AI corrections
            ai_corrections = []
            for i, (orig, corr) in enumerate(zip(original_lines, corrected_lines)):
                if orig.strip() != corr.strip():
                    ai_corrections.append(SyntaxError(
                        line_number=i + 1,
                        error_type="ai_correction",
                        description=f"AI corrected: '{orig.strip()}' → '{corr.strip()}'",
                        suggested_fix=corr.strip(),
                        severity="info"
                    ))
            
            return ai_corrections
            
        except Exception as e:
            return [SyntaxError(
                line_number=0,
                error_type="ai_error",
                description=f"AI correction failed: {str(e)}",
                suggested_fix="Manual review required",
                severity="warning"
            )]
    
    def _apply_corrections(self, content: str, errors: List[SyntaxError]) -> Tuple[str, List[str]]:
        """Apply corrections to the diagram"""
        
        corrected_lines = content.split('\n')
        corrections_applied = []
        
        for error in errors:
            if error.error_type == "missing_direction":
                # Add direction to first line
                if corrected_lines[0].strip().startswith(('flowchart', 'graph')):
                    corrected_lines[0] = corrected_lines[0].strip() + ' TD'
                    corrections_applied.append(f"Added direction 'TD' to line {error.line_number}")
            
            elif error.error_type == "unmatched_quotes":
                # Fix unmatched quotes
                line_idx = error.line_number - 1
                if line_idx < len(corrected_lines):
                    fixed_line = self._fix_unmatched_quotes(corrected_lines[line_idx])
                    if fixed_line != corrected_lines[line_idx]:
                        corrected_lines[line_idx] = fixed_line
                        corrections_applied.append(f"Fixed unmatched quotes on line {error.line_number}")
            
            elif error.error_type == "invalid_arrow":
                # Fix invalid arrows
                line_idx = error.line_number - 1
                if line_idx < len(corrected_lines):
                    fixed_line = self._fix_invalid_arrow(corrected_lines[line_idx])
                    if fixed_line != corrected_lines[line_idx]:
                        corrected_lines[line_idx] = fixed_line
                        corrections_applied.append(f"Fixed invalid arrow on line {error.line_number}")
            
            elif error.error_type == "ai_correction":
                # Apply AI correction
                line_idx = error.line_number - 1
                if line_idx < len(corrected_lines):
                    corrected_lines[line_idx] = error.suggested_fix
                    corrections_applied.append(f"Applied AI correction on line {error.line_number}")
        
        return '\n'.join(corrected_lines), corrections_applied
    
    def _has_unmatched_quotes(self, line: str) -> bool:
        """Check if line has unmatched quotes"""
        quote_count = line.count('"') + line.count("'")
        return quote_count % 2 != 0
    
    def _has_invalid_node_syntax(self, line: str) -> bool:
        """Check for invalid node syntax"""
        # Basic node patterns: NodeID[Label], NodeID --> NodeID, etc.
        if '[' in line and ']' in line:
            return not re.match(r'^[A-Za-z][A-Za-z0-9_]*\[.*\]$', line.strip())
        elif '-->' in line or '--' in line:
            return not re.match(r'^[A-Za-z][A-Za-z0-9_]*\s*(-->|--|==>|==)\s*[A-Za-z][A-Za-z0-9_]*$', line.strip())
        return False
    
    def _has_invalid_arrow(self, line: str) -> bool:
        """Check for invalid arrow syntax"""
        if '->' in line or '--' in line or '==' in line:
            # Check if arrow is properly formatted
            return not re.search(r'(-->|--|==>|==|-.->|~>|~)', line)
        return False
    
    def _is_valid_node_shape(self, line: str) -> bool:
        """Check if node shape is valid"""
        valid_shapes = ['[', ']', '(', ')', '{', '}', '[[', ']]', '((', '))', '{{', '}}']
        return any(shape in line for shape in valid_shapes)
    
    def _is_valid_sequence_message(self, line: str) -> bool:
        """Check if sequence message is valid"""
        return re.match(r'^[A-Za-z][A-Za-z0-9_]*\s*(->>|-->>|->|-->>)\s*[A-Za-z][A-Za-z0-9_]*\s*:', line.strip())
    
    def _fix_unmatched_quotes(self, line: str) -> str:
        """Fix unmatched quotes in a line"""
        quote_count = line.count('"') + line.count("'")
        if quote_count % 2 != 0:
            # Add missing quote at the end
            if line.count('"') % 2 != 0:
                line += '"'
            else:
                line += "'"
        return line
    
    def _fix_invalid_arrow(self, line: str) -> str:
        """Fix invalid arrow syntax"""
        # Replace common invalid arrows with valid ones
        replacements = {
            '->': '-->',
            '=>': '==>',
            '~': '~>',
            '---': '-->',
            '===': '==>'
        }
        
        for invalid, valid in replacements.items():
            if invalid in line and valid not in line:
                line = line.replace(invalid, valid)
                break
        
        return line
    
    def _generate_warnings(self, content: str) -> List[str]:
        """Generate warnings for potential issues"""
        
        warnings = []
        lines = content.split('\n')
        
        # Check for very long lines
        for i, line in enumerate(lines, 1):
            if len(line) > 100:
                warnings.append(f"Line {i}: Very long line ({len(line)} chars) - consider breaking it up")
        
        # Check for too many nodes (performance warning)
        node_count = len([line for line in lines if '[' in line and ']' in line])
        if node_count > 50:
            warnings.append(f"Large diagram with {node_count} nodes - may render slowly")
        
        # Check for complex nested structures
        if content.count('{') > 10:
            warnings.append("Complex nested structure - ensure proper bracket matching")
        
        return warnings


# Global instance
mermaid_corrector = MermaidSyntaxCorrector()


def render_mermaid_syntax_corrector():
    """Streamlit UI for Mermaid syntax correction"""
    
    st.subheader("🔧 Mermaid Syntax Corrector")
    
    # Input diagram
    diagram_content = st.text_area(
        "Enter Mermaid Diagram:",
        height=300,
        placeholder="flowchart TD\n    A[Start] --> B[Process]\n    B --> C[End]",
        key="mermaid_input"
    )
    
    if st.button("🔍 Validate & Correct", type="primary"):
        if not diagram_content.strip():
            st.warning("Please enter a Mermaid diagram")
            return
        
        with st.spinner("Validating and correcting syntax..."):
            result = mermaid_corrector.correct_diagram(diagram_content)
        
        # Display results
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Original Diagram:**")
            st.code(diagram_content, language="mermaid")
        
        with col2:
            st.write("**Corrected Diagram:**")
            st.code(result.corrected_diagram, language="mermaid")
        
        # Status
        if result.is_valid:
            st.success("✅ Diagram is now valid!")
        else:
            st.error("❌ Diagram still has errors")
        
        # Show errors
        if result.errors_found:
            with st.expander("🔍 Errors Found", expanded=True):
                for error in result.errors_found:
                    severity_color = {
                        'error': '🔴',
                        'warning': '🟡',
                        'info': '🔵'
                    }
                    
                    st.write(f"{severity_color.get(error.severity, '⚪')} **Line {error.line_number}**: {error.description}")
                    st.write(f"   💡 **Fix**: {error.suggested_fix}")
                    st.write("---")
        
        # Show corrections applied
        if result.corrections_applied:
            with st.expander("✅ Corrections Applied"):
                for correction in result.corrections_applied:
                    st.write(f"• {correction}")
        
        # Show warnings
        if result.warnings:
            with st.expander("⚠️ Warnings"):
                for warning in result.warnings:
                    st.write(f"• {warning}")
        
        # Update session state with corrected diagram
        st.session_state.mermaid_corrected = result.corrected_diagram
    
    # Quick actions
    if st.session_state.get('mermaid_corrected'):
        st.write("**Quick Actions:**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📋 Copy Corrected"):
                st.code(st.session_state.mermaid_corrected)
                st.success("Corrected diagram copied!")
        
        with col2:
            if st.button("🔄 Use Corrected"):
                st.session_state.mermaid_input = st.session_state.mermaid_corrected
                st.rerun()
        
        with col3:
            if st.button("💾 Save to File"):
                from pathlib import Path
                output_path = Path("outputs/visualizations/corrected_diagram.mmd")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(st.session_state.mermaid_corrected)
                st.success(f"Saved to {output_path}")


def validate_mermaid_syntax(diagram_content: str) -> Tuple[bool, str, List[str]]:
    """
    Quick validation function for use in other components
    
    Returns:
        (is_valid, corrected_diagram, errors)
    """
    
    # Run the async function synchronously
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    result = loop.run_until_complete(mermaid_corrector.correct_diagram(diagram_content))
    errors = [f"Line {e.line_number}: {e.description}" for e in result.errors_found]
    
    return result.is_valid, result.corrected_diagram, errors
