"""
Multi-Repository Analysis Service

Enterprise-grade multi-repository analysis and architecture views.
Features:
- Unified frontend/backend architecture analysis
- Cross-repository dependency detection
- Combined RAG context aggregation
- Technology stack detection and mapping
"""

import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class RepositoryConfig:
    """Configuration for a repository."""
    repo_id: str
    name: str
    path: str
    repo_type: str  # "frontend", "backend", "fullstack", "library", "other"
    language: str  # "typescript", "python", "csharp", "java", etc.
    framework: Optional[str] = None  # "angular", "react", "fastapi", "dotnet", etc.
    indexed: bool = False
    last_indexed: Optional[str] = None
    file_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CrossRepoLink:
    """A link between components in different repositories."""
    source_repo: str
    source_component: str
    source_type: str  # "api_call", "import", "reference"
    target_repo: str
    target_component: str
    link_type: str  # "consumes", "implements", "references"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MultiRepoContext:
    """Combined context from multiple repositories."""
    repositories: List[RepositoryConfig]
    cross_repo_links: List[CrossRepoLink]
    combined_entities: List[Dict[str, Any]]
    combined_apis: List[Dict[str, Any]]
    technology_stack: Dict[str, List[str]]
    architecture_summary: str
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["repositories"] = [r.to_dict() if isinstance(r, RepositoryConfig) else r for r in self.repositories]
        result["cross_repo_links"] = [l.to_dict() if isinstance(l, CrossRepoLink) else l for l in self.cross_repo_links]
        return result


