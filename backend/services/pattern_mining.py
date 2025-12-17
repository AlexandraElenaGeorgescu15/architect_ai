"""
Pattern Mining Service - Refactored from components/pattern_mining.py
Detects design patterns, anti-patterns, and code smells.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
import ast
import re
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
import json
from collections import defaultdict

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.utils.tool_detector import should_exclude_path, get_user_project_directories
from backend.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PatternMatch:
    """Represents a detected pattern match."""
    pattern_name: str
    location: str  # file_path:line_number
    confidence: float  # 0.0 to 1.0
    details: Dict[str, Any]
    severity: str = "info"  # "info", "warning", "error"


@dataclass
class CodeSmell:
    """Represents a detected code smell."""
    smell_type: str
    location: str
    severity: str
    description: str
    suggestion: str


@dataclass
class SecurityIssue:
    """Represents a detected security issue."""
    issue_type: str
    location: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    recommendation: str


@dataclass
class PatternDetail:
    """Summarized pattern information for reporting."""
    name: str
    pattern_type: str
    description: str
    frequency: int
    severity: str
    files: List[str]
    suggestions: List[str]


@dataclass
class PatternAnalysisResult:
    """Comprehensive pattern analysis output."""
    patterns: List[PatternDetail]
    code_smells: List[CodeSmell]
    security_issues: List[SecurityIssue]
    metrics: Dict[str, Any]
    recommendations: List[str]
    code_quality_score: float
    created_at: str


class PatternMiner:
    """
    Pattern mining service for codebase analysis.
    
    Features:
    - Design pattern detection (Singleton, Factory, Observer, etc.)
    - Code smell detection
    - Security issue detection
    - Pattern caching
    """
    
    def __init__(self):
        """Initialize Pattern Miner."""
        self.patterns_detected: List[PatternMatch] = []
        self.code_smells: List[CodeSmell] = []
        self.security_issues: List[SecurityIssue] = []
        self._cache_file: Optional[Path] = None
        
        logger.info("Pattern Miner initialized")
    
    def detect_singleton(self, file_path: Path, tree: ast.AST) -> List[PatternMatch]:
        """
        Detect Singleton pattern.
        
        Args:
            file_path: Path to file
            tree: AST tree
        
        Returns:
            List of pattern matches
        """
        matches = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for Singleton indicators
                has_instance_var = False
                has_get_instance = False
                has_private_constructor = False
                
                for item in node.body:
                    # Check for _instance or __instance variable
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id in ['_instance', '__instance']:
                                has_instance_var = True
                    
                    # Check for get_instance method
                    if isinstance(item, ast.FunctionDef):
                        if item.name in ['get_instance', 'getInstance', 'instance']:
                            has_get_instance = True
                        # Check for private __new__ or __init__
                        if item.name == '__new__':
                            has_private_constructor = True
                
                if has_instance_var and has_get_instance:
                    matches.append(PatternMatch(
                        pattern_name="Singleton",
                        location=f"{file_path}:{node.lineno}",
                        confidence=0.9,
                        details={
                            "class_name": node.name,
                            "indicators": ["instance_variable", "get_instance_method"]
                        }
                    ))
        
        return matches
    
    def detect_factory(self, file_path: Path, tree: ast.AST) -> List[PatternMatch]:
        """
        Detect Factory pattern.
        
        Args:
            file_path: Path to file
            tree: AST tree
        
        Returns:
            List of pattern matches
        """
        matches = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for Factory indicators
                has_create_method = False
                has_factory_name = False
                returns_objects = False
                
                # Check class name
                if 'Factory' in node.name or 'factory' in node.name.lower():
                    has_factory_name = True
                
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        # Check for create/create_* methods
                        if item.name.startswith('create') or item.name in ['get', 'build']:
                            has_create_method = True
                            # Check if it returns something
                            for child in ast.walk(item):
                                if isinstance(child, ast.Return):
                                    returns_objects = True
                
                if has_factory_name and has_create_method and returns_objects:
                    matches.append(PatternMatch(
                        pattern_name="Factory",
                        location=f"{file_path}:{node.lineno}",
                        confidence=0.85,
                        details={
                            "class_name": node.name,
                            "indicators": ["factory_name", "create_method", "returns_objects"]
                        }
                    ))
        
        return matches
    
    def detect_observer(self, file_path: Path, tree: ast.AST) -> List[PatternMatch]:
        """
        Detect Observer pattern.
        
        Args:
            file_path: Path to file
            tree: AST tree
        
        Returns:
            List of pattern matches
        """
        matches = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for Observer indicators
                has_attach = False
                has_detach = False
                has_notify = False
                has_observers_list = False
                
                for item in node.body:
                    # Check for observers list
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                if 'observer' in target.id.lower() or 'listener' in target.id.lower():
                                    has_observers_list = True
                    
                    # Check for observer methods
                    if isinstance(item, ast.FunctionDef):
                        if 'attach' in item.name.lower() or 'subscribe' in item.name.lower():
                            has_attach = True
                        if 'detach' in item.name.lower() or 'unsubscribe' in item.name.lower():
                            has_detach = True
                        if 'notify' in item.name.lower() or 'update' in item.name.lower():
                            has_notify = True
                
                if (has_observers_list and has_attach and has_notify) or \
                   (has_attach and has_detach and has_notify):
                    matches.append(PatternMatch(
                        pattern_name="Observer",
                        location=f"{file_path}:{node.lineno}",
                        confidence=0.8,
                        details={
                            "class_name": node.name,
                            "indicators": ["observers_list", "attach/detach", "notify"]
                        }
                    ))
        
        return matches
    
    def detect_code_smells(self, file_path: Path, tree: ast.AST) -> List[CodeSmell]:
        """
        Detect code smells.
        
        Args:
            file_path: Path to file
            tree: AST tree
        
        Returns:
            List of code smells
        """
        smells = []
        
        for node in ast.walk(tree):
            # Long Method smell
            if isinstance(node, ast.FunctionDef):
                method_length = len(node.body) if hasattr(node, 'body') else 0
                if method_length > 50:
                    smells.append(CodeSmell(
                        smell_type="Long Method",
                        location=f"{file_path}:{node.lineno}",
                        severity="warning",
                        description=f"Method '{node.name}' has {method_length} lines",
                        suggestion="Consider breaking into smaller methods"
                    ))
                
                # Too Many Parameters
                param_count = len(node.args.args)
                if param_count > 5:
                    smells.append(CodeSmell(
                        smell_type="Too Many Parameters",
                        location=f"{file_path}:{node.lineno}",
                        severity="warning",
                        description=f"Method '{node.name}' has {param_count} parameters",
                        suggestion="Consider using a parameter object or builder pattern"
                    ))
            
            # God Class smell
            if isinstance(node, ast.ClassDef):
                class_size = len(node.body)
                method_count = sum(1 for item in node.body if isinstance(item, ast.FunctionDef))
                
                if class_size > 200 or method_count > 20:
                    smells.append(CodeSmell(
                        smell_type="God Class",
                        location=f"{file_path}:{node.lineno}",
                        severity="error",
                        description=f"Class '{node.name}' is too large ({class_size} lines, {method_count} methods)",
                        suggestion="Consider splitting into smaller, focused classes"
                    ))
                
                # Feature Envy
                external_calls = 0
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        for child in ast.walk(item):
                            if isinstance(child, ast.Attribute):
                                if isinstance(child.value, ast.Name) and child.value.id != 'self':
                                    external_calls += 1
                
                if external_calls > 10:
                    smells.append(CodeSmell(
                        smell_type="Feature Envy",
                        location=f"{file_path}:{node.lineno}",
                        severity="warning",
                        description=f"Class '{node.name}' accesses many external attributes",
                        suggestion="Consider moving methods closer to the data they use"
                    ))
        
        return smells
    
    def detect_security_issues(self, file_path: Path, content: str) -> List[SecurityIssue]:
        """
        Detect security issues.
        
        Args:
            file_path: Path to file
            content: File content
        
        Returns:
            List of security issues
        """
        issues = []
        
        # Hardcoded secrets
        secret_patterns = [
            (r'password\s*=\s*["\']([^"\']+)["\']', "Hardcoded Password", "high"),
            (r'api_key\s*=\s*["\']([^"\']+)["\']', "Hardcoded API Key", "high"),
            (r'secret\s*=\s*["\']([^"\']+)["\']', "Hardcoded Secret", "high"),
            (r'aws_access_key\s*=\s*["\']([^"\']+)["\']', "Hardcoded AWS Key", "critical"),
        ]
        
        for pattern, issue_type, severity in secret_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append(SecurityIssue(
                    issue_type=issue_type,
                    location=f"{file_path}:{line_num}",
                    severity=severity,
                    description=f"Potential hardcoded secret found",
                    recommendation="Move secrets to environment variables or secure vault"
                ))
        
        # SQL Injection risks
        sql_injection_patterns = [
            (r'execute\s*\(\s*["\']([^"\']*%[sd])', "SQL Injection Risk", "high"),
            (r'query\s*\(\s*f["\']([^"\']*\+)', "SQL Injection Risk", "high"),
        ]
        
        for pattern, issue_type, severity in sql_injection_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append(SecurityIssue(
                    issue_type=issue_type,
                    location=f"{file_path}:{line_num}",
                    severity=severity,
                    description="Potential SQL injection vulnerability",
                    recommendation="Use parameterized queries or ORM"
                ))
        
        # Weak cryptography
        weak_crypto_patterns = [
            (r'MD5\s*\(', "Weak Hash Algorithm", "medium"),
            (r'SHA1\s*\(', "Weak Hash Algorithm", "medium"),
            (r'DES\s*\(', "Weak Encryption", "high"),
        ]
        
        for pattern, issue_type, severity in weak_crypto_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append(SecurityIssue(
                    issue_type=issue_type,
                    location=f"{file_path}:{line_num}",
                    severity=severity,
                    description=f"Use of weak cryptographic algorithm",
                    recommendation="Use SHA-256 or stronger, AES for encryption"
                ))
        
        return issues
    
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a single file for patterns, smells, and security issues.
        Supports Python, C#, TypeScript, and JavaScript.
        
        Args:
            file_path: Path to file
        
        Returns:
            Dictionary with analysis results
        """
        if not file_path.exists():
            return {"error": "File not found"}
        
        if should_exclude_path(file_path):
            return {"excluded": True, "reason": "Tool directory"}
        
        suffix = file_path.suffix.lower()
        if suffix not in ['.py', '.cs', '.ts', '.tsx', '.js', '.jsx']:
            return {"error": f"Unsupported file type: {suffix}"}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Dispatch based on file type
            if suffix == '.py':
                return self._analyze_python_file(file_path, content)
            elif suffix == '.cs':
                return self._analyze_csharp_file(file_path, content)
            elif suffix in ['.ts', '.tsx', '.js', '.jsx']:
                return self._analyze_typescript_file(file_path, content)
            else:
                return {"error": f"Unsupported file type: {suffix}"}
            
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            return {"error": f"Syntax error: {e}"}
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _analyze_python_file(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Analyze Python file using AST."""
        tree = ast.parse(content, filename=str(file_path))
        
        # Detect patterns
        patterns = []
        patterns.extend(self.detect_singleton(file_path, tree))
        patterns.extend(self.detect_factory(file_path, tree))
        patterns.extend(self.detect_observer(file_path, tree))
        
        # Detect code smells
        smells = self.detect_code_smells(file_path, tree)
        
        # Detect security issues
        security = self.detect_security_issues(file_path, content)
        
        return {
            "file_path": str(file_path),
            "patterns": [asdict(p) for p in patterns],
            "code_smells": [asdict(s) for s in smells],
            "security_issues": [asdict(sec) for sec in security]
        }
        
    def _analyze_csharp_file(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Analyze C# file using regex patterns."""
        patterns = []
        smells = []
        security = []
        
        # Detect Singleton pattern (sealed class with private constructor and static Instance)
        if re.search(r'sealed\s+class\s+\w+.*?private\s+\w+\s*\(\)', content, re.DOTALL):
            if re.search(r'public\s+static\s+\w+\s+Instance', content):
                patterns.append(PatternMatch(
                    pattern_name="Singleton",
                    location=f"{file_path}:1",
                    confidence=0.8,
                    details={"language": "C#", "type": "Creational"},
                    severity="info"
                ))
        
        # Detect Factory pattern (class name contains "Factory" and has Create/Build methods)
        if re.search(r'class\s+\w*Factory\w*', content):
            if re.search(r'public\s+\w+\s+(Create|Build)\w*\s*\(', content):
                patterns.append(PatternMatch(
                    pattern_name="Factory",
                    location=f"{file_path}:1",
                    confidence=0.75,
                    details={"language": "C#", "type": "Creational"},
                    severity="info"
                ))
        
        # Detect Repository pattern
        if re.search(r'interface\s+I\w*Repository', content) or re.search(r'class\s+\w*Repository', content):
            patterns.append(PatternMatch(
                pattern_name="Repository",
                location=f"{file_path}:1",
                confidence=0.85,
                details={"language": "C#", "type": "Structural"},
                severity="info"
            ))
        
        # Detect large methods (code smell)
        method_matches = re.finditer(r'(public|private|protected)\s+\w+\s+\w+\s*\([^)]*\)\s*{', content)
        for match in method_matches:
            start = match.end()
            brace_count = 1
            end = start
            for i in range(start, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i
                        break
            
            method_lines = content[start:end].count('\n')
            if method_lines > 50:
                line_num = content[:start].count('\n') + 1
                smells.append(CodeSmell(
                    smell_type="Long Method",
                    location=f"{file_path}:{line_num}",
                    severity="warning",
                    description=f"Method has {method_lines} lines (recommended: < 50)",
                    suggestion="Consider breaking this method into smaller, focused methods"
                ))
        
        return {
            "file_path": str(file_path),
            "patterns": [asdict(p) for p in patterns],
            "code_smells": [asdict(s) for s in smells],
            "security_issues": [asdict(sec) for sec in security]
        }
    
    def _analyze_typescript_file(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Analyze TypeScript/JavaScript file using regex patterns."""
        patterns = []
        smells = []
        security = []
        
        # Detect Singleton pattern (class with private constructor and getInstance)
        if re.search(r'class\s+\w+.*?private\s+constructor', content, re.DOTALL):
            if re.search(r'static\s+getInstance', content):
                patterns.append(PatternMatch(
                    pattern_name="Singleton",
                    location=f"{file_path}:1",
                    confidence=0.8,
                    details={"language": "TypeScript", "type": "Creational"},
                    severity="info"
                ))
        
        # Detect Factory pattern
        if re.search(r'(class|function)\s+\w*Factory\w*', content):
            if re.search(r'(create|build)\w*\s*\(', content, re.IGNORECASE):
                patterns.append(PatternMatch(
                    pattern_name="Factory",
                    location=f"{file_path}:1",
                    confidence=0.75,
                    details={"language": "TypeScript", "type": "Creational"},
                    severity="info"
                ))
        
        # Detect Observer pattern (EventEmitter, addEventListener, or subject/observer)
        if re.search(r'(EventEmitter|addEventListener|removeEventListener)', content):
            patterns.append(PatternMatch(
                pattern_name="Observer",
                location=f"{file_path}:1",
                confidence=0.7,
                details={"language": "TypeScript", "type": "Behavioral"},
                severity="info"
            ))
        
        # Detect custom hooks pattern (React)
        hook_matches = re.findall(r'export\s+(function|const)\s+(use[A-Z]\w+)', content)
        if hook_matches:
            patterns.append(PatternMatch(
                pattern_name="Custom Hook",
                location=f"{file_path}:1",
                confidence=0.9,
                details={"language": "TypeScript/React", "type": "Architectural", "hooks": [h[1] for h in hook_matches]},
                severity="info"
            ))
        
        # Detect long functions (code smell)
        function_matches = re.finditer(r'(function|const)\s+\w+\s*[=\(][^{]*{', content)
        for match in function_matches:
            start = match.end() - 1  # Start at the opening brace
            brace_count = 0
            end = start
            for i in range(start, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i
                        break
            
            func_lines = content[start:end].count('\n')
            if func_lines > 50:
                line_num = content[:start].count('\n') + 1
                smells.append(CodeSmell(
                    smell_type="Long Function",
                    location=f"{file_path}:{line_num}",
                    severity="warning",
                    description=f"Function has {func_lines} lines (recommended: < 50)",
                    suggestion="Consider breaking this function into smaller, focused functions"
                ))
        
        return {
            "file_path": str(file_path),
            "patterns": [asdict(p) for p in patterns],
            "code_smells": [asdict(s) for s in smells],
            "security_issues": [asdict(sec) for sec in security]
        }
    
    def analyze_directory(
        self,
        directory: Path,
        recursive: bool = True,
        detectors: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze directory for patterns, smells, and security issues.
        
        Args:
            directory: Directory to analyze
            recursive: Whether to analyze recursively
            detectors: Optional list of specific detectors to run
        
        Returns:
            Dictionary with analysis results
        """
        self.patterns_detected.clear()
        self.code_smells.clear()
        self.security_issues.clear()
        
        # Get user project directories (excludes tool)
        user_dirs = get_user_project_directories()
        
        if directory not in user_dirs:
            logger.warning(f"Directory {directory} not in user project directories")
            return {"error": "Directory not in user project"}
        
        # Find all source code files (Python, C#, TypeScript, JavaScript)
        file_extensions = ["*.py", "*.cs", "*.ts", "*.tsx", "*.js", "*.jsx"]
        files = []
        
        for ext in file_extensions:
            pattern = f"**/{ext}" if recursive else ext
            if recursive:
                files.extend(directory.rglob(ext))
            else:
                files.extend(directory.glob(ext))
        
        logger.info(f"Analyzing {len(files)} files for patterns...")
        
        for file_path in files:
            if should_exclude_path(file_path):
                continue
            
            try:
                result = self.analyze_file(file_path)
                if "error" in result or result.get("excluded"):
                    continue
                
                # Aggregate results - ensure confidence is always present
                for pattern_dict in result.get("patterns", []):
                    # Ensure confidence exists and is valid
                    if "confidence" not in pattern_dict or not isinstance(pattern_dict.get("confidence"), (int, float)):
                        pattern_dict["confidence"] = 0.5  # Default confidence
                    else:
                        # Clamp confidence between 0 and 1
                        pattern_dict["confidence"] = max(0.0, min(1.0, float(pattern_dict["confidence"])))
                    self.patterns_detected.append(PatternMatch(**pattern_dict))
                
                for smell_dict in result.get("code_smells", []):
                    self.code_smells.append(CodeSmell(**smell_dict))
                
                for sec_dict in result.get("security_issues", []):
                    self.security_issues.append(SecurityIssue(**sec_dict))
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
        
        return self.get_report()

    def analyze_project(
        self,
        project_root: Path,
        include_design_patterns: bool = True,
        include_anti_patterns: bool = True,
        include_code_smells: bool = True
    ) -> PatternAnalysisResult:
        """Public entry point used by the analysis service."""

        report = self.analyze_directory(project_root, recursive=True)
        if "error" in report:
            raise ValueError(report["error"])

        # Filter results based on flags
        pattern_matches = self.patterns_detected if include_design_patterns else []
        # Currently anti-patterns are represented via code smells, keep placeholder for compatibility
        code_smells = self.code_smells if include_code_smells else []
        security_issues = self.security_issues

        pattern_details = self._summarize_patterns(pattern_matches)
        metrics = self._build_metrics(pattern_details, code_smells, security_issues, report.get("statistics", {}))
        recommendations = self._build_recommendations(pattern_details, code_smells, security_issues)
        quality_score = self._calculate_quality_score(metrics)

        return PatternAnalysisResult(
            patterns=pattern_details,
            code_smells=code_smells,
            security_issues=security_issues,
            metrics=metrics,
            recommendations=recommendations,
            code_quality_score=quality_score,
            created_at=report.get("created_at", datetime.now().isoformat())
        )
    
    def get_report(self) -> Dict[str, Any]:
        """
        Get analysis report.
        
        Returns:
            Dictionary with complete analysis report
        """
        # Count patterns by type
        pattern_counts = {}
        for pattern in self.patterns_detected:
            pattern_counts[pattern.pattern_name] = pattern_counts.get(pattern.pattern_name, 0) + 1
        
        # Count smells by type
        smell_counts = {}
        for smell in self.code_smells:
            smell_counts[smell.smell_type] = smell_counts.get(smell.smell_type, 0) + 1
        
        # Count security issues by severity
        security_by_severity = {}
        for issue in self.security_issues:
            security_by_severity[issue.severity] = security_by_severity.get(issue.severity, 0) + 1
        
        return {
            "patterns_detected": [asdict(p) for p in self.patterns_detected],
            "code_smells": [asdict(s) for s in self.code_smells],
            "security_issues": [asdict(sec) for sec in self.security_issues],
            "statistics": {
                "total_files_analyzed": len(set(p.location.split(':')[0] for p in self.patterns_detected)),
                "patterns_found": len(self.patterns_detected),
                "pattern_counts": pattern_counts,
                "code_smells_found": len(self.code_smells),
                "smell_counts": smell_counts,
                "security_issues_found": len(self.security_issues),
                "security_by_severity": security_by_severity
            },
            "created_at": datetime.now().isoformat()
        }
    
    def _summarize_patterns(self, patterns: List[PatternMatch]) -> List[PatternDetail]:
        """Aggregate pattern matches into concise summaries."""
        summaries: Dict[str, PatternDetail] = {}
        severity_rank = {
            "info": 0,
            "low": 1,
            "warning": 2,
            "medium": 3,
            "high": 4,
            "error": 5,
            "critical": 6,
        }

        suggestion_lookup = {
            "singleton": ["Ensure lazy initialization is thread-safe and consider dependency injection if possible."],
            "factory": ["Confirm factory methods are cohesive and avoid excessive branching or configuration complexity."],
            "observer": ["Validate observers are unsubscribed properly to avoid memory leaks and unexpected notifications."],
        }

        for match in patterns:
            key = match.pattern_name.lower()
            file_path = match.location.split(':')[0] if ':' in match.location else match.location
            indicators = match.details.get("indicators") if isinstance(match.details, dict) else None
            description = (
                f"{match.pattern_name} pattern detected"
                + (f" via {', '.join(indicators)}" if indicators else "")
                + (f" in {match.details.get('class_name')}" if isinstance(match.details, dict) and match.details.get('class_name') else "")
                + "."
            )

            entry = summaries.get(key)
            if not entry:
                suggestions = suggestion_lookup.get(
                    key,
                    [
                        "Review this pattern's usage to confirm it aligns with current requirements and doesn't introduce unnecessary coupling.",
                    ],
                )

                entry = PatternDetail(
                    name=match.pattern_name,
                    pattern_type=match.pattern_name,
                    description=description,
                    frequency=1,
                    severity=match.severity or "info",
                    files=[file_path],
                    suggestions=suggestions,
                )
                summaries[key] = entry
            else:
                entry.frequency += 1
                if file_path and file_path not in entry.files:
                    entry.files.append(file_path)
                current_rank = severity_rank.get(entry.severity, 0)
                incoming_rank = severity_rank.get(match.severity or "info", 0)
                if incoming_rank > current_rank:
                    entry.severity = match.severity or entry.severity

        return sorted(summaries.values(), key=lambda item: item.frequency, reverse=True)

    def _build_metrics(
        self,
        patterns: List[PatternDetail],
        code_smells: List[CodeSmell],
        security_issues: List[SecurityIssue],
        base_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine raw statistics with derived metrics."""

        metrics: Dict[str, Any] = {}
        metrics.update({k: v for k, v in base_stats.items() if isinstance(v, (int, float))})

        total_pattern_occurrences = sum(pattern.frequency for pattern in patterns)
        metrics["total_patterns"] = total_pattern_occurrences
        metrics["unique_patterns"] = len(patterns)
        metrics["total_code_smells"] = len(code_smells)
        metrics["total_security_issues"] = len(security_issues)

        pattern_counts = {pattern.name: pattern.frequency for pattern in patterns}
        code_smells_by_type: Dict[str, int] = defaultdict(int)
        for smell in code_smells:
            code_smells_by_type[smell.smell_type] += 1

        security_by_severity: Dict[str, int] = defaultdict(int)
        for issue in security_issues:
            security_by_severity[issue.severity] += 1

        files_with_patterns = {file for pattern in patterns for file in pattern.files}
        files_with_smells = {smell.location.split(':')[0] for smell in code_smells}
        files_with_security = {issue.location.split(':')[0] for issue in security_issues}

        metrics["files_with_issues"] = len(files_with_patterns | files_with_smells | files_with_security)
        metrics["patterns_by_type"] = pattern_counts
        metrics["code_smells_by_type"] = dict(code_smells_by_type)
        metrics["security_by_severity"] = dict(security_by_severity)

        return metrics

    def _build_recommendations(
        self,
        patterns: List[PatternDetail],
        code_smells: List[CodeSmell],
        security_issues: List[SecurityIssue]
    ) -> List[str]:
        """Generate actionable follow-up recommendations."""

        recommendations: List[str] = []

        severity_order = {
            "info": 0,
            "low": 1,
            "medium": 2,
            "warning": 2,
            "moderate": 2,
            "high": 3,
            "critical": 4,
        }

        for pattern in patterns:
            if pattern.severity not in {"info", "low"}:
                message = pattern.suggestions[0] if pattern.suggestions else f"Review occurrences of {pattern.name}."
                recommendations.append(f"{pattern.name}: {message}")

        for smell in code_smells[:5]:
            recommendations.append(
                f"Refactor {smell.location} to address the {smell.smell_type.lower()} smell (severity: {smell.severity})."
            )

        if security_issues:
            worst_issue = max(
                security_issues,
                key=lambda issue: severity_order.get(str(issue.severity).lower(), 0)
            )
            recommendations.append(
                "Prioritize remediation of detected security issues, starting with "
                f"{worst_issue.issue_type} ({worst_issue.severity})."
            )

        if not recommendations:
            recommendations.append(
                "Great news! No significant design patterns, code smells, or security issues were detected."
            )

        # Preserve order while removing duplicates
        return list(dict.fromkeys(recommendations))

    def _calculate_quality_score(self, metrics: Dict[str, Any]) -> float:
        """Compute an overall code quality score (0-100)."""

        def metric_value(name: str) -> float:
            value = metrics.get(name, 0)
            return float(value) if isinstance(value, (int, float)) else 0.0

        score = 100.0
        score -= metric_value("total_code_smells") * 2.5
        score -= metric_value("total_security_issues") * 5.0

        total_patterns = metric_value("total_patterns")
        unique_patterns = metric_value("unique_patterns")
        score -= max(0.0, total_patterns - unique_patterns) * 1.0

        return max(0.0, min(100.0, score))

    def cache_results(self, cache_file: Optional[Path] = None):
        """
        Cache analysis results to disk.
        
        Args:
            cache_file: Optional cache file path
        """
        if cache_file is None:
            cache_file = Path("outputs/.cache") / "pattern_mining.json"
        
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._cache_file = cache_file
        
        report = self.get_report()
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Pattern mining results cached to {cache_file}")
    
    def load_cached_results(self, cache_file: Optional[Path] = None) -> bool:
        """
        Load cached results.
        
        Args:
            cache_file: Optional cache file path
        
        Returns:
            True if cache loaded successfully
        """
        if cache_file is None:
            cache_file = Path("outputs/.cache") / "pattern_mining.json"
        
        if not cache_file.exists():
            return False
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Restore results - ensure confidence is always present
            patterns_data = data.get("patterns_detected", [])
            for p in patterns_data:
                # Ensure confidence exists and is valid
                if "confidence" not in p or not isinstance(p.get("confidence"), (int, float)):
                    p["confidence"] = 0.5  # Default confidence
                else:
                    # Clamp confidence between 0 and 1
                    p["confidence"] = max(0.0, min(1.0, float(p["confidence"])))
            
            self.patterns_detected = [PatternMatch(**p) for p in patterns_data]
            self.code_smells = [CodeSmell(**s) for s in data.get("code_smells", [])]
            self.security_issues = [SecurityIssue(**sec) for sec in data.get("security_issues", [])]
            
            logger.info(f"Pattern mining results loaded from cache")
            return True
            
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return False


# Global miner instance
_miner: Optional[PatternMiner] = None


def get_miner() -> PatternMiner:
    """Get or create global Pattern Miner instance."""
    global _miner
    if _miner is None:
        _miner = PatternMiner()
    return _miner

