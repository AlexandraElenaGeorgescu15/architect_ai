"""
Design Review Service

AI-powered code and architecture review system.
Capabilities:
- Architecture compliance validation
- Test coverage analysis
- Security vulnerability detection
- Design pattern verification
- SOLID principles validation
- Code quality assessment
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class ReviewSeverity(str, Enum):
    """Severity level for review findings."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    SUGGESTION = "suggestion"


@dataclass
class ReviewFinding:
    """A single finding from the review."""
    category: str  # "architecture", "testing", "security", "patterns", "performance"
    severity: ReviewSeverity
    title: str
    description: str
    file_path: Optional[str]
    line_number: Optional[int]
    recommendation: str
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["severity"] = self.severity.value
        return result


@dataclass
class DesignReviewResult:
    """Complete design review result."""
    review_id: str
    review_type: str  # "full", "architecture", "security", "tests"
    files_reviewed: int
    findings: List[ReviewFinding]
    summary: str
    score: float  # 0-100
    created_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["findings"] = [f.to_dict() if isinstance(f, ReviewFinding) else f for f in self.findings]
        return result


# Common anti-patterns to detect
ANTI_PATTERNS = {
    "god_class": {
        "description": "Class with too many responsibilities",
        "threshold_lines": 500,
        "threshold_methods": 20,
        "severity": ReviewSeverity.WARNING
    },
    "long_method": {
        "description": "Method/function that's too long",
        "threshold_lines": 50,
        "severity": ReviewSeverity.INFO
    },
    "magic_numbers": {
        "description": "Hardcoded numeric values without explanation",
        "severity": ReviewSeverity.INFO
    },
    "deep_nesting": {
        "description": "Too many levels of nesting",
        "threshold_levels": 4,
        "severity": ReviewSeverity.WARNING
    },
    "missing_error_handling": {
        "description": "No try/catch or error handling",
        "severity": ReviewSeverity.WARNING
    },
    "sql_injection": {
        "description": "Potential SQL injection vulnerability",
        "severity": ReviewSeverity.CRITICAL
    },
    "hardcoded_secrets": {
        "description": "Hardcoded API keys, passwords, or tokens",
        "severity": ReviewSeverity.CRITICAL
    },
}


