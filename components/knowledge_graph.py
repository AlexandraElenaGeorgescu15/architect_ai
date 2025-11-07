"""
Knowledge Graph System for Component Relationships

Analyzes codebase to build a knowledge graph of component relationships,
dependencies, and interactions. Provides insights into system architecture
and component coupling.
"""

import os
import json
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import networkx as nx
import streamlit as st


@dataclass
class Component:
    """Represents a code component (class, function, module)"""
    name: str
    type: str  # "class", "function", "module", "interface"
    file_path: str
    line_number: int
    dependencies: List[str] = None
    dependents: List[str] = None
    complexity: int = 0
    size: int = 0
    documentation: str = ""
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.dependents is None:
            self.dependents = []


@dataclass
class Relationship:
    """Represents a relationship between components"""
    source: str
    target: str
    relationship_type: str  # "imports", "inherits", "calls", "uses", "implements"
    strength: float = 1.0
    context: str = ""


@dataclass
class KnowledgeGraph:
    """Knowledge graph of component relationships"""
    components: Dict[str, Component]
    relationships: List[Relationship]
    metrics: Dict[str, Any]
    
    def to_dict(self):
        return {
            "components": {k: asdict(v) for k, v in self.components.items()},
            "relationships": [asdict(r) for r in self.relationships],
            "metrics": self.metrics
        }


