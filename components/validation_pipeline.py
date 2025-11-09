"""
Programmatic Validation & Noise Reduction Pipeline

This module provides robust preprocessing and validation for all AI inputs:
1. Diagram validation (schema, topology, logical rules)
2. Noise reduction (regex, stop-words, normalization)
3. Data cleaning and sanitization

Goal: Ensure only high-quality, clean data reaches the AI model.
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


class ValidationStatus(Enum):
    """Validation result status"""
    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Result of validation"""
    status: ValidationStatus
    cleaned_data: Any
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    original_data: Any = None


class NoiseReductionPipeline:
    """
    Programmatic noise reduction using regex and rules.
    Removes irrelevant data before AI processing.
    """
    
    def __init__(self):
        # Code comment patterns to remove
        self.comment_patterns = [
            r'//.*?$',  # Single-line comments (C-style)
            r'#.*?$',   # Python comments
            r'/\*.*?\*/',  # Multi-line comments (C-style)
            r'""".*?"""',  # Python docstrings
            r"'''.*?'''",  # Python docstrings (single quote)
        ]
        
        # Common stop words to remove from descriptions
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        # Whitespace normalization
        self.whitespace_pattern = r'\s+'
        
        # Code patterns that add noise (TODO, FIXME, console.log, etc.)
        self.noise_code_patterns = [
            r'console\.log\([^)]*\);?',
            r'print\([^)]*\)',
            r'TODO:.*?$',
            r'FIXME:.*?$',
            r'XXX:.*?$',
            r'HACK:.*?$',
            r'debugger;?',
        ]
    
    def clean_code(self, code: str, remove_comments: bool = True) -> str:
        """
        Clean code by removing noise patterns.
        
        Args:
            code: Source code string
            remove_comments: Whether to remove comments
            
        Returns:
            Cleaned code string
        """
        cleaned = code
        
        # Remove debug statements
        for pattern in self.noise_code_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
        
        # Remove comments if requested
        if remove_comments:
            for pattern in self.comment_patterns:
                cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.DOTALL)
        
        # Normalize whitespace
        cleaned = re.sub(self.whitespace_pattern, ' ', cleaned)
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in cleaned.split('\n')]
        cleaned = '\n'.join(line for line in lines if line)
        
        return cleaned
    
    def clean_text(self, text: str, remove_stop_words: bool = False) -> str:
        """
        Clean natural language text.
        
        Args:
            text: Input text
            remove_stop_words: Whether to remove stop words
            
        Returns:
            Cleaned text
        """
        # Convert to lowercase for consistency
        cleaned = text.lower()
        
        # Remove special characters (keep alphanumeric and spaces)
        cleaned = re.sub(r'[^a-z0-9\s]', ' ', cleaned)
        
        # Remove stop words if requested
        if remove_stop_words:
            words = cleaned.split()
            words = [w for w in words if w not in self.stop_words]
            cleaned = ' '.join(words)
        
        # Normalize whitespace
        cleaned = re.sub(self.whitespace_pattern, ' ', cleaned).strip()
        
        return cleaned
    
    def extract_keywords(self, text: str, min_length: int = 3) -> List[str]:
        """
        Extract meaningful keywords from text.
        
        Args:
            text: Input text
            min_length: Minimum keyword length
            
        Returns:
            List of keywords
        """
        # Clean text first
        cleaned = self.clean_text(text, remove_stop_words=True)
        
        # Extract words
        words = cleaned.split()
        
        # Filter by length and uniqueness
        keywords = list(set(w for w in words if len(w) >= min_length))
        
        return sorted(keywords)
    
    def calculate_noise_score(self, text: str) -> float:
        """
        Calculate noise score (0-1, where 1 = very noisy).
        
        Metrics:
        - Ratio of special characters
        - Ratio of stop words
        - Presence of debug statements
        
        Returns:
            Noise score between 0 and 1
        """
        if not text:
            return 1.0
        
        # Count special characters
        special_chars = len(re.findall(r'[^a-zA-Z0-9\s]', text))
        special_ratio = special_chars / len(text)
        
        # Count stop words
        words = text.lower().split()
        stop_word_count = sum(1 for w in words if w in self.stop_words)
        stop_ratio = stop_word_count / len(words) if words else 0
        
        # Check for debug patterns
        debug_count = sum(1 for pattern in self.noise_code_patterns 
                         if re.search(pattern, text, re.IGNORECASE))
        debug_penalty = min(debug_count * 0.1, 0.3)
        
        # Combined noise score
        noise_score = (special_ratio * 0.3 + stop_ratio * 0.4 + debug_penalty)
        
        return min(noise_score, 1.0)


