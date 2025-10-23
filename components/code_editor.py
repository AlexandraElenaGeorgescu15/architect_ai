"""
Monaco Code Editor Component
Beautiful in-app code editing with syntax highlighting
"""

import streamlit as st
import streamlit.components.v1 as components

def render_code_editor(code: str, language: str = "python", height: int = 600, theme: str = "vs-dark", read_only: bool = False):
    """
    Render Monaco code editor
    
    Args:
        code: Initial code content
        language: Programming language (python, typescript, javascript, html, css, etc.)
        height: Editor height in pixels
        theme: Editor theme (vs-dark, vs-light, hc-black)
        read_only: Whether editor is read-only
    
    Returns:
        Edited code content
    """
    
    # Create unique key for this editor instance
    editor_id = f"monaco_editor_{hash(code[:100])}"
    
    # Monaco editor HTML
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                margin: 0;
                padding: 0;
                overflow: hidden;
            }}
            #container {{
                width: 100%;
                height: {height}px;
            }}
            .actions {{
                position: absolute;
                top: 10px;
                right: 10px;
                z-index: 1000;
                display: flex;
                gap: 10px;
            }}
            .btn {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: 600;
                font-size: 14px;
                transition: transform 0.2s;
            }}
            .btn:hover {{
                transform: translateY(-2px);
            }}
        </style>
    </head>
    <body>
        <div class="actions">
            <button class="btn" onclick="formatCode()">🎨 Format</button>
            <button class="btn" onclick="copyCode()">📋 Copy</button>
            <button class="btn" onclick="downloadCode()">💾 Download</button>
        </div>
        <div id="container"></div>
        
        <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs/loader.min.js"></script>
        <script>
            require.config({{ paths: {{ 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' }}}});
            
            let editor;
            
            require(['vs/editor/editor.main'], function() {{
                editor = monaco.editor.create(document.getElementById('container'), {{
                    value: {repr(code)},
                    language: '{language}',
                    theme: '{theme}',
                    readOnly: {str(read_only).lower()},
                    automaticLayout: true,
                    fontSize: 14,
                    minimap: {{ enabled: true }},
                    scrollBeyondLastLine: false,
                    lineNumbers: 'on',
                    renderWhitespace: 'selection',
                    folding: true,
                    suggest: {{
                        enabled: true
                    }},
                    quickSuggestions: true,
                    wordWrap: 'on'
                }});
                
                // Send updates to Streamlit
                editor.onDidChangeModelContent((event) => {{
                    window.parent.postMessage({{
                        type: 'streamlit:setComponentValue',
                        value: editor.getValue()
                    }}, '*');
                }});
            }});
            
            function formatCode() {{
                if (editor) {{
                    editor.getAction('editor.action.formatDocument').run();
                }}
            }}
            
            function copyCode() {{
                if (editor) {{
                    const code = editor.getValue();
                    navigator.clipboard.writeText(code).then(() => {{
                        alert('Code copied to clipboard!');
                    }});
                }}
            }}
            
            function downloadCode() {{
                if (editor) {{
                    const code = editor.getValue();
                    const blob = new Blob([code], {{ type: 'text/plain' }});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'code.{language}';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                }}
            }}
        </script>
    </body>
    </html>
    """
    
    # Render Monaco editor
    edited_code = components.html(html_code, height=height + 50, scrolling=False)
    
    return edited_code if edited_code is not None else code


def render_multi_file_editor(files: dict, height: int = 600):
    """
    Render Monaco editor with multiple file tabs
    
    Args:
        files: Dictionary of {filename: code_content}
        height: Editor height in pixels
    
    Returns:
        Dictionary of edited files
    """
    
    if not files:
        st.info("No files to edit")
        return {}
    
    # File tabs
    selected_file = st.selectbox(
        "📁 Select File",
        list(files.keys()),
        key="file_selector"
    )
    
    if selected_file:
        # Determine language from file extension
        extension_map = {
            '.py': 'python',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.json': 'json',
            '.md': 'markdown',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.cs': 'csharp',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.sql': 'sql'
        }
        
        ext = '.' + selected_file.split('.')[-1] if '.' in selected_file else ''
        language = extension_map.get(ext, 'plaintext')
        
        # Render editor for selected file
        edited_code = render_code_editor(
            files[selected_file],
            language=language,
            height=height
        )
        
        # Update files dictionary
        if edited_code is not None:
            files[selected_file] = edited_code
    
    return files

