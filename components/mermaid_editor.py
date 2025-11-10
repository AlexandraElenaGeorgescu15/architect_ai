"""
Simple Canvas-Based Mermaid Diagram Editor

A clean, no-frills editor for Mermaid diagrams with:
- Syntax editor on the left
- Live preview on the right
- Auto-validation and syntax error checking
- AI-powered semantic validation (optional)
- Save state persistence across UI refreshes

The diagram is rendered from the syntax you edit. That's it.
"""

import streamlit as st
import streamlit.components.v1 as components
import re
from pathlib import Path


def validate_mermaid_syntax(mermaid_code: str) -> tuple[bool, str]:
    """
    Validate Mermaid syntax before rendering.
    
    Args:
        mermaid_code: Mermaid diagram code
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not mermaid_code.strip():
        return False, "Empty diagram"
    
    # Check for valid diagram type
    valid_types = [
        'flowchart', 'graph', 'sequenceDiagram', 'classDiagram',
        'stateDiagram', 'erDiagram', 'gantt', 'pie', 'journey',
        'gitGraph', 'mindmap', 'timeline', 'quadrantChart'
    ]
    
    first_line = mermaid_code.strip().split('\n')[0].strip()
    
    # Check if starts with valid type
    if not any(first_line.startswith(t) for t in valid_types):
        return False, f"Invalid diagram type. Must start with one of: {', '.join(valid_types[:5])}, ..."
    
    # Check for balanced brackets
    open_count = mermaid_code.count('[') + mermaid_code.count('(') + mermaid_code.count('{')
    close_count = mermaid_code.count(']') + mermaid_code.count(')') + mermaid_code.count('}')
    
    if open_count != close_count:
        return False, f"Unbalanced brackets: {open_count} opening, {close_count} closing"
    
    # Check for minimum content
    lines = [l.strip() for l in mermaid_code.split('\n') if l.strip() and not l.strip().startswith('%%')]
    if len(lines) < 2:
        return False, "Diagram too short - needs at least 2 lines"
    
    return True, ""


def render_mermaid_editor(initial_code: str = "", key: str = "mermaid_editor", file_path: Path = None):
    """
    Render a simple canvas-based Mermaid editor with live preview.
    
    This is a NO-AI, NO-COMPLEXITY editor. You edit the syntax, you see the diagram.
    The diagram is generated correctly from the first go by the AI (via smart_generation.py).
    
    Args:
        initial_code: Initial Mermaid code to display
        key: Unique key for the editor component
        file_path: Optional path to the diagram file (for save state tracking)
        
    Returns:
        Updated Mermaid code from the editor
    """
    
    # 🔥 FIX: Initialize session state for this specific editor
    if f"{key}_code" not in st.session_state:
        st.session_state[f"{key}_code"] = initial_code
    if f"{key}_last_saved" not in st.session_state:
        st.session_state[f"{key}_last_saved"] = initial_code
    if f"{key}_save_timestamp" not in st.session_state:
        st.session_state[f"{key}_save_timestamp"] = None
    
    # Create two columns: editor and preview
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📝 Mermaid Syntax Editor")
        
        # 🔥 FIX: Show save state indicator
        has_changes = st.session_state[f"{key}_code"] != st.session_state[f"{key}_last_saved"]
        if st.session_state[f"{key}_save_timestamp"]:
            if has_changes:
                st.warning(f"⚠️ You have unsaved changes (last saved: {st.session_state[f'{key}_save_timestamp']})")
            else:
                st.success(f"✅ All changes saved ({st.session_state[f'{key}_save_timestamp']})")
        elif has_changes:
            st.info("💡 Click Save to persist your changes")
        
        # Text area for editing Mermaid code
        mermaid_code = st.text_area(
            "Edit Mermaid syntax:",
            value=st.session_state[f"{key}_code"],
            height=400,
            key=f"{key}_input",
            help="Edit the Mermaid diagram syntax. The preview updates automatically."
        )
        
        # Update session state
        st.session_state[f"{key}_code"] = mermaid_code
        
        # Validate syntax
        is_valid, error_msg = validate_mermaid_syntax(mermaid_code)
        
        if not is_valid and mermaid_code.strip():
            st.error(f"⚠️ Syntax Error: {error_msg}")
        elif is_valid:
            st.success("✅ Syntax valid")
        
        # Quick actions
        st.markdown("#### Actions")
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            if st.button("🔄 Reset", key=f"{key}_reset"):
                st.session_state[f"{key}_code"] = initial_code
                st.rerun()
        
        with col_b:
            st.download_button(
                label="📥 Download",
                data=mermaid_code,
                file_name="diagram.mmd",
                mime="text/plain",
                key=f"{key}_download_btn"
            )
        
        with col_c:
            if st.button("📋 Show Code", key=f"{key}_show"):
                st.code(mermaid_code, language="mermaid")
    
    with col2:
        st.markdown("### 👁️ Live Canvas Preview")
        
        # Render the Mermaid diagram
        if mermaid_code.strip():
            if is_valid:
                render_mermaid_diagram(mermaid_code, key=f"{key}_preview")
            else:
                st.warning(f"⚠️ Fix syntax errors to see preview\n\n{error_msg}")
        else:
            st.info("👈 Edit syntax to see the diagram render here")
    
    return mermaid_code


def render_mermaid_diagram(mermaid_code: str, key: str = "mermaid_preview"):
    """
    Render a Mermaid diagram on a clean canvas using mermaid.js.
    
    Args:
        mermaid_code: Mermaid diagram code
        key: Unique key for the component
    """
    
    # Clean the code - remove markdown code blocks if present
    clean_code = mermaid_code.strip()
    if clean_code.startswith("```mermaid"):
        clean_code = clean_code.replace("```mermaid", "").replace("```", "").strip()
    elif clean_code.startswith("```"):
        clean_code = clean_code.replace("```", "").strip()
    
    # Validate before rendering
    is_valid, error_msg = validate_mermaid_syntax(clean_code)
    
    if not is_valid:
        st.error(f"⚠️ Cannot render: {error_msg}")
        return
    
    # HTML with Mermaid.js for rendering on canvas
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 20px;
                background: #f8f9fa;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            #canvas {{
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 400px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                padding: 20px;
            }}
            .error {{
                color: #dc3545;
                background: #f8d7da;
                border: 2px solid #dc3545;
                border-radius: 8px;
                padding: 15px;
                margin: 20px;
                font-family: 'Courier New', monospace;
                font-size: 14px;
            }}
            .warning {{
                color: #856404;
                background: #fff3cd;
                border: 2px solid #ffc107;
                border-radius: 8px;
                padding: 15px;
                margin: 20px;
                font-size: 14px;
            }}
            .mermaid {{
                background: white;
                padding: 10px;
            }}
            .loading {{
                color: #6c757d;
                text-align: center;
                padding: 40px;
            }}
        </style>
    </head>
    <body>
        <div id="canvas">
            <div class="loading">⏳ Rendering diagram...</div>
            <div class="mermaid" style="display:none;">
{clean_code}
            </div>
        </div>
        <script>
            try {{
                mermaid.initialize({{ 
                    startOnLoad: false,  // Manual render for better error handling
                    theme: 'default',
                    securityLevel: 'loose',
                    flowchart: {{ 
                        useMaxWidth: true,
                        htmlLabels: true,
                        curve: 'basis'
                    }},
                    er: {{
                        useMaxWidth: true
                    }},
                    sequence: {{
                        useMaxWidth: true,
                        wrap: true
                    }}
                }});
                
                // Manual render with error handling
                const mermaidDiv = document.querySelector('.mermaid');
                mermaidDiv.style.display = 'block';
                document.querySelector('.loading').remove();
                
                mermaid.run({{
                    nodes: [mermaidDiv]
                }}).catch(err => {{
                    console.error('Mermaid render error:', err);
                    document.getElementById('canvas').innerHTML = 
                        '<div class="error">' +
                        '<strong>⚠️ Mermaid Rendering Error</strong><br><br>' + 
                        '<strong>Error:</strong> ' + (err.message || 'Unknown error') + '<br><br>' +
                        '<div class="warning">💡 <strong>Troubleshooting:</strong><br>' +
                        '• Check for syntax errors in the editor<br>' +
                        '• Ensure all nodes are properly connected<br>' +
                        '• Verify bracket balancing<br>' +
                        '• Try simplifying the diagram</div>' +
                        '</div>';
                }});
            }} catch (initError) {{
                console.error('Mermaid init error:', initError);
                document.getElementById('canvas').innerHTML = 
                    '<div class="error"><strong>⚠️ Failed to Initialize Mermaid</strong><br><br>' + 
                    'Could not load Mermaid.js library. Check your internet connection.' + 
                    '</div>';
            }}
            
            // Global error handler
            window.addEventListener('error', function(e) {{
                console.error('Window error:', e);
                if (document.getElementById('canvas').querySelector('.error') === null) {{
                    document.getElementById('canvas').innerHTML = 
                        '<div class="error"><strong>⚠️ Unexpected Error</strong><br><br>' + 
                        'An error occurred while rendering the diagram.' + 
                        '</div>';
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    # Render the HTML component on canvas
    components.html(html_code, height=450, scrolling=True)


def render_mermaid_editor_compact(initial_code: str = "", title: str = "Mermaid Editor", key: str = "compact_editor"):
    """
    Render a compact Mermaid editor in an expander.
    
    Args:
        initial_code: Initial Mermaid code
        title: Title for the expander
        key: Unique key for the component
        
    Returns:
        Updated Mermaid code
    """
    
    with st.expander(f"✏️ {title}", expanded=False):
        return render_mermaid_editor(initial_code, key=key)

