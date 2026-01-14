"""
Artifact Dependency Service

Manages cross-artifact relationships and dependency tracking.
Enables detection of outdated downstream artifacts when upstream
artifacts are modified.
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
import json
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ArtifactLink:
    """A link between two artifacts."""
    source_id: str
    source_type: str
    target_id: str
    target_type: str
    link_type: str  # "depends_on", "derived_from", "complements"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ArtifactNode:
    """An artifact in the dependency graph."""
    artifact_id: str
    artifact_type: str
    content_hash: str
    created_at: str
    updated_at: str
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StalenessReport:
    """Report on artifact staleness."""
    artifact_id: str
    artifact_type: str
    is_stale: bool
    reason: str
    stale_since: Optional[str]  # When it became stale
    upstream_changes: List[Dict[str, Any]]  # What changed upstream
    recommendation: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Define artifact dependencies (upstream → downstream)
ARTIFACT_DEPENDENCIES = {
    # ERD is upstream of many things
    "mermaid_erd": {
        "downstream": ["api_docs", "code_prototype", "mermaid_sequence", "mermaid_class"],
        "reason": "ERD defines the data model used by these artifacts"
    },
    
    # Architecture diagram affects components and sequences
    "mermaid_architecture": {
        "downstream": ["mermaid_component", "mermaid_sequence", "mermaid_data_flow", "code_prototype"],
        "reason": "Architecture defines the system structure these build on"
    },
    
    # API docs affect code and UI
    "api_docs": {
        "downstream": ["code_prototype", "dev_visual_prototype"],
        "reason": "API docs define the interface implemented by code and consumed by UI"
    },
    
    # Code prototype affects UI
    "code_prototype": {
        "downstream": ["dev_visual_prototype"],
        "reason": "Backend code provides the data and APIs for the frontend"
    },
    
    # Class diagram affects code
    "mermaid_class": {
        "downstream": ["code_prototype"],
        "reason": "Class diagram defines the code structure"
    },
    
    # Sequence diagram is documentation
    "mermaid_sequence": {
        "downstream": ["api_docs", "workflows"],
        "reason": "Sequence shows the flow that API and workflows document"
    },
    
    # State diagram affects code logic
    "mermaid_state": {
        "downstream": ["code_prototype"],
        "reason": "State machine logic needs to be implemented in code"
    },
    
    # Component diagram
    "mermaid_component": {
        "downstream": ["mermaid_c4_component", "code_prototype"],
        "reason": "Component structure guides implementation"
    },
    
    # C4 diagrams
    "mermaid_c4_context": {
        "downstream": ["mermaid_c4_container"],
        "reason": "Context diagram provides boundary for container diagram"
    },
    "mermaid_c4_container": {
        "downstream": ["mermaid_c4_component"],
        "reason": "Container diagram provides boundary for component diagram"
    },
    "mermaid_c4_component": {
        "downstream": ["mermaid_c4_deployment", "code_prototype"],
        "reason": "Component diagram guides implementation and deployment"
    },
    
    # JIRA stories
    "jira": {
        "downstream": ["workflows", "estimations"],
        "reason": "Stories define work that workflows and estimations document"
    },
}


class ArtifactLinker:
    """
    Manages artifact dependencies and detects staleness.
    
    Features:
    - Track artifact creation and updates
    - Build dependency graph
    - Detect when downstream artifacts are stale
    - Suggest which artifacts need regeneration
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize with optional persistence path."""
        self.storage_path = storage_path or Path("data/artifact_links.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory graph
        self.nodes: Dict[str, ArtifactNode] = {}
        self.links: List[ArtifactLink] = []
        
        # Load from storage
        self._load()
        
        logger.info(f"Artifact Linker initialized with {len(self.nodes)} nodes, {len(self.links)} links")
    
    def _load(self):
        """Load graph from storage."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                self.nodes = {
                    k: ArtifactNode(**v) for k, v in data.get("nodes", {}).items()
                }
                self.links = [ArtifactLink(**l) for l in data.get("links", [])]
            except Exception as e:
                logger.warning(f"Failed to load artifact links: {e}")
    
    def _save(self):
        """Save graph to storage."""
        try:
            data = {
                "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
                "links": [l.to_dict() for l in self.links],
                "updated_at": datetime.now().isoformat()
            }
            self.storage_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save artifact links: {e}")
    
    def _compute_hash(self, content: str) -> str:
        """Compute content hash for change detection."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def register_artifact(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ArtifactNode:
        """
        Register a new or updated artifact.
        
        Returns the artifact node.
        """
        content_hash = self._compute_hash(content)
        now = datetime.now().isoformat()
        
        if artifact_id in self.nodes:
            # Update existing
            node = self.nodes[artifact_id]
            if node.content_hash != content_hash:
                node.content_hash = content_hash
                node.updated_at = now
                node.version += 1
                logger.info(f"Updated artifact {artifact_id} to version {node.version}")
        else:
            # Create new
            node = ArtifactNode(
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                content_hash=content_hash,
                created_at=now,
                updated_at=now,
                version=1,
                metadata=metadata or {}
            )
            self.nodes[artifact_id] = node
            logger.info(f"Registered new artifact {artifact_id}")
            
            # Auto-create dependency links based on type
            self._auto_link_artifact(node)
        
        self._save()
        return node
    
    def _auto_link_artifact(self, node: ArtifactNode):
        """Automatically create dependency links based on artifact type."""
        artifact_type = node.artifact_type
        
        # Find upstream artifacts that this depends on
        for upstream_type, deps in ARTIFACT_DEPENDENCIES.items():
            if artifact_type in deps["downstream"]:
                # Find existing upstream artifacts
                for upstream_id, upstream_node in self.nodes.items():
                    if upstream_node.artifact_type == upstream_type:
                        self.add_link(
                            source_id=upstream_id,
                            source_type=upstream_type,
                            target_id=node.artifact_id,
                            target_type=artifact_type,
                            link_type="depends_on"
                        )
    
    def add_link(
        self,
        source_id: str,
        source_type: str,
        target_id: str,
        target_type: str,
        link_type: str = "depends_on"
    ) -> ArtifactLink:
        """Add a link between artifacts."""
        # Check if link already exists
        for link in self.links:
            if link.source_id == source_id and link.target_id == target_id:
                return link
        
        link = ArtifactLink(
            source_id=source_id,
            source_type=source_type,
            target_id=target_id,
            target_type=target_type,
            link_type=link_type
        )
        self.links.append(link)
        self._save()
        
        logger.info(f"Added link: {source_id} --[{link_type}]--> {target_id}")
        return link
    
    def get_upstream(self, artifact_id: str) -> List[ArtifactNode]:
        """Get all artifacts that this artifact depends on."""
        upstream_ids = [
            link.source_id for link in self.links
            if link.target_id == artifact_id
        ]
        return [self.nodes[id] for id in upstream_ids if id in self.nodes]
    
    def get_downstream(self, artifact_id: str) -> List[ArtifactNode]:
        """Get all artifacts that depend on this artifact."""
        downstream_ids = [
            link.target_id for link in self.links
            if link.source_id == artifact_id
        ]
        return [self.nodes[id] for id in downstream_ids if id in self.nodes]
    
    def check_staleness(self, artifact_id: str) -> StalenessReport:
        """
        Check if an artifact is stale (upstream has changed).
        
        An artifact is stale if any of its upstream dependencies
        have been updated after it was last updated.
        """
        if artifact_id not in self.nodes:
            return StalenessReport(
                artifact_id=artifact_id,
                artifact_type="unknown",
                is_stale=False,
                reason="Artifact not found in dependency graph",
                stale_since=None,
                upstream_changes=[],
                recommendation="Register this artifact first"
            )
        
        node = self.nodes[artifact_id]
        upstream = self.get_upstream(artifact_id)
        
        if not upstream:
            return StalenessReport(
                artifact_id=artifact_id,
                artifact_type=node.artifact_type,
                is_stale=False,
                reason="No upstream dependencies",
                stale_since=None,
                upstream_changes=[],
                recommendation="This artifact has no dependencies to track"
            )
        
        # Check each upstream for changes
        upstream_changes = []
        stale_since = None
        
        for up_node in upstream:
            if up_node.updated_at > node.updated_at:
                upstream_changes.append({
                    "artifact_id": up_node.artifact_id,
                    "artifact_type": up_node.artifact_type,
                    "updated_at": up_node.updated_at,
                    "version": up_node.version
                })
                if stale_since is None or up_node.updated_at < stale_since:
                    stale_since = up_node.updated_at
        
        is_stale = len(upstream_changes) > 0
        
        if is_stale:
            changed_types = [c["artifact_type"] for c in upstream_changes]
            reason = f"Upstream artifacts changed: {', '.join(changed_types)}"
            recommendation = f"Regenerate this {node.artifact_type} to reflect upstream changes"
        else:
            reason = "All upstream dependencies are older than this artifact"
            recommendation = "No action needed"
        
        return StalenessReport(
            artifact_id=artifact_id,
            artifact_type=node.artifact_type,
            is_stale=is_stale,
            reason=reason,
            stale_since=stale_since,
            upstream_changes=upstream_changes,
            recommendation=recommendation
        )
    
    def get_all_stale_artifacts(self) -> List[StalenessReport]:
        """Get all artifacts that are stale."""
        stale = []
        for artifact_id in self.nodes:
            report = self.check_staleness(artifact_id)
            if report.is_stale:
                stale.append(report)
        return stale
    
    def get_dependency_tree(self, artifact_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the full dependency tree.
        
        If artifact_id is provided, returns tree rooted at that artifact.
        Otherwise returns the full graph.
        """
        if artifact_id and artifact_id in self.nodes:
            return self._build_subtree(artifact_id, set())
        
        # Build full graph
        roots = self._find_roots()
        return {
            "roots": [self._build_subtree(r, set()) for r in roots],
            "total_nodes": len(self.nodes),
            "total_links": len(self.links)
        }
    
    def _find_roots(self) -> List[str]:
        """Find root nodes (no upstream dependencies)."""
        all_targets = {link.target_id for link in self.links}
        return [
            node_id for node_id in self.nodes
            if node_id not in all_targets
        ]
    
    def _build_subtree(self, artifact_id: str, visited: Set[str]) -> Dict[str, Any]:
        """Build subtree for an artifact."""
        if artifact_id in visited or artifact_id not in self.nodes:
            return {"id": artifact_id, "circular": True}
        
        visited.add(artifact_id)
        node = self.nodes[artifact_id]
        downstream = self.get_downstream(artifact_id)
        staleness = self.check_staleness(artifact_id)
        
        return {
            "id": artifact_id,
            "type": node.artifact_type,
            "version": node.version,
            "updated_at": node.updated_at,
            "is_stale": staleness.is_stale,
            "children": [
                self._build_subtree(d.artifact_id, visited.copy())
                for d in downstream
            ]
        }
    
    def get_impact_analysis(self, artifact_id: str) -> Dict[str, Any]:
        """
        Analyze impact of changing an artifact.
        
        Returns all downstream artifacts that would need updating.
        """
        if artifact_id not in self.nodes:
            return {
                "artifact_id": artifact_id,
                "impact": [],
                "total_affected": 0,
                "message": "Artifact not found"
            }
        
        node = self.nodes[artifact_id]
        affected = self._collect_downstream_recursive(artifact_id, set())
        
        return {
            "artifact_id": artifact_id,
            "artifact_type": node.artifact_type,
            "impact": [
                {
                    "artifact_id": a.artifact_id,
                    "artifact_type": a.artifact_type,
                    "depth": depth,
                    "action": f"Regenerate {a.artifact_type} to reflect changes"
                }
                for a, depth in affected
            ],
            "total_affected": len(affected),
            "recommendation": f"Updating {node.artifact_type} will affect {len(affected)} downstream artifacts"
        }
    
    def _collect_downstream_recursive(
        self,
        artifact_id: str,
        visited: Set[str],
        depth: int = 1
    ) -> List[Tuple[ArtifactNode, int]]:
        """Recursively collect downstream artifacts."""
        affected = []
        downstream = self.get_downstream(artifact_id)
        
        for node in downstream:
            if node.artifact_id not in visited:
                visited.add(node.artifact_id)
                affected.append((node, depth))
                affected.extend(
                    self._collect_downstream_recursive(node.artifact_id, visited, depth + 1)
                )
        
        return affected
    
    def get_graph_summary(self) -> Dict[str, Any]:
        """Get summary statistics of the dependency graph."""
        type_counts: Dict[str, int] = {}
        for node in self.nodes.values():
            type_counts[node.artifact_type] = type_counts.get(node.artifact_type, 0) + 1
        
        stale_count = len(self.get_all_stale_artifacts())
        
        return {
            "total_artifacts": len(self.nodes),
            "total_links": len(self.links),
            "artifacts_by_type": type_counts,
            "stale_artifacts": stale_count,
            "roots": self._find_roots(),
            "health": "good" if stale_count == 0 else "needs_attention"
        }


# Singleton instance
_artifact_linker: Optional[ArtifactLinker] = None


def get_artifact_linker() -> ArtifactLinker:
    """Get or create artifact linker singleton."""
    global _artifact_linker
    if _artifact_linker is None:
        _artifact_linker = ArtifactLinker()
    return _artifact_linker
