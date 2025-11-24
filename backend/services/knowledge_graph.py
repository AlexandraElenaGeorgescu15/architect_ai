"""
Knowledge Graph Service - Refactored from components/knowledge_graph.py
Builds knowledge graph from codebase using AST parsing and NetworkX.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
import ast
import logging
import networkx as nx
import json
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.utils.tool_detector import should_exclude_path, get_user_project_directories
from backend.core.config import settings

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """
    Knowledge Graph builder for codebase analysis.
    
    Features:
    - AST parsing for Python
    - Support for TypeScript/JavaScript (future)
    - NetworkX graph construction
    - Graph query methods (shortest path, centrality)
    - Graph caching
    - Graph visualization export
    """
    
    def __init__(self):
        """Initialize Knowledge Graph builder."""
        self.graph: nx.DiGraph = nx.DiGraph()
        self.file_nodes: Dict[str, str] = {}  # file_path -> node_id
        self.class_nodes: Dict[str, str] = {}  # class_name -> node_id
        self.function_nodes: Dict[str, str] = {}  # function_name -> node_id
        self._cache_file: Optional[Path] = None
        
        logger.info("Knowledge Graph Builder initialized")
    
    def _get_node_id(self, node_type: str, name: str, file_path: Optional[str] = None) -> str:
        """
        Generate unique node ID.
        
        Args:
            node_type: Type of node (file, class, function, method)
            name: Name of the node
            file_path: Optional file path for scoping
        
        Returns:
            Unique node ID
        """
        if file_path:
            return f"{node_type}:{file_path}:{name}"
        return f"{node_type}:{name}"
    
    def _parse_python_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse Python file using AST.
        
        Args:
            file_path: Path to Python file
        
        Returns:
            List of extracted components (classes, functions, methods)
        """
        components = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            # Extract file-level information
            file_node = {
                "type": "file",
                "name": file_path.name,
                "path": str(file_path),
                "line_start": 1,
                "line_end": len(content.split('\n'))
            }
            components.append(file_node)
            
            # Walk AST to extract classes and functions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        "type": "class",
                        "name": node.name,
                        "file_path": str(file_path),
                        "line_start": node.lineno,
                        "line_end": node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
                        "bases": [ast.unparse(base) for base in node.bases] if hasattr(ast, 'unparse') else [],
                        "methods": []
                    }
                    
                    # Extract methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = {
                                "type": "method",
                                "name": item.name,
                                "class_name": node.name,
                                "file_path": str(file_path),
                                "line_start": item.lineno,
                                "line_end": item.end_lineno if hasattr(item, 'end_lineno') else item.lineno,
                                "args": [arg.arg for arg in item.args.args]
                            }
                            class_info["methods"].append(method_info)
                            components.append(method_info)
                    
                    components.append(class_info)
                
                elif isinstance(node, ast.FunctionDef):
                    # Top-level function
                    func_info = {
                        "type": "function",
                        "name": node.name,
                        "file_path": str(file_path),
                        "line_start": node.lineno,
                        "line_end": node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
                        "args": [arg.arg for arg in node.args.args]
                    }
                    components.append(func_info)
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        import_info = {
                            "type": "import",
                            "module": alias.name,
                            "alias": alias.asname,
                            "file_path": str(file_path),
                            "line_start": node.lineno
                        }
                        components.append(import_info)
                elif isinstance(node, ast.ImportFrom):
                    import_info = {
                        "type": "import_from",
                        "module": node.module or "",
                        "names": [alias.name for alias in node.names],
                        "file_path": str(file_path),
                        "line_start": node.lineno
                    }
                    components.append(import_info)
            
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}", exc_info=True)
        
        return components
    
    def _parse_typescript_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse TypeScript/JavaScript file using regex patterns.
        
        Args:
            file_path: Path to TypeScript/JavaScript file
        
        Returns:
            List of extracted components
        """
        import re
        components = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # File node
            components.append({
                "type": "file",
                "name": file_path.name,
                "path": str(file_path),
                "line_start": 1,
                "line_end": len(lines)
            })
            
            # Extract classes (class/interface/type)
            class_pattern = r'(?:export\s+)?(?:abstract\s+)?(?:class|interface|type)\s+(\w+)'
            for i, line in enumerate(lines, 1):
                match = re.search(class_pattern, line)
                if match:
                    components.append({
                        "type": "class",
                        "name": match.group(1),
                        "file_path": str(file_path),
                        "line_start": i,
                        "line_end": i
                    })
            
            # Extract functions/methods
            func_pattern = r'(?:export\s+)?(?:async\s+)?(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=]+)\s*=>)'
            for i, line in enumerate(lines, 1):
                match = re.search(func_pattern, line)
                if match:
                    name = match.group(1) or match.group(2)
                    if name:
                        components.append({
                            "type": "function",
                            "name": name,
                            "file_path": str(file_path),
                            "line_start": i,
                            "line_end": i
                        })
            
            # Extract imports
            import_pattern = r'import\s+(?:{[^}]+}|[^;]+)\s+from\s+[\'"]([^\'"]+)[\'"]'
            for i, line in enumerate(lines, 1):
                match = re.search(import_pattern, line)
                if match:
                    components.append({
                        "type": "import",
                        "module": match.group(1),
                        "file_path": str(file_path),
                        "line_start": i
                    })
            
        except Exception as e:
            logger.error(f"Error parsing TypeScript file {file_path}: {e}")
        
        return components
    
    def _parse_csharp_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse C# file using regex patterns.
        
        Args:
            file_path: Path to C# file
        
        Returns:
            List of extracted components
        """
        import re
        components = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # File node
            components.append({
                "type": "file",
                "name": file_path.name,
                "path": str(file_path),
                "line_start": 1,
                "line_end": len(lines)
            })
            
            # Extract namespaces
            namespace_pattern = r'namespace\s+([\w\.]+)'
            for i, line in enumerate(lines, 1):
                match = re.search(namespace_pattern, line)
                if match:
                    components.append({
                        "type": "namespace",
                        "name": match.group(1),
                        "file_path": str(file_path),
                        "line_start": i,
                        "line_end": i
                    })
            
            # Extract classes/interfaces
            class_pattern = r'(?:public|private|protected|internal)?\s*(?:static|abstract|sealed)?\s*(?:class|interface|struct|record)\s+(\w+)'
            for i, line in enumerate(lines, 1):
                match = re.search(class_pattern, line)
                if match:
                    components.append({
                        "type": "class",
                        "name": match.group(1),
                        "file_path": str(file_path),
                        "line_start": i,
                        "line_end": i
                    })
            
            # Extract methods/functions
            method_pattern = r'(?:public|private|protected|internal)?\s*(?:static|virtual|override|async)?\s*\w+\s+(\w+)\s*\([^)]*\)'
            for i, line in enumerate(lines, 1):
                match = re.search(method_pattern, line)
                if match and not line.strip().startswith('//'):
                    name = match.group(1)
                    # Filter out keywords
                    if name not in ['if', 'while', 'for', 'foreach', 'switch', 'using', 'return']:
                        components.append({
                            "type": "method",
                            "name": name,
                            "file_path": str(file_path),
                            "line_start": i,
                            "line_end": i
                        })
            
            # Extract using statements
            using_pattern = r'using\s+([\w\.]+);'
            for i, line in enumerate(lines, 1):
                match = re.search(using_pattern, line)
                if match:
                    components.append({
                        "type": "import",
                        "module": match.group(1),
                        "file_path": str(file_path),
                        "line_start": i
                    })
            
        except Exception as e:
            logger.error(f"Error parsing C# file {file_path}: {e}")
        
        return components
    
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a single file and extract components.
        
        Args:
            file_path: Path to file
        
        Returns:
            Dictionary with extracted components
        """
        if not file_path.exists():
            return {"error": "File not found"}
        
        if should_exclude_path(file_path):
            return {"excluded": True, "reason": "Tool directory"}
        
        # Determine file type and parse accordingly
        if file_path.suffix == '.py':
            components = self._parse_python_file(file_path)
        elif file_path.suffix in ['.ts', '.tsx', '.js', '.jsx']:
            components = self._parse_typescript_file(file_path)
        elif file_path.suffix == '.cs':
            components = self._parse_csharp_file(file_path)
        else:
            return {"error": f"Unsupported file type: {file_path.suffix}"}
        
        return {
            "file_path": str(file_path),
            "components": components,
            "component_count": len(components)
        }
    
    def build_graph(self, directory: Path, recursive: bool = True) -> nx.DiGraph:
        """
        Build knowledge graph from directory.
        
        Args:
            directory: Directory to analyze
            recursive: Whether to analyze recursively
        
        Returns:
            NetworkX directed graph
        """
        self.graph = nx.DiGraph()
        self.file_nodes.clear()
        self.class_nodes.clear()
        self.function_nodes.clear()
        
        # Get user project directories (excludes tool)
        user_dirs = get_user_project_directories()
        
        if directory not in user_dirs:
            logger.warning(f"Directory {directory} not in user project directories")
            return self.graph
        
        # Find all supported code files
        supported_extensions = ['.py', '.ts', '.tsx', '.js', '.jsx', '.cs']
        files = []
        
        if recursive:
            for ext in supported_extensions:
                pattern = f"**/*{ext}"
                files.extend(list(directory.rglob(pattern)))
        else:
            for ext in supported_extensions:
                pattern = f"*{ext}"
                files.extend(list(directory.glob(pattern)))
        
        logger.info(f"Building knowledge graph from {len(files)} files...")
        
        for file_path in files:
            if should_exclude_path(file_path):
                continue
            
            try:
                result = self.analyze_file(file_path)
                if "error" in result or result.get("excluded"):
                    continue
                
                components = result.get("components", [])
                self._add_components_to_graph(file_path, components)
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
        
        logger.info(f"Knowledge graph built: {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges")
        return self.graph
    
    def _add_components_to_graph(self, file_path: Path, components: List[Dict[str, Any]]):
        """
        Add components to graph with relationships.
        
        Args:
            file_path: Path to file
            components: List of component dictionaries
        """
        file_node_id = None
        
        # Add file node
        for comp in components:
            if comp.get("type") == "file":
                file_node_id = self._get_node_id("file", comp["name"], str(file_path))
                # Remove 'type' and 'name' from comp to avoid duplicate keyword arguments
                comp_copy = {k: v for k, v in comp.items() if k not in ('type', 'name', 'path')}
                self.graph.add_node(
                    file_node_id,
                    type="file",
                    name=comp["name"],
                    path=str(file_path),
                    **comp_copy
                )
                self.file_nodes[str(file_path)] = file_node_id
                break
        
        # Add class nodes
        for comp in components:
            if comp.get("type") == "class":
                class_node_id = self._get_node_id("class", comp["name"], str(file_path))
                # Remove 'type', 'name', and 'file_path' from comp to avoid duplicate keyword arguments
                comp_copy = {k: v for k, v in comp.items() if k not in ('type', 'name', 'file_path')}
                self.graph.add_node(
                    class_node_id,
                    type="class",
                    name=comp["name"],
                    file_path=str(file_path),
                    **comp_copy
                )
                self.class_nodes[comp["name"]] = class_node_id
                
                # Link class to file
                if file_node_id:
                    self.graph.add_edge(file_node_id, class_node_id, relationship="contains")
                
                # Add inheritance relationships
                for base in comp.get("bases", []):
                    # Try to find base class node
                    base_node_id = self.class_nodes.get(base, None)
                    if base_node_id:
                        self.graph.add_edge(class_node_id, base_node_id, relationship="inherits")
        
        # Add function nodes
        for comp in components:
            if comp.get("type") == "function":
                func_node_id = self._get_node_id("function", comp["name"], str(file_path))
                # Remove 'type', 'name', and 'file_path' from comp to avoid duplicate keyword arguments
                comp_copy = {k: v for k, v in comp.items() if k not in ('type', 'name', 'file_path')}
                self.graph.add_node(
                    func_node_id,
                    type="function",
                    name=comp["name"],
                    file_path=str(file_path),
                    **comp_copy
                )
                self.function_nodes[comp["name"]] = func_node_id
                
                # Link function to file
                if file_node_id:
                    self.graph.add_edge(file_node_id, func_node_id, relationship="contains")
        
        # Add method nodes
        for comp in components:
            if comp.get("type") == "method":
                method_node_id = self._get_node_id("method", comp["name"], str(file_path))
                class_name = comp.get("class_name", "")
                class_node_id = self.class_nodes.get(class_name)
                
                # Remove 'type', 'name', 'class_name', and 'file_path' from comp to avoid duplicate keyword arguments
                comp_copy = {k: v for k, v in comp.items() if k not in ('type', 'name', 'class_name', 'file_path')}
                self.graph.add_node(
                    method_node_id,
                    type="method",
                    name=comp["name"],
                    class_name=class_name,
                    file_path=str(file_path),
                    **comp_copy
                )
                
                # Link method to class
                if class_node_id:
                    self.graph.add_edge(class_node_id, method_node_id, relationship="contains")
        
        # Add import relationships
        for comp in components:
            if comp.get("type") in ["import", "import_from"]:
                if file_node_id:
                    # Create import edge
                    module = comp.get("module", "")
                    if module:
                        import_node_id = self._get_node_id("module", module)
                        if not self.graph.has_node(import_node_id):
                            self.graph.add_node(import_node_id, type="module", name=module)
                        self.graph.add_edge(file_node_id, import_node_id, relationship="imports")
    
    def get_shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """
        Get shortest path between two nodes.
        
        Args:
            source: Source node name or ID
            target: Target node name or ID
        
        Returns:
            List of node IDs in path, or None if no path exists
        """
        try:
            # Find nodes by name if needed
            source_id = self._find_node_by_name(source) or source
            target_id = self._find_node_by_name(target) or target
            
            if source_id not in self.graph or target_id not in self.graph:
                return None
            
            path = nx.shortest_path(self.graph, source_id, target_id)
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    
    def _find_node_by_name(self, name: str) -> Optional[str]:
        """Find node ID by name."""
        for node_id, data in self.graph.nodes(data=True):
            if data.get("name") == name:
                return node_id
        return None
    
    def get_centrality(self, metric: str = "degree") -> Dict[str, float]:
        """
        Calculate centrality metrics for nodes.
        
        Args:
            metric: Centrality metric ("degree", "betweenness", "closeness", "eigenvector")
        
        Returns:
            Dictionary mapping node IDs to centrality scores
        """
        if metric == "degree":
            return dict(nx.degree_centrality(self.graph))
        elif metric == "betweenness":
            return dict(nx.betweenness_centrality(self.graph))
        elif metric == "closeness":
            return dict(nx.closeness_centrality(self.graph))
        elif metric == "eigenvector":
            return dict(nx.eigenvector_centrality(self.graph, max_iter=100))
        else:
            raise ValueError(f"Unknown centrality metric: {metric}")
    
    def get_most_connected_nodes(self, top_k: int = 10) -> List[Tuple[str, int]]:
        """
        Get nodes with most connections.
        
        Args:
            top_k: Number of top nodes to return
        
        Returns:
            List of (node_id, degree) tuples
        """
        degrees = dict(self.graph.degree())
        sorted_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)
        return sorted_nodes[:top_k]
    
    def export_to_dict(self) -> Dict[str, Any]:
        """
        Export graph to dictionary format.
        
        Returns:
            Dictionary representation of graph
        """
        nodes = []
        for node_id, data in self.graph.nodes(data=True):
            nodes.append({
                "id": node_id,
                **data
            })
        
        edges = []
        for source, target, data in self.graph.edges(data=True):
            edges.append({
                "source": source,
                "target": target,
                **data
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "created_at": datetime.now().isoformat()
            }
        }
    
    def export_to_json(self, file_path: Path):
        """
        Export graph to JSON file.
        
        Args:
            file_path: Path to output JSON file
        """
        data = self.export_to_dict()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Graph exported to {file_path}")
    
    def cache_graph(self, cache_file: Optional[Path] = None):
        """
        Cache graph to disk.
        
        Args:
            cache_file: Optional cache file path
        """
        if cache_file is None:
            cache_file = Path("outputs/.cache") / "knowledge_graph.json"
        
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._cache_file = cache_file
        self.export_to_json(cache_file)
        logger.info(f"Graph cached to {cache_file}")
    
    def load_cached_graph(self, cache_file: Optional[Path] = None) -> bool:
        """
        Load graph from cache.
        
        Args:
            cache_file: Optional cache file path
        
        Returns:
            True if cache loaded successfully
        """
        if cache_file is None:
            cache_file = Path("outputs/.cache") / "knowledge_graph.json"
        
        if not cache_file.exists():
            return False
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Rebuild graph from data
            self.graph = nx.DiGraph()
            
            for node in data.get("nodes", []):
                node_id = node.pop("id")
                self.graph.add_node(node_id, **node)
            
            for edge in data.get("edges", []):
                source = edge.pop("source")
                target = edge.pop("target")
                self.graph.add_edge(source, target, **edge)
            
            logger.info(f"Graph loaded from cache: {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges")
            return True
            
        except Exception as e:
            logger.error(f"Error loading graph cache: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get graph statistics.
        
        Returns:
            Dictionary with graph statistics
        """
        # Count weakly connected components (NOT the actual sets - just the count!)
        component_count = nx.number_weakly_connected_components(self.graph) if self.graph.nodes else 0
        
        return {
            "node_count": len(self.graph.nodes),
            "edge_count": len(self.graph.edges),
            "file_count": len(self.file_nodes),
            "class_count": len(self.class_nodes),
            "function_count": len(self.function_nodes),
            "total_classes": len(self.class_nodes),  # Frontend expects this
            "total_functions": len(self.function_nodes),  # Frontend expects this
            "total_files": len(self.file_nodes),  # Frontend expects this
            "is_connected": nx.is_weakly_connected(self.graph) if self.graph.nodes else False,
            "component_count": component_count
        }


# Global builder instance
_builder: Optional[KnowledgeGraphBuilder] = None


def get_builder() -> KnowledgeGraphBuilder:
    """Get or create global Knowledge Graph builder instance."""
    global _builder
    if _builder is None:
        _builder = KnowledgeGraphBuilder()
    return _builder



