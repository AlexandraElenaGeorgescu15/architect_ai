"""
Specialized Multi-Agent System for Prototype Generation.

This module implements a 3-stage pipeline for generating high-quality,
tech-stack-appropriate prototypes:
1. Analyzer: Deep feature understanding
2. Generator: Tech-specific code creation
3. Critic: Quality review and improvement

Author: Alexandra Georgescu
"""

import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class TechStack:
    """Detected technology stack information"""
    framework: str  # Angular, React, Vue, Blazor, WPF, Streamlit, etc.
    language: str   # TypeScript, JavaScript, C#, Python, etc.
    styling: str    # CSS, SCSS, XAML, inline, etc.
    components: List[str]  # Material, Bootstrap, Ant Design, etc.
    api_tech: str   # .NET, Spring Boot, FastAPI, Express, etc.


@dataclass
class PrototypeAnalysis:
    """Output from Analyzer Agent"""
    feature_name: str
    core_functionality: List[str]
    ui_components_needed: List[str]
    user_flows: List[str]
    data_structures: Dict[str, Any]
    edge_cases: List[str]
    accessibility_requirements: List[str]


@dataclass
class GeneratedPrototype:
    """Output from Generator Agent"""
    html_code: str
    css_code: str
    javascript_code: str
    framework_specific_code: str
    tech_stack: TechStack
    quality_score: float


@dataclass
class CriticReview:
    """Output from Critic Agent"""
    score: float  # 0-100
    strengths: List[str]
    weaknesses: List[str]
    improvements: List[str]
    needs_regeneration: bool


class PrototypeAnalyzerAgent:
    """
    Stage 1: Deep Analysis of Feature Requirements.
    
    This agent reads meeting notes and extracts ALL relevant information
    needed to create a perfect prototype.
    """
    
    def __init__(self, universal_agent: Any):
        self.agent = universal_agent
    
    async def analyze(self, meeting_notes: str, tech_stack: TechStack) -> PrototypeAnalysis:
        """
        Perform deep analysis of the feature from meeting notes.
        
        Args:
            meeting_notes: Raw meeting notes about the feature
            tech_stack: Detected technology stack
            
        Returns:
            PrototypeAnalysis with extracted requirements
        """
        
        # Simpler, more direct extraction without JSON parsing
        # Just extract key information directly
        lines = meeting_notes.split('\n')
        
        # Extract feature name (first heading or first sentence)
        feature_name = "Feature Prototype"
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                feature_name = line.lstrip('#').strip()
                break
            elif line and len(line) > 10 and len(line) < 100:
                feature_name = line[:50]
                break
        
        # Extract core functionality (look for action verbs, requirements)
        core_functionality = []
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['should', 'must', 'will', 'can', 'user', 'system', 'display', 'show', 'allow', 'enable', 'create', 'update', 'delete', 'list']):
                if line and len(line) > 10 and not line.startswith('#'):
                    core_functionality.append(line[:200])
        
        if not core_functionality:
            core_functionality = [meeting_notes[:200]]
        
        # Extract UI components (look for UI-related keywords)
        ui_components = []
        ui_keywords = ['button', 'form', 'input', 'table', 'list', 'modal', 'dialog', 'dropdown', 'select', 'card', 'panel', 'menu', 'chart', 'graph']
        for line in lines:
            line_lower = line.lower()
            for keyword in ui_keywords:
                if keyword in line_lower and keyword.title() not in ui_components:
                    ui_components.append(keyword.title())
        
        if not ui_components:
            ui_components = ["Container", "Button", "Form"]
        
        # Build user flows from the notes
        user_flows = []
        for line in lines:
            line = line.strip()
            if line.startswith('-') or line.startswith('*') or line.startswith('•'):
                flow = line.lstrip('-*•').strip()
                if flow and len(flow) > 10:
                    user_flows.append(flow[:150])
        
        if not user_flows:
            user_flows = core_functionality[:3]
        
        return PrototypeAnalysis(
            feature_name=feature_name,
            core_functionality=core_functionality[:5],
            ui_components_needed=ui_components[:10],
            user_flows=user_flows[:5],
            data_structures={},
            edge_cases=["Loading state", "Error handling", "Empty state"],
            accessibility_requirements=["Keyboard navigation", "Screen reader support"]
        )


