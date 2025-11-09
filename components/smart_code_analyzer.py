"""
Smart Code Analyzer - Programmatic Intelligence for AI Enhancement

Uses regex, AST parsing, and pattern matching to extract valuable context
without relying on AI. This removes noise and provides structured data
that helps the AI make better decisions.

Features:
- Extract API endpoints with HTTP methods
- Find database models/entities with fields
- Detect UI components and their props
- Extract imports/dependencies graph
- Find test files and coverage
- Detect naming conventions
- Extract comments/documentation
- Find configuration patterns
"""

import re
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import json


@dataclass
class APIEndpoint:
    """Programmatically extracted API endpoint"""
    path: str
    method: str  # GET, POST, PUT, DELETE, PATCH
    file_path: str
    line_number: int
    controller: str
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    auth_required: bool = False


@dataclass
class DatabaseModel:
    """Programmatically extracted database model"""
    name: str
    file_path: str
    fields: Dict[str, str] = field(default_factory=dict)  # field_name -> type
    relationships: List[Tuple[str, str]] = field(default_factory=list)  # (type, target_model)
    indexes: List[str] = field(default_factory=list)


@dataclass
class UIComponent:
    """Programmatically extracted UI component"""
    name: str
    file_path: str
    framework: str  # Angular, React, Vue
    props: Dict[str, str] = field(default_factory=dict)
    events: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class NamingConvention:
    """Detected naming conventions"""
    files: str  # camelCase, PascalCase, kebab-case, snake_case
    variables: str
    functions: str
    classes: str
    constants: str
    confidence: float  # 0-1


