"""
Enhanced Metadata System
Extracts rich metadata from files for better filtering and retrieval
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

class MetadataEnhancer:
    """Extract and enhance metadata from files"""
    
    def __init__(self):
        self.language_patterns = {
            'python': [r'def ', r'class ', r'import ', r'from .* import'],
            'typescript': [r'interface ', r'type ', r'function ', r'const ', r'import '],
            'javascript': [r'function ', r'const ', r'let ', r'var ', r'import '],
            'csharp': [r'class ', r'namespace ', r'using ', r'public ', r'private '],
            'java': [r'class ', r'interface ', r'package ', r'import '],
            'go': [r'func ', r'package ', r'import ', r'type '],
            'rust': [r'fn ', r'struct ', r'impl ', r'use ']
        }
    
    def enhance(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from file
        
        Args:
            file_path: Path to the file
            content: File content
        
        Returns:
            Dictionary of metadata
        """
        metadata = {
            # Basic info
            'file_path': file_path,
            'file_name': Path(file_path).name,
            'file_type': Path(file_path).suffix,
            'file_size': len(content),
            'line_count': len(content.split('\n')),
            
            # Timestamps
            'last_modified': self._get_modified_time(file_path),
            'indexed_at': datetime.now().isoformat(),
            
            # Language detection
            'language': self._detect_language(file_path, content),
            
            # Code metrics
            'complexity_score': self._calculate_complexity(content),
            'comment_ratio': self._calculate_comment_ratio(content),
            
            # Content analysis
            'has_tests': self._has_tests(file_path, content),
            'has_documentation': self._has_documentation(content),
            'is_config': self._is_config_file(file_path),
            'is_generated': self._is_generated(content),
            
            # Code structure
            'function_count': self._count_functions(content),
            'class_count': self._count_classes(content),
            'import_count': self._count_imports(content),
            
            # Dependencies
            'imports': self._extract_imports(content),
            'exports': self._extract_exports(content),
            
            # Quality indicators
            'has_type_hints': self._has_type_hints(content),
            'has_error_handling': self._has_error_handling(content),
            'has_logging': self._has_logging(content),
            
            # Importance score
            'importance_score': 0.5  # Will be calculated
        }
        
        # Calculate importance score
        metadata['importance_score'] = self._calculate_importance(metadata)
        
        return metadata
    
    def _get_modified_time(self, file_path: str) -> str:
        """Get file modification time"""
        try:
            mtime = os.path.getmtime(file_path)
            return datetime.fromtimestamp(mtime).isoformat()
        except:
            return datetime.now().isoformat()
    
    def _detect_language(self, file_path: str, content: str) -> str:
        """Detect programming language"""
        ext = Path(file_path).suffix.lower()
        
        # Extension-based detection
        ext_map = {
            '.py': 'python',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.cs': 'csharp',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin'
        }
        
        if ext in ext_map:
            return ext_map[ext]
        
        # Pattern-based detection
        for lang, patterns in self.language_patterns.items():
            if any(re.search(pattern, content) for pattern in patterns):
                return lang
        
        return 'unknown'
    
    def _calculate_complexity(self, content: str) -> float:
        """Calculate code complexity score (0-1)"""
        lines = content.split('\n')
        
        # Count complexity indicators
        complexity_indicators = {
            'if': 0.1,
            'for': 0.1,
            'while': 0.1,
            'try': 0.1,
            'catch': 0.1,
            'switch': 0.15,
            'case': 0.05,
            '&&': 0.05,
            '||': 0.05,
            'async': 0.1,
            'await': 0.05
        }
        
        score = 0
        for line in lines:
            for indicator, weight in complexity_indicators.items():
                score += line.count(indicator) * weight
        
        # Normalize to 0-1
        normalized = min(score / max(len(lines), 1), 1.0)
        return round(normalized, 3)
    
    def _calculate_comment_ratio(self, content: str) -> float:
        """Calculate ratio of comments to code"""
        lines = content.split('\n')
        comment_lines = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(('#', '//', '/*', '*', '"""', "'''")):
                comment_lines += 1
        
        if len(lines) == 0:
            return 0.0
        
        return round(comment_lines / len(lines), 3)
    
    def _has_tests(self, file_path: str, content: str) -> bool:
        """Check if file contains tests"""
        test_indicators = [
            'test_', 'Test', 'describe(', 'it(', 'expect(',
            '@Test', 'unittest', 'pytest', 'jest', 'mocha'
        ]
        
        # Check file name
        if any(indicator in file_path.lower() for indicator in ['test', 'spec']):
            return True
        
        # Check content
        return any(indicator in content for indicator in test_indicators)
    
    def _has_documentation(self, content: str) -> bool:
        """Check if file has documentation"""
        doc_indicators = [
            '"""', "'''", '/**', '///', '@param', '@return',
            '@description', 'README', '# ', '## '
        ]
        
        return any(indicator in content for indicator in doc_indicators)
    
    def _is_config_file(self, file_path: str) -> bool:
        """Check if file is a configuration file"""
        config_extensions = {'.json', '.yaml', '.yml', '.toml', '.ini', '.env', '.config'}
        config_names = {'config', 'settings', 'package', 'tsconfig', 'webpack'}
        
        ext = Path(file_path).suffix.lower()
        name = Path(file_path).stem.lower()
        
        return ext in config_extensions or any(cfg in name for cfg in config_names)
    
    def _is_generated(self, content: str) -> bool:
        """Check if file is auto-generated"""
        generated_indicators = [
            'auto-generated', 'autogenerated', 'do not edit',
            'generated by', 'this file is generated'
        ]
        
        # Check first 10 lines
        first_lines = '\n'.join(content.split('\n')[:10]).lower()
        return any(indicator in first_lines for indicator in generated_indicators)
    
    def _count_functions(self, content: str) -> int:
        """Count functions in code"""
        patterns = [
            r'\bdef\s+\w+',  # Python
            r'\bfunction\s+\w+',  # JavaScript
            r'\bfunc\s+\w+',  # Go
            r'\bfn\s+\w+',  # Rust
            r'public\s+\w+\s+\w+\s*\(',  # Java/C#
        ]
        
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, content))
        
        return count
    
    def _count_classes(self, content: str) -> int:
        """Count classes in code"""
        patterns = [
            r'\bclass\s+\w+',  # Most languages
            r'\binterface\s+\w+',  # TypeScript/Java
            r'\bstruct\s+\w+',  # Go/Rust/C
        ]
        
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, content))
        
        return count
    
    def _count_imports(self, content: str) -> int:
        """Count import statements"""
        patterns = [
            r'^\s*import\s+',
            r'^\s*from\s+.+\s+import\s+',
            r'^\s*using\s+',
            r'^\s*require\s*\(',
        ]
        
        count = 0
        for line in content.split('\n'):
            for pattern in patterns:
                if re.match(pattern, line):
                    count += 1
                    break
        
        return count
    
    def _extract_imports(self, content: str) -> List[str]:
        """Extract imported modules/packages"""
        imports = []
        
        # Python imports
        python_imports = re.findall(r'(?:from|import)\s+([\w.]+)', content)
        imports.extend(python_imports[:10])  # Limit to 10
        
        # JavaScript/TypeScript imports
        js_imports = re.findall(r'import.*from\s+["\']([^"\']+)["\']', content)
        imports.extend(js_imports[:10])
        
        return list(set(imports))[:10]  # Unique, max 10
    
    def _extract_exports(self, content: str) -> List[str]:
        """Extract exported items"""
        exports = []
        
        # JavaScript/TypeScript exports
        export_patterns = [
            r'export\s+(?:default\s+)?(?:class|function|const|let|var)\s+(\w+)',
            r'export\s+\{\s*([^}]+)\s*\}'
        ]
        
        for pattern in export_patterns:
            matches = re.findall(pattern, content)
            exports.extend(matches)
        
        return list(set(exports))[:10]  # Unique, max 10
    
    def _has_type_hints(self, content: str) -> bool:
        """Check if code has type hints/annotations"""
        type_indicators = [
            ': str', ': int', ': bool', ': List', ': Dict',  # Python
            ': string', ': number', ': boolean',  # TypeScript
            '<T>', '<T extends',  # Generics
        ]
        
        return any(indicator in content for indicator in type_indicators)
    
    def _has_error_handling(self, content: str) -> bool:
        """Check if code has error handling"""
        error_indicators = [
            'try', 'catch', 'except', 'finally',
            'throw', 'raise', 'error', 'Error'
        ]
        
        return any(indicator in content for indicator in error_indicators)
    
    def _has_logging(self, content: str) -> bool:
        """Check if code has logging"""
        logging_indicators = [
            'console.log', 'console.error', 'console.warn',
            'logger.', 'logging.', 'log.', 'print('
        ]
        
        return any(indicator in content for indicator in logging_indicators)
    
    def _calculate_importance(self, metadata: Dict[str, Any]) -> float:
        """Calculate importance score based on metadata"""
        score = 0.5  # Base score
        
        # Boost for well-documented code
        if metadata['has_documentation']:
            score += 0.1
        
        # Boost for code with tests
        if metadata['has_tests']:
            score += 0.1
        
        # Boost for code with type hints
        if metadata['has_type_hints']:
            score += 0.05
        
        # Boost for code with error handling
        if metadata['has_error_handling']:
            score += 0.05
        
        # Penalty for generated files
        if metadata['is_generated']:
            score -= 0.2
        
        # Boost for recently modified files
        try:
            mod_time = datetime.fromisoformat(metadata['last_modified'])
            days_old = (datetime.now() - mod_time).days
            if days_old < 7:
                score += 0.1
            elif days_old < 30:
                score += 0.05
        except:
            pass
        
        # Boost for files with good comment ratio
        if 0.1 <= metadata['comment_ratio'] <= 0.3:
            score += 0.05
        
        # Normalize to 0-1
        return round(max(0.0, min(1.0, score)), 3)


# Global metadata enhancer
_metadata_enhancer = None

def get_metadata_enhancer() -> MetadataEnhancer:
    """Get or create global metadata enhancer"""
    global _metadata_enhancer
    if _metadata_enhancer is None:
        _metadata_enhancer = MetadataEnhancer()
    return _metadata_enhancer