class MultiRepoService:
    """
    Manages multiple repositories for unified analysis.
    
    Features:
    - Register and configure multiple repos
    - Index each repo separately
    - Detect cross-repo dependencies
    - Generate combined architecture views
    - Provide unified RAG context
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("data/multi_repo_config.json")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.repositories: Dict[str, RepositoryConfig] = {}
        self.cross_repo_links: List[CrossRepoLink] = []
        
        self._load_config()
        logger.info(f"Multi-Repo Service initialized with {len(self.repositories)} repositories")
    
    def _load_config(self):
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text())
                self.repositories = {
                    k: RepositoryConfig(**v) for k, v in data.get("repositories", {}).items()
                }
                self.cross_repo_links = [
                    CrossRepoLink(**l) for l in data.get("cross_repo_links", [])
                ]
            except Exception as e:
                logger.warning(f"Failed to load multi-repo config: {e}")
    
    def _save_config(self):
        """Save configuration to file."""
        try:
            data = {
                "repositories": {k: v.to_dict() for k, v in self.repositories.items()},
                "cross_repo_links": [l.to_dict() for l in self.cross_repo_links],
                "updated_at": datetime.now().isoformat()
            }
            self.config_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save multi-repo config: {e}")
    
    def register_repository(
        self,
        path: str,
        name: Optional[str] = None,
        repo_type: str = "other",
        language: str = "unknown",
        framework: Optional[str] = None
    ) -> RepositoryConfig:
        """
        Register a new repository for analysis.
        
        Args:
            path: Path to the repository
            name: Display name (defaults to folder name)
            repo_type: Type of repository (frontend, backend, etc.)
            language: Primary language
            framework: Framework used (optional)
            
        Returns:
            RepositoryConfig for the registered repo
        """
        repo_path = Path(path)
        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {path}")
        
        repo_id = repo_path.name.lower().replace(" ", "_")
        repo_name = name or repo_path.name
        
        # Auto-detect language and framework if not provided
        detected_lang, detected_framework = self._detect_repo_type(repo_path)
        
        config = RepositoryConfig(
            repo_id=repo_id,
            name=repo_name,
            path=str(repo_path.absolute()),
            repo_type=repo_type,
            language=language if language != "unknown" else detected_lang,
            framework=framework or detected_framework,
            indexed=False,
            file_count=self._count_files(repo_path)
        )
        
        self.repositories[repo_id] = config
        self._save_config()
        
        logger.info(f"Registered repository: {repo_name} ({repo_type}, {config.language})")
        return config
    
    def _detect_repo_type(self, repo_path: Path) -> tuple[str, Optional[str]]:
        """Auto-detect language and framework from repository files."""
        language = "unknown"
        framework = None
        
        # Check for package files
        if (repo_path / "package.json").exists():
            language = "typescript"
            pkg = json.loads((repo_path / "package.json").read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            
            if "@angular/core" in deps:
                framework = "angular"
            elif "react" in deps:
                framework = "react"
            elif "vue" in deps:
                framework = "vue"
            elif "next" in deps:
                framework = "nextjs"
        
        elif (repo_path / "requirements.txt").exists() or (repo_path / "pyproject.toml").exists():
            language = "python"
            req_file = repo_path / "requirements.txt"
            if req_file.exists():
                reqs = req_file.read_text().lower()
                if "fastapi" in reqs:
                    framework = "fastapi"
                elif "django" in reqs:
                    framework = "django"
                elif "flask" in reqs:
                    framework = "flask"
        
        elif (repo_path / "*.csproj").exists() or list(repo_path.glob("*.csproj")):
            language = "csharp"
            csproj_files = list(repo_path.glob("**/*.csproj"))
            if csproj_files:
                content = csproj_files[0].read_text().lower()
                if "microsoft.aspnetcore" in content:
                    framework = "aspnetcore"
                elif "microsoft.net.sdk.web" in content:
                    framework = "dotnet-web"
        
        elif (repo_path / "pom.xml").exists() or (repo_path / "build.gradle").exists():
            language = "java"
            if (repo_path / "pom.xml").exists():
                pom = (repo_path / "pom.xml").read_text().lower()
                if "spring-boot" in pom:
                    framework = "spring-boot"
        
        return language, framework
    
    def _count_files(self, repo_path: Path) -> int:
        """Count source files in repository."""
        extensions = {'.ts', '.tsx', '.js', '.jsx', '.py', '.cs', '.java', '.go', '.rs'}
        count = 0
        
        for ext in extensions:
            count += len(list(repo_path.glob(f"**/*{ext}")))
        
        return count
    
    def unregister_repository(self, repo_id: str) -> bool:
        """Remove a repository from tracking."""
        if repo_id in self.repositories:
            del self.repositories[repo_id]
            # Remove cross-repo links involving this repo
            self.cross_repo_links = [
                l for l in self.cross_repo_links
                if l.source_repo != repo_id and l.target_repo != repo_id
            ]
            self._save_config()
            return True
        return False
    
    def get_repositories(self) -> List[RepositoryConfig]:
        """Get all registered repositories."""
        return list(self.repositories.values())
    
    async def index_repository(self, repo_id: str) -> Dict[str, Any]:
        """
        Index a repository for RAG retrieval.
        
        Uses the existing RAG ingester but with repo-specific collection.
        """
        if repo_id not in self.repositories:
            raise ValueError(f"Unknown repository: {repo_id}")
        
        config = self.repositories[repo_id]
        repo_path = Path(config.path)
        
        try:
            # Use RAG ingester with custom collection
            from backend.services.rag_ingester import RAGIngester
            
            # Create repo-specific index path
            index_path = Path("rag/index") / repo_id
            index_path.mkdir(parents=True, exist_ok=True)
            
            ingester = RAGIngester(str(index_path))
            
            # Index the repository
            stats = await ingester.index_directory(repo_path, recursive=True)
            
            # Update config
            config.indexed = True
            config.last_indexed = datetime.now().isoformat()
            self._save_config()
            
            return {
                "repo_id": repo_id,
                "indexed": True,
                "files_indexed": stats.get("files_indexed", 0),
                "chunks_created": stats.get("chunks_created", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to index repository {repo_id}: {e}")
            return {
                "repo_id": repo_id,
                "indexed": False,
                "error": str(e)
            }
    
    def detect_cross_repo_links(self) -> List[CrossRepoLink]:
        """
        Detect dependencies between repositories.
        
        Looks for:
        - API calls from frontend to backend
        - Shared types/interfaces
        - Import references
        """
        links = []
        
        # Group repos by type
        frontends = [r for r in self.repositories.values() if r.repo_type == "frontend"]
        backends = [r for r in self.repositories.values() if r.repo_type == "backend"]
        
        for frontend in frontends:
            for backend in backends:
                # Detect API consumption patterns
                api_links = self._detect_api_consumption(frontend, backend)
                links.extend(api_links)
        
        self.cross_repo_links = links
        self._save_config()
        
        return links
    
    def _detect_api_consumption(
        self,
        frontend: RepositoryConfig,
        backend: RepositoryConfig
    ) -> List[CrossRepoLink]:
        """Detect API calls from frontend to backend."""
        links = []
        frontend_path = Path(frontend.path)
        
        # Look for HTTP calls in frontend code
        api_patterns = [
            r"fetch\s*\(\s*['\"`]([^'\"`]+)['\"`]",
            r"axios\.[a-z]+\s*\(\s*['\"`]([^'\"`]+)['\"`]",
            r"http\.(?:get|post|put|delete)\s*\(\s*['\"`]([^'\"`]+)['\"`]",
            r"this\.http\.(?:get|post|put|delete)\s*<[^>]+>\s*\(\s*['\"`]([^'\"`]+)['\"`]",
        ]
        
        import re
        
        for ts_file in frontend_path.glob("**/*.ts"):
            try:
                content = ts_file.read_text(encoding="utf-8", errors="ignore")
                
                for pattern in api_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if match.startswith("/api") or match.startswith("http"):
                            links.append(CrossRepoLink(
                                source_repo=frontend.repo_id,
                                source_component=str(ts_file.relative_to(frontend_path)),
                                source_type="api_call",
                                target_repo=backend.repo_id,
                                target_component=match,
                                link_type="consumes",
                                metadata={"endpoint": match}
                            ))
            except Exception as e:
                logger.debug(f"Failed to parse {ts_file}: {e}")
        
        return links
    
    def build_combined_context(self) -> MultiRepoContext:
        """
        Build a combined context from all registered repositories.
        
        Returns unified view of:
        - All entities across repos
        - All APIs
        - Technology stack
        - Architecture summary
        """
        combined_entities = []
        combined_apis = []
        tech_stack: Dict[str, List[str]] = {}
        
        for repo in self.repositories.values():
            # Add to tech stack
            if repo.language not in tech_stack:
                tech_stack[repo.language] = []
            if repo.framework:
                tech_stack[repo.language].append(repo.framework)
            
            # Extract entities and APIs from each repo
            # This would use the knowledge graph for each repo
            try:
                from backend.services.knowledge_graph import KnowledgeGraphBuilder
                kg = KnowledgeGraphBuilder()
                kg.build_graph(Path(repo.path))
                
                # Extract classes/entities
                for node_id, data in kg.graph.nodes(data=True):
                    if data.get("type") in ["class", "interface", "model"]:
                        combined_entities.append({
                            "repo": repo.repo_id,
                            "name": data.get("name", node_id),
                            "type": data.get("type"),
                            "file": data.get("file_path")
                        })
                    elif data.get("type") in ["function", "method"]:
                        if "api" in data.get("name", "").lower() or "endpoint" in data.get("name", "").lower():
                            combined_apis.append({
                                "repo": repo.repo_id,
                                "name": data.get("name"),
                                "file": data.get("file_path")
                            })
            except Exception as e:
                logger.warning(f"Failed to extract from {repo.repo_id}: {e}")
        
        # Detect cross-repo links if not already done
        if not self.cross_repo_links:
            self.detect_cross_repo_links()
        
        # Generate architecture summary
        summary = self._generate_architecture_summary(tech_stack)
        
        return MultiRepoContext(
            repositories=list(self.repositories.values()),
            cross_repo_links=self.cross_repo_links,
            combined_entities=combined_entities,
            combined_apis=combined_apis,
            technology_stack=tech_stack,
            architecture_summary=summary
        )
    
    def _generate_architecture_summary(self, tech_stack: Dict[str, List[str]]) -> str:
        """Generate a human-readable architecture summary."""
        repos = list(self.repositories.values())
        
        if not repos:
            return "No repositories registered."
        
        parts = [f"Multi-Repository Architecture ({len(repos)} repos):"]
        
        for repo in repos:
            parts.append(f"- {repo.name} ({repo.repo_type}): {repo.language}")
            if repo.framework:
                parts.append(f"  Framework: {repo.framework}")
        
        if self.cross_repo_links:
            parts.append(f"\nCross-repo connections: {len(self.cross_repo_links)}")
        
        return "\n".join(parts)
    
    async def get_combined_rag_context(
        self,
        query: str,
        repo_ids: Optional[List[str]] = None,
        max_chunks: int = 10
    ) -> Dict[str, Any]:
        """
        Get RAG context from multiple repositories.
        
        Args:
            query: The search query
            repo_ids: Specific repos to search (None = all)
            max_chunks: Max chunks per repo
            
        Returns:
            Combined context from all repos
        """
        from backend.services.rag_retriever import RAGRetriever
        
        target_repos = repo_ids or list(self.repositories.keys())
        combined_results = []
        
        for repo_id in target_repos:
            if repo_id not in self.repositories:
                continue
            
            config = self.repositories[repo_id]
            if not config.indexed:
                continue
            
            try:
                index_path = Path("rag/index") / repo_id
                retriever = RAGRetriever(str(index_path))
                
                results = retriever.retrieve(query, k=max_chunks)
                
                for result in results:
                    result["repo_id"] = repo_id
                    result["repo_name"] = config.name
                    combined_results.append(result)
                    
            except Exception as e:
                logger.warning(f"Failed to retrieve from {repo_id}: {e}")
        
        # Sort by relevance score
        combined_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return {
            "query": query,
            "total_results": len(combined_results),
            "results": combined_results[:max_chunks * 2],  # Return top results
            "repos_searched": target_repos
        }


# Singleton instance
_multi_repo_service: Optional[MultiRepoService] = None


def get_multi_repo_service() -> MultiRepoService:
    """Get or create multi-repo service singleton."""
    global _multi_repo_service
    if _multi_repo_service is None:
        _multi_repo_service = MultiRepoService()
    return _multi_repo_service