class DesignReviewService:
    """
    AI-powered design and code review service.
    
    Features:
    - Architecture compliance checking
    - Test coverage analysis
    - Pattern detection (good and anti-patterns)
    - Security vulnerability scanning
    - SOLID principles validation
    """
    
    def __init__(self):
        self._generation_service = None
        self._pattern_mining = None
        self._knowledge_graph = None
    
    @property
    def generation_service(self):
        """Lazy load generation service."""
        if self._generation_service is None:
            from backend.services.enhanced_generation import EnhancedGenerationService
            self._generation_service = EnhancedGenerationService()
        return self._generation_service
    
    @property
    def pattern_mining(self):
        """Lazy load pattern mining service."""
        if self._pattern_mining is None:
            from backend.services.pattern_mining import PatternMiningService
            self._pattern_mining = PatternMiningService()
        return self._pattern_mining
    
    @property
    def knowledge_graph(self):
        """Lazy load knowledge graph."""
        if self._knowledge_graph is None:
            from backend.services.knowledge_graph import KnowledgeGraphBuilder
            self._knowledge_graph = KnowledgeGraphBuilder()
        return self._knowledge_graph
    
    async def review_against_architecture(
        self,
        code_files: List[str],
        architecture_diagram: str,
        meeting_notes: Optional[str] = None
    ) -> DesignReviewResult:
        """
        Review code files against an architecture diagram.
        
        Checks if the implementation matches the intended architecture.
        """
        review_id = f"rev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        findings: List[ReviewFinding] = []
        
        # Parse architecture from diagram
        components = self._extract_components_from_diagram(architecture_diagram)
        
        # Analyze code files
        code_summary = self._summarize_code_files(code_files)
        
        # Use AI to compare architecture vs implementation
        prompt = f"""Compare this architecture diagram with the actual implementation.

ARCHITECTURE DIAGRAM:
{architecture_diagram}

DETECTED COMPONENTS IN DIAGRAM:
{', '.join(components)}

ACTUAL CODE STRUCTURE:
{code_summary}

{f'MEETING NOTES (requirements):{chr(10)}{meeting_notes}' if meeting_notes else ''}

Analyze and identify:
1. Components in diagram that are NOT implemented
2. Components implemented that are NOT in diagram
3. Relationships/connections that don't match
4. Missing API endpoints or data flows
5. Architectural violations

For each finding, provide:
- Category: architecture
- Severity: critical/warning/info
- Title: Brief description
- Description: Detailed explanation
- Recommendation: How to fix

Output as JSON array of findings."""

        try:
            # Get AI analysis
            from backend.models.dto import ArtifactType
            result = await self.generation_service.generate_with_pipeline(
                artifact_type=ArtifactType.API_DOCS,  # Use docs type for analysis
                meeting_notes=prompt,
                options={"temperature": 0.3}
            )
            
            # Parse AI response
            ai_findings = self._parse_ai_findings(result.get("content", ""))
            findings.extend(ai_findings)
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            findings.append(ReviewFinding(
                category="architecture",
                severity=ReviewSeverity.INFO,
                title="AI Analysis Unavailable",
                description=f"Could not perform AI-powered analysis: {e}",
                file_path=None,
                line_number=None,
                recommendation="Review architecture manually"
            ))
        
        # Calculate score
        score = self._calculate_score(findings)
        
        return DesignReviewResult(
            review_id=review_id,
            review_type="architecture",
            files_reviewed=len(code_files),
            findings=findings,
            summary=self._generate_summary(findings),
            score=score,
            created_at=datetime.now().isoformat()
        )
    
    async def review_test_coverage(
        self,
        source_files: List[str],
        test_files: List[str]
    ) -> DesignReviewResult:
        """
        Review test coverage for source files.
        
        Identifies:
        - Source files without tests
        - Untested functions/methods
        - Missing test types (unit, integration, e2e)
        """
        review_id = f"rev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        findings: List[ReviewFinding] = []
        
        # Map source files to test files
        source_test_map = self._map_sources_to_tests(source_files, test_files)
        
        for source, tests in source_test_map.items():
            if not tests:
                findings.append(ReviewFinding(
                    category="testing",
                    severity=ReviewSeverity.WARNING,
                    title=f"No tests for {Path(source).name}",
                    description=f"Source file {source} has no corresponding test file",
                    file_path=source,
                    line_number=None,
                    recommendation=f"Create test file for {Path(source).name}"
                ))
        
        # Analyze test quality
        for test_file in test_files:
            quality_findings = self._analyze_test_quality(test_file)
            findings.extend(quality_findings)
        
        score = self._calculate_score(findings)
        
        return DesignReviewResult(
            review_id=review_id,
            review_type="tests",
            files_reviewed=len(source_files) + len(test_files),
            findings=findings,
            summary=self._generate_summary(findings),
            score=score,
            created_at=datetime.now().isoformat()
        )
    
    async def review_security(
        self,
        file_paths: List[str]
    ) -> DesignReviewResult:
        """
        Perform security review of code files.
        
        Checks for:
        - Hardcoded secrets
        - SQL injection
        - XSS vulnerabilities
        - Insecure dependencies
        """
        review_id = f"rev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        findings: List[ReviewFinding] = []
        
        for file_path in file_paths:
            path = Path(file_path)
            if not path.exists():
                continue
            
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                
                # Check for hardcoded secrets
                secret_findings = self._check_hardcoded_secrets(content, file_path)
                findings.extend(secret_findings)
                
                # Check for SQL injection
                sql_findings = self._check_sql_injection(content, file_path)
                findings.extend(sql_findings)
                
                # Check for XSS
                xss_findings = self._check_xss_vulnerabilities(content, file_path)
                findings.extend(xss_findings)
                
            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")
        
        score = self._calculate_score(findings)
        
        return DesignReviewResult(
            review_id=review_id,
            review_type="security",
            files_reviewed=len(file_paths),
            findings=findings,
            summary=self._generate_summary(findings),
            score=score,
            created_at=datetime.now().isoformat()
        )
    
    async def review_patterns(
        self,
        directory: str
    ) -> DesignReviewResult:
        """
        Review code for design patterns and anti-patterns.
        """
        review_id = f"rev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        findings: List[ReviewFinding] = []
        files_reviewed = 0
        
        path = Path(directory)
        
        # Use pattern mining service
        try:
            patterns = self.pattern_mining.analyze_directory(path)
            
            # Convert pattern findings to review findings
            for pattern in patterns.get("anti_patterns", []):
                findings.append(ReviewFinding(
                    category="patterns",
                    severity=ReviewSeverity.WARNING,
                    title=f"Anti-pattern: {pattern['name']}",
                    description=pattern.get("description", ""),
                    file_path=pattern.get("location"),
                    line_number=pattern.get("line"),
                    recommendation=pattern.get("fix", "Refactor this code")
                ))
            
            # Good patterns as info
            for pattern in patterns.get("design_patterns", []):
                findings.append(ReviewFinding(
                    category="patterns",
                    severity=ReviewSeverity.INFO,
                    title=f"Good pattern: {pattern['name']}",
                    description=f"Detected {pattern['name']} pattern",
                    file_path=pattern.get("location"),
                    line_number=pattern.get("line"),
                    recommendation="Keep using this pattern"
                ))
            
            files_reviewed = patterns.get("files_analyzed", 0)
            
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            findings.append(ReviewFinding(
                category="patterns",
                severity=ReviewSeverity.INFO,
                title="Pattern Analysis Error",
                description=str(e),
                file_path=None,
                line_number=None,
                recommendation="Ensure pattern mining service is available"
            ))
        
        score = self._calculate_score(findings)
        
        return DesignReviewResult(
            review_id=review_id,
            review_type="patterns",
            files_reviewed=files_reviewed,
            findings=findings,
            summary=self._generate_summary(findings),
            score=score,
            created_at=datetime.now().isoformat()
        )
    
    async def review_code_quality(
        self,
        directory: str,
        files: List[str]
    ) -> DesignReviewResult:
        """
        Review code quality using AI without a diagram.
        
        Checks for:
        - SOLID principles
        - Code smell
        - Maintainability
        - Error handling
        """
        review_id = f"rev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        findings: List[ReviewFinding] = []
        
        # Summarize code for AI context
        code_summary = self._summarize_code_files(files)
        
        prompt = f"""Review the following code structure and file list for general code quality.
        
CODE STRUCTURE:
{code_summary}

Analyze for:
1. SOLID Principle violations
2. Obvious code smells (God classes, spaghetti code hints)
3. Project structure issues
4. Naming convention inconsistencies

For each finding, provide:
- Category: patterns
- Severity: warning/info
- Title: Brief description
- Description: Detailed explanation
- Recommendation: Specific refactoring advice

Output as JSON array of findings."""

        try:
            # Get AI analysis
            from backend.models.dto import ArtifactType
            result = await self.generation_service.generate_with_pipeline(
                artifact_type=ArtifactType.API_DOCS,  # Use docs type for analysis
                meeting_notes=prompt,
                options={"temperature": 0.3}
            )
            
            # Parse AI response
            ai_findings = self._parse_ai_findings(result.get("content", ""))
            findings.extend(ai_findings)
            
        except Exception as e:
            logger.error(f"AI code quality analysis failed: {e}")
            findings.append(ReviewFinding(
                category="patterns",
                severity=ReviewSeverity.INFO,
                title="AI Analysis Failed",
                description=f"Could not perform AI analysis: {e}",
                file_path=None,
                line_number=None,
                recommendation="Manual review required"
            ))
            
        score = self._calculate_score(findings)
        
        return DesignReviewResult(
            review_id=review_id,
            review_type="code_quality",
            files_reviewed=len(files),
            findings=findings,
            summary=self._generate_summary(findings),
            score=score,
            created_at=datetime.now().isoformat()
        )

    async def full_review(
        self,
        directory: str,
        architecture_diagram: Optional[str] = None,
        meeting_notes: Optional[str] = None
    ) -> DesignReviewResult:
        """
        Perform a comprehensive design review.
        
        Combines:
        - Architecture compliance (if diagram provided)
        - Code Quality (AI fallback if no diagram)
        - Test coverage
        - Security
        - Patterns
        """
        review_id = f"rev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        all_findings: List[ReviewFinding] = []
        
        path = Path(directory)
        
        # Get all source and test files
        source_extensions = {'.py', '.ts', '.tsx', '.js', '.jsx', '.cs', '.java'}
        test_patterns = ['test_', '_test.', '.test.', '.spec.', 'Test.']
        
        all_files = []
        source_files = []
        test_files = []
        
        for ext in source_extensions:
            for file_path in path.glob(f"**/*{ext}"):
                file_str = str(file_path)
                all_files.append(file_str)
                
                if any(p in file_path.name for p in test_patterns):
                    test_files.append(file_str)
                else:
                    source_files.append(file_str)
        
        # Run all review types
        if architecture_diagram:
            arch_result = await self.review_against_architecture(
                source_files[:50],  # Limit for performance
                architecture_diagram,
                meeting_notes
            )
            all_findings.extend(arch_result.findings)
        else:
            # Fallback: General AI Code Quality Review
            quality_result = await self.review_code_quality(directory, source_files[:50])
            all_findings.extend(quality_result.findings)
        
        test_result = await self.review_test_coverage(source_files[:50], test_files)
        all_findings.extend(test_result.findings)
        
        security_result = await self.review_security(source_files[:30])
        all_findings.extend(security_result.findings)
        
        pattern_result = await self.review_patterns(directory)
        all_findings.extend(pattern_result.findings)
        
        # Deduplicate findings
        all_findings = self._deduplicate_findings(all_findings)
        
        score = self._calculate_score(all_findings)
        
        return DesignReviewResult(
            review_id=review_id,
            review_type="full",
            files_reviewed=len(all_files),
            findings=all_findings,
            summary=self._generate_summary(all_findings),
            score=score,
            created_at=datetime.now().isoformat()
        )
    
    def _extract_components_from_diagram(self, diagram: str) -> List[str]:
        """Extract component names from a diagram."""
        import re
        
        # Look for node definitions
        patterns = [
            r'\[([^\]]+)\]',  # [Component Name]
            r'\(([^\)]+)\)',  # (Component Name)
            r'(\w+)\s*\[',    # ComponentName[
            r'(\w+)\s*\{',    # ComponentName{
        ]
        
        components = set()
        for pattern in patterns:
            matches = re.findall(pattern, diagram)
            components.update(matches)
        
        return list(components)
    
    def _summarize_code_files(self, file_paths: List[str]) -> str:
        """Create a summary of code file structure."""
        summary_parts = []
        
        for file_path in file_paths[:20]:  # Limit for prompt size
            path = Path(file_path)
            if path.exists():
                # Get file info
                summary_parts.append(f"- {path.name}: {path.suffix}")
        
        return "\n".join(summary_parts) if summary_parts else "No files found"
    
    def _parse_ai_findings(self, ai_response: str) -> List[ReviewFinding]:
        """Parse AI response into ReviewFindings."""
        import json
        
        findings = []
        
        try:
            # Try to extract JSON from response
            json_match = None
            if "[" in ai_response and "]" in ai_response:
                start = ai_response.index("[")
                end = ai_response.rindex("]") + 1
                json_match = ai_response[start:end]
            
            if json_match:
                items = json.loads(json_match)
                for item in items:
                    severity = ReviewSeverity.INFO
                    if item.get("severity", "").lower() == "critical":
                        severity = ReviewSeverity.CRITICAL
                    elif item.get("severity", "").lower() == "warning":
                        severity = ReviewSeverity.WARNING
                    
                    findings.append(ReviewFinding(
                        category=item.get("category", "architecture"),
                        severity=severity,
                        title=item.get("title", "Finding"),
                        description=item.get("description", ""),
                        file_path=item.get("file_path"),
                        line_number=item.get("line_number"),
                        recommendation=item.get("recommendation", "")
                    ))
        except Exception as e:
            logger.warning(f"Failed to parse AI findings: {e}")
        
        return findings
    
    def _map_sources_to_tests(
        self,
        source_files: List[str],
        test_files: List[str]
    ) -> Dict[str, List[str]]:
        """Map source files to their corresponding test files."""
        mapping: Dict[str, List[str]] = {}
        
        for source in source_files:
            source_path = Path(source)
            source_name = source_path.stem
            
            # Find matching test files
            matching_tests = []
            for test in test_files:
                test_path = Path(test)
                test_name = test_path.stem.lower()
                
                if source_name.lower() in test_name or test_name.replace("test_", "").replace("_test", "") == source_name.lower():
                    matching_tests.append(test)
            
            mapping[source] = matching_tests
        
        return mapping
    
    def _analyze_test_quality(self, test_file: str) -> List[ReviewFinding]:
        """Analyze quality of a test file."""
        findings = []
        path = Path(test_file)
        
        if not path.exists():
            return findings
        
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")
            
            # Check for assertions
            has_assertions = any(
                "assert" in line.lower() or "expect(" in line or ".toBe" in line
                for line in lines
            )
            
            if not has_assertions:
                findings.append(ReviewFinding(
                    category="testing",
                    severity=ReviewSeverity.WARNING,
                    title="No assertions found",
                    description=f"Test file {path.name} may not have proper assertions",
                    file_path=test_file,
                    line_number=None,
                    recommendation="Add assertions to verify expected behavior"
                ))
            
            # Check test count
            test_count = len([l for l in lines if "def test_" in l or "it(" in l or "test(" in l])
            if test_count == 0:
                findings.append(ReviewFinding(
                    category="testing",
                    severity=ReviewSeverity.WARNING,
                    title="No test functions found",
                    description=f"Test file {path.name} has no test functions",
                    file_path=test_file,
                    line_number=None,
                    recommendation="Add test functions"
                ))
            
        except Exception as e:
            logger.warning(f"Failed to analyze test {test_file}: {e}")
        
        return findings
    
    def _check_hardcoded_secrets(self, content: str, file_path: str) -> List[ReviewFinding]:
        """Check for hardcoded secrets."""
        import re
        findings = []
        
        secret_patterns = [
            (r'api[_-]?key\s*[=:]\s*["\'][^"\']{20,}["\']', "API key"),
            (r'password\s*[=:]\s*["\'][^"\']+["\']', "Password"),
            (r'secret\s*[=:]\s*["\'][^"\']{10,}["\']', "Secret"),
            (r'token\s*[=:]\s*["\'][^"\']{20,}["\']', "Token"),
            (r'["\'][A-Za-z0-9]{32,}["\']', "Potential API key"),
        ]
        
        for pattern, secret_type in secret_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                findings.append(ReviewFinding(
                    category="security",
                    severity=ReviewSeverity.CRITICAL,
                    title=f"Hardcoded {secret_type}",
                    description=f"Possible hardcoded {secret_type.lower()} detected",
                    file_path=file_path,
                    line_number=line_num,
                    recommendation=f"Move {secret_type.lower()} to environment variables"
                ))
        
        return findings
    
    def _check_sql_injection(self, content: str, file_path: str) -> List[ReviewFinding]:
        """Check for SQL injection vulnerabilities."""
        import re
        findings = []
        
        # Look for string concatenation in SQL
        patterns = [
            r'execute\s*\(\s*["\'][^"\']*\s*\+',
            r'query\s*\(\s*["\'][^"\']*\s*\+',
            r'SELECT\s+.*\s*\+\s*\w+',
            r'f"SELECT\s+',
            r'f\'SELECT\s+',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                findings.append(ReviewFinding(
                    category="security",
                    severity=ReviewSeverity.CRITICAL,
                    title="Potential SQL Injection",
                    description="String concatenation in SQL query detected",
                    file_path=file_path,
                    line_number=line_num,
                    recommendation="Use parameterized queries instead"
                ))
        
        return findings
    
    def _check_xss_vulnerabilities(self, content: str, file_path: str) -> List[ReviewFinding]:
        """Check for XSS vulnerabilities."""
        import re
        findings = []
        
        # Look for innerHTML usage
        patterns = [
            (r'\.innerHTML\s*=', "innerHTML assignment"),
            (r'dangerouslySetInnerHTML', "dangerouslySetInnerHTML usage"),
            (r'document\.write\(', "document.write usage"),
        ]
        
        for pattern, desc in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                findings.append(ReviewFinding(
                    category="security",
                    severity=ReviewSeverity.WARNING,
                    title=f"Potential XSS: {desc}",
                    description=f"{desc} can lead to XSS if user input is not sanitized",
                    file_path=file_path,
                    line_number=line_num,
                    recommendation="Sanitize user input before rendering"
                ))
        
        return findings
    
    def _calculate_score(self, findings: List[ReviewFinding]) -> float:
        """Calculate review score based on findings."""
        if not findings:
            return 100.0
        
        # Start with 100, deduct based on severity
        score = 100.0
        
        for finding in findings:
            if finding.severity == ReviewSeverity.CRITICAL:
                score -= 15
            elif finding.severity == ReviewSeverity.WARNING:
                score -= 5
            elif finding.severity == ReviewSeverity.INFO:
                score -= 1
        
        return max(0.0, score)
    
    def _generate_summary(self, findings: List[ReviewFinding]) -> str:
        """Generate a summary of findings."""
        if not findings:
            return "No issues found. Code looks good!"
        
        critical = len([f for f in findings if f.severity == ReviewSeverity.CRITICAL])
        warnings = len([f for f in findings if f.severity == ReviewSeverity.WARNING])
        info = len([f for f in findings if f.severity == ReviewSeverity.INFO])
        
        parts = []
        if critical:
            parts.append(f"{critical} critical issue(s)")
        if warnings:
            parts.append(f"{warnings} warning(s)")
        if info:
            parts.append(f"{info} info item(s)")
        
        return f"Found {', '.join(parts)}"
    
    def _deduplicate_findings(self, findings: List[ReviewFinding]) -> List[ReviewFinding]:
        """Remove duplicate findings."""
        seen = set()
        unique = []
        
        for finding in findings:
            key = (finding.title, finding.file_path, finding.line_number)
            if key not in seen:
                seen.add(key)
                unique.append(finding)
        
        return unique


# Singleton instance
_design_review_service: Optional[DesignReviewService] = None


def get_design_review_service() -> DesignReviewService:
    """Get or create design review service singleton."""
    global _design_review_service
    if _design_review_service is None:
        _design_review_service = DesignReviewService()
    return _design_review_service
