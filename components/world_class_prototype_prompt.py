"""
World-Class Prototype Generation Prompt Template

This module contains the most comprehensive, battle-tested prompt
for generating high-quality HTML prototypes.

Author: Alexandra Georgescu
"""


def build_world_class_prompt(feature_name: str, full_context: str, ui_elements: list, requirements: list) -> str:
    """
    Build the absolute best prototype generation prompt.
    
    This prompt includes:
    - Complete HTML/CSS/JS structure with working examples
    - Modern design system (colors, spacing, typography)
    - Functional JavaScript patterns (forms, modals, tables, charts)
    - Realistic data examples
    - Accessibility best practices
    """
    
    # Build UI-specific guidance
    ui_guidance = "\n".join([
        f"• {elem}: Include functional implementation with proper styling"
        for elem in ui_elements
    ]) if ui_elements else "• Basic layout with cards and sections"
    
    # Build requirements list
    req_list = "\n".join([
        f"{i+1}. {req}"
        for i, req in enumerate(requirements[:8])
    ]) if requirements else "1. Create a user-friendly interface"
    
    prompt = f"""
═══════════════════════════════════════════════════════════════════════════════
🎨 WORLD-CLASS PROTOTYPE GENERATOR
═══════════════════════════════════════════════════════════════════════════════

FEATURE TO BUILD: **{feature_name}**

FULL CONTEXT & REQUIREMENTS:
───────────────────────────────────────────────────────────────────────────────
{full_context[:1500]}

KEY REQUIREMENTS:
{req_list}

UI ELEMENTS NEEDED:
{ui_guidance}

═══════════════════════════════════════════════════════════════════════════════
📋 YOUR MISSION
═══════════════════════════════════════════════════════════════════════════════

Create a COMPLETE, PRODUCTION-QUALITY HTML prototype that:

✅ **Functionality**: Implements ALL requirements from the context above
✅ **Design**: Modern, professional, visually stunning interface
✅ **Interactions**: ALL buttons, forms, and controls ACTUALLY WORK
✅ **Data**: Uses realistic, feature-specific sample data (no placeholders)
✅ **Responsive**: Works on mobile and desktop
✅ **Accessible**: Proper ARIA labels, keyboard navigation
✅ **Standalone**: ONE complete HTML file (no external dependencies)

═══════════════════════════════════════════════════════════════════════════════
🎨 DESIGN SYSTEM TO USE
═══════════════════════════════════════════════════════════════════════════════

COLORS:
• Primary: #667eea (Purple Blue)
• Secondary: #764ba2 (Deep Purple)
• Success: #10b981 (Green)
• Warning: #f59e0b (Amber)
• Error: #ef4444 (Red)
• Background: #f9fafb (Light Gray)
• Text: #1f2937 (Dark Gray)
• White: #ffffff

SPACING (8px grid):
• xs: 4px
• sm: 8px
• md: 16px
• lg: 24px
• xl: 32px
• 2xl: 48px

TYPOGRAPHY:
• Heading 1: 2.5rem, bold
• Heading 2: 2rem, semi-bold
• Heading 3: 1.5rem, semi-bold
• Body: 1rem, normal
• Small: 0.875rem, normal

SHADOWS:
• Card: 0 4px 6px rgba(0,0,0,0.1)
• Hover: 0 8px 20px rgba(0,0,0,0.15)
• Modal: 0 20px 60px rgba(0,0,0,0.3)

BORDER RADIUS:
• Small: 4px
• Medium: 8px
• Large: 16px
• Pill: 999px

═══════════════════════════════════════════════════════════════════════════════
💻 COMPLETE HTML STRUCTURE (USE THIS AS TEMPLATE)
═══════════════════════════════════════════════════════════════════════════════

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{feature_name}</title>
    <style>
        /* ═══════════════════════════════════════════════════════════════
           RESET & BASE STYLES
           ═══════════════════════════════════════════════════════════════ */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 
                         'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #1f2937;
        }}
        
        /* ═══════════════════════════════════════════════════════════════
           LAYOUT
           ═══════════════════════════════════════════════════════════════ */
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 48px;
            animation: fadeIn 0.5s ease-out;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        /* ═══════════════════════════════════════════════════════════════
           TYPOGRAPHY
           ═══════════════════════════════════════════════════════════════ */
        h1 {{
            color: #1f2937;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        
        h2 {{
            color: #374151;
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 16px;
            margin-top: 32px;
        }}
        
        h3 {{
            color: #4b5563;
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 12px;
        }}
        
        p {{
            line-height: 1.6;
            color: #6b7280;
            margin-bottom: 16px;
        }}
        
        /* ═══════════════════════════════════════════════════════════════
           BUTTONS
           ═══════════════════════════════════════════════════════════════ */
        .btn {{
            display: inline-block;
            padding: 12px 32px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            border: none;
            transition: all 0.3s ease;
            text-decoration: none;
        }}
        
        .btn-primary {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }}
        
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        }}
        
        .btn-secondary {{
            background: #f3f4f6;
            color: #374151;
        }}
        
        .btn-secondary:hover {{
            background: #e5e7eb;
        }}
        
        .btn-success {{
            background: #10b981;
            color: white;
        }}
        
        .btn-danger {{
            background: #ef4444;
            color: white;
        }}
        
        /* ═══════════════════════════════════════════════════════════════
           FORMS
           ═══════════════════════════════════════════════════════════════ */
        .form-group {{
            margin-bottom: 24px;
        }}
        
        label {{
            display: block;
            font-weight: 600;
            color: #374151;
            margin-bottom: 8px;
        }}
        
        input[type="text"],
        input[type="email"],
        input[type="password"],
        input[type="number"],
        select,
        textarea {{
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }}
        
        input:focus,
        select:focus,
        textarea:focus {{
            outline: none;
            border-color: #667eea;
        }}
        
        .form-error {{
            color: #ef4444;
            font-size: 14px;
            margin-top: 4px;
        }}
        
        /* ═══════════════════════════════════════════════════════════════
           CARDS
           ═══════════════════════════════════════════════════════════════ */
        .card {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 24px;
            transition: box-shadow 0.3s;
        }}
        
        .card:hover {{
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        }}
        
        /* ═══════════════════════════════════════════════════════════════
           TABLES
           ═══════════════════════════════════════════════════════════════ */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 24px 0;
        }}
        
        th {{
            background: #f9fafb;
            padding: 16px;
            text-align: left;
            font-weight: 600;
            color: #374151;
            border-bottom: 2px solid #e5e7eb;
        }}
        
        td {{
            padding: 16px;
            border-bottom: 1px solid #f3f4f6;
        }}
        
        tr:hover {{
            background: #f9fafb;
        }}
        
        /* ═══════════════════════════════════════════════════════════════
           MODALS
           ═══════════════════════════════════════════════════════════════ */
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            z-index: 1000;
            animation: modalFadeIn 0.3s;
        }}
        
        @keyframes modalFadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        
        .modal-content {{
            position: relative;
            background: white;
            max-width: 600px;
            margin: 100px auto;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            animation: modalSlideIn 0.3s;
        }}
        
        @keyframes modalSlideIn {{
            from {{ transform: translateY(-50px); opacity: 0; }}
            to {{ transform: translateY(0); opacity: 1; }}
        }}
        
        .modal-close {{
            position: absolute;
            top: 16px;
            right: 16px;
            font-size: 28px;
            cursor: pointer;
            color: #9ca3af;
        }}
        
        .modal-close:hover {{
            color: #374151;
        }}
        
        /* ═══════════════════════════════════════════════════════════════
           BADGES & LABELS
           ═══════════════════════════════════════════════════════════════ */
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 14px;
            font-weight: 600;
        }}
        
        .badge-success {{ background: #d1fae5; color: #065f46; }}
        .badge-warning {{ background: #fef3c7; color: #92400e; }}
        .badge-error {{ background: #fee2e2; color: #991b1b; }}
        .badge-info {{ background: #dbeafe; color: #1e40af; }}
        
        /* ═══════════════════════════════════════════════════════════════
           NOTIFICATIONS
           ═══════════════════════════════════════════════════════════════ */
        .notification {{
            position: fixed;
            top: 24px;
            right: 24px;
            padding: 16px 24px;
            border-radius: 8px;
            color: white;
            box-shadow: 0 8px 20px rgba(0,0,0,0.2);
            animation: slideIn 0.3s;
            z-index: 2000;
        }}
        
        @keyframes slideIn {{
            from {{ transform: translateX(400px); }}
            to {{ transform: translateX(0); }}
        }}
        
        .notification.success {{ background: #10b981; }}
        .notification.error {{ background: #ef4444; }}
        .notification.warning {{ background: #f59e0b; }}
        
        /* ═══════════════════════════════════════════════════════════════
           RESPONSIVE
           ═══════════════════════════════════════════════════════════════ */
        @media (max-width: 768px) {{
            .container {{
                padding: 24px;
            }}
            
            h1 {{ font-size: 2rem; }}
            h2 {{ font-size: 1.5rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{feature_name}</h1>
        <p>Feature-specific subtitle or description here</p>
        
        <!-- ═══════════════════════════════════════════════════════════════
             YOUR FEATURE IMPLEMENTATION GOES HERE
             
             REMEMBER:
             - Use realistic, feature-specific data
             - Implement ALL requirements from the context
             - Make all buttons and forms FUNCTIONAL
             - Add proper event handlers in JavaScript below
             ═══════════════════════════════════════════════════════════════ -->
        
        <!-- Example: Action Button -->
        <button class="btn btn-primary" onclick="openFeatureModal()">
            Primary Action
        </button>
        
        <!-- Example: Data Table -->
        <table>
            <thead>
                <tr>
                    <th>Column 1</th>
                    <th>Column 2</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="dataTable">
                <!-- JavaScript will populate this -->
            </tbody>
        </table>
        
        <!-- Example: Modal -->
        <div id="featureModal" class="modal">
            <div class="modal-content">
                <span class="modal-close" onclick="closeFeatureModal()">&times;</span>
                <h2>Modal Title</h2>
                <form onsubmit="handleFormSubmit(event)">
                    <div class="form-group">
                        <label>Input Field:</label>
                        <input type="text" required placeholder="Enter value">
                    </div>
                    <button type="submit" class="btn btn-primary">Submit</button>
                </form>
            </div>
        </div>
    </div>
    
    <script>
        /* ═══════════════════════════════════════════════════════════════
           SAMPLE DATA (Replace with feature-specific data)
           ═══════════════════════════════════════════════════════════════ */
        const sampleData = [
            {{ id: 1, name: 'Item 1', status: 'active' }},
            {{ id: 2, name: 'Item 2', status: 'pending' }},
            {{ id: 3, name: 'Item 3', status: 'completed' }}
        ];
        
        /* ═══════════════════════════════════════════════════════════════
           MODAL FUNCTIONS
           ═══════════════════════════════════════════════════════════════ */
        function openFeatureModal() {{
            document.getElementById('featureModal').style.display = 'block';
        }}
        
        function closeFeatureModal() {{
            document.getElementById('featureModal').style.display = 'none';
        }}
        
        // Close modal on outside click
        window.onclick = function(event) {{
            const modal = document.getElementById('featureModal');
            if (event.target == modal) {{
                modal.style.display = 'none';
            }}
        }}
        
        /* ═══════════════════════════════════════════════════════════════
           FORM HANDLING
           ═══════════════════════════════════════════════════════════════ */
        function handleFormSubmit(event) {{
            event.preventDefault();
            
            // Get form data
            const formData = new FormData(event.target);
            
            // Validate (example)
            if (!formData.get('fieldName')) {{
                showNotification('Please fill all fields', 'error');
                return;
            }}
            
            // Process submission
            showNotification('Success! Data saved.', 'success');
            closeFeatureModal();
            event.target.reset();
        }}
        
        /* ═══════════════════════════════════════════════════════════════
           TABLE POPULATION
           ═══════════════════════════════════════════════════════════════ */
        function populateTable() {{
            const tbody = document.getElementById('dataTable');
            tbody.innerHTML = sampleData.map(item => `
                <tr>
                    <td>${{item.name}}</td>
                    <td>
                        <span class="badge badge-${{item.status === 'active' ? 'success' : 'warning'}}">
                            ${{item.status}}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-secondary" onclick="viewItem(${{item.id}})">
                            View
                        </button>
                    </td>
                </tr>
            `).join('');
        }}
        
        function viewItem(id) {{
            alert(`Viewing item ${{id}}`);
            // Implement actual view logic here
        }}
        
        /* ═══════════════════════════════════════════════════════════════
           NOTIFICATION SYSTEM
           ═══════════════════════════════════════════════════════════════ */
        function showNotification(message, type = 'success') {{
            const notification = document.createElement('div');
            notification.className = `notification ${{type}}`;
            notification.textContent = message;
            document.body.appendChild(notification);
            
            setTimeout(() => {{
                notification.style.animation = 'slideOut 0.3s';
                setTimeout(() => notification.remove(), 300);
            }}, 3000);
        }}
        
        /* ═══════════════════════════════════════════════════════════════
           INITIALIZATION
           ═══════════════════════════════════════════════════════════════ */
        document.addEventListener('DOMContentLoaded', function() {{
            populateTable();
            
            // Add any initialization logic here
            console.log('Prototype initialized');
        }});
        
        // ADD YOUR FEATURE-SPECIFIC JAVASCRIPT HERE
        // Remember to:
        // 1. Use the sample data structure above
        // 2. Implement ALL interactive features from requirements
        // 3. Add proper error handling
        // 4. Make it feel like a real application
    </script>
</body>
</html>

═══════════════════════════════════════════════════════════════════════════════
🚫 CRITICAL: WHAT NOT TO DO
═══════════════════════════════════════════════════════════════════════════════

❌ DO NOT create a generic template - this must be about "{feature_name}"
❌ DO NOT use placeholder data like "Lorem ipsum" or "Example 1, Example 2"
❌ DO NOT leave functions empty - implement REAL logic
❌ DO NOT leave placeholder comments without code
❌ DO NOT show "Architect.AI" or any other unrelated app
❌ DO NOT use external CSS/JS libraries or CDN links
❌ DO NOT wrap output in markdown code fences (```html)
❌ DO NOT add explanations - output ONLY the HTML code
❌ DO NOT reference functions without defining them
❌ DO NOT create non-working buttons (every button MUST have onclick handler)

═══════════════════════════════════════════════════════════════════════════════
✅ WHAT TO DO
═══════════════════════════════════════════════════════════════════════════════

✅ Use the COMPLETE template above as your starting point
✅ Replace ALL placeholder comments with feature-specific content
✅ Use realistic data relevant to "{feature_name}"
✅ Implement ALL requirements from the context
✅ Make ALL interactions work (buttons, forms, modals, tables)
✅ Every button MUST have a working onclick handler or event listener
✅ Every form MUST have a working submit handler
✅ All JavaScript functions referenced in HTML MUST be defined
✅ Add proper success/error notifications
✅ Use the design system colors and spacing
✅ Make it responsive (mobile + desktop)
✅ Output ONE complete, valid HTML file
✅ Test mentally: if you click a button, something MUST happen

═══════════════════════════════════════════════════════════════════════════════
📤 OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════════

Start with: <!DOCTYPE html>
End with: </html>

Output ONLY valid HTML code. No markdown. No explanations. Just code.
"""
    
    return prompt

