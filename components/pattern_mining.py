"""
Pattern Mining System for Code Analysis

Extracts common patterns, anti-patterns, and architectural insights from codebases.
Identifies reusable patterns, code smells, and optimization opportunities.
"""

import os
import re
import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import streamlit as st


@dataclass
class CodePattern:
    """Represents a discovered code pattern"""
    name: str
    pattern_type: str  # "design_pattern", "anti_pattern", "idiom", "smell"
    description: str
    examples: List[str]
    frequency: int
    files: List[str]
    severity: str = "medium"  # "low", "medium", "high", "critical"
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class PatternAnalysis:
    """Results of pattern mining analysis"""
    patterns: List[CodePattern]
    metrics: Dict[str, Any]
    recommendations: List[str]
    code_quality_score: float


class PatternDetector:
    """Detects various code patterns and anti-patterns"""
    
    def __init__(self):
        self.patterns = []
        self.file_contents = {}
        
    def analyze_project(self, project_root: Path) -> PatternAnalysis:
        """Analyze project for patterns"""
        print(f"[INFO] Analyzing patterns in {project_root}")
        
        # Load all source files
        self._load_source_files(project_root)
        
        # Detect patterns
        patterns = []
        patterns.extend(self._detect_design_patterns())
        patterns.extend(self._detect_anti_patterns())
        patterns.extend(self._detect_code_smells())
        patterns.extend(self._detect_idioms())
        
        # Calculate metrics
        metrics = self._calculate_metrics(patterns)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(patterns)
        
        # Calculate code quality score
        quality_score = self._calculate_quality_score(patterns)
        
        return PatternAnalysis(
            patterns=patterns,
            metrics=metrics,
            recommendations=recommendations,
            code_quality_score=quality_score
        )
    
    def _load_source_files(self, project_root: Path):
        """Load all source files (intelligently excludes tool itself)"""
        from components._tool_detector import get_user_project_directories, should_exclude_path
        
        extensions = {'.py', '.ts', '.tsx', '.js', '.jsx', '.cs', '.java'}
        
        # Get user project directories (automatically excludes tool)
        user_dirs = get_user_project_directories()
        
        for user_dir in user_dirs:
            for file_path in user_dir.rglob('*'):
                if (file_path.is_file() and 
                    file_path.suffix in extensions and
                    not any(part.startswith('.') for part in file_path.parts) and
                    'node_modules' not in str(file_path) and
                    '__pycache__' not in str(file_path) and
                    not should_exclude_path(file_path)):
                    
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        self.file_contents[str(file_path)] = content
                    except Exception as e:
                        print(f"[WARN] Failed to read {file_path}: {e}")
    
    def _detect_design_patterns(self) -> List[CodePattern]:
        """Detect common design patterns"""
        patterns = []
        
        # Singleton Pattern
        singleton_files = []
        for file_path, content in self.file_contents.items():
            if self._is_singleton_pattern(content):
                singleton_files.append(file_path)
        
        if singleton_files:
            patterns.append(CodePattern(
                name="Singleton Pattern",
                pattern_type="design_pattern",
                description="Ensures a class has only one instance",
                examples=self._extract_singleton_examples(singleton_files),
                frequency=len(singleton_files),
                files=singleton_files,
                severity="medium",
                suggestions=["Consider if singleton is necessary", "Use dependency injection instead"]
            ))
        
        # Factory Pattern
        factory_files = []
        for file_path, content in self.file_contents.items():
            if self._is_factory_pattern(content):
                factory_files.append(file_path)
        
        if factory_files:
            patterns.append(CodePattern(
                name="Factory Pattern",
                pattern_type="design_pattern",
                description="Creates objects without specifying their exact class",
                examples=self._extract_factory_examples(factory_files),
                frequency=len(factory_files),
                files=factory_files,
                severity="low",
                suggestions=["Good use of abstraction", "Consider factory registry for multiple factories"]
            ))
        
        # Observer Pattern
        observer_files = []
        for file_path, content in self.file_contents.items():
            if self._is_observer_pattern(content):
                observer_files.append(file_path)
        
        if observer_files:
            patterns.append(CodePattern(
                name="Observer Pattern",
                pattern_type="design_pattern",
                description="Notifies multiple objects about state changes",
                examples=self._extract_observer_examples(observer_files),
                frequency=len(observer_files),
                files=observer_files,
                severity="low",
                suggestions=["Consider using event systems", "Be careful of memory leaks"]
            ))
        
        return patterns
    
    def _detect_anti_patterns(self) -> List[CodePattern]:
        """Detect anti-patterns"""
        patterns = []
        
        # God Class
        god_class_files = []
        for file_path, content in self.file_contents.items():
            if self._is_god_class(content):
                god_class_files.append(file_path)
        
        if god_class_files:
            patterns.append(CodePattern(
                name="God Class",
                pattern_type="anti_pattern",
                description="Class with too many responsibilities",
                examples=self._extract_god_class_examples(god_class_files),
                frequency=len(god_class_files),
                files=god_class_files,
                severity="high",
                suggestions=["Split into smaller classes", "Apply Single Responsibility Principle"]
            ))
        
        # Long Method
        long_method_files = []
        for file_path, content in self.file_contents.items():
            if self._is_long_method(content):
                long_method_files.append(file_path)
        
        if long_method_files:
            patterns.append(CodePattern(
                name="Long Method",
                pattern_type="anti_pattern",
                description="Methods that are too long and complex",
                examples=self._extract_long_method_examples(long_method_files),
                frequency=len(long_method_files),
                files=long_method_files,
                severity="medium",
                suggestions=["Break into smaller methods", "Extract helper functions"]
            ))
        
        # Duplicate Code
        duplicate_files = []
        for file_path, content in self.file_contents.items():
            if self._has_duplicate_code(content):
                duplicate_files.append(file_path)
        
        if duplicate_files:
            patterns.append(CodePattern(
                name="Duplicate Code",
                pattern_type="anti_pattern",
                description="Repeated code blocks across files",
                examples=self._extract_duplicate_examples(duplicate_files),
                frequency=len(duplicate_files),
                files=duplicate_files,
                severity="medium",
                suggestions=["Extract common functionality", "Create utility functions"]
            ))
        
        return patterns
    
    def _detect_code_smells(self) -> List[CodePattern]:
        """Detect code smells"""
        patterns = []
        
        # Magic Numbers
        magic_number_files = []
        for file_path, content in self.file_contents.items():
            if self._has_magic_numbers(content):
                magic_number_files.append(file_path)
        
        if magic_number_files:
            patterns.append(CodePattern(
                name="Magic Numbers",
                pattern_type="smell",
                description="Hard-coded numeric values without explanation",
                examples=self._extract_magic_number_examples(magic_number_files),
                frequency=len(magic_number_files),
                files=magic_number_files,
                severity="low",
                suggestions=["Use named constants", "Add comments explaining the values"]
            ))
        
        # Dead Code
        dead_code_files = []
        for file_path, content in self.file_contents.items():
            if self._has_dead_code(content):
                dead_code_files.append(file_path)
        
        if dead_code_files:
            patterns.append(CodePattern(
                name="Dead Code",
                pattern_type="smell",
                description="Unused code that can be removed",
                examples=self._extract_dead_code_examples(dead_code_files),
                frequency=len(dead_code_files),
                files=dead_code_files,
                severity="low",
                suggestions=["Remove unused imports", "Delete unused functions and variables"]
            ))
        
        # Complex Conditionals
        complex_condition_files = []
        for file_path, content in self.file_contents.items():
            if self._has_complex_conditionals(content):
                complex_condition_files.append(file_path)
        
        if complex_condition_files:
            patterns.append(CodePattern(
                name="Complex Conditionals",
                pattern_type="smell",
                description="Overly complex if/else statements",
                examples=self._extract_complex_conditional_examples(complex_condition_files),
                frequency=len(complex_condition_files),
                files=complex_condition_files,
                severity="medium",
                suggestions=["Simplify conditions", "Use guard clauses", "Extract boolean methods"]
            ))
        
        return patterns
    
    def _detect_idioms(self) -> List[CodePattern]:
        """Detect language-specific idioms"""
        patterns = []
        
        # Python-specific idioms
        python_idiom_files = []
        for file_path, content in self.file_contents.items():
            if file_path.endswith('.py') and self._has_python_idioms(content):
                python_idiom_files.append(file_path)
        
        if python_idiom_files:
            patterns.append(CodePattern(
                name="Python Idioms",
                pattern_type="idiom",
                description="Good Python-specific coding practices",
                examples=self._extract_python_idiom_examples(python_idiom_files),
                frequency=len(python_idiom_files),
                files=python_idiom_files,
                severity="low",
                suggestions=["Good use of Python features", "Consider list comprehensions", "Use context managers"]
            ))
        
        # TypeScript-specific idioms
        ts_idiom_files = []
        for file_path, content in self.file_contents.items():
            if file_path.endswith(('.ts', '.tsx')) and self._has_typescript_idioms(content):
                ts_idiom_files.append(file_path)
        
        if ts_idiom_files:
            patterns.append(CodePattern(
                name="TypeScript Idioms",
                pattern_type="idiom",
                description="Good TypeScript-specific coding practices",
                examples=self._extract_typescript_idiom_examples(ts_idiom_files),
                frequency=len(ts_idiom_files),
                files=ts_idiom_files,
                severity="low",
                suggestions=["Good use of types", "Consider interfaces", "Use strict mode"]
            ))
        
        return patterns
    
    # Pattern detection methods
    def _is_singleton_pattern(self, content: str) -> bool:
        """Check if code contains singleton pattern"""
        patterns = [
            r'class\s+\w+.*:\s*\n.*_instance\s*=',  # Single or double underscore
            r'def\s+__new__.*:\s*\n.*if.*_instance',  # Single or double underscore
            r'@singleton',
            r'getInstance\s*\(',
            r'_instance\s*=\s*None',  # Explicit None assignment
            r'if\s+cls\._instance\s+is\s+None',  # Explicit singleton check
        ]
        return any(re.search(pattern, content, re.MULTILINE | re.DOTALL) for pattern in patterns)
    
    def _is_factory_pattern(self, content: str) -> bool:
        """Check if code contains factory pattern"""
        patterns = [
            r'class\s+\w*Factory\w*',
            r'def\s+create_\w+',
            r'def\s+get_\w+.*:\s*\n.*return.*\(',
            r'factory\s*='
        ]
        return any(re.search(pattern, content, re.MULTILINE | re.DOTALL) for pattern in patterns)
    
    def _is_observer_pattern(self, content: str) -> bool:
        """Check if code contains observer pattern"""
        patterns = [
            r'notify\s*\(',
            r'addObserver\s*\(',
            r'removeObserver\s*\(',
            r'observers\s*=',
            r'@observer'
        ]
        return any(re.search(pattern, content, re.MULTILINE | re.DOTALL) for pattern in patterns)
    
    def _is_god_class(self, content: str) -> bool:
        """Check if class is too large (God Class)"""
        if not content.strip():
            return False
        
        lines = content.split('\n')
        if len(lines) < 50:
            return False
        
        # Check for large classes
        class_pattern = r'class\s+\w+.*:\s*\n(.*?)(?=\nclass|\n\w+\s*=|\Z)'
        matches = re.findall(class_pattern, content, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            class_lines = match.count('\n')
            if class_lines > 200:  # Large class threshold
                return True
        
        return False
    
    def _is_long_method(self, content: str) -> bool:
        """Check for long methods"""
        if not content.strip():
            return False
        
        # Check for methods with many lines
        method_pattern = r'def\s+\w+.*:\s*\n(.*?)(?=\ndef|\nclass|\Z)'
        matches = re.findall(method_pattern, content, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            method_lines = match.count('\n')
            if method_lines > 30:  # Long method threshold
                return True
        
        return False
    
    def _has_duplicate_code(self, content: str) -> bool:
        """Check for duplicate code blocks"""
        lines = content.split('\n')
        
        # Look for repeated blocks of 5+ lines
        for i in range(len(lines) - 10):
            block1 = lines[i:i+5]
            for j in range(i+5, len(lines) - 5):
                block2 = lines[j:j+5]
                if block1 == block2:
                    return True
        
        return False
    
    def _has_magic_numbers(self, content: str) -> bool:
        """Check for magic numbers"""
        # Look for standalone numbers (not in variable assignments)
        number_pattern = r'(?<!\w)\d+(?:\.\d+)?(?!\w)'
        numbers = re.findall(number_pattern, content)
        
        # Filter out common numbers (0, 1, 100, etc.)
        magic_numbers = [n for n in numbers if n not in ['0', '1', '100', '1000', '24', '60']]
        
        return len(magic_numbers) > 5  # Threshold for magic numbers
    
    def _has_dead_code(self, content: str) -> bool:
        """Check for dead code (unused imports, functions)"""
        # Check for unused imports (simplified)
        import_pattern = r'import\s+(\w+)'
        imports = re.findall(import_pattern, content)
        
        # Check if imports are used
        unused_imports = []
        for imp in imports:
            if imp not in content.replace(f'import {imp}', ''):
                unused_imports.append(imp)
        
        return len(unused_imports) > 2  # Threshold for dead code
    
    def _has_complex_conditionals(self, content: str) -> bool:
        """Check for complex conditionals"""
        # Look for nested if statements or complex boolean expressions
        if_pattern = r'if\s+.*:\s*\n.*if\s+.*:\s*\n.*if\s+.*:'
        return bool(re.search(if_pattern, content, re.MULTILINE | re.DOTALL))
    
    def _has_python_idioms(self, content: str) -> bool:
        """Check for Python idioms"""
        idioms = [
            r'with\s+\w+.*:',
            r'\[.*for.*in.*\]',
            r'lambda\s+\w+:',
            r'@\w+',
            r'__\w+__'
        ]
        return any(re.search(idiom, content) for idiom in idioms)
    
    def _has_typescript_idioms(self, content: str) -> bool:
        """Check for TypeScript idioms"""
        idioms = [
            r'interface\s+\w+',
            r'type\s+\w+\s*=',
            r':\s*\w+\[\]',
            r'async\s+\w+',
            r'Promise<\w+>'
        ]
        return any(re.search(idiom, content) for idiom in idioms)
    
    # Example extraction methods
    def _extract_singleton_examples(self, files: List[str]) -> List[str]:
        """Extract singleton pattern examples"""
        examples = []
        for file_path in files[:3]:  # Limit to 3 examples
            content = self.file_contents[file_path]
            # Extract relevant lines
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'singleton' in line.lower() or '__instance' in line:
                    start = max(0, i-2)
                    end = min(len(lines), i+3)
                    example = '\n'.join(lines[start:end])
                    examples.append(f"{file_path}:{i+1}\n{example}")
                    break
        return examples
    
    def _extract_factory_examples(self, files: List[str]) -> List[str]:
        """Extract factory pattern examples"""
        examples = []
        for file_path in files[:3]:
            content = self.file_contents[file_path]
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'factory' in line.lower() or 'create_' in line:
                    start = max(0, i-2)
                    end = min(len(lines), i+3)
                    example = '\n'.join(lines[start:end])
                    examples.append(f"{file_path}:{i+1}\n{example}")
                    break
        return examples
    
    def _extract_observer_examples(self, files: List[str]) -> List[str]:
        """Extract observer pattern examples"""
        examples = []
        for file_path in files[:3]:
            content = self.file_contents[file_path]
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'observer' in line.lower() or 'notify' in line.lower():
                    start = max(0, i-2)
                    end = min(len(lines), i+3)
                    example = '\n'.join(lines[start:end])
                    examples.append(f"{file_path}:{i+1}\n{example}")
                    break
        return examples
    
    def _extract_god_class_examples(self, files: List[str]) -> List[str]:
        """Extract god class examples"""
        examples = []
        for file_path in files[:2]:
            content = self.file_contents[file_path]
            lines = content.split('\n')
            # Find the largest class
            largest_class = ""
            max_lines = 0
            current_class = ""
            in_class = False
            
            for line in lines:
                if line.strip().startswith('class '):
                    if in_class and len(current_class.split('\n')) > max_lines:
                        largest_class = current_class
                        max_lines = len(current_class.split('\n'))
                    current_class = line
                    in_class = True
                elif in_class:
                    current_class += '\n' + line
            
            if largest_class:
                examples.append(f"{file_path}\n{largest_class[:200]}...")
        
        return examples
    
    def _extract_long_method_examples(self, files: List[str]) -> List[str]:
        """Extract long method examples"""
        examples = []
        for file_path in files[:2]:
            content = self.file_contents[file_path]
            lines = content.split('\n')
            # Find the longest method
            longest_method = ""
            max_lines = 0
            current_method = ""
            in_method = False
            
            for line in lines:
                if line.strip().startswith('def '):
                    if in_method and len(current_method.split('\n')) > max_lines:
                        longest_method = current_method
                        max_lines = len(current_method.split('\n'))
                    current_method = line
                    in_method = True
                elif in_method and line.strip() and not line.startswith(' '):
                    in_method = False
                elif in_method:
                    current_method += '\n' + line
            
            if longest_method:
                examples.append(f"{file_path}\n{longest_method[:200]}...")
        
        return examples
    
    def _extract_duplicate_examples(self, files: List[str]) -> List[str]:
        """Extract duplicate code examples"""
        examples = []
        for file_path in files[:2]:
            content = self.file_contents[file_path]
            lines = content.split('\n')
            
            # Find duplicate blocks
            for i in range(len(lines) - 10):
                block1 = lines[i:i+5]
                for j in range(i+5, len(lines) - 5):
                    block2 = lines[j:j+5]
                    if block1 == block2:
                        examples.append(f"{file_path}:{i+1}-{i+5}\n" + '\n'.join(block1))
                        break
                if examples:
                    break
        
        return examples
    
    def _extract_magic_number_examples(self, files: List[str]) -> List[str]:
        """Extract magic number examples"""
        examples = []
        for file_path in files[:3]:
            content = self.file_contents[file_path]
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if re.search(r'(?<!\w)\d+(?:\.\d+)?(?!\w)', line) and '=' in line:
                    examples.append(f"{file_path}:{i+1}\n{line}")
                    if len(examples) >= 3:
                        break
        
        return examples
    
    def _extract_dead_code_examples(self, files: List[str]) -> List[str]:
        """Extract dead code examples"""
        examples = []
        for file_path in files[:3]:
            content = self.file_contents[file_path]
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') and 'unused' in line.lower():
                    examples.append(f"{file_path}:{i+1}\n{line}")
                    if len(examples) >= 3:
                        break
        
        return examples
    
    def _extract_complex_conditional_examples(self, files: List[str]) -> List[str]:
        """Extract complex conditional examples"""
        examples = []
        for file_path in files[:2]:
            content = self.file_contents[file_path]
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if 'if' in line and len(line) > 80:  # Long conditional
                    examples.append(f"{file_path}:{i+1}\n{line}")
                    if len(examples) >= 2:
                        break
        
        return examples
    
    def _extract_python_idiom_examples(self, files: List[str]) -> List[str]:
        """Extract Python idiom examples"""
        examples = []
        for file_path in files[:3]:
            content = self.file_contents[file_path]
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if any(idiom in line for idiom in ['with ', '[', 'lambda', '@']):
                    examples.append(f"{file_path}:{i+1}\n{line}")
                    if len(examples) >= 3:
                        break
        
        return examples
    
    def _extract_typescript_idiom_examples(self, files: List[str]) -> List[str]:
        """Extract TypeScript idiom examples"""
        examples = []
        for file_path in files[:3]:
            content = self.file_contents[file_path]
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if any(idiom in line for idiom in ['interface', 'type ', 'Promise<', 'async']):
                    examples.append(f"{file_path}:{i+1}\n{line}")
                    if len(examples) >= 3:
                        break
        
        return examples
    
    def _calculate_metrics(self, patterns: List[CodePattern]) -> Dict[str, Any]:
        """Calculate pattern analysis metrics"""
        if not patterns:
            return {}
        
        metrics = {
            "total_patterns": len(patterns),
            "design_patterns": len([p for p in patterns if p.pattern_type == "design_pattern"]),
            "anti_patterns": len([p for p in patterns if p.pattern_type == "anti_pattern"]),
            "code_smells": len([p for p in patterns if p.pattern_type == "smell"]),
            "idioms": len([p for p in patterns if p.pattern_type == "idiom"]),
            "high_severity": len([p for p in patterns if p.severity == "high"]),
            "critical_severity": len([p for p in patterns if p.severity == "critical"]),
        }
        
        # Pattern frequency distribution
        pattern_counts = Counter(p.name for p in patterns)
        metrics["most_common_patterns"] = dict(pattern_counts.most_common(5))
        
        # File impact
        all_files = set()
        for pattern in patterns:
            all_files.update(pattern.files)
        metrics["affected_files"] = len(all_files)
        
        return metrics
    
    def _generate_recommendations(self, patterns: List[CodePattern]) -> List[str]:
        """Generate recommendations based on patterns"""
        recommendations = []
        
        # High severity patterns
        high_severity = [p for p in patterns if p.severity in ["high", "critical"]]
        if high_severity:
            recommendations.append(f"🚨 Address {len(high_severity)} high/critical severity issues")
        
        # Anti-patterns
        anti_patterns = [p for p in patterns if p.pattern_type == "anti_pattern"]
        if anti_patterns:
            recommendations.append(f"⚠️ Refactor {len(anti_patterns)} anti-patterns")
        
        # Code smells
        smells = [p for p in patterns if p.pattern_type == "smell"]
        if smells:
            recommendations.append(f"🧹 Clean up {len(smells)} code smells")
        
        # Design patterns
        design_patterns = [p for p in patterns if p.pattern_type == "design_pattern"]
        if design_patterns:
            recommendations.append(f"✅ Good use of {len(design_patterns)} design patterns")
        
        # Specific recommendations
        if any(p.name == "God Class" for p in patterns):
            recommendations.append("🔧 Consider splitting large classes using Single Responsibility Principle")
        
        if any(p.name == "Long Method" for p in patterns):
            recommendations.append("✂️ Break down long methods into smaller, focused functions")
        
        if any(p.name == "Duplicate Code" for p in patterns):
            recommendations.append("🔄 Extract common functionality to reduce code duplication")
        
        return recommendations
    
    def _calculate_quality_score(self, patterns: List[CodePattern]) -> float:
        """Calculate overall code quality score (0-100)"""
        if not patterns:
            return 100.0
        
        score = 100.0
        
        # Deduct points for anti-patterns and smells
        for pattern in patterns:
            if pattern.pattern_type == "anti_pattern":
                if pattern.severity == "critical":
                    score -= 15
                elif pattern.severity == "high":
                    score -= 10
                elif pattern.severity == "medium":
                    score -= 5
                else:
                    score -= 2
            elif pattern.pattern_type == "smell":
                if pattern.severity == "high":
                    score -= 5
                elif pattern.severity == "medium":
                    score -= 3
                else:
                    score -= 1
        
        # Bonus points for good design patterns
        design_patterns = [p for p in patterns if p.pattern_type == "design_pattern"]
        score += min(len(design_patterns) * 2, 10)  # Max 10 bonus points
        
        return max(0.0, min(100.0, score))


class PatternMiningVisualizer:
    """Visualizes pattern mining results using Streamlit"""
    
    def __init__(self):
        self.pattern_detector = PatternDetector()
    
    def render_pattern_mining_ui(self):
        """Render pattern mining UI"""
        st.subheader("🔍 Pattern Mining - Code Analysis")
        
        # Project selection
        project_root = st.text_input(
            "Project Root Path:",
            value=".",
            help="Path to the project root directory",
            key="pm_project_root"
        )
        
        if st.button("🔍 Analyze Patterns", type="primary"):
            try:
                with st.spinner("Analyzing code patterns..."):
                    project_path = Path(project_root)
                    if not project_path.exists():
                        st.error(f"Path does not exist: {project_root}")
                        return
                    
                    analysis = self.pattern_detector.analyze_project(project_path)
                    
                    # Store in session state
                    st.session_state.pattern_analysis = analysis
                    
                    st.success(f"✅ Found {len(analysis.patterns)} patterns")
                    
            except Exception as e:
                st.error(f"❌ Analysis failed: {e}")
                import traceback
                st.code(traceback.format_exc())
        
        # Display results
        if 'pattern_analysis' in st.session_state:
            self._display_pattern_analysis(st.session_state.pattern_analysis)
    
    def _display_pattern_analysis(self, analysis: PatternAnalysis):
        """Display pattern analysis results"""
        
        # Quality Score
        st.subheader("📊 Code Quality Score")
        score = analysis.code_quality_score
        
        if score >= 80:
            st.success(f"🟢 Excellent: {score:.1f}/100")
        elif score >= 60:
            st.warning(f"🟡 Good: {score:.1f}/100")
        else:
            st.error(f"🔴 Needs Improvement: {score:.1f}/100")
        
        # Metrics overview
        st.subheader("📈 Analysis Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Patterns", analysis.metrics.get("total_patterns", 0))
        with col2:
            st.metric("Anti-patterns", analysis.metrics.get("anti_patterns", 0))
        with col3:
            st.metric("Code Smells", analysis.metrics.get("code_smells", 0))
        with col4:
            st.metric("Design Patterns", analysis.metrics.get("design_patterns", 0))
        
        # Recommendations
        if analysis.recommendations:
            st.subheader("💡 Recommendations")
            for rec in analysis.recommendations:
                st.write(rec)
        
        # Pattern details
        st.subheader("🔍 Pattern Details")
        
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            pattern_type = st.selectbox(
                "Filter by Type:",
                ["All"] + list(set(p.pattern_type for p in analysis.patterns))
            )
        with col2:
            severity = st.selectbox(
                "Filter by Severity:",
                ["All"] + list(set(p.severity for p in analysis.patterns))
            )
        
        # Display patterns
        filtered_patterns = analysis.patterns
        if pattern_type != "All":
            filtered_patterns = [p for p in filtered_patterns if p.pattern_type == pattern_type]
        if severity != "All":
            filtered_patterns = [p for p in filtered_patterns if p.severity == severity]
        
        # Sort by severity
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        filtered_patterns.sort(key=lambda x: severity_order.get(x.severity, 0), reverse=True)
        
        for pattern in filtered_patterns:
            # Color code by severity
            if pattern.severity == "critical":
                color = "🔴"
            elif pattern.severity == "high":
                color = "🟠"
            elif pattern.severity == "medium":
                color = "🟡"
            else:
                color = "🟢"
            
            with st.expander(f"{color} {pattern.name} ({pattern.pattern_type})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Type**: {pattern.pattern_type}")
                    st.write(f"**Severity**: {pattern.severity}")
                    st.write(f"**Frequency**: {pattern.frequency}")
                    st.write(f"**Files**: {len(pattern.files)}")
                
                with col2:
                    st.write(f"**Description**: {pattern.description}")
                
                # Examples
                if pattern.examples:
                    st.write("**Examples**:")
                    for example in pattern.examples[:2]:  # Show max 2 examples
                        st.code(example, language="python")
                
                # Suggestions
                if pattern.suggestions:
                    st.write("**Suggestions**:")
                    for suggestion in pattern.suggestions:
                        st.write(f"• {suggestion}")
        
        # Export options
        st.subheader("📤 Export Analysis")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Export as JSON", key="pattern_export_json_btn"):
                analysis_data = {
                    "patterns": [asdict(p) for p in analysis.patterns],
                    "metrics": analysis.metrics,
                    "recommendations": analysis.recommendations,
                    "quality_score": analysis.code_quality_score
                }
                st.download_button(
                    label="Download Analysis",
                    data=json.dumps(analysis_data, indent=2),
                    file_name="pattern_analysis.json",
                    mime="application/json",
                    key="pattern_download_json"
                )
        
        with col2:
            if st.button("📊 Export Report", key="pattern_export_report_btn"):
                report = self._generate_text_report(analysis)
                st.download_button(
                    label="Download Report",
                    data=report,
                    file_name="pattern_analysis_report.txt",
                    mime="text/plain",
                    key="pattern_download_report"
                )
    
    def _generate_text_report(self, analysis: PatternAnalysis) -> str:
        """Generate a text report of the analysis"""
        report = f"""
Pattern Mining Analysis Report
=============================

Code Quality Score: {analysis.code_quality_score:.1f}/100

Summary:
--------
Total Patterns Found: {len(analysis.patterns)}
Design Patterns: {analysis.metrics.get('design_patterns', 0)}
Anti-patterns: {analysis.metrics.get('anti_patterns', 0)}
Code Smells: {analysis.metrics.get('code_smells', 0)}
Idioms: {analysis.metrics.get('idioms', 0)}

Recommendations:
---------------
"""
        for rec in analysis.recommendations:
            report += f"• {rec}\n"
        
        report += "\nPattern Details:\n"
        report += "----------------\n"
        
        for pattern in analysis.patterns:
            report += f"\n{pattern.name} ({pattern.pattern_type})\n"
            report += f"Severity: {pattern.severity}\n"
            report += f"Frequency: {pattern.frequency}\n"
            report += f"Description: {pattern.description}\n"
            if pattern.suggestions:
                report += "Suggestions:\n"
                for suggestion in pattern.suggestions:
                    report += f"  • {suggestion}\n"
        
        return report


def render_pattern_mining_ui():
    """Render pattern mining UI"""
    visualizer = PatternMiningVisualizer()
    visualizer.render_pattern_mining_ui()
