"""
Universal Context Service - The Powerhouse that Knows Your Entire Project by Heart.

This service:
1. Indexes ALL user project files (everything except architect_ai_cursor_poc)
2. Ranks files by importance (main files > helpers > UI components)
3. Builds a comprehensive cached context that EVERYTHING uses
4. Provides baseline knowledge to: Chat, KG, PM, Artifacts, Everything!
5. Auto-rebuilds when files change or index is lost
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
import logging
import asyncio
from datetime import datetime, timedelta
import json

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.utils.tool_detector import get_user_project_directories, should_exclude_path
from backend.services.rag_ingester import RAGIngester
from backend.services.rag_retriever import RAGRetriever
from backend.services.knowledge_graph import get_builder as get_kg_builder
from backend.services.pattern_mining import get_miner
from backend.core.config import settings
from backend.core.cache import get_cache_manager
from backend.core.metrics import get_metrics_collector

logger = logging.getLogger(__name__)
metrics = get_metrics_collector()


class UniversalContextService:
    """
    Universal Context Service - Makes RAG know your entire project by heart.
    
    This is the POWERHOUSE that provides comprehensive project knowledge to:
    - Floating Chat
    - Knowledge Graph
    - Pattern Mining  
    - Meeting Notes Analysis
    - Artifact Generation
    - Everything!
    
    Features:
    - Complete project indexing (all user directories)
    - Importance-based file ranking
    - Universal context caching
    - Auto-rebuild on changes
    - Smart retrieval with baseline context
    """
    
    def __init__(self):
        """Initialize Universal Context Service."""
        self.cache = get_cache_manager()
        self.rag_ingester = RAGIngester()
        self.rag_retriever = RAGRetriever()
        self.kg_builder = get_kg_builder()
        self.pattern_miner = get_miner()
        
        # Universal context cache
        self._universal_context: Optional[Dict[str, Any]] = None
        self._last_build: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=6)  # Rebuild every 6 hours or on changes
        
        # File importance scores
        self._file_importance: Dict[str, float] = {}
        
        # Project structure map
        self._project_map: Dict[str, Any] = {}
        
        logger.info("🚀 Universal Context Service initialized - RAG Powerhouse ready!")
    
    def _calculate_file_importance(self, file_path: Path) -> float:
        """
        Calculate importance score for a file (0.0 to 1.0).
        Higher score = more important = prioritized in context.
        
        Importance hierarchy:
        1.0 - Main entry points, core business logic
        0.9 - Controllers, services, API routes
        0.8 - Models, entities, schemas
        0.7 - Components, modules
        0.6 - Utilities, helpers
        0.5 - Configuration files
        0.4 - UI components
        0.3 - Tests
        0.2 - Styles, assets
        0.1 - Build files, configs
        
        Args:
            file_path: Path to file
        
        Returns:
            Importance score (0.0 to 1.0)
        """
        file_str = str(file_path).lower()
        file_name = file_path.name.lower()
        
        # 1.0 - Main entry points
        if file_name in ['main.py', 'app.py', 'index.ts', 'index.js', 'program.cs', 'startup.cs', 'main.cs']:
            return 1.0
        if 'main' in file_str and ('workflow' in file_str or 'process' in file_str or 'core' in file_str):
            return 1.0
        
        # 0.9 - Controllers, Services, API Routes
        if 'controller' in file_str or 'service' in file_str or '/api/' in file_str or '/routes/' in file_str:
            return 0.9
        if file_name.endswith('controller.cs') or file_name.endswith('service.cs'):
            return 0.9
        if file_name.endswith('controller.ts') or file_name.endswith('service.ts'):
            return 0.9
        
        # 0.8 - Models, Entities, Schemas
        if '/models/' in file_str or '/entities/' in file_str or '/schemas/' in file_str or '/dto/' in file_str:
            return 0.8
        if file_name.endswith('model.py') or file_name.endswith('dto.cs') or file_name.endswith('entity.cs'):
            return 0.8
        
        # 0.7 - Core Components, Modules
        if '/components/' in file_str and not ('/ui/' in file_str or '/views/' in file_str):
            return 0.7
        if '/modules/' in file_str or '/core/' in file_str:
            return 0.7
        
        # 0.6 - Utilities, Helpers
        if '/utils/' in file_str or '/helpers/' in file_str or '/lib/' in file_str:
            return 0.6
        if file_name.startswith('util') or file_name.startswith('helper'):
            return 0.6
        
        # 0.5 - Configuration
        if file_path.suffix in ['.json', '.yaml', '.yml', '.toml', '.ini', '.conf']:
            if 'package' not in file_name and 'tsconfig' not in file_name:
                return 0.5
        if file_name in ['settings.py', 'config.py', 'appsettings.json']:
            return 0.5
        
        # 0.4 - UI Components
        if '/components/' in file_str and ('/ui/' in file_str or '/views/' in file_str):
            return 0.4
        if '/pages/' in file_str or '/screens/' in file_str:
            return 0.4
        
        # 0.3 - Tests
        if '/test' in file_str or file_name.startswith('test_') or file_name.endswith('.spec.ts'):
            return 0.3
        
        # 0.2 - Styles, Assets
        if file_path.suffix in ['.css', '.scss', '.sass', '.less']:
            return 0.2
        
        # 0.1 - Build configs
        if file_name in ['package.json', 'tsconfig.json', 'angular.json', 'webpack.config.js']:
            return 0.1
        
        # Default: moderate importance
        return 0.5
    
    async def build_universal_context(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """
        Build comprehensive universal context from entire project.
        This is the POWERHOUSE - it knows EVERYTHING about your project.
        
        Args:
            force_rebuild: Force rebuild even if cache is fresh
        
        Returns:
            Universal context dictionary with complete project knowledge
        """
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] ========== BUILD UNIVERSAL CONTEXT STARTED ==========")
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 1: Checking cache")
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 1.1: force_rebuild={force_rebuild}, has_cached_context={bool(self._universal_context)}")
        
        # Check if cache is still fresh
        if (not force_rebuild and 
            self._universal_context and 
            self._last_build and 
            (datetime.now() - self._last_build) < self._cache_ttl):
            logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 1.2: Cache HIT - Using cached universal context (still fresh)")
            logger.info(f"🚀 [UNIVERSAL_CONTEXT] ========== BUILD UNIVERSAL CONTEXT COMPLETE (FROM CACHE) ==========")
            return self._universal_context
        
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 1.2: Cache MISS or expired - building fresh context")
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 2: Building universal project context - this will take a moment...")
        metrics.increment("universal_context_builds")
        
        start_time = datetime.now()
        
        # Get all user project directories (everything except tool)
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 3: Getting user project directories")
        user_dirs = get_user_project_directories()
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 3.1: Found {len(user_dirs)} user project directories: {[str(d.name) for d in user_dirs]}")
        
        # Step 1: Ensure RAG index is complete
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 4: Ensuring RAG index is complete")
        await self._ensure_complete_index(user_dirs)
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 4.1: RAG index complete")
        
        # Step 2: Build file importance map
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 5: Building file importance map")
        await self._build_importance_map(user_dirs)
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 5.1: File importance map built: {len(self._file_importance)} files")
        
        # Step 3: Build project structure map
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 6: Building project structure map")
        await self._build_project_map(user_dirs)
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 6.1: Project structure map built")
        
        # Step 4: Build Knowledge Graph for all directories
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 7: Building Knowledge Graph")
        kg_context = await self._build_complete_kg(user_dirs)
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 7.1: Knowledge Graph built: {kg_context.get('total_nodes', 0)} nodes, {kg_context.get('total_edges', 0)} edges")
        
        # Step 5: Run Pattern Mining on all directories
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 8: Running Pattern Mining")
        pm_context = await self._build_complete_patterns(user_dirs)
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 8.1: Pattern Mining complete: {len(pm_context.get('patterns', []))} patterns found")
        
        # Step 6: Extract key entities and relationships
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 9: Extracting key entities")
        key_entities = self._extract_key_entities(kg_context)
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 9.1: Extracted {len(key_entities)} key entities")
        
        # Step 7: Build universal context summary
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 10: Building universal context summary")
        build_duration = (datetime.now() - start_time).total_seconds()
        universal_context = {
            "built_at": datetime.now().isoformat(),
            "project_directories": [str(d) for d in user_dirs],
            "total_files": len(self._file_importance),
            "project_map": self._project_map,
            "key_entities": key_entities,
            "knowledge_graph": kg_context,
            "patterns": pm_context,
            "importance_scores": self._file_importance,
            "build_duration_seconds": build_duration
        }
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 10.1: Universal context summary built")
        
        # Cache the universal context
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 11: Caching universal context")
        self._universal_context = universal_context
        self._last_build = datetime.now()
        
        # Also cache in persistent storage (cache.set is synchronous, not async)
        self.cache.set(
            "universal_context",
            universal_context,
            ttl=int(self._cache_ttl.total_seconds())
        )
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] Step 11.1: Universal context cached (TTL={self._cache_ttl.total_seconds()}s)")
        
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] ========== BUILD UNIVERSAL CONTEXT COMPLETE ==========")
        logger.info(f"🚀 [UNIVERSAL_CONTEXT] ✅ Universal context built in {build_duration:.2f}s")
        logger.info(f"🚀 [UNIVERSAL_CONTEXT]    📊 Total files: {universal_context['total_files']}")
        logger.info(f"🚀 [UNIVERSAL_CONTEXT]    🏗️ KG nodes: {kg_context.get('total_nodes', 0)}")
        logger.info(f"🚀 [UNIVERSAL_CONTEXT]    🔍 Patterns: {len(pm_context.get('patterns', []))}")
        
        return universal_context
    
    async def _ensure_complete_index(self, user_dirs: List[Path]):
        """Ensure RAG index contains ALL user project files."""
        logger.info(f"📥 [UNIVERSAL_CONTEXT] Ensuring RAG index is complete for {len(user_dirs)} directories...")
        
        for directory in user_dirs:
            logger.info(f"   Indexing project: {directory}")
            stats = await self.rag_ingester.index_directory(directory, recursive=True)
            logger.info(f"   ✅ Indexed: {stats['files_indexed']} files, {stats['chunks_created']} chunks. (Processed: {stats['files_processed']}, Skipped: {stats['files_skipped']}, Excluded: {stats['files_excluded']}, Errors: {stats['errors']})")
    
    async def _build_importance_map(self, user_dirs: List[Path]):
        """Build importance scores for all files."""
        logger.info("📊 Calculating file importance scores...")
        
        self._file_importance.clear()
        
        for directory in user_dirs:
            for file_path in directory.rglob("*"):
                if not file_path.is_file():
                    continue
                
                if should_exclude_path(file_path):
                    continue
                
                # Calculate importance
                importance = self._calculate_file_importance(file_path)
                self._file_importance[str(file_path)] = importance
        
        logger.info(f"   ✅ Scored {len(self._file_importance)} files")
    
    async def _build_project_map(self, user_dirs: List[Path]):
        """Build high-level project structure map."""
        logger.info("🗺️ [UNIVERSAL_CONTEXT] Building project structure map...")
        
        self._project_map = {
            "directories": {},
            "file_types": {},
            "key_files": []
        }
        
        total_files_mapped = 0
        for directory in user_dirs:
            dir_name = directory.name
            logger.info(f"   Mapping directory: {dir_name} ({directory})")
            self._project_map["directories"][dir_name] = {
                "path": str(directory),
                "file_count": 0,
                "subdirectories": []
            }
            
            project_file_count = 0
            for file_path in directory.rglob("*"):
                if not file_path.is_file():
                    continue
                
                if should_exclude_path(file_path):
                    continue
                
                # Count files
                project_file_count += 1
                total_files_mapped += 1
                
                # Track file types
                ext = file_path.suffix
                if ext:
                    self._project_map["file_types"][ext] = self._project_map["file_types"].get(ext, 0) + 1
                
                # Track key files (importance >= 0.8)
                importance = self._file_importance.get(str(file_path), 0.5)
                if importance >= 0.8:
                    self._project_map["key_files"].append({
                        "path": str(file_path),
                        "name": file_path.name,
                        "importance": importance
                    })
            
            self._project_map["directories"][dir_name]["file_count"] = project_file_count
            logger.info(f"   ✅ Mapped {project_file_count} files in {dir_name}")
        
        # Sort key files by importance
        self._project_map["key_files"].sort(key=lambda x: x["importance"], reverse=True)
        
        logger.info(f"   ✅ Total files mapped across all projects: {total_files_mapped}")
        logger.info(f"   ✅ Found {len(self._project_map['key_files'])} key files")
    
    async def _build_complete_kg(self, user_dirs: List[Path]) -> Dict[str, Any]:
        """Build Knowledge Graph for entire project."""
        logger.info("🕸️ Building complete Knowledge Graph...")
        
        all_nodes = []
        all_edges = []
        
        for directory in user_dirs:
            try:
                graph = await asyncio.to_thread(
                    self.kg_builder.build_graph,
                    directory,
                    recursive=True
                )
                
                # Extract nodes and edges
                all_nodes.extend(graph.nodes(data=True))
                all_edges.extend(graph.edges(data=True))
            except Exception as e:
                logger.error(f"Error building KG for {directory}: {e}")
        
        logger.info(f"   ✅ KG complete: {len(all_nodes)} nodes, {len(all_edges)} edges")
        
        return {
            "total_nodes": len(all_nodes),
            "total_edges": len(all_edges),
            "nodes": [{"id": n[0], **n[1]} for n in all_nodes[:1000]],  # Limit to first 1000 for storage
            "edges": [{"source": e[0], "target": e[1], **e[2]} for e in all_edges[:1000]]
        }
    
    async def _build_complete_patterns(self, user_dirs: List[Path]) -> Dict[str, Any]:
        """Run Pattern Mining on entire project."""
        logger.info("🔍 Running Pattern Mining on entire project...")
        
        all_patterns = []
        
        for directory in user_dirs:
            try:
                analysis = await asyncio.to_thread(
                    self.pattern_miner.analyze_project,
                    directory,
                    include_design_patterns=True,
                    include_anti_patterns=True,
                    include_code_smells=True
                )
                
                # analysis is a PatternAnalysisResult object, not a dict
                if hasattr(analysis, 'patterns') and analysis.patterns:
                    all_patterns.extend(analysis.patterns)
                elif isinstance(analysis, dict):
                    patterns = analysis.get("patterns", [])
                    all_patterns.extend(patterns)
            except Exception as e:
                logger.error(f"Error analyzing patterns for {directory}: {e}")
        
        logger.info(f"   ✅ Found {len(all_patterns)} patterns")
        
        return {
            "total_patterns": len(all_patterns),
            "patterns": all_patterns[:100]  # Limit to top 100 for storage
        }
    
    def _extract_key_entities(self, kg_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract key entities from Knowledge Graph."""
        nodes = kg_context.get("nodes", [])
        
        # Find most important nodes (classes, main functions)
        key_entities = []
        for node in nodes:
            node_type = node.get("type", "")
            if node_type in ["class", "namespace", "interface"]:
                key_entities.append({
                    "name": node.get("name", ""),
                    "type": node_type,
                    "file": node.get("file_path", "")
                })
        
        return key_entities[:50]  # Top 50 key entities
    
    async def get_universal_context(self) -> Dict[str, Any]:
        """
        Get the universal context (builds if not exists).
        
        Returns:
            Universal context with complete project knowledge
        """
        if not self._universal_context:
            return await self.build_universal_context()
        
        return self._universal_context
    
    async def get_smart_context_for_query(
        self,
        query: str,
        artifact_type: Optional[str] = None,
        k: int = 18
    ) -> Dict[str, Any]:
        """
        Get smart context for a query, combining universal baseline with targeted retrieval.
        
        This is what artifact generation and chat should use!
        
        Args:
            query: User query or requirements
            artifact_type: Optional artifact type for targeted retrieval
            k: Number of targeted results to add
        
        Returns:
            Smart context with universal baseline + targeted results
        """
        # Get universal context as baseline
        universal = await self.get_universal_context()
        
        # Get targeted retrieval results
        targeted_snippets = await self.rag_retriever.retrieve(
            query=query,
            k=k,
            artifact_type=artifact_type
        )
        
        # Rank targeted snippets by file importance
        for snippet in targeted_snippets:
            file_path = snippet.get("metadata", {}).get("file_path", "")
            importance = self._file_importance.get(file_path, 0.5)
            snippet["importance"] = importance
            snippet["combined_score"] = snippet.get("score", 0.5) * (0.7) + importance * (0.3)
        
        # Sort by combined score
        targeted_snippets.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        
        return {
            "universal_context": universal,
            "targeted_snippets": targeted_snippets,
            "key_entities": universal.get("key_entities", []),
            "project_map": universal.get("project_map", {}),
            "query": query,
            "artifact_type": artifact_type
        }


# Singleton instance
_service_instance: Optional[UniversalContextService] = None


def get_universal_context_service() -> UniversalContextService:
    """Get or create the Universal Context Service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = UniversalContextService()
    return _service_instance