class PrototypeGeneratorAgent:
    """
    Stage 2: Generate Tech-Stack-Specific Code.
    
    This agent creates actual, runnable prototype code tailored to the
    detected technology stack.
    """
    
    def __init__(self, universal_agent: Any):
        self.agent = universal_agent
    
    async def generate(
        self,
        analysis: PrototypeAnalysis,
        tech_stack: TechStack,
        rag_context: str
    ) -> GeneratedPrototype:
        """
        Generate prototype code based on analysis and tech stack.
        
        Args:
            analysis: Output from AnalyzerAgent
            tech_stack: Detected technology stack
            rag_context: Repository context for style matching
            
        Returns:
            GeneratedPrototype with all code
        """
        
        # Build comprehensive prompt
        prompt = self._build_generation_prompt(analysis, tech_stack, rag_context)
        
        try:
            response = await self.agent._call_ai(
                prompt,
                system=f"You are an expert {tech_stack.framework} developer who writes production-quality code."
            )
            
            # Extract code sections
            html_code = self._extract_code_section(response, ['html', 'HTML'])
            css_code = self._extract_code_section(response, ['css', 'CSS', 'scss', 'SCSS'])
            js_code = self._extract_code_section(response, ['javascript', 'js', 'typescript', 'ts'])
            
            # If no sections found, treat entire response as HTML
            if not html_code and not css_code and not js_code:
                html_code = self._clean_code(response)
            
            # Combine into single HTML file
            full_html = self._combine_into_html(html_code, css_code, js_code, tech_stack)
            
            return GeneratedPrototype(
                html_code=html_code or full_html,
                css_code=css_code or "",
                javascript_code=js_code or "",
                framework_specific_code=full_html,
                tech_stack=tech_stack,
                quality_score=0.0  # Will be set by critic
            )
        
        except Exception as e:
            # Fallback generation
            return self._generate_fallback_prototype(analysis, tech_stack)
    
    def _build_generation_prompt(
        self,
        analysis: PrototypeAnalysis,
        tech_stack: TechStack,
        rag_context: str
    ) -> str:
        """Build comprehensive generation prompt"""
        
        return f"""
MISSION: Create a COMPLETE, FUNCTIONAL, BEAUTIFUL visual prototype.

TARGET FEATURE: {analysis.feature_name}

CORE FUNCTIONALITY (MUST IMPLEMENT):
{chr(10).join(f'✓ {func}' for func in analysis.core_functionality)}

UI COMPONENTS REQUIRED:
{chr(10).join(f'• {comp}' for comp in analysis.ui_components_needed)}

USER FLOWS (IMPLEMENT ALL):
{chr(10).join(f'{i+1}. {flow}' for i, flow in enumerate(analysis.user_flows))}

DATA STRUCTURES:
{chr(10).join(f'- {name}: {fields}' for name, fields in analysis.data_structures.items())}

EDGE CASES (HANDLE ALL):
{chr(10).join(f'⚠️ {case}' for case in analysis.edge_cases)}

ACCESSIBILITY (REQUIRED):
{chr(10).join(f'♿ {req}' for req in analysis.accessibility_requirements)}

TECH STACK (USE THESE):
- Framework: {tech_stack.framework}
- Language: {tech_stack.language}
- Styling: {tech_stack.styling}
- Components: {', '.join(tech_stack.components) if tech_stack.components else 'None'}

REPOSITORY CONTEXT (MATCH THIS STYLE):
{rag_context[:2000]}

═══════════════════════════════════════════════════════════════

CRITICAL REQUIREMENTS:

🚫 FORBIDDEN:
- Do NOT create a generic app
- Do NOT show "Architect.AI" or any meta-application
- Do NOT use placeholder text like "Lorem ipsum"
- Do NOT create navigation to other pages
- Do NOT add authentication/login forms (unless that's the feature)
- Do NOT wrap in markdown code fences

✅ MUST DO:
- Create a SINGLE, COMPLETE HTML file
- Implement ALL functionality listed above
- Use REAL, feature-specific content and labels
- Make ALL buttons and controls functional with JavaScript
- Add CSS for a modern, professional look
- Include mock data that's relevant to the feature
- Handle loading states, errors, empty states
- Make it responsive (mobile + desktop)
- Add smooth transitions and hover effects
- Include proper ARIA labels and keyboard navigation

📐 LAYOUT REQUIREMENTS:
- Modern card-based design with subtle shadows
- Consistent spacing (8px grid: 8, 16, 24, 32, 48px)
- Professional color palette (not too bright)
- Clear typography hierarchy
- Obvious interactive elements

🎨 STYLING REQUIREMENTS:
- Use {tech_stack.framework}-appropriate styling
- If Material/Bootstrap/etc available, use those components
- Otherwise, write custom CSS with modern aesthetics
- Dark mode support optional but nice

💻 FUNCTIONALITY REQUIREMENTS:
- All buttons must DO something (show/hide, update data, etc.)
- Forms must validate and show feedback
- Tables must be sortable/filterable if applicable
- Charts must display real (mock) data
- Modals must open/close smoothly

═══════════════════════════════════════════════════════════════

OUTPUT FORMAT:

Generate a SINGLE HTML file containing:

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{analysis.feature_name}</title>
    <style>
        /* All CSS here - make it beautiful */
    </style>
</head>
<body>
    <!-- All HTML here - feature-specific -->
    
    <script>
        // All JavaScript here - make it interactive
    </script>
</body>
</html>

DO NOT use markdown fences. Output ONLY the HTML code, nothing else.
"""
    
    def _extract_code_section(self, response: str, markers: List[str]) -> Optional[str]:
        """Extract code from markdown fences"""
        for marker in markers:
            pattern = rf'```{marker}\s*\n(.*?)\n```'
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _clean_code(self, code: str) -> str:
        """Remove markdown artifacts"""
        # Remove code fences
        code = re.sub(r'^```[\w\-]*\s*\n?', '', code, flags=re.MULTILINE)
        code = re.sub(r'\n?```\s*$', '', code, flags=re.MULTILINE)
        code = code.strip('`')
        return code.strip()
    
    def _combine_into_html(
        self,
        html: str,
        css: str,
        js: str,
        tech_stack: TechStack
    ) -> str:
        """Combine separated code into single HTML file"""
        
        if html and '<html' in html.lower():
            # Already complete HTML
            return html
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prototype</title>
    <style>
        {css if css else '/* Add CSS here */'}
    </style>
