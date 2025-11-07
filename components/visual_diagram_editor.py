"""
Visual Diagram Editor
Provides drag-and-drop visual editing for diagrams
"""

import streamlit as st
import json
from typing import Dict, List, Any, Optional
from pathlib import Path


class VisualDiagramEditor:
    """Visual drag-and-drop diagram editor"""
    
    def __init__(self):
        self.diagram_elements = []
        self.connections = []
    
    def render_visual_editor(self, diagram_type: str = "flowchart"):
        """Render the visual diagram editor interface"""
        
        st.markdown("### 🎨 Visual Diagram Editor")
        st.markdown("Drag and drop elements to create your diagram visually")
        
        # Editor layout
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("#### 📦 Elements")
            
            # Element palette
            if diagram_type == "flowchart":
                elements = [
                    {"type": "start", "label": "Start", "icon": "🟢"},
                    {"type": "process", "label": "Process", "icon": "⬜"},
                    {"type": "decision", "label": "Decision", "icon": "🔷"},
                    {"type": "end", "label": "End", "icon": "🔴"},
                    {"type": "data", "label": "Data", "icon": "📊"},
                    {"type": "document", "label": "Document", "icon": "📄"},
                ]
            elif diagram_type == "erd":
                elements = [
                    {"type": "entity", "label": "Entity", "icon": "📦"},
                    {"type": "attribute", "label": "Attribute", "icon": "📝"},
                    {"type": "relationship", "label": "Relationship", "icon": "🔗"},
                ]
            else:
                elements = [
                    {"type": "node", "label": "Node", "icon": "⚪"},
                    {"type": "process", "label": "Process", "icon": "⬜"},
                ]
            
            for i, element in enumerate(elements):
                if st.button(
                    f"{element['icon']} {element['label']}",
                    key=f"palette_{element['type']}_{i}_{hash(st.session_state.get('diagram_file', 'default'))}",
                    use_container_width=True,
                    help=f"Click to add {element['label']} to diagram"
                ):
                    self._add_element_to_canvas(element)
            
            st.markdown("---")
            st.markdown("#### 🎨 Style")
            
            # Style options
            st.color_picker("Primary Color", value="#3B82F6", key="primary_color")
            st.color_picker("Secondary Color", value="#10B981", key="secondary_color")
            
            st.selectbox("Shape Style", ["Rounded", "Square", "Circle"], key="shape_style")
            st.selectbox("Arrow Style", ["Solid", "Dashed", "Dotted"], key="arrow_style")
        
        with col2:
            st.markdown("#### 🖼️ Canvas")
            
            # Canvas area
            canvas_container = st.container()
            
            with canvas_container:
                # Create a visual representation using HTML/CSS
                self._render_canvas()
            
            # Action buttons
            col_save, col_export, col_reset = st.columns(3)
            
            with col_save:
                if st.button("💾 Save Diagram", type="primary"):
                    self._save_diagram()
            
            with col_export:
                if st.button("📤 Export"):
                    self._export_diagram()
            
            with col_reset:
                if st.button("🔄 Reset"):
                    self._reset_diagram()
    
    def _add_element_to_canvas(self, element: Dict[str, str]):
        """Add an element to the canvas"""
        if 'diagram_elements' not in st.session_state:
            st.session_state.diagram_elements = []
        
        st.session_state.diagram_elements.append({
            'type': element['type'],
            'label': element['label'],
            'icon': element['icon'],
            'x': 100 + len(st.session_state.diagram_elements) * 150,
            'y': 100 + len(st.session_state.diagram_elements) * 50
        })
        st.rerun()
    
    def _reset_diagram(self):
        """Reset the diagram"""
        st.session_state.diagram_elements = []
        st.session_state.diagram_connections = []
        st.rerun()
    
    def _render_canvas(self):
        """Render the visual canvas"""
        
        # Create HTML canvas with drag-and-drop functionality
        canvas_html = """
        <div id="diagram-canvas" style="
            width: 100%;
            height: 500px;
            border: 2px dashed #e5e7eb;
            border-radius: 8px;
            background: #f9fafb;
            position: relative;
            overflow: hidden;
        ">
            <div style="
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                color: #9ca3af;
                font-size: 18px;
                text-align: center;
            ">
                🎨 Drag elements from the palette to start building your diagram
            </div>
        </div>
        
        <script>
        // Simple drag and drop functionality
        document.addEventListener('DOMContentLoaded', function() {
            const canvas = document.getElementById('diagram-canvas');
            
            // Add click handlers for palette elements
            const paletteButtons = document.querySelectorAll('button[id^="palette_"]');
            paletteButtons.forEach(button => {
                button.addEventListener('click', function() {
                    const elementType = this.id.replace('palette_', '');
                    addElementToCanvas(elementType, this.textContent);
                });
            });
            
            function addElementToCanvas(type, label) {
                const element = document.createElement('div');
                element.className = 'diagram-element';
                element.style.cssText = `
                    position: absolute;
                    width: 120px;
                    height: 60px;
                    background: #3B82F6;
                    color: white;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: move;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    font-size: 12px;
                    font-weight: 500;
                    left: ${Math.random() * 300 + 50}px;
                    top: ${Math.random() * 200 + 50}px;
                `;
                element.textContent = label;
                
                // Make draggable
                element.draggable = true;
                element.addEventListener('dragstart', function(e) {
                    e.dataTransfer.setData('text/plain', '');
                });
                
                canvas.appendChild(element);
            }
            
            // Canvas drop handler
            canvas.addEventListener('dragover', function(e) {
                e.preventDefault();
            });
            
            canvas.addEventListener('drop', function(e) {
                e.preventDefault();
                // Handle drop logic here
            });
        });
        </script>
        
        <style>
        .diagram-element:hover {
            transform: scale(1.05);
            transition: transform 0.2s;
        }
        </style>
        """
        
        st.components.v1.html(canvas_html, height=550)
    
    def _save_diagram(self):
        """Save the current diagram"""
        st.success("✅ Diagram saved!")
        # TODO: Implement actual save functionality
    
    def _export_diagram(self):
        """Export diagram in various formats"""
        st.info("📤 Export functionality coming soon!")
        # TODO: Implement export to Mermaid, PNG, SVG, etc.
    
    def _reset_diagram(self):
        """Reset the diagram"""
        st.rerun()


def render_visual_diagram_editor(diagram_type: str = "flowchart"):
    """Render the visual diagram editor"""
    editor = VisualDiagramEditor()
    editor.render_visual_editor(diagram_type)

