"""
Automated Code Review System
Analyzes code for quality, best practices, and potential issues
"""

import re
from typing import Dict, List, Any
from pathlib import Path

class CodeReviewer:
    """Automated code review and analysis"""
    
    def __init__(self):
        self.severity_levels = ["INFO", "WARNING", "ERROR", "CRITICAL"]
    
    def review_code(self, file_path: str, content: str, language: str) -> Dict[str, Any]:
        """
        Perform comprehensive code review
        
        Args:
            file_path: Path to the file
            content: File content
            language: Programming language
        
        Returns:
            Dictionary with review results
        """
        issues = []
        
        # Run all checks
        issues.extend(self._check_complexity(content, language))
        issues.extend(self._check_code_smells(content, language))
        issues.extend(self._check_security(content, language))
        issues.extend(self._check_performance(content, language))
        issues.extend(self._check_best_practices(content, language))
        issues.extend(self._check_documentation(content, language))
        issues.extend(self._check_testing(content, language))
        
        # Calculate metrics
        metrics = self._calculate_metrics(content, language)
        
        # Calculate overall score
        score = self._calculate_score(issues, metrics)
        
        return {
            "file_path": file_path,
            "language": language,
            "issues": issues,
            "metrics": metrics,
            "score": score,
            "summary": self._generate_summary(issues, metrics, score)
        }
    
    def _check_complexity(self, content: str, language: str) -> List[Dict[str, Any]]:
        """Check code complexity"""
        issues = []
        lines = content.split('\n')
        
        # Check function length
        if language in ["python", "javascript", "typescript"]:
            func_pattern = r"(def|function|const\s+\w+\s*=\s*\(.*\)\s*=>)"
            current_func_start = None
            
            for i, line in enumerate(lines, 1):
                if re.search(func_pattern, line):
                    if current_func_start:
                        func_length = i - current_func_start
                        if func_length > 50:
                            issues.append({
                                "line": current_func_start,
                                "severity": "WARNING",
                                "category": "complexity",
                                "message": f"Function is too long ({func_length} lines). Consider breaking it down."
                            })
                    current_func_start = i
        
        # Check nesting depth
        max_indent = 0
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                if language == "python":
                    indent_level = indent // 4
                else:
                    indent_level = indent // 2
                max_indent = max(max_indent, indent_level)
        
        if max_indent > 4:
            issues.append({
                "line": 0,
                "severity": "WARNING",
                "category": "complexity",
                "message": f"Deep nesting detected (level {max_indent}). Consider refactoring."
            })
        
        # Check cyclomatic complexity (simplified)
        complexity_keywords = ["if", "elif", "else if", "for", "while", "case", "catch", "&&", "||"]
        complexity_count = sum(content.count(keyword) for keyword in complexity_keywords)
        
        if complexity_count > 20:
            issues.append({
                "line": 0,
                "severity": "WARNING",
                "category": "complexity",
                "message": f"High cyclomatic complexity ({complexity_count}). Consider simplifying logic."
            })
        
        return issues
    
    def _check_code_smells(self, content: str, language: str) -> List[Dict[str, Any]]:
        """Check for code smells"""
        issues = []
        lines = content.split('\n')
        
        # Long parameter lists
        if language in ["python", "javascript", "typescript", "csharp"]:
            for i, line in enumerate(lines, 1):
                # Count parameters in function definitions
                if re.search(r"(def|function|public|private)\s+\w+\s*\(", line):
                    params = re.findall(r"\(([^)]+)\)", line)
                    if params:
                        param_count = len([p.strip() for p in params[0].split(',') if p.strip()])
                        if param_count > 5:
                            issues.append({
                                "line": i,
                                "severity": "WARNING",
                                "category": "code_smell",
                                "message": f"Too many parameters ({param_count}). Consider using a configuration object."
                            })
        
        # Magic numbers
        magic_numbers = re.findall(r'\b(\d{2,})\b', content)
        if len(magic_numbers) > 5:
            issues.append({
                "line": 0,
                "severity": "INFO",
                "category": "code_smell",
                "message": f"Multiple magic numbers found ({len(magic_numbers)}). Consider using named constants."
            })
        
        # Duplicate code (simple check)
        line_dict = {}
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if len(stripped) > 30:  # Only check substantial lines
                if stripped in line_dict:
                    issues.append({
                        "line": i,
                        "severity": "INFO",
                        "category": "code_smell",
                        "message": f"Duplicate code detected (also on line {line_dict[stripped]})"
                    })
                else:
                    line_dict[stripped] = i
        
        # Long lines
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                issues.append({
                    "line": i,
                    "severity": "INFO",
                    "category": "code_smell",
                    "message": f"Line too long ({len(line)} chars). Consider breaking it up."
                })
        
        return issues
    
    def _check_security(self, content: str, language: str) -> List[Dict[str, Any]]:
        """Check for security issues"""
        issues = []
        lines = content.split('\n')
        
        # SQL Injection risks
        sql_patterns = [
            (r"execute\s*\(\s*['\"].*\+", "Potential SQL injection via string concatenation"),
            (r"query\s*\(\s*['\"].*\+", "Potential SQL injection via string concatenation"),
            (r"SELECT.*\+", "Potential SQL injection in SELECT statement"),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, message in sql_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        "line": i,
                        "severity": "CRITICAL",
                        "category": "security",
                        "message": message
                    })
        
        # Hardcoded credentials
        credential_patterns = [
            (r"password\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password"),
            (r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API key"),
            (r"secret\s*=\s*['\"][^'\"]+['\"]", "Hardcoded secret"),
            (r"token\s*=\s*['\"][^'\"]+['\"]", "Hardcoded token"),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, message in credential_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        "line": i,
                        "severity": "CRITICAL",
                        "category": "security",
                        "message": message
                    })
        
        # Unsafe eval/exec
        if language == "python":
            for i, line in enumerate(lines, 1):
                if re.search(r"\b(eval|exec)\s*\(", line):
                    issues.append({
                        "line": i,
                        "severity": "ERROR",
                        "category": "security",
                        "message": "Unsafe use of eval/exec"
                    })
        
        # XSS risks (JavaScript/TypeScript)
        if language in ["javascript", "typescript"]:
            for i, line in enumerate(lines, 1):
                if "innerHTML" in line or "dangerouslySetInnerHTML" in line:
                    issues.append({
                        "line": i,
                        "severity": "WARNING",
                        "category": "security",
                        "message": "Potential XSS risk with innerHTML"
                    })
        
        return issues
    
    def _check_performance(self, content: str, language: str) -> List[Dict[str, Any]]:
        """Check for performance issues"""
        issues = []
        lines = content.split('\n')
        
        # Nested loops
        loop_keywords = ["for", "while", "forEach"]
        for i, line in enumerate(lines, 1):
            if any(keyword in line for keyword in loop_keywords):
                # Check next 20 lines for nested loops
                for j in range(i, min(i + 20, len(lines))):
                    if any(keyword in lines[j] for keyword in loop_keywords) and j != i:
                        issues.append({
                            "line": i,
                            "severity": "WARNING",
                            "category": "performance",
                            "message": "Nested loops detected. Consider optimization."
                        })
                        break
        
        # Inefficient string concatenation in loops
        if language == "python":
            for i, line in enumerate(lines, 1):
                if "for " in line or "while " in line:
                    # Check next 10 lines for string concatenation
                    for j in range(i, min(i + 10, len(lines))):
                        if "+=" in lines[j] and ("str" in lines[j] or "'" in lines[j] or '"' in lines[j]):
                            issues.append({
                                "line": j + 1,
                                "severity": "INFO",
                                "category": "performance",
                                "message": "String concatenation in loop. Consider using join()."
                            })
                            break
        
        # Synchronous operations that should be async
        if language in ["javascript", "typescript"]:
            sync_patterns = [
                (r"fs\.readFileSync", "Use async fs.readFile instead"),
                (r"fs\.writeFileSync", "Use async fs.writeFile instead"),
                (r"\.sync\(", "Consider using async version"),
            ]
            
            for i, line in enumerate(lines, 1):
                for pattern, message in sync_patterns:
                    if re.search(pattern, line):
                        issues.append({
                            "line": i,
                            "severity": "INFO",
                            "category": "performance",
                            "message": message
                        })
        
        return issues
    
    def _check_best_practices(self, content: str, language: str) -> List[Dict[str, Any]]:
        """Check for best practices"""
        issues = []
        lines = content.split('\n')
        
        # Missing error handling
        has_try_catch = "try" in content or "catch" in content or "except" in content
        has_risky_operations = any(keyword in content for keyword in ["fetch", "axios", "http", "file", "database"])
        
        if has_risky_operations and not has_try_catch:
            issues.append({
                "line": 0,
                "severity": "WARNING",
                "category": "best_practice",
                "message": "Missing error handling for risky operations"
            })
        
        # Console.log in production code (JavaScript/TypeScript)
        if language in ["javascript", "typescript"]:
            for i, line in enumerate(lines, 1):
                if "console.log" in line and "// " not in line:
                    issues.append({
                        "line": i,
                        "severity": "INFO",
                        "category": "best_practice",
                        "message": "Remove console.log before production"
                    })
        
        # Missing type hints (Python)
        if language == "python":
            func_count = len(re.findall(r"def\s+\w+\s*\(", content))
            typed_func_count = len(re.findall(r"def\s+\w+\s*\([^)]*:\s*\w+", content))
            
            if func_count > 0 and typed_func_count / func_count < 0.5:
                issues.append({
                    "line": 0,
                    "severity": "INFO",
                    "category": "best_practice",
                    "message": "Consider adding type hints to functions"
                })
        
        # Unused imports (simple check)
        if language == "python":
            imports = re.findall(r"import\s+(\w+)", content)
            for imp in imports:
                if content.count(imp) == 1:  # Only appears in import statement
                    issues.append({
                        "line": 0,
                        "severity": "INFO",
                        "category": "best_practice",
                        "message": f"Potentially unused import: {imp}"
                    })
        
        return issues
    
    def _check_documentation(self, content: str, language: str) -> List[Dict[str, Any]]:
        """Check documentation quality"""
        issues = []
        lines = content.split('\n')
        
        # Check for docstrings/comments on functions
        if language == "python":
            for i, line in enumerate(lines, 1):
                if re.search(r"def\s+\w+\s*\(", line):
                    # Check if next line has docstring
                    if i < len(lines):
                        next_line = lines[i].strip()
                        if not next_line.startswith('"""') and not next_line.startswith("'''"):
                            issues.append({
                                "line": i,
                                "severity": "INFO",
                                "category": "documentation",
                                "message": "Missing docstring for function"
                            })
        
        # Check for JSDoc comments (JavaScript/TypeScript)
        if language in ["javascript", "typescript"]:
            for i, line in enumerate(lines, 1):
                if re.search(r"(function|const\s+\w+\s*=\s*\(.*\)\s*=>)", line):
                    # Check previous lines for JSDoc
                    has_jsdoc = False
                    for j in range(max(0, i - 5), i):
                        if "/**" in lines[j]:
                            has_jsdoc = True
                            break
                    
                    if not has_jsdoc:
                        issues.append({
                            "line": i,
                            "severity": "INFO",
                            "category": "documentation",
                            "message": "Missing JSDoc comment for function"
                        })
        
        # Check comment ratio
        comment_lines = sum(1 for line in lines if line.strip().startswith(('#', '//', '/*', '*')))
        code_lines = len([line for line in lines if line.strip() and not line.strip().startswith(('#', '//', '/*', '*'))])
        
        if code_lines > 50 and comment_lines / max(code_lines, 1) < 0.1:
            issues.append({
                "line": 0,
                "severity": "INFO",
                "category": "documentation",
                "message": "Low comment ratio. Consider adding more documentation."
            })
        
        return issues
    
    def _check_testing(self, content: str, language: str) -> List[Dict[str, Any]]:
        """Check testing practices"""
        issues = []
        
        # Check if test file has actual tests
        is_test_file = any(keyword in content for keyword in ["test_", "Test", "describe(", "it(", "@Test"])
        
        if is_test_file:
            test_count = (
                content.count("test_") +
                content.count("it(") +
                content.count("@Test")
            )
            
            if test_count < 3:
                issues.append({
                    "line": 0,
                    "severity": "WARNING",
                    "category": "testing",
                    "message": f"Test file has few tests ({test_count}). Consider adding more coverage."
                })
            
            # Check for assertions
            has_assertions = any(keyword in content for keyword in ["assert", "expect(", "should", "assertEquals"])
            if not has_assertions:
                issues.append({
                    "line": 0,
                    "severity": "ERROR",
                    "category": "testing",
                    "message": "Test file missing assertions"
                })
        
        return issues
    
    def _calculate_metrics(self, content: str, language: str) -> Dict[str, Any]:
        """Calculate code metrics"""
        lines = content.split('\n')
        
        # Line counts
        total_lines = len(lines)
        code_lines = len([line for line in lines if line.strip() and not line.strip().startswith(('#', '//', '/*', '*'))])
        comment_lines = len([line for line in lines if line.strip().startswith(('#', '//', '/*', '*'))])
        blank_lines = total_lines - code_lines - comment_lines
        
        # Function/class counts
        if language == "python":
            function_count = len(re.findall(r"def\s+\w+", content))
            class_count = len(re.findall(r"class\s+\w+", content))
        elif language in ["javascript", "typescript"]:
            function_count = len(re.findall(r"(function\s+\w+|const\s+\w+\s*=\s*\(.*\)\s*=>)", content))
            class_count = len(re.findall(r"class\s+\w+", content))
        else:
            function_count = 0
            class_count = 0
        
        # Complexity (simplified)
        complexity = sum(content.count(keyword) for keyword in ["if", "for", "while", "case", "catch"])
        
        return {
            "total_lines": total_lines,
            "code_lines": code_lines,
            "comment_lines": comment_lines,
            "blank_lines": blank_lines,
            "comment_ratio": round(comment_lines / max(code_lines, 1), 3),
            "function_count": function_count,
            "class_count": class_count,
            "cyclomatic_complexity": complexity,
            "avg_complexity_per_function": round(complexity / max(function_count, 1), 2)
        }
    
    def _calculate_score(self, issues: List[Dict[str, Any]], metrics: Dict[str, Any]) -> float:
        """Calculate overall code quality score (0-100)"""
        score = 100.0
        
        # Deduct points for issues
        severity_penalties = {
            "INFO": 1,
            "WARNING": 3,
            "ERROR": 5,
            "CRITICAL": 10
        }
        
        for issue in issues:
            penalty = severity_penalties.get(issue["severity"], 1)
            score -= penalty
        
        # Bonus for good metrics
        if metrics["comment_ratio"] >= 0.15:
            score += 5
        
        if metrics["avg_complexity_per_function"] < 5:
            score += 5
        
        return max(0.0, min(100.0, score))
    
    def _generate_summary(self, issues: List[Dict[str, Any]], metrics: Dict[str, Any], score: float) -> str:
        """Generate review summary"""
        issue_counts = {}
        for issue in issues:
            severity = issue["severity"]
            issue_counts[severity] = issue_counts.get(severity, 0) + 1
        
        summary_parts = [
            f"Code Quality Score: {score:.1f}/100",
            f"Total Issues: {len(issues)}"
        ]
        
        for severity in ["CRITICAL", "ERROR", "WARNING", "INFO"]:
            if severity in issue_counts:
                summary_parts.append(f"{severity}: {issue_counts[severity]}")
        
        summary_parts.extend([
            f"Lines of Code: {metrics['code_lines']}",
            f"Comment Ratio: {metrics['comment_ratio']:.1%}",
            f"Functions: {metrics['function_count']}",
            f"Avg Complexity: {metrics['avg_complexity_per_function']:.1f}"
        ])
        
        return " | ".join(summary_parts)


# Global code reviewer
_code_reviewer = None

def get_code_reviewer() -> CodeReviewer:
    """Get or create global code reviewer"""
    global _code_reviewer
    if _code_reviewer is None:
        _code_reviewer = CodeReviewer()
    return _code_reviewer