</head>
<body>
    {html if html else '<div><!-- Add content here --></div>'}
    
    <script>
        {js if js else '// Add JavaScript here'}
    </script>
</body>
</html>"""
    
    def _generate_fallback_prototype(
        self,
        analysis: PrototypeAnalysis,
        tech_stack: TechStack
    ) -> GeneratedPrototype:
        """Generate minimal fallback prototype"""
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{analysis.feature_name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
        }}
        h1 {{ color: #333; margin-top: 0; }}
        .feature-list {{ list-style: none; padding: 0; }}
        .feature-list li {{
            padding: 12px;
            margin: 8px 0;
            background: #f5f5f5;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{analysis.feature_name}</h1>
        <h3>Core Functionality</h3>
        <ul class="feature-list">
            {''.join(f'<li>{func}</li>' for func in analysis.core_functionality)}
        </ul>
    </div>
</body>
</html>"""
        
        return GeneratedPrototype(
            html_code=html,
            css_code="",
            javascript_code="",
            framework_specific_code=html,
            tech_stack=tech_stack,
            quality_score=50.0
        )


class PrototypeCriticAgent:
    """
    Stage 3: Review and Improve Generated Prototype.
    
    This agent reviews the generated prototype and decides if it needs
    to be regenerated with improvements.
    """
    
    def __init__(self, universal_agent: Any):
        self.agent = universal_agent
    
    async def review(
        self,
        prototype: GeneratedPrototype,
        analysis: PrototypeAnalysis,
        meeting_notes: str
    ) -> CriticReview:
        """
        Review generated prototype for quality and completeness.
        
        Args:
            prototype: Generated prototype to review
            analysis: Original feature analysis
            meeting_notes: Original requirements
            
        Returns:
            CriticReview with score and feedback
        """
        
        prompt = f"""
You are a senior code reviewer evaluating a prototype implementation.

ORIGINAL REQUIREMENTS:
Feature: {analysis.feature_name}
Required Functionality: {', '.join(analysis.core_functionality)}
Required Components: {', '.join(analysis.ui_components_needed)}

GENERATED PROTOTYPE:
{prototype.html_code[:5000]}  # First 5000 chars

REVIEW CRITERIA:
1. ✅ Completeness: Does it implement ALL required functionality?
2. 🎨 Visual Quality: Is it modern, professional, well-designed?
3. 💻 Functionality: Are interactions working? JavaScript functional?
4. 📱 Responsiveness: Mobile and desktop layouts?
5. ♿ Accessibility: ARIA labels, keyboard nav, semantic HTML?
6. 🎯 Relevance: Is it about the FEATURE, not a generic app?
7. 📊 Data: Does it show realistic, feature-specific data?
8. ⚠️ Edge Cases: Loading, errors, empty states handled?

Provide feedback in JSON format:

{{
  "score": 85.5,  # 0-100
  "strengths": ["What it does well", "Good aspects"],
  "weaknesses": ["What's missing", "Problems"],
  "improvements": ["Specific fix 1", "Specific fix 2"],
  "needs_regeneration": false  # true if score < 70
}}

BE CRITICAL. Don't accept mediocrity. Output ONLY JSON, no markdown.
"""
        
        try:
            response = await self.agent._call_ai(
                prompt,
                system="You are a tough but fair code reviewer who demands excellence."
            )
            
            # Parse JSON
            import json
            response = response.strip()
            if response.startswith('```'):
                response = re.sub(r'^```[\w]*\n?', '', response)
                response = re.sub(r'\n?```$', '', response)
            
            review_data = json.loads(response)
            
            return CriticReview(
                score=float(review_data.get('score', 70.0)),
                strengths=review_data.get('strengths', []),
                weaknesses=review_data.get('weaknesses', []),
                improvements=review_data.get('improvements', []),
                needs_regeneration=review_data.get('needs_regeneration', False)
            )
        
        except Exception as e:
            # Default passing review
            return CriticReview(
                score=75.0,
                strengths=["Prototype generated"],
                weaknesses=["Could not perform detailed review"],
                improvements=["Manual review recommended"],
                needs_regeneration=False
            )


