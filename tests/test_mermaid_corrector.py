#!/usr/bin/env python3
"""
Test script for Mermaid Syntax Corrector
Demonstrates the functionality of the Mermaid syntax correction system
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.mermaid_syntax_corrector import mermaid_corrector


async def test_mermaid_corrector():
    """Test the Mermaid syntax corrector with various examples"""
    
    print("Testing Mermaid Syntax Corrector")
    print("=" * 50)
    
    # Test cases with common syntax errors
    test_cases = [
        {
            "name": "Flowchart with missing direction",
            "content": """flowchart
    A[Start] --> B[Process]
    B --> C[End]""",
            "expected_fixes": ["missing_direction"]
        },
        {
            "name": "Graph with unmatched quotes",
            "content": """graph TD
    A["Start] --> B[Process]
    B --> C[End]""",
            "expected_fixes": ["unmatched_quotes"]
        },
        {
            "name": "Sequence diagram with missing participants",
            "content": """sequenceDiagram
    A->>B: Hello
    B-->>A: Hi""",
            "expected_fixes": ["missing_participants"]
        },
        {
            "name": "Valid flowchart (should pass)",
            "content": """flowchart TD
    A[Start] --> B[Process]
    B --> C[End]""",
            "expected_fixes": []
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print("-" * 30)
        
        print("Original:")
        print(test_case['content'])
        
        # Run correction
        result = await mermaid_corrector.correct_diagram(test_case['content'], f"test_{i}")
        
        print(f"\nValid: {result.is_valid}")
        print(f"Corrections applied: {len(result.corrections_applied)}")
        
        if result.errors_found:
            print("Errors found:")
            for error in result.errors_found:
                print(f"  - Line {error.line_number}: {error.description}")
                print(f"    Fix: {error.suggested_fix}")
        
        if result.corrections_applied:
            print("Corrections applied:")
            for correction in result.corrections_applied:
                print(f"  - {correction}")
        
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
        
        print("\nCorrected diagram:")
        print(result.corrected_diagram)
        
        print("\n" + "=" * 50)


async def test_diagram_types():
    """Test different diagram types"""
    
    print("\nTesting Different Diagram Types")
    print("=" * 50)
    
    diagram_types = [
        {
            "name": "Flowchart",
            "content": """flowchart TD
    A[Start] --> B[Process]
    B --> C[End]"""
        },
        {
            "name": "Sequence Diagram",
            "content": """sequenceDiagram
    participant A
    participant B
    A->>B: Hello
    B-->>A: Hi"""
        },
        {
            "name": "Class Diagram",
            "content": """classDiagram
    class Animal {
        +String name
        +makeSound()
    }
    class Dog {
        +bark()
    }
    Animal <|-- Dog"""
        },
        {
            "name": "State Diagram",
            "content": """stateDiagram-v2
    [*] --> Still
    Still --> [*]
    Still --> Moving
    Moving --> Still"""
        },
        {
            "name": "ER Diagram",
            "content": """erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
    CUSTOMER {
        string name
        string email
    }"""
        }
    ]
    
    for diagram in diagram_types:
        print(f"\n{diagram['name']}")
        print("-" * 20)
        
        result = await mermaid_corrector.correct_diagram(diagram['content'], diagram['name'].lower())
        
        print(f"Valid: {result.is_valid}")
        if result.errors_found:
            print(f"Errors: {len(result.errors_found)}")
        if result.corrections_applied:
            print(f"Corrections: {len(result.corrections_applied)}")
        
        print("Result:")
        print(result.corrected_diagram)


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(test_mermaid_corrector())
        asyncio.run(test_diagram_types())
        print("\nAll tests completed successfully!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