class CodeAnalyzer:
    """Analyzes code to extract component relationships"""
    
    def __init__(self):
        self.components = {}
        self.relationships = []
        self.file_dependencies = defaultdict(set)
        
    def analyze_file(self, file_path: Path) -> List[Component]:
        """Analyze a single file and extract components"""
        components = []
        
        try:
            suffix = file_path.suffix.lower()
            if suffix == '.py':
                components.extend(self._analyze_python_file(file_path))
            elif suffix in {'.ts', '.tsx', '.js', '.jsx'}:
                components.extend(self._analyze_typescript_file(file_path))
            elif suffix == '.cs':
                components.extend(self._analyze_csharp_file(file_path))
            elif suffix in {'.c', '.cc', '.cpp', '.cxx', '.h', '.hpp'}:
                components.extend(self._analyze_cpp_file(file_path))
        except Exception as e:
            print(f"[WARN] Failed to analyze {file_path}: {e}")
            
        return components
    
    def _analyze_python_file(self, file_path: Path) -> List[Component]:
        """Analyze Python file for components"""
        components = []
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        try:
            tree = ast.parse(content)
            
            # Extract imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # Extract classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    component = Component(
                        name=node.name,
                        type="class",
                        file_path=str(file_path),
                        line_number=node.lineno,
                        dependencies=imports.copy(),
                        complexity=self._calculate_complexity(node),
                        size=len(node.body),
                        documentation=self._extract_docstring(node)
                    )
                    components.append(component)
                    
                    # Extract methods
                    for method in node.body:
                        if isinstance(method, ast.FunctionDef):
                            method_component = Component(
                                name=f"{node.name}.{method.name}",
                                type="method",
                                file_path=str(file_path),
                                line_number=method.lineno,
                                dependencies=imports.copy(),
                                complexity=self._calculate_complexity(method),
                                size=len(method.body),
                                documentation=self._extract_docstring(method)
                            )
                            components.append(method_component)
            
            # Extract functions (not inside classes)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if this function is inside a class (skip if it is)
                    is_method = False
                    try:
                        for parent in ast.walk(tree):
                            if isinstance(parent, ast.ClassDef) and hasattr(parent, 'body'):
                                # Safely check if node is in parent.body
                                if isinstance(parent.body, list) and node in parent.body:
                                    is_method = True
                                    break
                    except (TypeError, AttributeError):
                        # If comparison fails, assume it's not a method
                        pass
                    
                    if not is_method:
                        component = Component(
                            name=node.name,
                            type="function",
                            file_path=str(file_path),
                            line_number=node.lineno,
                            dependencies=imports.copy(),
                            complexity=self._calculate_complexity(node),
                            size=len(node.body),
                            documentation=self._extract_docstring(node)
                        )
                        components.append(component)
                    
        except (SyntaxError, TypeError, AttributeError) as e:
            # Handle parsing errors gracefully
            pass
            
        return components
    
    def _analyze_typescript_file(self, file_path: Path) -> List[Component]:
        """Analyze TypeScript/JavaScript file for components"""
        components = []
        content = file_path.read_text(encoding='utf-8', errors='ignore')

        import_symbols, import_modules = self._parse_typescript_imports(content)
        base_dependencies = import_symbols + import_modules

        # Extract classes
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            extends = match.group(2) if match.group(2) else None

            size, complexity = self._estimate_ts_block_metrics(content, match.start())
            deps = list(dict.fromkeys(base_dependencies + ([extends] if extends else [])))

            component = Component(
                name=class_name,
                type="class",
                file_path=str(file_path),
                line_number=content[:match.start()].count('\n') + 1,
                dependencies=deps,
                complexity=complexity,
                size=size,
                documentation=""
            )
            components.append(component)

        # Extract functions (named, exported, or assigned)
        function_pattern = (
            r'(?:export\s+)?(?:async\s+)?function\s+(\w+)'  # function foo()
            r'|(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\('  # const foo = (
            r'|(?:export\s+)?(\w+)\s*:\s*\w+\s*=\s*(?:async\s+)?\('  # foo: Foo = (
        )

        for match in re.finditer(function_pattern, content):
            func_name = match.group(1) or match.group(2) or match.group(3)
            if not func_name:
                continue

            size, complexity = self._estimate_ts_block_metrics(content, match.start())
            component = Component(
                name=func_name,
                type="function",
                file_path=str(file_path),
                line_number=content[:match.start()].count('\n') + 1,
                dependencies=list(dict.fromkeys(base_dependencies)),
                complexity=complexity,
                size=size,
                documentation=""
            )
            components.append(component)

        return components
    
    def _analyze_csharp_file(self, file_path: Path) -> List[Component]:
        """Analyze C# file for components"""
        components = []
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        # Extract using statements
        using_pattern = r'using\s+([^;]+);'
        imports = re.findall(using_pattern, content)
        
        # Extract classes
        class_pattern = r'(?:public\s+|private\s+|internal\s+|protected\s+)?(?:static\s+)?(?:abstract\s+)?(?:sealed\s+)?class\s+(\w+)(?:\s*:\s*([\w,\s]+))?'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            inherits_str = match.group(2) if match.group(2) else ""
            inherits = [seg.strip() for seg in inherits_str.split(',') if seg.strip()]
            
            component = Component(
                name=class_name,
                type="class",
                file_path=str(file_path),
                line_number=content[:match.start()].count('\n') + 1,
                dependencies=imports.copy(),
                documentation=""
            )
            component.dependencies.extend(inherits)
            components.append(component)
        
        # Extract interfaces
        interface_pattern = r'(?:public\s+|private\s+|internal\s+)?interface\s+(\w+)'
        for match in re.finditer(interface_pattern, content):
            interface_name = match.group(1)
            component = Component(
                name=interface_name,
                type="interface",
                file_path=str(file_path),
                line_number=content[:match.start()].count('\n') + 1,
                dependencies=imports.copy(),
                documentation=""
            )
            components.append(component)
        
        # Extract top-level methods (static utility functions)
        method_pattern = r'(?:public|private|internal|protected)\s+(?:static\s+)?(?:async\s+)?(?:[\w<>\[\]]+\s+)+(?P<name>\w+)\s*\('
        for match in re.finditer(method_pattern, content):
            method_name = match.group('name')
            line_number = content[:match.start()].count('\n') + 1
            component = Component(
                name=f"{method_name}()",
                type="function",
                file_path=str(file_path),
                line_number=line_number,
                dependencies=imports.copy(),
                documentation=""
            )
            components.append(component)

        return components

    def _analyze_cpp_file(self, file_path: Path) -> List[Component]:
        """Analyze C/C++ file for components (classes, structs, functions)."""
        components: List[Component] = []
        content = file_path.read_text(encoding='utf-8', errors='ignore')

        include_pattern = re.compile(r'#include\s+["<]([^">]+)[">]')
        includes = include_pattern.findall(content)

        class_pattern = re.compile(r'(class|struct)\s+(\w+)(?:\s*:\s*([\w\s:,]+))?\s*{', re.MULTILINE)
        for match in class_pattern.finditer(content):
            class_name = match.group(2)
            inherits_raw = match.group(3) or ""
            inherits = [seg.strip().split(' ')[-1] for seg in inherits_raw.split(',') if seg.strip()]

            component = Component(
                name=class_name,
                type="class" if match.group(1) == "class" else "struct",
                file_path=str(file_path),
                line_number=content[:match.start()].count('\n') + 1,
                dependencies=includes + inherits,
                complexity=0,
                size=0,
                documentation=""
            )
            components.append(component)

        function_pattern = re.compile(r'^(?:[\w:\*\&<>]+\s+)+(?P<name>[A-Za-z_][\w:]*)\s*\([^;]*?\)\s*{', re.MULTILINE)
        for match in function_pattern.finditer(content):
            func_name = match.group('name')
            line_number = content[:match.start()].count('\n') + 1
            size, complexity = self._estimate_cpp_metrics(content, match.start())
            component = Component(
                name=f"{func_name}()",
                type="function",
                file_path=str(file_path),
                line_number=line_number,
                dependencies=includes,
                complexity=complexity,
                size=size,
                documentation=""
            )
            components.append(component)

        return components

    def _parse_typescript_imports(self, content: str) -> Tuple[List[str], List[str]]:
        """Parse TypeScript import statements into symbol and module lists."""
        import_symbols: List[str] = []
        import_modules: List[str] = []

        import_pattern = re.compile(
            r'import\s+(?P<body>.+?)\s+from\s+[\'"](?!http)(?P<module>[^\'"]+)[\'"];?',
            re.MULTILINE
        )

        for match in import_pattern.finditer(content):
            body = match.group('body').strip()
            module = match.group('module').strip()

            if module:
                import_modules.append(module)

            names = self._extract_ts_import_names(body)
            import_symbols.extend(names)

        return import_symbols, import_modules

    def _extract_ts_import_names(self, body: str) -> List[str]:
        """Extract symbol names from a TypeScript import body."""
        names: List[str] = []
        cleaned_body = body.replace('\n', ' ').strip()

        # Named imports inside braces
        for group in re.findall(r'{([^}]*)}', cleaned_body):
            for part in group.split(','):
                name = part.strip()
                if not name:
                    continue
                if name.startswith('type '):
                    name = name[5:].strip()
                if ' as ' in name:
                    name = name.split(' as ')[0].strip()
                if name:
                    names.append(name)

        # Remove named portion to process default/namespace imports
        cleaned_no_named = re.sub(r'{[^}]*}', '', cleaned_body).strip()
        for segment in [seg.strip() for seg in cleaned_no_named.split(',') if seg.strip()]:
            if segment.startswith('*'):
                continue  # namespace import, skip
            if segment.startswith('type '):
                segment = segment[5:].strip()
            if ' as ' in segment:
                segment = segment.split(' as ')[0].strip()
            if segment and segment not in names:
                names.append(segment)

        return names

    def _estimate_ts_block_metrics(self, content: str, start_index: int) -> Tuple[int, int]:
        """Estimate size (lines) and simple cyclomatic complexity for TS blocks."""
        block = self._extract_code_block(content, start_index)
        if not block:
            return 0, 1

        lines = block.count('\n') + 1
        complexity_tokens = [' if ', '\nif', ' for ', '\nfor', ' while ', ' switch', ' case ', ' catch', '&&', '||', '?:']
        complexity = 1
        for token in complexity_tokens:
            complexity += block.count(token)

        return lines, max(complexity, 1)

    def _extract_code_block(self, content: str, start_index: int) -> str:
        """Extract code block starting from the first '{' after start_index."""
        brace_index = content.find('{', start_index)
        if brace_index == -1:
            return ""

        depth = 0
        for idx in range(brace_index, len(content)):
            char = content[idx]
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return content[brace_index:idx + 1]

        return ""

    def _estimate_cpp_metrics(self, content: str, start_index: int) -> Tuple[int, int]:
        block = self._extract_code_block(content, start_index)
        if not block:
            return 0, 1

        lines = block.count('\n') + 1
        complexity_tokens = [' if ', '\nif', ' for ', '\nfor', ' while ', ' switch', ' case ', ' catch', '&&', '||']
        complexity = 1
        for token in complexity_tokens:
            complexity += block.count(token)

        return lines, max(complexity, 1)
    
    def _calculate_complexity(self, node) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, 
                               ast.ExceptHandler, ast.With, ast.AsyncWith)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
                
        return complexity
    
    def _extract_docstring(self, node) -> str:
        """Extract docstring from AST node"""
        if (hasattr(node, 'body') and node.body and 
            isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            return node.body[0].value.value
        return ""


class KnowledgeGraphBuilder:
    """Builds knowledge graph from analyzed components"""
    
    def __init__(self):
        self.analyzer = CodeAnalyzer()
        self.graph = nx.DiGraph()
        
    def build_graph(self, project_root: Path) -> KnowledgeGraph:
        """Build knowledge graph from project"""
        print(f"[INFO] Building knowledge graph for {project_root}")
        
        # Analyze all files
        all_components = []
        for file_path in self._get_source_files(project_root):
            components = self.analyzer.analyze_file(file_path)
            all_components.extend(components)
            
            # Store components
            for component in components:
                self.analyzer.components[component.name] = component
                self.graph.add_node(component.name, **asdict(component))
        
        # Build relationships
        relationships = self._build_relationships(all_components)
        
        # Calculate metrics
        metrics = self._calculate_metrics()
        
        return KnowledgeGraph(
            components=self.analyzer.components,
            relationships=relationships,
            metrics=metrics
        )
    
    def _get_source_files(self, project_root: Path) -> List[Path]:
        """Get all source files to analyze (intelligently excludes tool itself)"""
        from components._tool_detector import get_user_project_directories, should_exclude_path
        
        extensions = {
            '.py', '.ts', '.tsx', '.js', '.jsx', '.cs', '.java',
            '.c', '.cc', '.cpp', '.cxx', '.h', '.hpp'
        }
        files = []
        
        # Get user project directories (automatically excludes tool)
        user_dirs = get_user_project_directories()
        print(f"[KNOWLEDGE_GRAPH] Scanning user project directories:")
        for d in user_dirs:
            print(f"[KNOWLEDGE_GRAPH]   - {d.name}")
        
        # Scan user directories
        for user_dir in user_dirs:
            for file_path in user_dir.rglob('*'):
                if (file_path.is_file() and 
                    file_path.suffix in extensions and
                    not any(part.startswith('.') for part in file_path.parts) and
                    'node_modules' not in str(file_path) and
                    '__pycache__' not in str(file_path) and
                    not should_exclude_path(file_path)):
                    files.append(file_path)
        
        print(f"[KNOWLEDGE_GRAPH] Found {len(files)} source files to analyze")
        return files
    
    def _build_relationships(self, components: List[Component]) -> List[Relationship]:
        """Build relationships between components"""
        relationships = []
        
        for component in components:
            # Add dependency relationships
            for dep in component.dependencies:
                if dep in self.analyzer.components:
                    relationship = Relationship(
                        source=component.name,
                        target=dep,
                        relationship_type="depends_on",
                        strength=1.0,
                        context=f"Import in {component.file_path}"
                    )
                    relationships.append(relationship)

                    edge_attrs = {
                        "relationship_type": relationship.relationship_type,
                        "context": relationship.context
                    }
                    if self.graph.has_edge(component.name, dep):
                        self.graph[component.name][dep]['weight'] = self.graph[component.name][dep].get('weight', 1) + 1
                    else:
                        self.graph.add_edge(component.name, dep, weight=1, **edge_attrs)
                    
                    # Add reverse relationship
                    if dep in self.analyzer.components:
                        self.analyzer.components[dep].dependents.append(component.name)
        
        return relationships
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate graph metrics"""
        if not self.graph.nodes():
            return {}
        
        metrics = {
            "total_components": len(self.graph.nodes()),
            "total_relationships": len(self.graph.edges()),
            "average_degree": sum(dict(self.graph.degree()).values()) / len(self.graph.nodes()),
            "strongly_connected_components": len(list(nx.strongly_connected_components(self.graph))),
            "weakly_connected_components": len(list(nx.weakly_connected_components(self.graph))),
            "density": nx.density(self.graph),
            "clustering_coefficient": nx.average_clustering(self.graph.to_undirected()),
        }
        
        # Component type distribution
        type_counts = Counter()
        for component in self.analyzer.components.values():
            type_counts[component.type] += 1
        metrics["component_types"] = dict(type_counts)
        
        # Complexity metrics
        complexities = [c.complexity for c in self.analyzer.components.values()]
        if complexities:
            metrics["avg_complexity"] = sum(complexities) / len(complexities)
            metrics["max_complexity"] = max(complexities)
        
        return metrics


class KnowledgeGraphVisualizer:
    """Visualizes knowledge graph using Streamlit"""
    
    def __init__(self):
        self.graph_builder = KnowledgeGraphBuilder()
    
    def render_knowledge_graph_ui(self):
        """Render knowledge graph UI"""
        st.subheader("📈 Knowledge Graph - Component Relationships")
        
        # Project selection
        project_root = st.text_input(
            "Project Root Path:",
            value=".",
            help="Path to the project root directory",
            key="kg_project_root"
        )
        
        if st.button("🔍 Analyze Project", type="primary", key="kg_analyze_project"):
            try:
                with st.spinner("Analyzing project structure..."):
                    project_path = Path(project_root)
                    if not project_path.exists():
                        st.error(f"Path does not exist: {project_root}")
                        return
                    
                    knowledge_graph = self.graph_builder.build_graph(project_path)
                    
                    # Store in session state
                    st.session_state.knowledge_graph = knowledge_graph
                    
                    st.success(f"✅ Analyzed {len(knowledge_graph.components)} components")
                    
            except Exception as e:
                st.error(f"❌ Analysis failed: {e}")
                import traceback
                st.code(traceback.format_exc())
        
        # Display results
        if 'knowledge_graph' in st.session_state:
            self._display_knowledge_graph(st.session_state.knowledge_graph)
    
    def _display_knowledge_graph(self, kg: KnowledgeGraph):
        """Display knowledge graph results"""
        
        # Metrics overview
        st.subheader("📊 Graph Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Components", kg.metrics.get("total_components", 0))
        with col2:
            st.metric("Relationships", kg.metrics.get("total_relationships", 0))
        with col3:
            st.metric("Avg Degree", f"{kg.metrics.get('average_degree', 0):.1f}")
        with col4:
            st.metric("Density", f"{kg.metrics.get('density', 0):.3f}")
        
        # Component type distribution
        if "component_types" in kg.metrics:
            st.subheader("📋 Component Types")
            type_data = kg.metrics["component_types"]
            
            col1, col2 = st.columns(2)
            with col1:
                st.bar_chart(type_data)
            with col2:
                for comp_type, count in type_data.items():
                    st.write(f"**{comp_type.title()}**: {count}")
        
        # Component details
        st.subheader("🔍 Component Details")
        
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            component_type = st.selectbox(
                "Filter by Type:",
                ["All"] + list(set(c.type for c in kg.components.values()))
            )
        with col2:
            sort_by = st.selectbox(
                "Sort by:",
                ["name", "complexity", "size", "dependencies"]
            )
        
        # Display components
        components = list(kg.components.values())
        if component_type != "All":
            components = [c for c in components if c.type == component_type]
        
        if sort_by == "complexity":
            components.sort(key=lambda x: x.complexity, reverse=True)
        elif sort_by == "size":
            components.sort(key=lambda x: x.size, reverse=True)
        elif sort_by == "dependencies":
            components.sort(key=lambda x: len(x.dependencies), reverse=True)
        else:
            components.sort(key=lambda x: x.name)
        
        # Component table
        for component in components[:20]:  # Show top 20
            with st.expander(f"🔧 {component.name} ({component.type})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**File**: `{component.file_path}`")
                    st.write(f"**Line**: {component.line_number}")
                    st.write(f"**Complexity**: {component.complexity}")
                    st.write(f"**Size**: {component.size} lines")
                
                with col2:
                    st.write(f"**Dependencies**: {len(component.dependencies)}")
                    if component.dependencies:
                        st.write("Dependencies:")
                        for dep in component.dependencies[:5]:
                            st.write(f"- {dep}")
                        if len(component.dependencies) > 5:
                            st.write(f"... and {len(component.dependencies) - 5} more")
                
                if component.documentation:
                    st.write("**Documentation**:")
                    st.code(component.documentation[:200] + "..." if len(component.documentation) > 200 else component.documentation)
        
        # Relationships
        st.subheader("🔗 Component Relationships")
        
        if kg.relationships:
            relationship_types = list(set(r.relationship_type for r in kg.relationships))
            rel_type = st.selectbox("Relationship Type:", relationship_types)
            
            filtered_rels = [r for r in kg.relationships if r.relationship_type == rel_type]
            
            for rel in filtered_rels[:10]:  # Show top 10
                st.write(f"**{rel.source}** → {rel.target} ({rel.relationship_type})")
                if rel.context:
                    st.caption(rel.context)
        
        # Export options
        st.subheader("📤 Export Knowledge Graph")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Export as JSON", key="kg_export_json_btn"):
                json_data = kg.to_dict()
                st.download_button(
                    label="Download JSON",
                    data=json.dumps(json_data, indent=2),
                    file_name="knowledge_graph.json",
                    mime="application/json",
                    key="kg_download_json"
                )
        
        with col2:
            if st.button("📊 Export Metrics", key="kg_export_metrics_btn"):
                metrics_data = kg.metrics
                st.download_button(
                    label="Download Metrics",
                    data=json.dumps(metrics_data, indent=2),
                    file_name="graph_metrics.json",
                    mime="application/json",
                    key="kg_download_metrics"
                )


def render_knowledge_graph_ui():
    """Render knowledge graph UI"""
    visualizer = KnowledgeGraphVisualizer()
    visualizer.render_knowledge_graph_ui()