class SmartCodeAnalyzer:
    """Programmatic code analysis without AI"""
    
    def __init__(self):
        self.api_patterns = {
            # .NET/C# patterns
            'dotnet': [
                r'\[Http(Get|Post|Put|Delete|Patch)\(?\"?([^\"]*?)\"?\)?\]',
                r'\[Route\(\"([^\"]+)\"\)\]',
            ],
            # FastAPI/Flask patterns
            'python': [
                r'@app\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]',
                r'@router\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]',
            ],
            # Express.js patterns
            'javascript': [
                r'router\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]',
                r'app\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]',
            ],
            # Spring Boot patterns
            'java': [
                r'@(Get|Post|Put|Delete|Patch)Mapping\([\"\'](.*?)[\"\']',
                r'@RequestMapping\(.*?path\s*=\s*[\"\'](.*?)[\"\']',
            ]
        }
    
    def analyze_project(self, project_root: Path) -> Dict:
        """
        Comprehensive programmatic analysis
        Returns structured data for AI consumption
        """
        result = {
            'api_endpoints': [],
            'database_models': [],
            'ui_components': [],
            'naming_conventions': None,
            'dependency_graph': {},
            'test_coverage': {},
            'documentation_coverage': {},
            'code_smells': []
        }
        
        # Analyze all code files
        code_files = self._find_code_files(project_root)
        
        for file_path in code_files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Extract API endpoints
                endpoints = self._extract_api_endpoints(file_path, content)
                result['api_endpoints'].extend(endpoints)
                
                # Extract database models
                models = self._extract_database_models(file_path, content)
                result['database_models'].extend(models)
                
                # Extract UI components
                components = self._extract_ui_components(file_path, content)
                result['ui_components'].extend(components)
                
                # Build dependency graph
                imports = self._extract_imports(file_path, content)
                result['dependency_graph'][str(file_path)] = imports
                
            except Exception as e:
                print(f"[WARN] Failed to analyze {file_path}: {e}")
        
        # Detect naming conventions
        result['naming_conventions'] = self._detect_naming_conventions(code_files)
        
        # Calculate test coverage
        result['test_coverage'] = self._calculate_test_coverage(project_root, code_files)
        
        return result
    
    def _find_code_files(self, root: Path) -> List[Path]:
        """Find all relevant code files"""
        extensions = {'.py', '.cs', '.ts', '.js', '.jsx', '.tsx', '.java', '.vue'}
        exclude_dirs = {'node_modules', 'venv', '.venv', '__pycache__', 'bin', 'obj', 'dist', 'build'}
        
        files = []
        for ext in extensions:
            for file_path in root.rglob(f'*{ext}'):
                if not any(excl in file_path.parts for excl in exclude_dirs):
                    files.append(file_path)
        
        return files
    
    def _extract_api_endpoints(self, file_path: Path, content: str) -> List[APIEndpoint]:
        """Extract API endpoints using regex patterns"""
        endpoints = []
        
        # Detect language
        ext = file_path.suffix
        language = {
            '.cs': 'dotnet',
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'javascript',
            '.java': 'java'
        }.get(ext)
        
        if not language:
            return endpoints
        
        patterns = self.api_patterns.get(language, [])
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            for pattern in patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    try:
                        if language == 'dotnet':
                            # .NET: [HttpGet("api/users")]
                            method = match.group(1).upper()
                            path = match.group(2) if len(match.groups()) > 1 else ""
                        else:
                            # Python/JS: @app.get("/api/users")
                            method = match.group(1).upper()
                            path = match.group(2)
                        
                        # Extract controller name
                        controller = self._extract_controller_name(file_path, content, i)
                        
                        # Extract parameters
                        params = self._extract_endpoint_params(lines, i, language)
                        
                        endpoints.append(APIEndpoint(
                            path=path or "/",
                            method=method,
                            file_path=str(file_path),
                            line_number=i + 1,
                            controller=controller,
                            parameters=params
                        ))
                    except Exception as e:
                        continue
        
        return endpoints
    
    def _extract_controller_name(self, file_path: Path, content: str, line_num: int) -> str:
        """Extract controller/route handler name"""
        # Look backwards for class/function definition
        lines = content.split('\n')
        for i in range(min(line_num, len(lines) - 1), max(0, line_num - 20), -1):
            line = lines[i]
            # Class definition
            class_match = re.search(r'class\s+(\w+)', line)
            if class_match:
                return class_match.group(1)
            # Function definition
            func_match = re.search(r'def\s+(\w+)|function\s+(\w+)|public\s+\w+\s+(\w+)', line)
            if func_match:
                return func_match.group(1) or func_match.group(2) or func_match.group(3)
        
        return file_path.stem
    
    def _extract_endpoint_params(self, lines: List[str], line_num: int, language: str) -> List[str]:
        """Extract endpoint parameters"""
        params = []
        
        # Look at next 5 lines for parameter definitions
        for i in range(line_num, min(line_num + 5, len(lines))):
            line = lines[i]
            
            if language == 'dotnet':
                # [FromBody] UserDto user
                param_matches = re.findall(r'\[From\w+\]\s+\w+\s+(\w+)', line)
                params.extend(param_matches)
            elif language == 'python':
                # (user: UserDto)
                param_matches = re.findall(r'(\w+):\s*\w+', line)
                params.extend(param_matches)
        
        return params
    
    def _extract_database_models(self, file_path: Path, content: str) -> List[DatabaseModel]:
        """Extract database models/entities"""
        models = []
        
        ext = file_path.suffix
        if ext == '.cs':
            # C# Entity Framework models
            models.extend(self._extract_csharp_models(file_path, content))
        elif ext == '.py':
            # Python SQLAlchemy/Django models
            models.extend(self._extract_python_models(file_path, content))
        
        return models
    
    def _extract_csharp_models(self, file_path: Path, content: str) -> List[DatabaseModel]:
        """Extract C# EF models"""
        models = []
        
        # Find class definitions that look like models
        class_pattern = r'public\s+class\s+(\w+)(?:\s*:\s*\w+)?'
        classes = re.finditer(class_pattern, content)
        
        for class_match in classes:
            class_name = class_match.group(1)
            class_start = class_match.start()
            
            # Extract fields (properties)
            fields = {}
            prop_pattern = r'public\s+(\w+(?:<\w+>)?)\s+(\w+)\s*{\s*get;\s*set;\s*}'
            props = re.finditer(prop_pattern, content[class_start:])
            
            for prop_match in props:
                prop_type = prop_match.group(1)
                prop_name = prop_match.group(2)
                fields[prop_name] = prop_type
            
            if fields:  # Only add if has fields (likely a model)
                models.append(DatabaseModel(
                    name=class_name,
                    file_path=str(file_path),
                    fields=fields
                ))
        
        return models
    
    def _extract_python_models(self, file_path: Path, content: str) -> List[DatabaseModel]:
        """Extract Python ORM models"""
        models = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if inherits from Base/Model
                    bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
                    if any(b in ['Model', 'Base', 'Document'] for b in bases):
                        fields = {}
                        
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name):
                                        # Try to get type from annotation
                                        field_type = 'Unknown'
                                        if isinstance(item.value, ast.Call):
                                            if hasattr(item.value.func, 'attr'):
                                                field_type = item.value.func.attr
                                        
                                        fields[target.id] = field_type
                        
                        if fields:
                            models.append(DatabaseModel(
                                name=node.name,
                                file_path=str(file_path),
                                fields=fields
                            ))
        except SyntaxError:
            pass
        
        return models
    
    def _extract_ui_components(self, file_path: Path, content: str) -> List[UIComponent]:
        """Extract UI components"""
        components = []
        
        if file_path.suffix == '.ts' and file_path.name.endswith('.component.ts'):
            # Angular component
            comp_name = file_path.stem.replace('.component', '')
            selector_match = re.search(r'selector:\s*[\'"]([^\'"]+)[\'"]', content)
            
            if selector_match:
                components.append(UIComponent(
                    name=comp_name,
                    file_path=str(file_path),
                    framework='Angular',
                    props=self._extract_angular_inputs(content)
                ))
        
        elif file_path.suffix in ['.jsx', '.tsx']:
            # React component
            comp_match = re.search(r'(?:function|const)\s+(\w+)', content)
            if comp_match:
                components.append(UIComponent(
                    name=comp_match.group(1),
                    file_path=str(file_path),
                    framework='React',
                    props=self._extract_react_props(content)
                ))
        
        return components
    
    def _extract_angular_inputs(self, content: str) -> Dict[str, str]:
        """Extract Angular @Input properties"""
        inputs = {}
        input_pattern = r'@Input\(\)\s+(\w+)(?::\s*(\w+))?'
        
        for match in re.finditer(input_pattern, content):
            prop_name = match.group(1)
            prop_type = match.group(2) or 'any'
            inputs[prop_name] = prop_type
        
        return inputs
    
    def _extract_react_props(self, content: str) -> Dict[str, str]:
        """Extract React component props"""
        props = {}
        
        # Look for Props interface
        props_pattern = r'interface\s+\w*Props\s*{([^}]+)}'
        match = re.search(props_pattern, content)
        
        if match:
            props_body = match.group(1)
            prop_lines = re.findall(r'(\w+)(?:\?)?:\s*(\w+)', props_body)
            props = {name: type_ for name, type_ in prop_lines}
        
        return props
    
    def _extract_imports(self, file_path: Path, content: str) -> List[str]:
        """Extract import dependencies"""
        imports = []
        
        # Python imports
        if file_path.suffix == '.py':
            imports.extend(re.findall(r'from\s+([\w.]+)\s+import', content))
            imports.extend(re.findall(r'import\s+([\w.]+)', content))
        
        # JavaScript/TypeScript imports
        elif file_path.suffix in ['.js', '.ts', '.jsx', '.tsx']:
            imports.extend(re.findall(r'from\s+[\'"]([^\'"]+)[\'"]', content))
            imports.extend(re.findall(r'import\s+[\'"]([^\'"]+)[\'"]', content))
        
        # C# using statements
        elif file_path.suffix == '.cs':
            imports.extend(re.findall(r'using\s+([\w.]+);', content))
        
        return list(set(imports))  # Remove duplicates
    
    def _detect_naming_conventions(self, files: List[Path]) -> NamingConvention:
        """Detect naming conventions from code"""
        conventions = {
            'camelCase': 0,
            'PascalCase': 0,
            'snake_case': 0,
            'kebab-case': 0
        }
        
        for file_path in files[:50]:  # Sample first 50 files
            name = file_path.stem
            
            if '-' in name:
                conventions['kebab-case'] += 1
            elif '_' in name:
                conventions['snake_case'] += 1
            elif name[0].isupper():
                conventions['PascalCase'] += 1
            elif name[0].islower():
                conventions['camelCase'] += 1
        
        # Find dominant convention
        dominant = max(conventions, key=conventions.get)
        total = sum(conventions.values())
        confidence = conventions[dominant] / total if total > 0 else 0
        
        return NamingConvention(
            files=dominant,
            variables='camelCase',  # Default assumptions
            functions='camelCase',
            classes='PascalCase',
            constants='UPPER_SNAKE_CASE',
            confidence=confidence
        )
    
    def _calculate_test_coverage(self, root: Path, code_files: List[Path]) -> Dict:
        """Calculate which files have tests"""
        test_patterns = ['test_', '_test.', '.spec.', '.test.']
        
        test_files = set()
        for file in code_files:
            if any(pattern in file.name.lower() for pattern in test_patterns):
                test_files.add(file.stem.replace('test_', '').replace('_test', '').replace('.spec', '').replace('.test', ''))
        
        code_modules = set()
        for file in code_files:
            if not any(pattern in file.name.lower() for pattern in test_patterns):
                code_modules.add(file.stem)
        
        tested = code_modules & test_files
        coverage_percent = (len(tested) / len(code_modules) * 100) if code_modules else 0
        
        return {
            'total_modules': len(code_modules),
            'tested_modules': len(tested),
            'coverage_percent': coverage_percent,
            'untested_modules': list(code_modules - test_files)[:10]  # Show first 10
        }
    
    def format_for_ai(self, analysis: Dict) -> str:
        """Format analysis results for AI consumption"""
        output = []
        
        # API Endpoints
        if analysis['api_endpoints']:
            output.append("=== DETECTED API ENDPOINTS (PROGRAMMATIC) ===")
            for endpoint in analysis['api_endpoints'][:20]:  # Limit to 20
                output.append(f"{endpoint.method} {endpoint.path}")
                output.append(f"  Controller: {endpoint.controller}")
                if endpoint.parameters:
                    output.append(f"  Parameters: {', '.join(endpoint.parameters)}")
                output.append("")
        
        # Database Models
        if analysis['database_models']:
            output.append("=== DETECTED DATABASE MODELS (PROGRAMMATIC) ===")
            for model in analysis['database_models'][:15]:
                output.append(f"Model: {model.name}")
                for field_name, field_type in list(model.fields.items())[:10]:
                    output.append(f"  - {field_name}: {field_type}")
                output.append("")
        
        # UI Components
        if analysis['ui_components']:
            output.append("=== DETECTED UI COMPONENTS (PROGRAMMATIC) ===")
            for comp in analysis['ui_components'][:15]:
                output.append(f"{comp.framework} Component: {comp.name}")
                if comp.props:
                    output.append(f"  Props: {', '.join(comp.props.keys())}")
                output.append("")
        
        # Naming Conventions
        if analysis['naming_conventions']:
            conv = analysis['naming_conventions']
            output.append("=== DETECTED NAMING CONVENTIONS ===")
            output.append(f"Files: {conv.files} (confidence: {conv.confidence:.0%})")
            output.append(f"Variables: {conv.variables}")
            output.append(f"Functions: {conv.functions}")
            output.append(f"Classes: {conv.classes}")
            output.append("")
        
        # Test Coverage
        if analysis['test_coverage']:
            cov = analysis['test_coverage']
            output.append("=== TEST COVERAGE (PROGRAMMATIC) ===")
            output.append(f"Coverage: {cov['coverage_percent']:.1f}% ({cov['tested_modules']}/{cov['total_modules']} modules)")
            if cov.get('untested_modules'):
                output.append(f"Untested: {', '.join(cov['untested_modules'][:5])}")
            output.append("")
        
        return '\n'.join(output)


# Global instance
_analyzer = None

def get_smart_analyzer() -> SmartCodeAnalyzer:
    """Get global smart analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = SmartCodeAnalyzer()
    return _analyzer