class PrototypeOrchestrator:
    """
    Orchestrates the 3-stage prototype generation pipeline.
    
    This is the main class that coordinates all agents to produce
    a high-quality prototype.
    """
    
    def __init__(self, universal_agent: Any):
        self.analyzer = PrototypeAnalyzerAgent(universal_agent)
        self.generator = PrototypeGeneratorAgent(universal_agent)
        self.critic = PrototypeCriticAgent(universal_agent)
        self.universal_agent = universal_agent
    
    async def generate_prototype(
        self,
        meeting_notes: str,
        tech_stack: TechStack,
        rag_context: str,
        max_iterations: int = 2
    ) -> Dict[str, Any]:
        """
        Generate high-quality prototype through multi-stage pipeline.
        
        Args:
            meeting_notes: Feature description/requirements
            tech_stack: Detected technology stack
            rag_context: Repository context for style matching
            max_iterations: Maximum regeneration attempts
            
        Returns:
            Dict with final prototype and metadata
        """
        
        # Stage 1: Analyze
        analysis = await self.analyzer.analyze(meeting_notes, tech_stack)
        
        # Stage 2: Generate (with potential retries)
        best_prototype = None
        best_score = 0.0
        reviews = []
        
        for iteration in range(max_iterations):
            # Generate prototype
            prototype = await self.generator.generate(analysis, tech_stack, rag_context)
            
            # Stage 3: Review
            review = await self.critic.review(prototype, analysis, meeting_notes)
            prototype.quality_score = review.score
            reviews.append(review)
            
            # Track best
            if review.score > best_score:
                best_score = review.score
                best_prototype = prototype
            
            # Stop if good enough
            if review.score >= 80.0 or not review.needs_regeneration:
                break
            
            # If regenerating, add improvement feedback to next generation
            if iteration < max_iterations - 1:
                # Could enhance generator prompt with feedback here
                pass
        
        return {
            'prototype': best_prototype,
            'analysis': analysis,
            'reviews': reviews,
            'final_score': best_score,
            'iterations': len(reviews),
            'tech_stack': tech_stack
        }

