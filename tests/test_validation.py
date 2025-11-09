#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive unit tests for validation/output_validator.py
Tests artifact validation and quality scoring
Target: 90%+ coverage
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from validation.output_validator import ArtifactValidator, ValidationResult


class TestArtifactValidator(unittest.TestCase):
    """Test suite for ArtifactValidator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = ArtifactValidator()
    
    def test_initialization(self):
        """Test validator initialization"""
        self.assertIsNotNone(self.validator)
        self.assertTrue(hasattr(self.validator, 'validate'))
    
    def test_validate_erd_valid(self):
        """Test validation of valid ERD"""
        valid_erd = """erDiagram
    USER ||--o{ ORDER : places
    ORDER ||--|{ LINE_ITEM : contains
    
    USER {
        int id PK
        string email
        string name
    }
    
    ORDER {
        int id PK
        int user_id FK
        date order_date
    }
    
    LINE_ITEM {
        int id PK
        int order_id FK
        string product
        int quantity
    }
"""
        
        result = self.validator.validate("erd", valid_erd, {})
        
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        self.assertGreater(result.score, 60)  # Should pass validation threshold
        self.assertIsInstance(result.errors, list)
        self.assertIsInstance(result.warnings, list)
    
    def test_validate_erd_invalid(self):
        """Test validation of invalid ERD"""
        invalid_erd = "This is not a valid ERD"
        
        result = self.validator.validate("erd", invalid_erd, {})
        
        self.assertIsInstance(result, ValidationResult)
        self.assertFalse(result.is_valid)
        self.assertLess(result.score, 60)  # Should fail validation
        self.assertGreater(len(result.errors), 0)  # Should have errors
    
    def test_validate_architecture_valid(self):
        """Test validation of valid architecture diagram"""
        valid_arch = """graph TD
    A[User Interface] --> B[API Gateway]
    B --> C[Authentication Service]
    B --> D[Business Logic]
    D --> E[Database]
    C --> E
"""
        
        result = self.validator.validate("architecture", valid_arch, {})
        
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        self.assertGreater(result.score, 60)
    
    def test_validate_empty_input(self):
        """Test validation of empty input"""
        result = self.validator.validate("erd", "", {})
        
        self.assertIsInstance(result, ValidationResult)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.score, 0)
    
    def test_validate_flowchart_valid(self):
        """Test validation of valid flowchart"""
        valid_flowchart = """flowchart TD
    Start([Start]) --> Input[Get User Input]
    Input --> Process[Process Data]
    Process --> Decision{Valid?}
    Decision -->|Yes| Success[Success]
    Decision -->|No| Error[Show Error]
    Error --> Input
    Success --> End([End])
"""
        
        result = self.validator.validate("flowchart", valid_flowchart, {})
        
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        self.assertGreater(result.score, 60)
    
    def test_validate_sequence_diagram_valid(self):
        """Test validation of valid sequence diagram"""
        valid_sequence = """sequenceDiagram
    participant User
    participant API
    participant DB
    
    User->>API: Login Request
    API->>DB: Validate Credentials
    DB-->>API: Credentials Valid
    API-->>User: Login Success
"""
        
        result = self.validator.validate("sequence_diagram", valid_sequence, {})
        
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        self.assertGreater(result.score, 60)
    
    def test_validation_result_properties(self):
        """Test ValidationResult properties"""
        result = ValidationResult(
            is_valid=True,
            score=85.0,
            errors=[],
            warnings=["Minor formatting issue"],
            suggestions=["Consider adding more details"],
            content="test content"
        )
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.score, 85.0)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(len(result.suggestions), 1)
        self.assertEqual(result.content, "test content")
    
    def test_score_ranges(self):
        """Test that scores are within valid range (0-100)"""
        test_cases = [
            ("erd", "erDiagram\n    USER ||--o{ ORDER : places"),
            ("architecture", "graph TD\n    A --> B"),
            ("flowchart", "flowchart TD\n    Start --> End"),
        ]
        
        for artifact_type, content in test_cases:
            result = self.validator.validate(artifact_type, content, {})
            self.assertGreaterEqual(result.score, 0)
            self.assertLessEqual(result.score, 100)
    
    def test_validate_with_context(self):
        """Test validation with additional context"""
        erd = "erDiagram\n    USER ||--o{ ORDER : places"
        context = {
            "meeting_notes": "Create a user and order system",
            "rag_context": "class User:\n    pass"
        }
        
        result = self.validator.validate("erd", erd, context)
        
        self.assertIsInstance(result, ValidationResult)
        # Validation should work with context
        self.assertIsInstance(result.score, (int, float))
    
    def test_validate_unknown_artifact_type(self):
        """Test validation of unknown artifact type"""
        result = self.validator.validate("unknown_type", "content", {})
        
        # Should handle gracefully
        self.assertIsInstance(result, ValidationResult)
        # Might have lower score or errors
        self.assertIsInstance(result.score, (int, float))


class TestValidationEdgeCases(unittest.TestCase):
    """Test edge cases in validation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = ArtifactValidator()
    
    def test_very_long_content(self):
        """Test validation of very long content"""
        long_erd = "erDiagram\n" + "    USER ||--o{ ORDER : places\n" * 1000
        
        result = self.validator.validate("erd", long_erd, {})
        
        # Should handle without crashing
        self.assertIsInstance(result, ValidationResult)
    
    def test_special_characters(self):
        """Test validation with special characters"""
        erd_with_special = """erDiagram
    USER ||--o{ ORDER : "places"
    USER {
        string name "User's Name"
        string email "user@example.com"
    }
"""
        
        result = self.validator.validate("erd", erd_with_special, {})
        
        # Should handle special characters
        self.assertIsInstance(result, ValidationResult)
    
    def test_unicode_content(self):
        """Test validation with Unicode characters"""
        erd_with_unicode = """erDiagram
    USUARIO ||--o{ PEDIDO : "realiza"
    USUARIO {
        int id PK
        string nombre
    }
"""
        
        result = self.validator.validate("erd", erd_with_unicode, {})
        
        # Should handle Unicode
        self.assertIsInstance(result, ValidationResult)
    
    def test_malformed_mermaid_syntax(self):
        """Test various malformed Mermaid syntaxes"""
        malformed_cases = [
            "erDiagram\n    USER ||-- INVALID",  # Missing relationship type
            "erDiagram\n    {",  # Incomplete syntax
            "erDiagram\n    USER",  # Missing relationship
            "",  # Empty
            "random text",  # Not Mermaid at all
        ]
        
        for content in malformed_cases:
            result = self.validator.validate("erd", content, {})
            # Should handle gracefully, likely with low score
            self.assertIsInstance(result, ValidationResult)
            self.assertIsInstance(result.score, (int, float))


class TestValidationResult(unittest.TestCase):
    """Test ValidationResult dataclass"""
    
    def test_create_validation_result(self):
        """Test creating ValidationResult"""
        result = ValidationResult(
            is_valid=True,
            score=90.0,
            errors=[],
            warnings=[],
            suggestions=[],
            content="test"
        )
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.score, 90.0)
        self.assertEqual(result.content, "test")
    
    def test_validation_result_with_errors(self):
        """Test ValidationResult with errors"""
        result = ValidationResult(
            is_valid=False,
            score=30.0,
            errors=["Missing entities", "Invalid syntax"],
            warnings=["Formatting issue"],
            suggestions=["Add more entities"],
            content="test"
        )
        
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 2)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(len(result.suggestions), 1)


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)


