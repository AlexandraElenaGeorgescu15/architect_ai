"""
ML Feature Engineering Service - Extracts features from code and diagrams.
Uses clustering, dimensionality reduction, and feature extraction for analysis.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import numpy as np
from datetime import datetime
import json

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Optional ML dependencies (graceful degradation if not available)
try:
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.decomposition import PCA
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available. ML features will be limited.")


class MLFeatureEngineer:
    """
    ML Feature Engineering service for codebase analysis.
    
    Features:
    - Code feature extraction (complexity, size, dependencies)
    - Diagram feature extraction (node count, edge count, depth)
    - Clustering analysis
    - Dimensionality reduction (PCA)
    - Feature importance analysis
    """
    
    def __init__(self):
        """Initialize ML Feature Engineer."""
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        self.vectorizer = TfidfVectorizer(max_features=100) if SKLEARN_AVAILABLE else None
        self.pca = None
        self.clusterer = None
        
        logger.info("ML Feature Engineer initialized")
    
    def extract_code_features(self, code_content: str, file_path: str) -> Dict[str, Any]:
        """
        Extract features from code content.
        
        Args:
            code_content: Source code content
            file_path: Path to file
        
        Returns:
            Dictionary of extracted features
        """
        features = {
            "file_path": file_path,
            "lines_of_code": len(code_content.split('\n')),
            "char_count": len(code_content),
            "word_count": len(code_content.split()),
            "function_count": code_content.count('def '),
            "class_count": code_content.count('class '),
            "import_count": code_content.count('import '),
            "comment_lines": sum(1 for line in code_content.split('\n') if line.strip().startswith('#')),
            "blank_lines": sum(1 for line in code_content.split('\n') if not line.strip()),
            "avg_line_length": np.mean([len(line) for line in code_content.split('\n')]) if code_content else 0,
            "max_line_length": max([len(line) for line in code_content.split('\n')], default=0),
            "cyclomatic_complexity_estimate": self._estimate_complexity(code_content),
            "nesting_depth": self._estimate_nesting_depth(code_content),
            "has_docstrings": '"""' in code_content or "'''" in code_content,
            "has_type_hints": ':' in code_content and '->' in code_content,
        }
        
        # Calculate derived features
        features["code_density"] = features["lines_of_code"] / max(features["char_count"], 1)
        features["comment_ratio"] = features["comment_lines"] / max(features["lines_of_code"], 1)
        features["blank_line_ratio"] = features["blank_lines"] / max(features["lines_of_code"], 1)
        
        return features
    
    def extract_diagram_features(self, diagram_content: str, diagram_type: str) -> Dict[str, Any]:
        """
        Extract features from diagram content (Mermaid, etc.).
        
        Args:
            diagram_content: Diagram content (Mermaid syntax, etc.)
            diagram_type: Type of diagram (erd, architecture, sequence, etc.)
        
        Returns:
            Dictionary of extracted features
        """
        features = {
            "diagram_type": diagram_type,
            "content_length": len(diagram_content),
            "line_count": len(diagram_content.split('\n')),
            "node_count": self._count_diagram_nodes(diagram_content, diagram_type),
            "edge_count": self._count_diagram_edges(diagram_content, diagram_type),
            "depth": self._estimate_diagram_depth(diagram_content, diagram_type),
            "has_labels": '[' in diagram_content or '(' in diagram_content,
            "has_styling": 'style' in diagram_content.lower() or 'classDef' in diagram_content,
            "has_interactions": 'click' in diagram_content.lower() or 'link' in diagram_content.lower(),
        }
        
        # Calculate derived features
        features["node_density"] = features["node_count"] / max(features["line_count"], 1)
        features["edge_to_node_ratio"] = features["edge_count"] / max(features["node_count"], 1)
        
        return features
    
    def _estimate_complexity(self, code: str) -> int:
        """Estimate cyclomatic complexity from code."""
        complexity = 1  # Base complexity
        
        # Count decision points
        complexity += code.count('if ')
        complexity += code.count('elif ')
        complexity += code.count('for ')
        complexity += code.count('while ')
        complexity += code.count('except ')
        complexity += code.count('case ')
        complexity += code.count('&&')
        complexity += code.count('||')
        
        return complexity
    
    def _estimate_nesting_depth(self, code: str) -> int:
        """Estimate maximum nesting depth."""
        max_depth = 0
        current_depth = 0
        
        for char in code:
            if char in ['{', '(', '[']:
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char in ['}', ')', ']']:
                current_depth = max(0, current_depth - 1)
        
        return max_depth
    
    def _count_diagram_nodes(self, content: str, diagram_type: str) -> int:
        """Count nodes in diagram."""
        if diagram_type in ['erd', 'erDiagram']:
            # Count entities in ERD
            return content.count('Entity') + content.count('entity') + len([line for line in content.split('\n') if '||' in line or '|' in line])
        elif diagram_type in ['architecture', 'graph']:
            # Count nodes in graph
            return len([line for line in content.split('\n') if '-->' in line or '---' in line])
        elif diagram_type in ['sequence', 'sequenceDiagram']:
            # Count participants
            return content.count('participant') + content.count('actor')
        else:
            # Generic: count lines that look like node definitions
            return len([line for line in content.split('\n') if any(keyword in line for keyword in ['[', '(', '{', 'node', 'Node'])])
    
    def _count_diagram_edges(self, content: str, diagram_type: str) -> int:
        """Count edges/relationships in diagram."""
        if diagram_type in ['erd', 'erDiagram']:
            # Count relationships
            return content.count('||') + content.count('|o') + content.count('o|')
        elif diagram_type in ['architecture', 'graph']:
            # Count arrows
            return content.count('-->') + content.count('---') + content.count('==>')
        elif diagram_type in ['sequence', 'sequenceDiagram']:
            # Count messages
            return content.count('->') + content.count('-->') + content.count('->>')
        else:
            # Generic: count arrows
            return content.count('->') + content.count('-->') + content.count('==>')
    
    def _estimate_diagram_depth(self, content: str, diagram_type: str) -> int:
        """Estimate hierarchical depth of diagram."""
        if diagram_type in ['erd', 'erDiagram']:
            # ERD depth is typically 1-2 levels
            return min(2, content.count('||') // 2)
        elif diagram_type in ['architecture', 'graph']:
            # Count nesting levels
            depth = 0
            for line in content.split('\n'):
                indent = len(line) - len(line.lstrip())
                depth = max(depth, indent // 2)
            return depth
        else:
            return 1
    
    def cluster_features(
        self,
        features_list: List[Dict[str, Any]],
        n_clusters: int = 5,
        method: str = "kmeans"
    ) -> Dict[str, Any]:
        """
        Cluster feature vectors.
        
        Args:
            features_list: List of feature dictionaries
            n_clusters: Number of clusters
            method: Clustering method ("kmeans" or "dbscan")
        
        Returns:
            Dictionary with cluster assignments and statistics
        """
        if not SKLEARN_AVAILABLE:
            return {"error": "scikit-learn not available"}
        
        if not features_list:
            return {"error": "No features provided"}
        
        # Convert features to matrix
        feature_matrix = self._features_to_matrix(features_list)
        
        if feature_matrix.shape[0] < n_clusters:
            return {"error": f"Not enough samples ({feature_matrix.shape[0]}) for {n_clusters} clusters"}
        
        # Normalize features
        feature_matrix_scaled = self.scaler.fit_transform(feature_matrix)
        
        # Perform clustering
        if method == "kmeans":
            self.clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = self.clusterer.fit_predict(feature_matrix_scaled)
        elif method == "dbscan":
            self.clusterer = DBSCAN(eps=0.5, min_samples=2)
            cluster_labels = self.clusterer.fit_predict(feature_matrix_scaled)
        else:
            return {"error": f"Unknown clustering method: {method}"}
        
        # Calculate cluster statistics
        cluster_stats = {}
        for cluster_id in set(cluster_labels):
            if cluster_id == -1:  # DBSCAN noise
                continue
            cluster_indices = [i for i, label in enumerate(cluster_labels) if label == cluster_id]
            cluster_features = [features_list[i] for i in cluster_indices]
            
            cluster_stats[cluster_id] = {
                "size": len(cluster_indices),
                "samples": [f.get("file_path", f"sample_{i}") for i, f in enumerate(cluster_features)],
                "avg_complexity": np.mean([f.get("cyclomatic_complexity_estimate", 0) for f in cluster_features]),
                "avg_lines": np.mean([f.get("lines_of_code", 0) for f in cluster_features]),
            }
        
        return {
            "cluster_labels": cluster_labels.tolist(),
            "cluster_stats": cluster_stats,
            "n_clusters": len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0),
            "method": method
        }
    
    def reduce_dimensions(
        self,
        features_list: List[Dict[str, Any]],
        n_components: int = 2
    ) -> Dict[str, Any]:
        """
        Reduce feature dimensions using PCA.
        
        Args:
            features_list: List of feature dictionaries
            n_components: Number of components to keep
        
        Returns:
            Dictionary with reduced dimensions and explained variance
        """
        if not SKLEARN_AVAILABLE:
            return {"error": "scikit-learn not available"}
        
        if not features_list:
            return {"error": "No features provided"}
        
        # Convert features to matrix
        feature_matrix = self._features_to_matrix(features_list)
        
        if feature_matrix.shape[1] < n_components:
            return {"error": f"Not enough features ({feature_matrix.shape[1]}) for {n_components} components"}
        
        # Normalize features
        feature_matrix_scaled = self.scaler.fit_transform(feature_matrix)
        
        # Perform PCA
        self.pca = PCA(n_components=n_components)
        reduced = self.pca.fit_transform(feature_matrix_scaled)
        
        return {
            "reduced_features": reduced.tolist(),
            "explained_variance_ratio": self.pca.explained_variance_ratio_.tolist(),
            "explained_variance": self.pca.explained_variance_.tolist(),
            "n_components": n_components,
            "total_variance_explained": float(np.sum(self.pca.explained_variance_ratio_))
        }
    
    def analyze_feature_importance(
        self,
        features_list: List[Dict[str, Any]],
        target_labels: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze feature importance using Random Forest.
        
        Args:
            features_list: List of feature dictionaries
            target_labels: Optional target labels for supervised learning
        
        Returns:
            Dictionary with feature importance scores
        """
        if not SKLEARN_AVAILABLE:
            return {"error": "scikit-learn not available"}
        
        if not features_list:
            return {"error": "No features provided"}
        
        # Convert features to matrix
        feature_matrix = self._features_to_matrix(features_list)
        feature_names = self._get_feature_names(features_list[0])
        
        if target_labels is None:
            # Unsupervised: use clustering labels as targets
            feature_matrix_scaled = self.scaler.fit_transform(feature_matrix)
            kmeans = KMeans(n_clusters=min(5, len(features_list)), random_state=42, n_init=10)
            target_labels = kmeans.fit_predict(feature_matrix_scaled)
        
        # Train Random Forest
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(feature_matrix, target_labels)
        
        # Get feature importance
        importances = rf.feature_importances_
        feature_importance = dict(zip(feature_names, importances.tolist()))
        
        # Sort by importance
        sorted_importance = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "feature_importance": feature_importance,
            "top_features": [{"name": name, "importance": score} for name, score in sorted_importance[:10]],
            "model_score": float(rf.score(feature_matrix, target_labels))
        }
    
    def analyze_project_structure(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Analyze project structure by extracting features from key files and clustering them.
        
        Args:
            file_paths: List of absolute file paths to analyze
            
        Returns:
            Dictionary with clustering results and statistics
        """
        feature_list = []
        valid_files = []
        
        for file_path_str in file_paths:
            try:
                path = Path(file_path_str)
                if not path.exists() or not path.is_file():
                    continue
                    
                # Skip non-code files
                if path.suffix.lower() not in ['.py', '.ts', '.tsx', '.js', '.jsx', '.cs', '.java']:
                    continue
                    
                content = path.read_text(encoding='utf-8', errors='ignore')
                if not content.strip():
                    continue
                    
                features = self.extract_code_features(content, str(path))
                feature_list.append(features)
                valid_files.append(str(path))
                
            except Exception as e:
                logger.warning(f"Failed to process file {file_path_str} for clustering: {e}")
                continue
        
        if not feature_list:
            return {"error": "No valid code files found to analyze"}
            
        # Cluster
        n_clusters = min(5, len(feature_list))
        if n_clusters < 2:
             return {
                "cluster_labels": [0] * len(feature_list),
                "cluster_stats": {
                    0: {
                        "size": len(feature_list),
                        "samples": [str(Path(f).name) for f in valid_files],
                        "avg_complexity": sum(f.get("cyclomatic_complexity_estimate", 0) for f in feature_list) / len(feature_list)
                    }
                },
                "n_clusters": 1,
                "note": "Not enough samples for clustering"
            }
            
        result = self.cluster_features(feature_list, n_clusters=n_clusters)
        
        # Clean up result for context (basenames only)
        if "cluster_stats" in result:
            for cid, stats in result["cluster_stats"].items():
                if "samples" in stats:
                    # Keep full paths in backend for reference if needed, but summary usually wants names
                    # For context builder, names are better
                    stats["samples"] = [str(Path(p).name) for p in stats["samples"]]
                    
        return result

    def _features_to_matrix(self, features_list: List[Dict[str, Any]]) -> np.ndarray:
        """Convert list of feature dictionaries to numpy matrix."""
        # Get numeric features only
        numeric_features = []
        for features in features_list:
            numeric = []
            for key, value in features.items():
                if isinstance(value, (int, float)) and not np.isnan(value):
                    numeric.append(value)
            numeric_features.append(numeric)
        
        return np.array(numeric_features)
    
    def _get_feature_names(self, sample_features: Dict[str, Any]) -> List[str]:
        """Get names of numeric features."""
        return [key for key, value in sample_features.items() if isinstance(value, (int, float))]


# Global engineer instance
_engineer: Optional[MLFeatureEngineer] = None


def get_engineer() -> MLFeatureEngineer:
    """Get or create global ML Feature Engineer instance."""
    global _engineer
    if _engineer is None:
        _engineer = MLFeatureEngineer()
    return _engineer



