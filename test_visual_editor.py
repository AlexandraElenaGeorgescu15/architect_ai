"""
Quick test script to demonstrate the Visual Diagram Editor
Run with: streamlit run test_visual_editor.py
"""

import streamlit as st
from components.visual_diagram_editor import render_visual_diagram_editor

st.set_page_config(page_title="Visual Diagram Editor Demo", layout="wide")

st.title("🎨 Visual Diagram Editor - Miro-Like Canvas")
st.markdown("### TRUE interactive drag-and-drop experience with 4 tabs")

st.info("""
**Features:**
- 👁️ **View Tab**: See your rendered Mermaid diagram
- 📝 **HTML Editor Tab**: Edit Mermaid code directly with live preview  
- 🎨 **Canvas Tab**: TRUE Miro-like drag-and-drop (move nodes, double-click to edit, multi-select)
- 📥 **Download Tab**: Export as .mmd, .md, or .json

**Canvas Controls:**
- Drag nodes anywhere on the canvas
- Double-click nodes to edit their text
- Click to select, Shift+Click for multi-select
- Use toolbar to add different shapes (Rectangle, Rounded, Diamond, Circle, Stadium)
- Color picker to customize node colors
""")

# Render the visual diagram editor
render_visual_diagram_editor(
    diagram_type="flowchart",
    initial_mermaid="graph TD\n    Start[🚀 Start Here] --> Process1[Add Nodes]\n    Process1 --> Process2[Drag & Drop]\n    Process2 --> End[✅ Export]",
    key_suffix="demo"
)
