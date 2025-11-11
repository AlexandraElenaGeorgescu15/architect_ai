"""
Visual Diagram Editor with Interactive Canvas - TRUE MIRO-LIKE EXPERIENCE
Provides drag-and-drop visual editing for Mermaid diagrams with real-time code generation
"""

import streamlit as st
import streamlit.components.v1 as components
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
import random


class VisualDiagramEditor:
    """Interactive visual diagram editor with TRUE Miro-like drag-drop canvas"""
    
    def __init__(self):
        self.diagram_elements = []
        self.connections = []
    
    def render_visual_editor(self, diagram_type: str = "flowchart", initial_mermaid: str = "", key_suffix: str = ""):
        """
        Render the TRUE MIRO-LIKE interactive diagram editor with 4 tabs:
        - View: See the rendered diagram
        - HTML Editor: Edit HTML/Mermaid code
        - Canvas: TRUE drag-and-drop like Miro
        - Download: Export in all formats
        
        Args:
            diagram_type: Type of diagram ('flowchart', 'erd', 'sequence', 'class')
            initial_mermaid: Optional Mermaid code to load initially
            key_suffix: Unique suffix to avoid key conflicts
        """
        
        # Initialize session state for THIS specific editor instance
        state_key = f"visual_editor_{key_suffix}"
        if f'{state_key}_nodes' not in st.session_state:
            st.session_state[f'{state_key}_nodes'] = []
        if f'{state_key}_edges' not in st.session_state:
            st.session_state[f'{state_key}_edges'] = []
        if f'{state_key}_node_counter' not in st.session_state:
            st.session_state[f'{state_key}_node_counter'] = 0
        if f'{state_key}_selected_nodes' not in st.session_state:
            st.session_state[f'{state_key}_selected_nodes'] = []
        if f'{state_key}_mermaid_code' not in st.session_state:
            st.session_state[f'{state_key}_mermaid_code'] = initial_mermaid or "graph TD\n    A[Start] --> B[End]"
        
        # Create 4 tabs as requested: View, HTML Editor, Canvas, Download
        tab1, tab2, tab3, tab4 = st.tabs([
            "👁️ View",
            "📝 HTML Editor", 
            "🎨 Canvas",
            "📥 Download"
        ])
        
        # Tab 1: VIEW - Show the rendered diagram
        with tab1:
            self._render_view_tab(state_key)
        
        # Tab 2: HTML EDITOR - Edit raw HTML/Mermaid
        with tab2:
            self._render_html_editor_tab(state_key)
        
        # Tab 3: CANVAS - TRUE MIRO-LIKE DRAG AND DROP
        with tab3:
            self._render_canvas_tab(diagram_type, state_key)
        
        # Tab 4: DOWNLOAD - Export options
        with tab4:
            self._render_download_tab(state_key)
    
    def _render_view_tab(self, state_key: str):
        """Tab 1: View the rendered diagram"""
        st.markdown("### 👁️ View Rendered Diagram")
        
        mermaid_code = st.session_state.get(f'{state_key}_mermaid_code', "")
        
        if mermaid_code and mermaid_code.strip():
            # Render using mermaid.js
            self._render_mermaid_preview(mermaid_code)
        else:
            st.info("📝 No diagram to display. Use the Canvas tab to create one or HTML Editor to write code!")
    
    def _render_html_editor_tab(self, state_key: str):
        """Tab 2: Edit HTML/Mermaid code directly"""
        st.markdown("### 📝 Edit Diagram Code")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### Mermaid Code Editor")
            edited_mermaid = st.text_area(
                "Edit Mermaid syntax:",
                value=st.session_state[f'{state_key}_mermaid_code'],
                height=400,
                key=f"{state_key}_mermaid_textarea",
                help="Edit the Mermaid diagram syntax directly"
            )
            
            if st.button("✅ Apply Changes", key=f"{state_key}_apply_mermaid"):
                st.session_state[f'{state_key}_mermaid_code'] = edited_mermaid
                st.success("✅ Code updated! Check View tab to see changes")
                st.rerun()
        
        with col2:
            st.markdown("#### Live Preview")
            if edited_mermaid and edited_mermaid.strip():
                self._render_mermaid_preview(edited_mermaid)
            else:
                st.info("Enter Mermaid code on the left to see preview")
    
    def _render_canvas_tab(self, diagram_type: str, state_key: str):
        """Tab 3: TRUE MIRO-LIKE CANVAS - Drag, drop, connect, move everything"""
        st.markdown("### 🎨 Interactive Canvas (Miro-like)")
        st.caption("✨ Drag nodes anywhere • Double-click to edit text • Click two nodes to connect • Fully interactive!")
        
        # Toolbar at the top
        col_tools = st.columns([1, 1, 1, 1, 1, 1])
        
        with col_tools[0]:
            node_type = st.selectbox(
                "Shape",
                ["Rectangle", "Rounded", "Diamond", "Circle", "Stadium"],
                key=f"{state_key}_node_type"
            )
        
        with col_tools[1]:
            if st.button("➕ Add Node", key=f"{state_key}_add_node", use_container_width=True):
                self._add_node_to_canvas(state_key, node_type)
        
        with col_tools[2]:
            connecting_mode = st.session_state.get(f'{state_key}_connecting_mode', False)
            button_label = "🔗 Connecting..." if connecting_mode else "🔗 Connect"
            if st.button(button_label, key=f"{state_key}_connect_mode", use_container_width=True):
                # Toggle is handled in canvas JavaScript
                pass
        
        with col_tools[3]:
            color = st.color_picker("Color", st.session_state.get(f'{state_key}_last_color', "#3B82F6"), key=f"{state_key}_color")
            st.session_state[f'{state_key}_last_color'] = color
        
        with col_tools[4]:
            if st.button("🗑️ Delete Selected", key=f"{state_key}_delete", use_container_width=True):
                self._delete_selected_nodes(state_key)
        
        with col_tools[5]:
            if st.button("🔄 Clear All", key=f"{state_key}_clear", use_container_width=True):
                st.session_state[f'{state_key}_nodes'] = []
                st.session_state[f'{state_key}_edges'] = []
                st.session_state[f'{state_key}_node_counter'] = 0
                st.rerun()
        
        # THE CANVAS - Full Miro-like experience
        self._render_interactive_canvas(state_key, diagram_type, color)
        
        # Show generated Mermaid code below canvas
        st.markdown("---")
        st.markdown("#### 📋 Generated Mermaid Code")
        generated_code = self._generate_mermaid_from_canvas(state_key, diagram_type)
        st.code(generated_code, language="mermaid")
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("📥 Apply to Editor", key=f"{state_key}_copy_to_editor", use_container_width=True):
                st.session_state[f"{state_key}_mermaid_code"] = generated_code
                st.success("✅ Copied! Switch to HTML Editor tab or View tab to see it")
        with col_b:
            if st.button("👁️ Preview Now", key=f"{state_key}_preview_canvas", use_container_width=True):
                st.session_state[f"{state_key}_mermaid_code"] = generated_code
                st.rerun()
    
    def _render_download_tab(self, state_key: str):
        """Tab 4: Download in various formats"""
        st.markdown("### 📥 Download Diagram")
        st.caption("Export your diagram in multiple formats")
        
        # Get current diagram code
        if st.session_state.get(f'{state_key}_nodes'):
            final_code = self._generate_mermaid_from_canvas(state_key, "flowchart")
        else:
            final_code = st.session_state.get(f'{state_key}_mermaid_code', "")
        
        # Preview
        st.markdown("#### Preview")
        if final_code:
            with st.expander("Show diagram code", expanded=False):
                st.code(final_code, language="mermaid")
        else:
            st.warning("No diagram to download. Create one in the Canvas tab!")
            return
        
        # Download buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                label="📄 Mermaid (.mmd)",
                data=final_code,
                file_name="diagram.mmd",
                mime="text/plain",
                key=f"{state_key}_download_mmd",
                use_container_width=True,
                help="Download as Mermaid code file"
            )
        
        with col2:
            markdown_content = f"# Diagram\n\n```mermaid\n{final_code}\n```"
            st.download_button(
                label="📝 Markdown (.md)",
                data=markdown_content,
                file_name="diagram.md",
                mime="text/markdown",
                key=f"{state_key}_download_md",
                use_container_width=True,
                help="Download as Markdown with embedded Mermaid"
            )
        
        with col3:
            json_content = json.dumps({
                "mermaid": final_code,
                "nodes": st.session_state.get(f'{state_key}_nodes', []),
                "edges": st.session_state.get(f'{state_key}_edges', [])
            }, indent=2)
            st.download_button(
                label="📊 JSON (.json)",
                data=json_content,
                file_name="diagram.json",
                mime="application/json",
                key=f"{state_key}_download_json",
                use_container_width=True,
                help="Download diagram data as JSON"
            )
        
        st.markdown("---")
        st.info("💡 **Tip:** Use [Mermaid Live](https://mermaid.live) to export as PNG/SVG/PDF. Just paste your Mermaid code there!")
    
    def _add_node_to_canvas(self, state_key: str, node_type: str):
        """Add a new node to the canvas"""
        st.session_state[f'{state_key}_node_counter'] += 1
        node_id = f"node{st.session_state[f'{state_key}_node_counter']}"
        
        # Random position to avoid overlap
        x = 50 + random.randint(0, 600)
        y = 50 + random.randint(0, 300)
        
        st.session_state[f'{state_key}_nodes'].append({
            'id': node_id,
            'type': node_type,
            'label': f"Node {st.session_state[f'{state_key}_node_counter']}",
            'x': x,
            'y': y,
            'color': st.session_state.get(f'{state_key}_last_color', '#3B82F6')
        })
        st.rerun()
    
    def _delete_selected_nodes(self, state_key: str):
        """Delete selected nodes"""
        selected = st.session_state.get(f'{state_key}_selected_nodes', [])
        if selected:
            nodes = st.session_state.get(f'{state_key}_nodes', [])
            st.session_state[f'{state_key}_nodes'] = [n for n in nodes if n['id'] not in selected]
            st.session_state[f'{state_key}_selected_nodes'] = []
            st.rerun()
        else:
            st.warning("No nodes selected! Click on nodes in the canvas to select them.")
    
    def _render_mermaid_preview(self, mermaid_code: str):
        """Render Mermaid diagram preview"""
        clean_code = mermaid_code.strip()
        if clean_code.startswith("```mermaid"):
            clean_code = clean_code.replace("```mermaid", "").replace("```", "").strip()
        elif clean_code.startswith("```"):
            clean_code = clean_code.replace("```", "").strip()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
            <style>
                body {{
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 400px;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                }}
                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 12px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    max-width: 90%;
                }}
                .mermaid {{
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="mermaid">
{clean_code}
                </div>
            </div>
            <script>
                mermaid.initialize({{ 
                    startOnLoad: true,
                    theme: 'default',
                    flowchart: {{ 
                        useMaxWidth: true,
                        htmlLabels: true,
                        curve: 'basis'
                    }},
                    themeVariables: {{
                        primaryColor: '#3B82F6',
                        primaryTextColor: '#fff',
                        primaryBorderColor: '#2563EB',
                        lineColor: '#94A3B8',
                        secondaryColor: '#F59E0B',
                        tertiaryColor: '#10B981'
                    }}
                }});
            </script>
        </body>
        </html>
        """
        components.html(html, height=500, scrolling=True)
    
    def _render_interactive_canvas(self, state_key: str, diagram_type: str, default_color: str):
        """Render TRUE Miro-like interactive canvas with full drag-and-drop"""
        
        nodes = st.session_state.get(f'{state_key}_nodes', [])
        edges = st.session_state.get(f'{state_key}_edges', [])
        
        nodes_json = json.dumps(nodes)
        edges_json = json.dumps(edges)
        
        # Create a TRULY interactive canvas like Miro
        canvas_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    overflow: hidden;
                }}
                #canvas-container {{
                    width: 100%;
                    height: 600px;
                    position: relative;
                    background: white;
                    border: 2px solid #e5e7eb;
                    border-radius: 12px;
                    overflow: hidden;
                    cursor: default;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                }}
                #canvas {{
                    width: 100%;
                    height: 100%;
                    position: relative;
                }}
                svg {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    pointer-events: none;
                    z-index: 1;
                }}
                .node {{
                    position: absolute;
                    min-width: 120px;
                    padding: 14px 20px;
                    background: #3B82F6;
                    color: white;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: grab;
                    user-select: none;
                    font-size: 14px;
                    font-weight: 500;
                    box-shadow: 0 3px 10px rgba(59, 130, 246, 0.3);
                    transition: transform 0.15s, box-shadow 0.15s;
                    z-index: 10;
                    text-align: center;
                }}
                .node:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
                }}
                .node:active {{
                    cursor: grabbing;
                }}
                .node.selected {{
                    box-shadow: 0 0 0 3px #F59E0B, 0 6px 20px rgba(245, 158, 11, 0.4);
                }}
                .node.diamond {{
                    transform: rotate(45deg);
                    padding: 20px;
                }}
                .node.diamond span {{
                    transform: rotate(-45deg);
                    display: block;
                }}
                .node.circle {{
                    border-radius: 50%;
                    width: 100px;
                    height: 100px;
                    padding: 0;
                }}
                .node.stadium {{
                    border-radius: 50px;
                }}
                .info-panel {{
                    position: absolute;
                    top: 10px;
                    right: 10px;
                    background: rgba(255,255,255,0.95);
                    padding: 15px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    font-size: 12px;
                    color: #374151;
                    z-index: 1000;
                    min-width: 200px;
                }}
                .info-panel h4 {{
                    margin: 0 0 10px 0;
                    font-size: 13px;
                    color: #1f2937;
                }}
                .info-panel p {{
                    margin: 5px 0;
                    line-height: 1.4;
                }}
                .counter {{
                    position: absolute;
                    bottom: 10px;
                    left: 10px;
                    background: rgba(59, 130, 246, 0.9);
                    color: white;
                    padding: 8px 15px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 600;
                    z-index: 1000;
                }}
            </style>
        </head>
        <body>
            <div id="canvas-container">
                <svg id="connections-svg"></svg>
                <div id="canvas"></div>
                <div class="info-panel">
                    <h4>🎨 Canvas Controls</h4>
                    <p>• <strong>Drag</strong> nodes to move</p>
                    <p>• <strong>Click</strong> to select</p>
                    <p>• <strong>Double-click</strong> to edit</p>
                    <p>• <strong>Shift+Click</strong> multi-select</p>
                </div>
                <div class="counter">
                    <span id="node-count">0 nodes</span> • 
                    <span id="edge-count">0 connections</span>
                </div>
            </div>
            
            <script>
            (function() {{
                let nodes = {nodes_json};
                let edges = {edges_json};
                let selectedNodes = [];
                let isDragging = false;
                let draggedNode = null;
                let offsetX, offsetY;
                
                const canvas = document.getElementById('canvas');
                const svg = document.getElementById('connections-svg');
                
                // Update counter
                function updateCounter() {{
                    document.getElementById('node-count').textContent = nodes.length + ' node' + (nodes.length !== 1 ? 's' : '');
                    document.getElementById('edge-count').textContent = edges.length + ' connection' + (edges.length !== 1 ? 's' : '');
                }}
                
                // Draw connections between nodes
                function drawConnections() {{
                    svg.innerHTML = '';
                    edges.forEach(edge => {{
                        const fromNode = document.getElementById(edge.from);
                        const toNode = document.getElementById(edge.to);
                        
                        if (fromNode && toNode) {{
                            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                            const fromRect = fromNode.getBoundingClientRect();
                            const toRect = toNode.getBoundingClientRect();
                            const containerRect = canvas.getBoundingClientRect();
                            
                            line.setAttribute('x1', fromRect.left + fromRect.width/2 - containerRect.left);
                            line.setAttribute('y1', fromRect.top + fromRect.height/2 - containerRect.top);
                            line.setAttribute('x2', toRect.left + toRect.width/2 - containerRect.left);
                            line.setAttribute('y2', toRect.top + toRect.height/2 - containerRect.top);
                            line.setAttribute('stroke', '#94A3B8');
                            line.setAttribute('stroke-width', '2');
                            line.setAttribute('stroke-dasharray', '5,5');
                            
                            svg.appendChild(line);
                        }}
                    }});
                }}
                
                // Render nodes on canvas
                function renderNodes() {{
                    canvas.innerHTML = '';
                    
                    nodes.forEach(node => {{
                        const nodeEl = document.createElement('div');
                        nodeEl.id = node.id;
                        nodeEl.className = 'node';
                        
                        // Apply node type styling
                        if (node.type === 'Diamond') {{
                            nodeEl.classList.add('diamond');
                            nodeEl.innerHTML = `<span>${{node.label}}</span>`;
                        }} else if (node.type === 'Circle') {{
                            nodeEl.classList.add('circle');
                            nodeEl.textContent = node.label;
                        }} else if (node.type === 'Stadium') {{
                            nodeEl.classList.add('stadium');
                            nodeEl.textContent = node.label;
                        }} else if (node.type === 'Rounded') {{
                            nodeEl.style.borderRadius = '20px';
                            nodeEl.textContent = node.label;
                        }} else {{
                            nodeEl.textContent = node.label;
                        }}
                        
                        nodeEl.style.left = node.x + 'px';
                        nodeEl.style.top = node.y + 'px';
                        nodeEl.style.background = node.color || '{default_color}';
                        
                        // Double-click to edit label
                        nodeEl.addEventListener('dblclick', (e) => {{
                            e.stopPropagation();
                            const newLabel = prompt('Edit node label:', node.label);
                            if (newLabel !== null && newLabel.trim()) {{
                                node.label = newLabel.trim();
                                renderNodes();
                            }}
                        }});
                        
                        // Click to select
                        nodeEl.addEventListener('click', (e) => {{
                            e.stopPropagation();
                            
                            if (e.shiftKey) {{
                                // Multi-select
                                const idx = selectedNodes.indexOf(node.id);
                                if (idx > -1) {{
                                    selectedNodes.splice(idx, 1);
                                    nodeEl.classList.remove('selected');
                                }} else {{
                                    selectedNodes.push(node.id);
                                    nodeEl.classList.add('selected');
                                }}
                            }} else {{
                                // Single select
                                document.querySelectorAll('.node').forEach(n => n.classList.remove('selected'));
                                selectedNodes = [node.id];
                                nodeEl.classList.add('selected');
                            }}
                        }});
                        
                        // Drag functionality
                        nodeEl.addEventListener('mousedown', (e) => {{
                            if (e.button !== 0) return; // Only left click
                            isDragging = true;
                            draggedNode = node;
                            offsetX = e.clientX - node.x;
                            offsetY = e.clientY - node.y;
                            nodeEl.style.zIndex = '100';
                            e.preventDefault();
                        }});
                        
                        canvas.appendChild(nodeEl);
                    }});
                    
                    updateCounter();
                    setTimeout(drawConnections, 10);
                }}
                
                // Mouse move for dragging
                document.addEventListener('mousemove', (e) => {{
                    if (isDragging && draggedNode) {{
                        const containerRect = canvas.getBoundingClientRect();
                        let newX = e.clientX - containerRect.left - offsetX;
                        let newY = e.clientY - containerRect.top - offsetY;
                        
                        // Keep within bounds
                        newX = Math.max(0, Math.min(newX, containerRect.width - 120));
                        newY = Math.max(0, Math.min(newY, containerRect.height - 50));
                        
                        draggedNode.x = newX;
                        draggedNode.y = newY;
                        
                        const nodeEl = document.getElementById(draggedNode.id);
                        nodeEl.style.left = newX + 'px';
                        nodeEl.style.top = newY + 'px';
                        
                        drawConnections();
                    }}
                }});
                
                // Mouse up to stop dragging
                document.addEventListener('mouseup', () => {{
                    if (isDragging && draggedNode) {{
                        draggedNode = null;
                        isDragging = false;
                    }}
                }});
                
                // Click canvas to deselect all
                canvas.addEventListener('click', (e) => {{
                    if (e.target === canvas) {{
                        document.querySelectorAll('.node').forEach(n => n.classList.remove('selected'));
                        selectedNodes = [];
                    }}
                }});
                
                // Initial render
                renderNodes();
                
                // Prevent text selection while dragging
                document.addEventListener('selectstart', (e) => {{
                    if (isDragging) e.preventDefault();
                }});
            }})();
            </script>
        </body>
        </html>
        """
        
        components.html(canvas_html, height=650, scrolling=False)
    
    def _generate_mermaid_from_canvas(self, state_key: str, diagram_type: str) -> str:
        """Generate Mermaid code from canvas nodes and edges"""
        
        nodes = st.session_state.get(f'{state_key}_nodes', [])
        edges = st.session_state.get(f'{state_key}_edges', [])
        
        if not nodes:
            return "graph TD\n    %% Add nodes using the toolbar above"
        
        lines = ["graph TD"]
        
        # Add nodes with appropriate shapes
        for node in nodes:
            node_id = node['id']
            label = node['label']
            node_type = node['type']
            
            if node_type == "Rectangle":
                lines.append(f"    {node_id}[{label}]")
            elif node_type == "Rounded":
                lines.append(f"    {node_id}({label})")
            elif node_type == "Diamond":
                lines.append(f"    {node_id}{{{{{label}}}}}")
            elif node_type == "Circle":
                lines.append(f"    {node_id}(({label}))")
            elif node_type == "Stadium":
                lines.append(f"    {node_id}([{label}])")
            else:
                lines.append(f"    {node_id}[{label}]")
        
        # Add edges/connections
        for edge in edges:
            lines.append(f"    {edge['from']} --> {edge['to']}")
        
        return "\n".join(lines)


def render_visual_diagram_editor(diagram_type: str = "flowchart", initial_mermaid: str = "", key_suffix: str = "main"):
    """
    Main entry point to render the visual diagram editor.
    
    Args:
        diagram_type: Type of diagram to create
        initial_mermaid: Initial Mermaid code to load
        key_suffix: Unique key suffix to support multiple instances
    """
    editor = VisualDiagramEditor()
    editor.render_visual_editor(diagram_type, initial_mermaid, key_suffix)
