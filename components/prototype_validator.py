"""
Prototype Validator - Ensures Generated HTML is Actually Functional

This module validates that generated prototypes have:
1. Feature-specific content (not generic)
2. Working JavaScript (functions defined and called)
3. Realistic data (not placeholders)

Author: Alexandra Georgescu
"""

import re
from typing import Dict, List, Tuple


class PrototypeValidator:
    """Validates that generated HTML prototypes are functional"""
    
    def __init__(self):
        self.generic_patterns = [
            r'Example\s+\d+',
            r'Lorem\s+ipsum',
            r'placeholder',
            r'Sample\s+data',
            r'Test\s+item',
            r'Demo\s+content',
            r'Generic',
            r'Feature\s+Prototype',  # If this is the title, it's too generic
        ]
        
        self.required_js_patterns = {
            'function_definitions': r'function\s+\w+\s*\(',
            'event_handlers': r'onclick=|addEventListener',
            'dom_manipulation': r'getElementById|querySelector',
        }
    
    def validate(self, html: str, feature_name: str) -> Tuple[bool, List[str], int]:
        """
        Validate that the prototype is functional and feature-specific.
        
        Args:
            html: Generated HTML content
            feature_name: Expected feature name
            
        Returns:
            Tuple of (is_valid, issues, quality_score)
        """
        issues = []
        quality_score = 100
        
        # Check 0: Is this actually HTML at all?
        # If it doesn't have basic HTML tags, it's completely invalid
        has_html_tags = any(tag in html.lower() for tag in ['<html', '<body', '<div', '<head', '<!doctype'])
        if not has_html_tags:
            issues.append("CRITICAL: Not HTML content - no HTML tags found")
            return False, issues, 0  # Return immediately with 0 score
        
        # Check 1: Has feature name in content
        if feature_name.lower() not in html.lower():
            issues.append(f"Missing feature name '{feature_name}' in content")
            quality_score -= 30
        
        # Check 2: Not too generic
        for pattern in self.generic_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if len(matches) > 3:  # More than 3 occurrences = too generic
                issues.append(f"Too many generic placeholders: '{pattern}' ({len(matches)} times)")
                quality_score -= 20
        
        # Check 3: Has JavaScript functionality
        has_functions = bool(re.search(self.required_js_patterns['function_definitions'], html))
        has_handlers = bool(re.search(self.required_js_patterns['event_handlers'], html))
        has_dom = bool(re.search(self.required_js_patterns['dom_manipulation'], html))
        
        if not has_functions:
            issues.append("No JavaScript functions defined")
            quality_score -= 25
        
        if not has_handlers:
            issues.append("No event handlers (onclick, addEventListener)")
            quality_score -= 15
        
        if not has_dom:
            issues.append("No DOM manipulation (getElementById, querySelector)")
            quality_score -= 10
        
        # Check 4: Has realistic structure
        if '<button' not in html.lower():
            issues.append("No buttons found")
            quality_score -= 10
        
        # Check 5: Length check (too short = incomplete)
        if len(html) < 1000:
            issues.append("HTML too short (< 1000 chars)")
            quality_score -= 30
        
        is_valid = quality_score >= 60
        
        return is_valid, issues, max(0, quality_score)
    
    def enhance_html_functionality(self, html: str, feature_name: str) -> str:
        """
        If validation fails, try to enhance the HTML to make it functional.
        This is a safety net for when AI generates incomplete code.
        """
        
        # If HTML is missing basic structure, wrap it
        if '<!DOCTYPE html>' not in html:
            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{feature_name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
    </style>
</head>
<body>
    <div class="container">
        {html}
    </div>
</body>
</html>"""
        
        # If missing JavaScript, add minimal functionality
        if '<script>' not in html.lower() and '<button' in html.lower():
            # Add before </body>
            js_code = """
    <script>
        // Auto-generated functionality for buttons
        document.addEventListener('DOMContentLoaded', function() {
            // Make all buttons show alerts
            const buttons = document.querySelectorAll('button');
            buttons.forEach((btn, index) => {
                if (!btn.onclick) {
                    btn.onclick = function() {
                        alert('Button clicked: ' + (btn.textContent || 'Button ' + (index + 1)));
                    };
                }
            });
            
            // Make forms show success
            const forms = document.querySelectorAll('form');
            forms.forEach(form => {
                form.onsubmit = function(e) {
                    e.preventDefault();
                    alert('Form submitted successfully!');
                    form.reset();
                };
            });
        });
    </script>
</body>"""
            html = html.replace('</body>', js_code)
        
        return html


def validate_and_enhance(html: str, feature_name: str) -> Tuple[str, Dict]:
    """
    Convenience function: validate and enhance if needed.
    
    Returns:
        Tuple of (enhanced_html, validation_report)
    """
    validator = PrototypeValidator()
    is_valid, issues, score = validator.validate(html, feature_name)
    
    report = {
        'is_valid': is_valid,
        'issues': issues,
        'quality_score': score,
        'enhanced': False
    }
    
    # CRITICAL: If score is 0 (not HTML at all), DO NOT enhance
    # This prevents wrapping meeting notes text as HTML
    if score == 0:
        report['error'] = 'Generated content is not HTML - model failed to follow instructions'
        return html, report  # Return as-is for debugging
    
    # If invalid but has some HTML structure, try to enhance
    if not is_valid and score < 60:
        html = validator.enhance_html_functionality(html, feature_name)
        report['enhanced'] = True
        
        # Re-validate
        is_valid_after, issues_after, score_after = validator.validate(html, feature_name)
        report['is_valid_after_enhancement'] = is_valid_after
        report['quality_score_after'] = score_after
    
    return html, report

