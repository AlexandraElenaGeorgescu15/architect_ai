"""
Static Code Analysis - November 9, 2025
Performs static analysis on critical files
"""

import sys
import os
from pathlib import Path
import re
import ast

# UTF-8 encoding fix for Windows
if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        pass

project_root = Path(__file__).parent.parent


def analyze_function_complexity(file_path: Path):
    """Analyze function complexity in a Python file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        return {"error": str(e)}
    
    functions = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Count lines
            if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                lines = node.end_lineno - node.lineno
            else:
                lines = 0
            
            # Count nested complexity (loops, ifs, etc.)
            complexity = 1  # Base complexity
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                    complexity += 1
            
            functions.append({
                'name': node.name,
                'lines': lines,
                'complexity': complexity
            })
    
    return functions


def check_code_smells(file_path: Path):
    """Check for common code smells"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    smells = []
    
    # Check for bare except
    bare_excepts = re.findall(r'except\s*:', content)
    if bare_excepts:
        smells.append(f"⚠️  Found {len(bare_excepts)} bare except: blocks")
    
    # Check for missing encoding
    file_opens = re.findall(r'open\([^)]+\)', content)
    for match in file_opens:
        if 'encoding=' not in match and 'mode=' in match and ('r' in match or 'w' in match):
            smells.append(f"⚠️  Potential missing encoding in: {match[:50]}")
    
    # Check for long lines
    lines = content.split('\n')
    long_lines = [(i+1, line) for i, line in enumerate(lines) if len(line) > 120]
    if long_lines:
        smells.append(f"⚠️  {len(long_lines)} lines exceed 120 chars")
    
    # Check for TODO/FIXME
    todos = [i+1 for i, line in enumerate(lines) if 'TODO' in line or 'FIXME' in line]
    if todos:
        smells.append(f"📝 {len(todos)} TODO/FIXME comments found")
    
    return smells


def analyze_imports(file_path: Path):
    """Analyze import statements"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return {"error": "Syntax error"}
    
    imports = []
    star_imports = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    if alias.name == '*':
                        star_imports.append(node.module)
                    else:
                        imports.append(f"{node.module}.{alias.name}")
    
    return {
        'total_imports': len(imports),
        'star_imports': star_imports,
        'unique_modules': len(set(imports))
    }


def run_analysis():
    """Run comprehensive static analysis"""
    print("="*80)
    print("🔍 STATIC CODE ANALYSIS")
    print("="*80)
    
    files_to_analyze = [
        "utils/entity_extractor.py",
        "agents/universal_agent.py",
        "validation/output_validator.py",
        "components/adaptive_learning.py",
    ]
    
    for file_path_str in files_to_analyze:
        file_path = project_root / file_path_str
        if not file_path.exists():
            continue
        
        print(f"\n{'='*80}")
        print(f"📄 {file_path_str}")
        print(f"{'='*80}")
        
        # File size
        size = file_path.stat().st_size
        print(f"Size: {size:,} bytes ({size/1024:.1f} KB)")
        
        # Line count
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        print(f"Lines: {len(lines):,}")
        
        # Function complexity
        functions = analyze_function_complexity(file_path)
        if isinstance(functions, dict) and 'error' in functions:
            print(f"⚠️  Syntax error: {functions['error']}")
        else:
            print(f"Functions: {len(functions)}")
            
            # Find most complex functions
            if functions:
                complex_funcs = sorted(functions, key=lambda x: x['complexity'], reverse=True)[:3]
                print("\n📊 Most Complex Functions:")
                for func in complex_funcs:
                    print(f"  - {func['name']}: {func['lines']} lines, complexity {func['complexity']}")
        
        # Import analysis
        import_info = analyze_imports(file_path)
        if 'error' not in import_info:
            print(f"\n📦 Imports: {import_info['total_imports']} total, {import_info['unique_modules']} unique modules")
            if import_info['star_imports']:
                print(f"  ⚠️  Star imports: {', '.join(import_info['star_imports'])}")
        
        # Code smells
        smells = check_code_smells(file_path)
        if smells:
            print("\n🔍 Code Smells:")
            for smell in smells[:5]:  # Show first 5
                print(f"  {smell}")
        else:
            print("\n✅ No major code smells detected")


def analyze_project_structure():
    """Analyze overall project structure"""
    print("\n" + "="*80)
    print("📁 PROJECT STRUCTURE ANALYSIS")
    print("="*80)
    
    # Count files by type
    py_files = list(project_root.rglob("*.py"))
    md_files = list(project_root.rglob("*.md"))
    yaml_files = list(project_root.rglob("*.yaml")) + list(project_root.rglob("*.yml"))
    
    print(f"\n📊 File Counts:")
    print(f"  Python files: {len(py_files)}")
    print(f"  Markdown files: {len(md_files)}")
    print(f"  YAML files: {len(yaml_files)}")
    
    # Total lines of code
    total_lines = 0
    total_size = 0
    
    for py_file in py_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                total_lines += len(f.readlines())
            total_size += py_file.stat().st_size
        except:
            pass
    
    print(f"\n📏 Python Code Stats:")
    print(f"  Total lines: {total_lines:,}")
    print(f"  Total size: {total_size/1024:.1f} KB")
    print(f"  Average file size: {total_size/len(py_files)/1024:.1f} KB")
    
    # Check directory structure
    key_dirs = [
        "agents", "components", "rag", "validation", "utils",
        "workers", "config", "tests", "outputs"
    ]
    
    print(f"\n📂 Key Directories:")
    for dir_name in key_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            py_count = len(list(dir_path.glob("*.py")))
            print(f"  ✅ {dir_name}/ ({py_count} Python files)")
        else:
            print(f"  ❌ {dir_name}/ (missing)")


def check_critical_functions():
    """Check if critical functions exist"""
    print("\n" + "="*80)
    print("🔧 CRITICAL FUNCTIONS CHECK")
    print("="*80)
    
    checks = [
        ("utils/entity_extractor.py", "extract_entities_from_file"),
        ("utils/entity_extractor.py", "generate_csharp_dto"),
        ("utils/entity_extractor.py", "generate_typescript_interface"),
        ("app/app_v2.py", "strip_markdown_artifacts"),
        ("agents/universal_agent.py", "generate_erd_only"),
        ("agents/universal_agent.py", "generate_code_prototype"),
        ("agents/universal_agent.py", "generate_visual_prototype"),
        ("validation/output_validator.py", "validate_erd"),
        ("components/adaptive_learning.py", "record_feedback"),
    ]
    
    for file_path_str, func_name in checks:
        file_path = project_root / file_path_str
        if not file_path.exists():
            print(f"❌ File not found: {file_path_str}")
            continue
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if f"def {func_name}" in content or f"async def {func_name}" in content:
            print(f"✅ {file_path_str}: {func_name}()")
        else:
            print(f"❌ {file_path_str}: {func_name}() NOT FOUND")


if __name__ == "__main__":
    run_analysis()
    analyze_project_structure()
    check_critical_functions()
    
    print("\n" + "="*80)
    print("✅ STATIC ANALYSIS COMPLETE")
    print("="*80)

