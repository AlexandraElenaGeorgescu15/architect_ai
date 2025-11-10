"""
Enhanced Prototype Generator - Reliable Multi-Stage System

This module provides a lightweight, reliable approach to generating
high-quality visual prototypes through multiple focused prompts.

Author: Alexandra Georgescu
"""

import asyncio
from typing import Optional, Dict, Any
from pathlib import Path


class EnhancedPrototypeGenerator:
    """
    Generates high-quality prototypes through 2-stage process:
    1. Requirements extraction (simple parsing, no AI)
    2. Focused HTML generation (single strong prompt)
    """
    
    def __init__(self, agent: Any):
        self.agent = agent
    
    def extract_requirements(self, meeting_notes: str) -> Dict[str, Any]:
        """
        Extract requirements from meeting notes WITHOUT AI.
        Simple, fast, reliable parsing.
        """
        lines = meeting_notes.split('\n')
        
        # Extract feature name (first meaningful line or heading)
        feature_name = "Feature Prototype"
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                feature_name = line.lstrip('#').strip()
                break
            elif line and len(line) > 10 and len(line) < 100 and not line.startswith('-'):
                feature_name = line
                break
        
        # Extract all meaningful lines
        requirements = []
        for line in lines:
            line = line.strip()
            if line and len(line) > 15 and not line.startswith('#'):
                requirements.append(line)
        
        # Extract UI elements mentioned
        ui_keywords = {
            'button': 'Button',
            'form': 'Form',
            'input': 'Input Field',
            'table': 'Table',
            'list': 'List',
            'modal': 'Modal/Dialog',
            'dropdown': 'Dropdown',
            'select': 'Select',
            'card': 'Card',
            'chart': 'Chart',
            'graph': 'Graph',
            'search': 'Search Bar',
            'filter': 'Filter',
            'tab': 'Tabs',
            'menu': 'Menu',
            'nav': 'Navigation'
        }
        
        ui_elements = set()
        notes_lower = meeting_notes.lower()
        for keyword, element in ui_keywords.items():
            if keyword in notes_lower:
                ui_elements.add(element)
        
        # Build structured requirements
        return {
            'feature_name': feature_name,
            'full_notes': meeting_notes[:2000],  # First 2000 chars
            'requirements': requirements[:10],  # Top 10 requirements
            'ui_elements': list(ui_elements),
            'has_form': 'form' in notes_lower or 'input' in notes_lower,
            'has_table': 'table' in notes_lower or 'list' in notes_lower,
            'has_modal': 'modal' in notes_lower or 'dialog' in notes_lower or 'popup' in notes_lower,
            'has_chart': 'chart' in notes_lower or 'graph' in notes_lower or 'visualization' in notes_lower
        }
    
    async def generate_html(self, requirements: Dict[str, Any]) -> str:
        """
        Generate HTML using WORLD-CLASS prompt template.
        This is the absolute best prototype generation system.
        """
        
        # Use the world-class prompt template
        from components.world_class_prototype_prompt import build_world_class_prompt
        
        prompt = build_world_class_prompt(
            feature_name=requirements['feature_name'],
            full_context=requirements['full_notes'],
            ui_elements=requirements['ui_elements'],
            requirements=requirements['requirements']
        )
        
        # Generate HTML with proper system prompt
        # ✅ FIXED: Pass artifact_type to enable smart generator
        html = await self.agent._call_ai(
            prompt,
            system_prompt=f"You are an expert frontend developer creating a functional, beautiful prototype for: {requirements['feature_name']}. Output ONLY valid HTML code, no explanations.",
            artifact_type="html_diagram"  # Enable smart generator with local-first + validation
        )
        
        return html
    
    async def generate_prototype(self, meeting_notes: str) -> str:
        """
        Main entry point: Extract requirements + Generate HTML + Validate & Enhance.
        
        Args:
            meeting_notes: Raw meeting notes about the feature
            
        Returns:
            Complete, validated, functional HTML string
        """
        # Stage 1: Extract requirements (fast, no AI)
        requirements = self.extract_requirements(meeting_notes)
        
        # Stage 2: Generate focused HTML (single AI call)
        html = await self.generate_html(requirements)
        
        # Stage 3: Validate and enhance to ensure functionality
        from components.prototype_validator import validate_and_enhance
        
        html, validation_report = validate_and_enhance(
            html,
            requirements['feature_name']
        )
        
        # Log validation results
        print(f"[Prototype Validation] Score: {validation_report['quality_score']}/100")
        if validation_report.get('enhanced'):
            print(f"[Prototype Validation] Enhanced to fix issues")
        if validation_report.get('issues'):
            print(f"[Prototype Validation] Issues: {', '.join(validation_report['issues'][:3])}")
        
        return html


def generate_enhanced_prototype(agent: Any, meeting_notes: str) -> str:
    """
    Convenience function for generating prototypes.
    
    Args:
        agent: UniversalArchitectAgent instance
        meeting_notes: Meeting notes content
        
    Returns:
        Generated HTML
    """
    generator = EnhancedPrototypeGenerator(agent)
    html = asyncio.run(generator.generate_prototype(meeting_notes))
    return html