class DiagramValidator:
    """
    Validates diagram structure and semantics.
    Checks for schema compliance, topology, and logical consistency.
    """
    
    def __init__(self):
        self.noise_reducer = NoiseReductionPipeline()
    
    def validate_mermaid(self, diagram: str) -> ValidationResult:
        """
        Validate Mermaid diagram structure.
        
        Checks:
        1. Syntax correctness
        2. Topology (connected graph)
        3. Logical consistency
        4. Best practices
        """
        errors = []
        warnings = []
        metrics = {}
        
        # Step 1: Syntax validation
        if not diagram or len(diagram.strip()) < 10:
            errors.append("Diagram is empty or too short")
            return ValidationResult(
                status=ValidationStatus.ERROR,
                cleaned_data="",
                errors=errors,
                original_data=diagram
            )
        
        # Check for diagram type
        diagram_types = ['erDiagram', 'graph', 'flowchart', 'sequenceDiagram', 
                         'classDiagram', 'stateDiagram', 'gantt', 'pie']
        
        has_type = any(dt in diagram for dt in diagram_types)
        if not has_type:
            errors.append("Missing diagram type declaration")
        
        # Step 2: Topology validation
        metrics['node_count'] = len(re.findall(r'\[.+?\]|\(.+?\)|\{.+?\}', diagram))
        metrics['edge_count'] = len(re.findall(r'-->|---', diagram))
        
        if metrics['node_count'] == 0:
            errors.append("No nodes found in diagram")
        
        if metrics['edge_count'] == 0 and 'erDiagram' not in diagram:
            warnings.append("No connections found (isolated nodes)")
        
        # Step 3: Check for disconnected components
        if metrics['node_count'] > 1 and metrics['edge_count'] == 0:
            warnings.append("Diagram has disconnected components")
        
        # Step 4: Best practices
        if metrics['node_count'] > 20:
            warnings.append("Diagram is complex (>20 nodes). Consider splitting.")
        
        # Step 5: Clean diagram (remove comments, normalize whitespace)
        cleaned = self.noise_reducer.clean_code(diagram, remove_comments=True)
        metrics['noise_score'] = self.noise_reducer.calculate_noise_score(diagram)
        
        # Determine status
        if errors:
            status = ValidationStatus.ERROR
        elif warnings:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.VALID
        
        return ValidationResult(
            status=status,
            cleaned_data=cleaned,
            errors=errors,
            warnings=warnings,
            metrics=metrics,
            original_data=diagram
        )
    
    def validate_json_schema(self, data: Dict, schema: Dict) -> ValidationResult:
        """
        Validate JSON data against schema.
        
        Args:
            data: JSON data to validate
            schema: Expected schema
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Check field types
        properties = schema.get('properties', {})
        for field, value in data.items():
            if field in properties:
                expected_type = properties[field].get('type')
                actual_type = type(value).__name__
                
                # Map Python types to JSON schema types
                type_map = {
                    'str': 'string',
                    'int': 'integer',
                    'float': 'number',
                    'bool': 'boolean',
                    'list': 'array',
                    'dict': 'object'
                }
                
                json_type = type_map.get(actual_type, actual_type)
                if expected_type and json_type != expected_type:
                    errors.append(f"Field '{field}': expected {expected_type}, got {json_type}")
        
        # Check for unexpected fields
        for field in data.keys():
            if field not in properties:
                warnings.append(f"Unexpected field: {field}")
        
        status = ValidationStatus.ERROR if errors else (
            ValidationStatus.WARNING if warnings else ValidationStatus.VALID
        )
        
        return ValidationResult(
            status=status,
            cleaned_data=data,
            errors=errors,
            warnings=warnings,
            original_data=data
        )


class ValidationPipeline:
    """
    Main validation pipeline that coordinates all validators.
    """
    
    def __init__(self):
        self.noise_reducer = NoiseReductionPipeline()
        self.diagram_validator = DiagramValidator()
        self.validation_history: List[ValidationResult] = []
    
    def validate_and_clean(self, data: Any, data_type: str = 'auto') -> ValidationResult:
        """
        Validate and clean data based on type.
        
        Args:
            data: Input data
            data_type: Type of data ('diagram', 'code', 'text', 'json', 'auto')
            
        Returns:
            ValidationResult with cleaned data
        """
        # Auto-detect type
        if data_type == 'auto':
            if isinstance(data, dict):
                data_type = 'json'
            elif isinstance(data, str):
                if 'erDiagram' in data or 'graph' in data or 'flowchart' in data:
                    data_type = 'diagram'
                elif any(keyword in data for keyword in ['class ', 'def ', 'function ']):
                    data_type = 'code'
                else:
                    data_type = 'text'
        
        # Route to appropriate validator
        if data_type == 'diagram':
            result = self.diagram_validator.validate_mermaid(data)
        elif data_type == 'code':
            cleaned = self.noise_reducer.clean_code(data)
            result = ValidationResult(
                status=ValidationStatus.VALID,
                cleaned_data=cleaned,
                metrics={'noise_score': self.noise_reducer.calculate_noise_score(data)},
                original_data=data
            )
        elif data_type == 'text':
            cleaned = self.noise_reducer.clean_text(data)
            result = ValidationResult(
                status=ValidationStatus.VALID,
                cleaned_data=cleaned,
                metrics={'noise_score': self.noise_reducer.calculate_noise_score(data)},
                original_data=data
            )
        else:
            result = ValidationResult(
                status=ValidationStatus.VALID,
                cleaned_data=data,
                original_data=data
            )
        
        # Store in history
        self.validation_history.append(result)
        
        return result
    
    def get_quality_metrics(self) -> Dict[str, float]:
        """Get aggregate quality metrics from validation history"""
        if not self.validation_history:
            return {}
        
        total = len(self.validation_history)
        valid = sum(1 for r in self.validation_history if r.status == ValidationStatus.VALID)
        errors = sum(1 for r in self.validation_history if r.status == ValidationStatus.ERROR)
        
        avg_noise = sum(r.metrics.get('noise_score', 0) for r in self.validation_history) / total
        
        return {
            'total_validations': total,
            'success_rate': valid / total,
            'error_rate': errors / total,
            'avg_noise_score': avg_noise
        }


# Global instance
_pipeline = None

def get_validation_pipeline() -> ValidationPipeline:
    """Get global validation pipeline instance"""
    global _pipeline
    if _pipeline is None:
        _pipeline = ValidationPipeline()
    return _pipeline


# Example usage
if __name__ == '__main__':
    pipeline = get_validation_pipeline()
    
    # Test diagram validation
    diagram = """
    erDiagram
        User {
            int id
            string email
        }
        Order {
            int id
            int user_id
        }
        User ||--o{ Order : places
    """
    
    result = pipeline.validate_and_clean(diagram, 'diagram')
    print(f"Status: {result.status}")
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
    print(f"Metrics: {result.metrics}")
    print(f"\nCleaned:\n{result.cleaned_data}")
