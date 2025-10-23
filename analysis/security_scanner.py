"""
Security Scanner
Scans code for security vulnerabilities and risks
"""

import re
from typing import Dict, List, Any, Tuple
from pathlib import Path

class SecurityScanner:
    """Scan code for security vulnerabilities"""
    
    def __init__(self):
        self.vulnerability_db = self._load_vulnerability_patterns()
    
    def _load_vulnerability_patterns(self) -> Dict[str, List[Tuple[str, str, str]]]:
        """Load vulnerability patterns for different languages"""
        return {
            "python": [
                # SQL Injection
                (r"execute\s*\(\s*['\"].*%s", "SQL Injection", "Use parameterized queries"),
                (r"execute\s*\(\s*['\"].*\+", "SQL Injection", "Use parameterized queries"),
                (r"\.format\s*\(.*SELECT", "SQL Injection", "Use parameterized queries"),
                
                # Command Injection
                (r"os\.system\s*\(", "Command Injection", "Avoid os.system, use subprocess with shell=False"),
                (r"subprocess\.call\s*\(.*shell\s*=\s*True", "Command Injection", "Set shell=False in subprocess"),
                (r"eval\s*\(", "Code Injection", "Never use eval() with user input"),
                (r"exec\s*\(", "Code Injection", "Never use exec() with user input"),
                
                # Path Traversal
                (r"open\s*\([^)]*\+", "Path Traversal", "Validate and sanitize file paths"),
                (r"os\.path\.join\s*\([^)]*input", "Path Traversal", "Validate user input before path operations"),
                
                # Insecure Deserialization
                (r"pickle\.loads?\s*\(", "Insecure Deserialization", "Avoid pickle with untrusted data"),
                (r"yaml\.load\s*\((?!.*Loader=yaml\.SafeLoader)", "Insecure Deserialization", "Use yaml.safe_load()"),
                
                # Weak Cryptography
                (r"md5\s*\(", "Weak Cryptography", "Use SHA-256 or stronger"),
                (r"sha1\s*\(", "Weak Cryptography", "Use SHA-256 or stronger"),
                (r"random\.random", "Weak Random", "Use secrets module for security-sensitive randomness"),
                
                # Hardcoded Secrets
                (r"password\s*=\s*['\"][^'\"]+['\"]", "Hardcoded Password", "Use environment variables or secret management"),
                (r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API Key", "Use environment variables"),
                (r"secret[_-]?key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded Secret", "Use environment variables"),
                (r"token\s*=\s*['\"][^'\"]{20,}['\"]", "Hardcoded Token", "Use environment variables"),
                
                # Insecure Network
                (r"requests\.get\s*\(\s*['\"]http://", "Insecure HTTP", "Use HTTPS"),
                (r"urllib\.request\.urlopen\s*\(\s*['\"]http://", "Insecure HTTP", "Use HTTPS"),
                (r"ssl\._create_unverified_context", "SSL Verification Disabled", "Enable SSL verification"),
                
                # Debug Mode
                (r"debug\s*=\s*True", "Debug Mode Enabled", "Disable debug mode in production"),
                (r"app\.run\s*\(.*debug\s*=\s*True", "Debug Mode Enabled", "Disable debug mode in production"),
            ],
            
            "javascript": [
                # XSS
                (r"innerHTML\s*=", "XSS Risk", "Use textContent or sanitize HTML"),
                (r"dangerouslySetInnerHTML", "XSS Risk", "Sanitize HTML before rendering"),
                (r"document\.write\s*\(", "XSS Risk", "Avoid document.write"),
                
                # SQL Injection
                (r"query\s*\(\s*['\"].*\+", "SQL Injection", "Use parameterized queries"),
                (r"execute\s*\(\s*['\"].*\+", "SQL Injection", "Use parameterized queries"),
                (r"`SELECT.*\$\{", "SQL Injection", "Use parameterized queries"),
                
                # Command Injection
                (r"exec\s*\(", "Command Injection", "Validate and sanitize input"),
                (r"eval\s*\(", "Code Injection", "Never use eval()"),
                (r"Function\s*\(", "Code Injection", "Avoid Function constructor"),
                
                # Insecure Random
                (r"Math\.random\s*\(", "Weak Random", "Use crypto.randomBytes() for security"),
                
                # Hardcoded Secrets
                (r"password\s*[:=]\s*['\"][^'\"]+['\"]", "Hardcoded Password", "Use environment variables"),
                (r"apiKey\s*[:=]\s*['\"][^'\"]+['\"]", "Hardcoded API Key", "Use environment variables"),
                (r"secret\s*[:=]\s*['\"][^'\"]+['\"]", "Hardcoded Secret", "Use environment variables"),
                
                # Insecure Network
                (r"http://", "Insecure HTTP", "Use HTTPS"),
                (r"rejectUnauthorized\s*:\s*false", "SSL Verification Disabled", "Enable SSL verification"),
                
                # Prototype Pollution
                (r"Object\.assign\s*\(\s*\{\}", "Prototype Pollution Risk", "Validate object keys"),
                (r"\[.*\]\s*=", "Prototype Pollution Risk", "Validate property names"),
            ],
            
            "typescript": [
                # Same as JavaScript plus type-specific issues
                (r"any\s+", "Type Safety", "Avoid 'any' type, use specific types"),
                (r"as\s+any", "Type Safety", "Avoid type assertions to 'any'"),
                (r"@ts-ignore", "Type Safety", "Fix type errors instead of ignoring"),
            ],
            
            "csharp": [
                # SQL Injection
                (r"SqlCommand\s*\(.*\+", "SQL Injection", "Use parameterized queries"),
                (r"ExecuteReader\s*\(.*\+", "SQL Injection", "Use parameterized queries"),
                
                # Command Injection
                (r"Process\.Start\s*\(", "Command Injection", "Validate and sanitize input"),
                
                # Path Traversal
                (r"File\.ReadAllText\s*\(.*\+", "Path Traversal", "Validate file paths"),
                (r"Path\.Combine\s*\(.*input", "Path Traversal", "Validate user input"),
                
                # Insecure Deserialization
                (r"BinaryFormatter", "Insecure Deserialization", "Use JSON or XML serialization"),
                
                # Weak Cryptography
                (r"MD5\.Create", "Weak Cryptography", "Use SHA256 or stronger"),
                (r"SHA1\.Create", "Weak Cryptography", "Use SHA256 or stronger"),
                (r"DES", "Weak Cryptography", "Use AES"),
                
                # Hardcoded Secrets
                (r"password\s*=\s*\"[^\"]+\"", "Hardcoded Password", "Use configuration or secret management"),
                (r"connectionString\s*=\s*\"[^\"]+\"", "Hardcoded Connection String", "Use configuration"),
            ]
        }
    
    def scan_file(self, file_path: str, content: str, language: str) -> Dict[str, Any]:
        """
        Scan a file for security vulnerabilities
        
        Args:
            file_path: Path to the file
            content: File content
            language: Programming language
        
        Returns:
            Dictionary with scan results
        """
        vulnerabilities = []
        
        # Get patterns for this language
        patterns = self.vulnerability_db.get(language, [])
        
        lines = content.split('\n')
        
        # Scan each line
        for i, line in enumerate(lines, 1):
            for pattern, vuln_type, recommendation in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    vulnerabilities.append({
                        "line": i,
                        "code": line.strip(),
                        "type": vuln_type,
                        "severity": self._get_severity(vuln_type),
                        "recommendation": recommendation,
                        "cwe": self._get_cwe(vuln_type)
                    })
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(vulnerabilities)
        
        return {
            "file_path": file_path,
            "language": language,
            "vulnerabilities": vulnerabilities,
            "risk_score": risk_score,
            "summary": self._generate_summary(vulnerabilities, risk_score)
        }
    
    def scan_directory(self, directory: str) -> Dict[str, Any]:
        """
        Scan entire directory for security vulnerabilities
        
        Args:
            directory: Directory path to scan
        
        Returns:
            Aggregated scan results
        """
        dir_path = Path(directory)
        all_vulnerabilities = []
        scanned_files = 0
        
        # Language extensions
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.cs': 'csharp'
        }
        
        # Scan all files
        for file_path in dir_path.rglob('*'):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in lang_map:
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        language = lang_map[ext]
                        result = self.scan_file(str(file_path), content, language)
                        
                        if result['vulnerabilities']:
                            all_vulnerabilities.extend(result['vulnerabilities'])
                        
                        scanned_files += 1
                    except Exception as e:
                        print(f"Error scanning {file_path}: {e}")
        
        # Aggregate results
        overall_risk = self._calculate_risk_score(all_vulnerabilities)
        
        return {
            "scanned_files": scanned_files,
            "total_vulnerabilities": len(all_vulnerabilities),
            "vulnerabilities_by_severity": self._group_by_severity(all_vulnerabilities),
            "vulnerabilities_by_type": self._group_by_type(all_vulnerabilities),
            "overall_risk_score": overall_risk,
            "recommendations": self._generate_recommendations(all_vulnerabilities)
        }
    
    def _get_severity(self, vuln_type: str) -> str:
        """Get severity level for vulnerability type"""
        critical = ["SQL Injection", "Command Injection", "Code Injection", "Insecure Deserialization"]
        high = ["XSS Risk", "Path Traversal", "Hardcoded Password", "Hardcoded API Key"]
        medium = ["Weak Cryptography", "Weak Random", "SSL Verification Disabled", "Debug Mode Enabled"]
        
        if vuln_type in critical:
            return "CRITICAL"
        elif vuln_type in high:
            return "HIGH"
        elif vuln_type in medium:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _get_cwe(self, vuln_type: str) -> str:
        """Get CWE (Common Weakness Enumeration) ID"""
        cwe_map = {
            "SQL Injection": "CWE-89",
            "Command Injection": "CWE-78",
            "Code Injection": "CWE-94",
            "XSS Risk": "CWE-79",
            "Path Traversal": "CWE-22",
            "Insecure Deserialization": "CWE-502",
            "Weak Cryptography": "CWE-327",
            "Weak Random": "CWE-338",
            "Hardcoded Password": "CWE-259",
            "Hardcoded API Key": "CWE-798",
            "Hardcoded Secret": "CWE-798",
            "SSL Verification Disabled": "CWE-295",
            "Insecure HTTP": "CWE-319",
            "Debug Mode Enabled": "CWE-489",
            "Prototype Pollution Risk": "CWE-1321"
        }
        
        return cwe_map.get(vuln_type, "CWE-Unknown")
    
    def _calculate_risk_score(self, vulnerabilities: List[Dict[str, Any]]) -> float:
        """Calculate overall risk score (0-100)"""
        if not vulnerabilities:
            return 0.0
        
        severity_weights = {
            "CRITICAL": 10,
            "HIGH": 7,
            "MEDIUM": 4,
            "LOW": 1
        }
        
        total_risk = sum(
            severity_weights.get(v.get("severity", "LOW"), 1)
            for v in vulnerabilities
        )
        
        # Normalize to 0-100
        risk_score = min(100.0, total_risk * 2)
        
        return round(risk_score, 1)
    
    def _group_by_severity(self, vulnerabilities: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group vulnerabilities by severity"""
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        for vuln in vulnerabilities:
            severity = vuln.get("severity", "LOW")
            counts[severity] = counts.get(severity, 0) + 1
        
        return counts
    
    def _group_by_type(self, vulnerabilities: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group vulnerabilities by type"""
        counts = {}
        
        for vuln in vulnerabilities:
            vuln_type = vuln.get("type", "Unknown")
            counts[vuln_type] = counts.get(vuln_type, 0) + 1
        
        return counts
    
    def _generate_summary(self, vulnerabilities: List[Dict[str, Any]], risk_score: float) -> str:
        """Generate scan summary"""
        if not vulnerabilities:
            return "No security vulnerabilities detected"
        
        by_severity = self._group_by_severity(vulnerabilities)
        
        parts = [
            f"Risk Score: {risk_score}/100",
            f"Total: {len(vulnerabilities)}"
        ]
        
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if by_severity[severity] > 0:
                parts.append(f"{severity}: {by_severity[severity]}")
        
        return " | ".join(parts)
    
    def _generate_recommendations(self, vulnerabilities: List[Dict[str, Any]]) -> List[str]:
        """Generate prioritized recommendations"""
        recommendations = {}
        
        for vuln in vulnerabilities:
            rec = vuln.get("recommendation", "")
            vuln_type = vuln.get("type", "")
            severity = vuln.get("severity", "LOW")
            
            if rec and rec not in recommendations:
                recommendations[rec] = {
                    "type": vuln_type,
                    "severity": severity,
                    "count": 1
                }
            elif rec:
                recommendations[rec]["count"] += 1
        
        # Sort by severity and count
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        sorted_recs = sorted(
            recommendations.items(),
            key=lambda x: (severity_order.get(x[1]["severity"], 4), -x[1]["count"])
        )
        
        return [
            f"{rec} ({data['type']}, {data['severity']}, {data['count']} occurrences)"
            for rec, data in sorted_recs[:10]  # Top 10 recommendations
        ]


# Global security scanner
_security_scanner = None

def get_security_scanner() -> SecurityScanner:
    """Get or create global security scanner"""
    global _security_scanner
    if _security_scanner is None:
        _security_scanner = SecurityScanner()
    return _security_scanner

