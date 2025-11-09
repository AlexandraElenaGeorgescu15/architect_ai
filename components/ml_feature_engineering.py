"""
ML-Driven Feature Engineering

Uses machine learning to extract intelligent features from code/diagrams:
1. Clustering (K-Means, DBSCAN) to find patterns
2. Random Forest for feature importance
3. Dimensionality reduction (PCA, t-SNE)
4. Anomaly detection

Goal: Surface the most relevant features for AI decision-making.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import json
from collections import defaultdict

# ML imports
try:
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("[WARN] scikit-learn not available. Install with: pip install scikit-learn")


@dataclass
class ClusterResult:
    """Result of clustering analysis"""
    cluster_labels: List[int]
    cluster_centers: Optional[np.ndarray]
    n_clusters: int
    silhouette_score: float
    cluster_examples: Dict[int, List[str]]  # cluster_id -> examples


@dataclass
class FeatureImportance:
    """Feature importance from Random Forest"""
    feature_names: List[str]
    importance_scores: List[float]
    top_features: List[Tuple[str, float]]  # (name, score) sorted by importance


class MLFeatureEngineer:
    """
    ML-driven feature engineering for code and diagrams.
    """
    
    def __init__(self):
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required. Install with: pip install scikit-learn")
        
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        self.scaler = StandardScaler()
        self.cluster_cache: Dict[str, ClusterResult] = {}
        self.feature_importance_cache: Dict[str, FeatureImportance] = {}
    
    def cluster_code_patterns(
        self,
        code_samples: List[str],
        n_clusters: int = 5,
        method: str = 'kmeans'
    ) -> ClusterResult:
        """
        Cluster code samples to find similar patterns.
        
        Args:
            code_samples: List of code strings
            n_clusters: Number of clusters (for k-means)
            method: 'kmeans' or 'dbscan'
            
        Returns:
            ClusterResult with cluster assignments
        """
        if not code_samples:
            return ClusterResult(
                cluster_labels=[],
                cluster_centers=None,
                n_clusters=0,
                silhouette_score=0.0,
                cluster_examples={}
            )
        
        # Step 1: Vectorize code using TF-IDF
        X = self.vectorizer.fit_transform(code_samples)
        X_dense = X.toarray()
        
        # Step 2: Apply clustering
        if method == 'kmeans':
            clusterer = KMeans(n_clusters=min(n_clusters, len(code_samples)), random_state=42)
            labels = clusterer.fit_predict(X_dense)
            centers = clusterer.cluster_centers_
        elif method == 'dbscan':
            clusterer = DBSCAN(eps=0.5, min_samples=2)
            labels = clusterer.fit_predict(X_dense)
            centers = None
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Step 3: Calculate silhouette score
        from sklearn.metrics import silhouette_score
        if len(set(labels)) > 1:
            sil_score = silhouette_score(X_dense, labels)
        else:
            sil_score = 0.0
        
        # Step 4: Group examples by cluster
        cluster_examples = defaultdict(list)
        for i, label in enumerate(labels):
            if label != -1:  # Skip noise points in DBSCAN
                cluster_examples[label].append(code_samples[i][:200])  # First 200 chars
        
        return ClusterResult(
            cluster_labels=labels.tolist(),
            cluster_centers=centers,
            n_clusters=len(cluster_examples),
            silhouette_score=sil_score,
            cluster_examples=dict(cluster_examples)
        )
    
    def find_feature_importance(
        self,
        features: np.ndarray,
        labels: np.ndarray,
        feature_names: List[str]
    ) -> FeatureImportance:
        """
        Use Random Forest to find most important features.
        
        Args:
            features: Feature matrix (n_samples x n_features)
            labels: Target labels (n_samples,)
            feature_names: Names of features
            
        Returns:
            FeatureImportance with ranked features
        """
        # Train Random Forest
        rf = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10)
        rf.fit(features, labels)
        
        # Get feature importances
        importances = rf.feature_importances_
        
        # Sort by importance
        indices = np.argsort(importances)[::-1]
        top_features = [(feature_names[i], importances[i]) for i in indices[:20]]
        
        return FeatureImportance(
            feature_names=feature_names,
            importance_scores=importances.tolist(),
            top_features=top_features
        )
    
    def extract_code_features(self, code: str) -> Dict[str, float]:
        """
        Extract numeric features from code for ML.
        
        Features:
        - Line count
        - Function count
        - Class count
        - Complexity (nested blocks)
        - Comment ratio
        - Import count
        """
        lines = code.split('\n')
        
        features = {
            'line_count': len(lines),
            'non_empty_lines': len([l for l in lines if l.strip()]),
            'function_count': len(re.findall(r'\bdef\s+\w+|\bfunction\s+\w+', code)),
            'class_count': len(re.findall(r'\bclass\s+\w+', code)),
            'import_count': len(re.findall(r'\bimport\s+|\bfrom\s+\w+\s+import', code)),
            'comment_count': len(re.findall(r'#.*|//.*|/\*.*?\*/', code)),
            'avg_line_length': np.mean([len(l) for l in lines]) if lines else 0,
            'max_indentation': max([len(l) - len(l.lstrip()) for l in lines]) if lines else 0,
        }
        
        # Calculate derived features
        features['comment_ratio'] = (
            features['comment_count'] / features['non_empty_lines']
            if features['non_empty_lines'] > 0 else 0
        )
        
        features['code_density'] = (
            (features['function_count'] + features['class_count']) / features['line_count']
            if features['line_count'] > 0 else 0
        )
        
        return features
    
    def reduce_dimensions(self, features: np.ndarray, n_components: int = 2) -> np.ndarray:
        """
        Reduce dimensionality using PCA for visualization.
        
        Args:
            features: Feature matrix (n_samples x n_features)
            n_components: Number of dimensions to reduce to
            
        Returns:
            Reduced feature matrix
        """
        pca = PCA(n_components=n_components)
        return pca.fit_transform(features)
    
    def detect_anomalies(
        self,
        features: np.ndarray,
        contamination: float = 0.1
    ) -> Tuple[np.ndarray, List[int]]:
        """
        Detect anomalous samples using Isolation Forest.
        
        Args:
            features: Feature matrix
            contamination: Expected fraction of anomalies
            
        Returns:
            (anomaly_scores, anomaly_indices)
        """
        from sklearn.ensemble import IsolationForest
        
        clf = IsolationForest(contamination=contamination, random_state=42)
        predictions = clf.fit_predict(features)
        scores = clf.score_samples(features)
        
        # Find anomalies (predictions == -1)
        anomaly_indices = np.where(predictions == -1)[0].tolist()
        
        return scores, anomaly_indices


class IntelligentFeatureExtractor:
    """
    Combines programmatic extraction with ML-driven insights.
    """
    
    def __init__(self):
        self.ml_engineer = MLFeatureEngineer() if SKLEARN_AVAILABLE else None
        self.feature_cache: Dict[str, Dict] = {}
    
    def extract_and_rank_features(
        self,
        code_samples: List[str],
        labels: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Extract features and rank by importance.
        
        Args:
            code_samples: List of code strings
            labels: Optional quality labels (0=bad, 1=good)
            
        Returns:
            Dictionary with:
            - clusters: Cluster assignments
            - feature_importance: If labels provided
            - extracted_features: Per-sample features
        """
        if not self.ml_engineer:
            return {'error': 'sklearn not available'}
        
        result = {}
        
        # Step 1: Cluster similar code
        cluster_result = self.ml_engineer.cluster_code_patterns(code_samples)
        result['clusters'] = {
            'n_clusters': cluster_result.n_clusters,
            'silhouette_score': cluster_result.silhouette_score,
            'cluster_examples': {
                k: v[:3] for k, v in cluster_result.cluster_examples.items()
            }  # Show first 3 examples per cluster
        }
        
        # Step 2: Extract numeric features
        features_list = []
        for code in code_samples:
            features = self.ml_engineer.extract_code_features(code)
            features_list.append(features)
        
        result['extracted_features'] = features_list
        
        # Step 3: If labels provided, find feature importance
        if labels is not None and len(labels) == len(code_samples):
            feature_matrix = np.array([
                list(f.values()) for f in features_list
            ])
            feature_names = list(features_list[0].keys())
            
            importance = self.ml_engineer.find_feature_importance(
                feature_matrix,
                np.array(labels),
                feature_names
            )
            
            result['feature_importance'] = {
                'top_10': importance.top_features[:10]
            }
        
        # Step 4: Detect anomalies
        feature_matrix = np.array([list(f.values()) for f in features_list])
        scores, anomaly_idx = self.ml_engineer.detect_anomalies(feature_matrix)
        
        result['anomalies'] = {
            'count': len(anomaly_idx),
            'indices': anomaly_idx,
            'examples': [code_samples[i][:100] for i in anomaly_idx[:3]]
        }
        
        return result
    
    def format_for_ai(self, analysis: Dict) -> str:
        """Format ML analysis for AI consumption"""
        output = []
        
        output.append("=== ML-DRIVEN FEATURE ANALYSIS ===\n")
        
        # Clusters
        if 'clusters' in analysis:
            clusters = analysis['clusters']
            output.append(f"Code Patterns: {clusters['n_clusters']} distinct clusters found")
            output.append(f"Cluster Quality: {clusters['silhouette_score']:.2f}")
            
            for cluster_id, examples in clusters.get('cluster_examples', {}).items():
                output.append(f"\nCluster {cluster_id} ({len(examples)} samples):")
                for ex in examples[:2]:
                    output.append(f"  - {ex[:80]}...")
        
        # Feature importance
        if 'feature_importance' in analysis:
            output.append("\n=== MOST IMPORTANT CODE FEATURES ===")
            for name, score in analysis['feature_importance']['top_10']:
                output.append(f"  {name}: {score:.3f}")
        
        # Anomalies
        if 'anomalies' in analysis:
            anom = analysis['anomalies']
            output.append(f"\n=== ANOMALIES DETECTED: {anom['count']} ===")
            for ex in anom.get('examples', []):
                output.append(f"  - {ex}...")
        
        return '\n'.join(output)


# Global instance
_extractor = None

def get_feature_extractor() -> IntelligentFeatureExtractor:
    """Get global feature extractor"""
    global _extractor
    if _extractor is None:
        _extractor = IntelligentFeatureExtractor()
    return _extractor


# Example usage
if __name__ == '__main__':
    import re
    
    extractor = get_feature_extractor()
    
    # Sample code
    samples = [
        "def add(a, b):\n    return a + b",
        "def subtract(x, y):\n    return x - y",
        "class Calculator:\n    def multiply(self, a, b):\n        return a * b",
        "for i in range(10):\n    print(i)",
    ]
    
    # Analyze
    result = extractor.extract_and_rank_features(samples, labels=[1, 1, 1, 0])
    
    print(extractor.format_for_ai(result))
