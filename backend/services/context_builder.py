"""
Context Builder Service - Combines RAG, Knowledge Graph, Pattern Mining, and ML Features.
Builds comprehensive context for artifact generation.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import asyncio

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.rag_retriever import RAGRetriever
from backend.services.rag_cache import get_rag_cache
from backend.services.knowledge_graph import get_builder as get_kg_builder
from backend.services.pattern_mining import get_miner
from backend.services.ml_features import get_engineer
from backend.services.universal_context import get_universal_context_service
from backend.core.config import settings
from backend.core.cache import get_cache_manager, cached
from backend.core.metrics import get_metrics_collector, timed
from backend.core.logger import get_logger
from backend.core.lazy_loading import lazy_property

logger = get_logger(__name__)
metrics = get_metrics_collector()


class ContextBuilder:
    """
    Context Builder service that combines multiple analysis sources.
    
    Features:
    - RAG retrieval (hybrid search)
    - Knowledge Graph analysis
    - Pattern Mining insights
    - ML Feature extraction
    - Context caching
    - Context assembly and ranking
    """
    
    def __init__(self):
        """Initialize Context Builder."""
        self.rag_retriever = RAGRetriever()
        self.rag_cache = get_rag_cache()
        self.kg_builder = get_kg_builder()
        self.pattern_miner = get_miner()
        self.ml_engineer = get_engineer()
        self.universal_context_service = get_universal_context_service()
        self._context_store: Dict[str, Dict[str, Any]] = {}  # Store contexts by ID
        
        # FIX: Memory management - limit context store size
        self._max_context_store_size = 50  # Keep last 50 contexts
        
        logger.info("Context Builder initialized with Universal Context Powerhouse")
    
    def _cleanup_old_contexts(self):
        """Remove old contexts to prevent memory growth."""
        if len(self._context_store) <= self._max_context_store_size:
            return
        
        # Sort by created_at and keep newest
        sorted_contexts = sorted(
            self._context_store.items(),
            key=lambda x: x[1].get("created_at", ""),
            reverse=True
        )
        
        # Keep only the newest N contexts
        self._context_store = dict(sorted_contexts[:self._max_context_store_size])
        logger.info(f"🧹 [CONTEXT] Cleaned up old contexts, {len(self._context_store)} remain")
    
    @timed("context_build", tags={"operation": "build_context"})
    async def build_context(
        self,
        meeting_notes: str,
        repo_id: Optional[str] = None,
        include_rag: bool = True,
        include_kg: bool = True,
        include_patterns: bool = True,
        include_ml_features: bool = False,
        max_rag_chunks: int = 18,
        kg_depth: int = 2,
        artifact_type: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Build comprehensive context from multiple sources.
        
        Args:
            meeting_notes: User requirements/meeting notes
            repo_id: Optional repository identifier
            include_rag: Whether to include RAG retrieval
            include_kg: Whether to include Knowledge Graph analysis
            include_patterns: Whether to include Pattern Mining
            include_ml_features: Whether to include ML features (slower)
            max_rag_chunks: Maximum number of RAG chunks to retrieve
            kg_depth: Knowledge Graph traversal depth
            artifact_type: Optional artifact type for targeted retrieval
            force_refresh: If True, bypass cache and always retrieve fresh context
        
        Returns:
            Dictionary with assembled context
        """
        # 🚀 STEP 1: Get Universal Context (baseline project knowledge)
        logger.info("🚀 Getting Universal Context - The baseline that knows your entire project by heart")
        
        try:
            universal_ctx = await self.universal_context_service.get_universal_context()
            if not universal_ctx:
                raise ValueError("Universal context service returned None")
        except Exception as e:
            logger.error(f"Failed to get universal context: {e}", exc_info=True)
            # Fallback to empty universal context
            universal_ctx = {
                "project_directories": [],
                "total_files": 0,
                "key_entities": [],
                "project_map": {},
                "knowledge_graph": {"nodes": [], "edges": []},
                "patterns": []
            }
        
        context = {
            "meeting_notes": meeting_notes,
            "repo_id": repo_id,
            "created_at": datetime.now().isoformat(),
            "universal_context": {
                "project_directories": universal_ctx.get("project_directories", []),
                "total_files": universal_ctx.get("total_files", 0),
                "key_entities": universal_ctx.get("key_entities", []),
                "project_map": universal_ctx.get("project_map", {})
            },
            "sources": {}
        }
        
        logger.info(f"✅ Universal Context loaded: {universal_ctx.get('total_files', 0)} files, {len(universal_ctx.get('key_entities', []))} key entities")
        
        # Check cache first (unless force_refresh is True)
        if not force_refresh:
            cache_key = self._get_cache_key(meeting_notes, repo_id, include_rag, include_kg, include_patterns)
            cached_context = self.rag_cache.get_context(meeting_notes)
            
            if cached_context and not include_ml_features:
                logger.info("Using cached targeted context (with universal baseline)")
                # Parse cached context to extract RAG data properly
                return {
                    **context,
                    "sources": {
                        "rag": {
                            "cached": True, 
                            "context": cached_context,
                            "num_snippets": cached_context.count("--- Snippet") if cached_context else 0
                        }
                    },
                    "assembled_context": cached_context,  # Include assembled context from cache
                    "from_cache": True,
                    "rag": cached_context  # Also include at top level for compatibility
                }
        else:
            logger.info("🔄 Force refresh requested - bypassing cache")
        
        # 🎯 STEP 2: Build targeted context on top of universal baseline
        logger.info("🎯 Building targeted context for this specific query")
        tasks = []
        task_names = []
        
        if include_rag:
            # Use smart context that combines universal + targeted
            tasks.append(self._build_smart_rag_context(meeting_notes, max_rag_chunks, artifact_type))
            task_names.append("rag")
        
        if include_kg:
            tasks.append(self._build_kg_context(meeting_notes, kg_depth))
            task_names.append("kg")
        
        if include_patterns:
            tasks.append(self._build_pattern_context(meeting_notes))
            task_names.append("patterns")
        
        if include_ml_features:
            tasks.append(self._build_ml_features_context(meeting_notes))
            task_names.append("ml_features")
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error building context source {task_names[i]}: {result}", exc_info=result)
                continue
            
            source_name = task_names[i]
            if result:
                context["sources"][source_name] = result
        
        # Assemble final context (returns dict with content and truncation_info)
        assembly_result = self._assemble_context(context)
        assembled_context = assembly_result["content"]
        truncation_info = assembly_result["truncation_info"]
        
        # Cache the assembled context
        if include_rag and "rag" in context["sources"]:
            rag_context = context["sources"]["rag"].get("context", "")
            if rag_context:
                self.rag_cache.set_context(meeting_notes, rag_context)
        
        final_context = {
            **context,
            "assembled_context": assembled_context,
            "truncation_info": truncation_info,  # Include truncation metadata for API transparency
            "from_cache": False,
            "context_id": context.get("created_at", datetime.now().isoformat())  # Use timestamp as ID
        }
        
        # Store context for retrieval by ID
        context_id = final_context["context_id"]
        self._context_store[context_id] = final_context
        
        # FIX: Cleanup old contexts to prevent memory leak
        self._cleanup_old_contexts()
        
        return final_context
    
    async def _build_smart_rag_context(self, meeting_notes: str, max_chunks: int, artifact_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Build SMART RAG context using Universal Context + Targeted Retrieval.
        This is the POWERHOUSE approach that knows your entire project + specific query needs.
        """
        try:
            # Use Universal Context Service's smart retrieval
            smart_ctx = await self.universal_context_service.get_smart_context_for_query(
                query=meeting_notes,
                artifact_type=artifact_type,
                k=max_chunks
            )
            
            targeted_snippets = smart_ctx.get("targeted_snippets", [])
            key_entities = smart_ctx.get("key_entities", [])
            
            context_parts = []
            for snippet in targeted_snippets:
                content = snippet.get("content", "")
                metadata = snippet.get("metadata", {})
                score = snippet.get("combined_score", snippet.get("score", 0.0))
                importance = snippet.get("importance", 0.5)
                
                context_parts.append({
                    "content": content,
                    "file_path": metadata.get("file_path", "unknown"),
                    "score": score,
                    "importance": importance,
                    "metadata": metadata
                })
            
            # Build context string with importance indicators
            context_lines = []
            context_lines.append("=== PROJECT CONTEXT (Universal Knowledge + Targeted Retrieval) ===\n")
            
            # Add key entities summary
            if key_entities:
                context_lines.append("🔑 KEY PROJECT ENTITIES:")
                for entity in key_entities[:10]:
                    context_lines.append(f"  - {entity.get('name', 'unknown')} ({entity.get('type', 'unknown')})")
                context_lines.append("")
            
            # Add targeted snippets (sorted by combined score)
            context_lines.append("📄 RELEVANT CODE SNIPPETS (ranked by importance + relevance):\n")
            for i, part in enumerate(context_parts, 1):
                importance_stars = "⭐" * int(part["importance"] * 5)
                context_lines.append(f"\n--- Snippet {i} {importance_stars} (score: {part['score']:.3f}) ---")
                context_lines.append(f"File: {part['file_path']}")
                context_lines.append(part["content"])
            
            context_str = "\n".join(context_lines)
            
            return {
                "context": context_str,
                "snippets": context_parts,
                "num_snippets": len(context_parts),
                "avg_score": sum(s["score"] for s in context_parts) / len(context_parts) if context_parts else 0.0,
                "key_entities": key_entities,
                "uses_universal_context": True
            }
        except Exception as e:
            logger.error(f"Error building smart RAG context: {e}", exc_info=True)
            # Fallback to basic RAG
            return await self._build_basic_rag_context(meeting_notes, max_chunks, artifact_type)
    
    async def _build_basic_rag_context(self, meeting_notes: str, max_chunks: int, artifact_type: Optional[str] = None) -> Dict[str, Any]:
        """Build basic RAG context (fallback if smart context fails)."""
        try:
            snippets = await self.rag_retriever.retrieve(meeting_notes, k=max_chunks, artifact_type=artifact_type)
            
            context_parts = []
            for snippet in snippets:
                content = snippet.get("content", "")
                metadata = snippet.get("metadata", {})
                score = snippet.get("score", 0.0)
                
                context_parts.append({
                    "content": content,
                    "file_path": metadata.get("path", "unknown"),
                    "score": score,
                    "metadata": metadata
                })
            
            context_str = "\n---\n".join([s["content"] for s in context_parts])
            
            return {
                "context": context_str,
                "snippets": context_parts,
                "num_snippets": len(context_parts),
                "avg_score": sum(s["score"] for s in context_parts) / len(context_parts) if context_parts else 0.0,
                "uses_universal_context": False
            }
        except Exception as e:
            logger.error(f"Error building basic RAG context: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _build_kg_context(self, meeting_notes: str, depth: int) -> Dict[str, Any]:
        """Build Knowledge Graph context."""
        try:
            # Extract key terms from meeting notes for graph query
            key_terms = self._extract_key_terms(meeting_notes)
            
            # Get graph stats
            stats = self.kg_builder.get_stats()
            
            # Find relevant nodes
            relevant_nodes = []
            for term in key_terms[:5]:  # Limit to top 5 terms
                node_id = self.kg_builder._find_node_by_name(term)
                if node_id:
                    relevant_nodes.append({
                        "term": term,
                        "node_id": node_id,
                        "found": True
                    })
            
            # Get most connected nodes (likely important)
            most_connected = self.kg_builder.get_most_connected_nodes(top_k=10)
            
            # Get centrality metrics
            centrality = self.kg_builder.get_centrality("degree")
            top_central = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "graph_stats": stats,
                "relevant_nodes": relevant_nodes,
                "most_connected": [{"node_id": nid, "degree": deg} for nid, deg in most_connected],
                "top_central_nodes": [{"node_id": nid, "centrality": score} for nid, score in top_central],
                "key_terms_searched": key_terms
            }
        except Exception as e:
            logger.error(f"Error building KG context: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _build_pattern_context(self, meeting_notes: str) -> Dict[str, Any]:
        """Build Pattern Mining context from ACTUAL detected patterns."""
        try:
            # Get REAL pattern mining results (not hardcoded!)
            from backend.services.analysis_service import get_service as get_analysis_service
            
            patterns_detected = []
            code_smells = []
            security_issues = []
            
            # Try to get actual pattern mining results
            try:
                # First check the pattern miner's cached results
                if self.pattern_miner.patterns_detected:
                    for pm in self.pattern_miner.patterns_detected:
                        patterns_detected.append({
                            "name": pm.pattern_name,
                            "file": pm.file_path,
                            "confidence": pm.confidence
                        })
                
                if self.pattern_miner.code_smells_detected:
                    for smell in self.pattern_miner.code_smells_detected[:10]:  # Top 10
                        code_smells.append({
                            "type": smell.smell_type,
                            "file": smell.file_path,
                            "severity": smell.severity
                        })
                
                if self.pattern_miner.security_issues_detected:
                    for issue in self.pattern_miner.security_issues_detected[:5]:  # Top 5
                        security_issues.append({
                            "type": issue.issue_type,
                            "severity": issue.severity,
                            "file": issue.file_path
                        })
            except Exception as e:
                logger.debug(f"Could not get pattern miner results: {e}")
            
            # Fallback to analysis service if pattern miner has no data
            if not patterns_detected:
                try:
                    analysis_service = get_analysis_service()
                    cached = analysis_service.last_analysis
                    if cached:
                        patterns_detected = cached.get("patterns", [])[:15]
                        code_smells = cached.get("code_smells", [])[:10]
                        security_issues = cached.get("security_issues", [])[:5]
                except Exception:
                    pass
            
            # Build response with actual data
            return {
                "patterns_available": len(patterns_detected) > 0,
                "patterns_detected": patterns_detected,
                "pattern_count": len(patterns_detected),
                "code_smells": code_smells,
                "code_smell_count": len(code_smells),
                "security_issues": security_issues,
                "security_issue_count": len(security_issues),
                "note": "Real pattern mining data from project analysis" if patterns_detected else "No patterns detected yet - run analysis first"
            }
        except Exception as e:
            logger.error(f"Error building pattern context: {e}", exc_info=True)
            return {"error": str(e), "patterns_available": False}
    
    async def _build_ml_features_context(self, meeting_notes: str) -> Dict[str, Any]:
        """Build ML Features context."""
        try:
            # Extract features from meeting notes itself
            features = self.ml_engineer.extract_code_features(meeting_notes, "meeting_notes.txt")
            
            return {
                "meeting_notes_features": features,
                "note": "ML features extracted from meeting notes. For code/diagram features, use /api/analysis/ml-features"
            }
        except Exception as e:
            logger.error(f"Error building ML features context: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _assemble_context(self, context: Dict[str, Any], max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        Assemble context from all sources into a single string with smart prioritization.
        
        Priority order (most important first):
        1. Key Entities (most critical for generation)
        2. User Requirements (meeting notes)
        3. High-relevance RAG snippets (sorted by score)
        4. Knowledge Graph insights
        5. Pattern Mining insights
        6. Lower-relevance RAG snippets (only if space permits)
        
        Args:
            context: Context dictionary with sources
            max_tokens: Maximum token limit (defaults to settings.context_assembly_max_tokens)
        
        Returns:
            Dictionary with:
            - content: Assembled context string
            - truncation_info: Metadata about what was truncated (for API transparency)
        """
        from rag.filters import estimate_tokens
        
        # Use centralized config for token limits
        if max_tokens is None:
            max_tokens = settings.context_assembly_max_tokens
        
        # Budget allocation (in tokens)
        # Reserve tokens for different sections with priorities
        key_entities_budget = int(max_tokens * 0.15)      # 15% for key entities
        requirements_budget = int(max_tokens * 0.25)      # 25% for meeting notes
        high_priority_rag_budget = int(max_tokens * 0.35) # 35% for high-score RAG
        kg_patterns_budget = int(max_tokens * 0.10)       # 10% for KG + patterns
        low_priority_rag_budget = int(max_tokens * 0.15)  # 15% for remaining RAG
        
        assembled_parts = []
        used_tokens = 0
        
        # Track truncation for API transparency
        truncation_info = {
            "any_truncated": False,
            "sections_truncated": [],
            "token_budget": max_tokens,
            "tokens_used": 0
        }
        
        def _add_section(content: str, budget: int, section_name: str) -> str:
            """Add a section if it fits within budget, with smart summarization if needed."""
            nonlocal used_tokens
            
            if not content or not content.strip():
                return ""
            
            content_tokens = estimate_tokens(content)
            
            if content_tokens <= budget:
                # Content fits, add it fully
                used_tokens += content_tokens
                return content
            
            # Content exceeds budget - use smart truncation
            # Track this for API transparency
            truncation_info["any_truncated"] = True
            truncation_info["sections_truncated"].append({
                "section": section_name,
                "original_tokens": content_tokens,
                "budget_tokens": budget,
                "reduction_percent": round((1 - budget / content_tokens) * 100, 1)
            })
            
            # Find natural break points (paragraphs, sections) to truncate
            lines = content.split('\n')
            truncated_lines = []
            current_tokens = 0
            
            for line in lines:
                line_tokens = estimate_tokens(line + '\n')
                if current_tokens + line_tokens <= budget:
                    truncated_lines.append(line)
                    current_tokens += line_tokens
                else:
                    # Check if we have meaningful content already
                    if current_tokens > budget * 0.5:
                        break
                    # Otherwise, try to fit partial line
                    remaining_budget = budget - current_tokens
                    if remaining_budget > 20:  # At least 20 tokens worth
                        char_limit = remaining_budget * 4  # Rough estimate
                        truncated_lines.append(line[:char_limit] + "...")
                        current_tokens += remaining_budget
                    break
            
            truncated_content = '\n'.join(truncated_lines)
            if truncated_content != content:
                truncated_content += f"\n\n[... {section_name} truncated to preserve higher-priority context ...]"
                logger.info(f"⚠️ [CONTEXT] {section_name} truncated from {content_tokens} to ~{current_tokens} tokens")
            
            used_tokens += current_tokens
            return truncated_content
        
        # ============================================================
        # PRIORITY 1: Key Entities (Critical for understanding project)
        # ============================================================
        key_entities_section = ""
        if "universal_context" in context:
            uc = context["universal_context"]
            key_entities = uc.get('key_entities', [])
            if key_entities:
                entity_lines = ["🔑 === KEY PROJECT ENTITIES (Most Important) ==="]
                # Prioritize entities by type: classes > functions > modules
                type_priority = {"class": 0, "function": 1, "module": 2, "file": 3}
                sorted_entities = sorted(
                    key_entities,
                    key=lambda e: type_priority.get(e.get('type', '').lower(), 99)
                )
                for entity in sorted_entities[:15]:  # Top 15 entities
                    entity_lines.append(f"  • {entity.get('name', 'unknown')} ({entity.get('type', 'unknown')})")
                key_entities_section = '\n'.join(entity_lines) + '\n'
        
        assembled_parts.append(_add_section(key_entities_section, key_entities_budget, "Key Entities"))
        
        # ============================================================
        # PRIORITY 2: User Requirements (Meeting Notes)
        # ============================================================
        requirements_section = "📋 === YOUR REQUIREMENTS ===\n" + context.get("meeting_notes", "")
        assembled_parts.append(_add_section(requirements_section, requirements_budget, "Requirements"))
        
        # ============================================================
        # PRIORITY 3: High-Relevance RAG Snippets
        # ============================================================
        high_priority_rag = ""
        low_priority_rag = ""
        
        if "rag" in context.get("sources", {}):
            rag_source = context["sources"]["rag"]
            snippets = rag_source.get("snippets", [])
            
            if snippets:
                # Sort snippets by score (highest first)
                sorted_snippets = sorted(snippets, key=lambda s: s.get("score", 0), reverse=True)
                
                # Split into high-priority (top 60%) and low-priority (bottom 40%)
                split_point = max(1, int(len(sorted_snippets) * 0.6))
                high_snippets = sorted_snippets[:split_point]
                low_snippets = sorted_snippets[split_point:]
                
                # Build high-priority RAG section
                high_lines = ["📄 === CODEBASE CONTEXT (High Relevance) ==="]
                for i, snippet in enumerate(high_snippets, 1):
                    score = snippet.get("score", 0)
                    file_path = snippet.get("file_path", "unknown")
                    content = snippet.get("content", "")
                    high_lines.append(f"\n--- Snippet {i} (score: {score:.3f}, file: {file_path}) ---")
                    high_lines.append(content)
                high_priority_rag = '\n'.join(high_lines)
                
                # Build low-priority RAG section
                if low_snippets:
                    low_lines = ["📄 === ADDITIONAL CONTEXT (Lower Relevance) ==="]
                    for i, snippet in enumerate(low_snippets, 1):
                        score = snippet.get("score", 0)
                        file_path = snippet.get("file_path", "unknown")
                        content = snippet.get("content", "")
                        low_lines.append(f"\n--- Snippet {len(high_snippets) + i} (score: {score:.3f}, file: {file_path}) ---")
                        low_lines.append(content)
                    low_priority_rag = '\n'.join(low_lines)
            elif "context" in rag_source:
                # Fallback to raw context string
                high_priority_rag = "📄 === CODEBASE CONTEXT ===\n" + rag_source["context"]
        
        assembled_parts.append(_add_section(high_priority_rag, high_priority_rag_budget, "High-Priority RAG"))
        
        # ============================================================
        # PRIORITY 4: Knowledge Graph + Pattern Mining Insights
        # ============================================================
        kg_patterns_section = ""
        
        # Knowledge Graph
        if "kg" in context.get("sources", {}):
            kg_source = context["sources"]["kg"]
            if "graph_stats" in kg_source:
                stats = kg_source["graph_stats"]
                kg_lines = ["\n🧠 === KNOWLEDGE GRAPH INSIGHTS ==="]
                kg_lines.append(f"Graph: {stats.get('node_count', 0)} nodes, {stats.get('edge_count', 0)} edges")
                
                if "most_connected" in kg_source:
                    kg_lines.append("Most Connected:")
                    for node in kg_source["most_connected"][:3]:
                        kg_lines.append(f"  • {node['node_id']} (degree: {node['degree']})")
                kg_patterns_section += '\n'.join(kg_lines) + '\n'
        
        # Pattern Mining (uses real data from _build_pattern_context)
        if "patterns" in context.get("sources", {}):
            pattern_source = context["sources"]["patterns"]
            if pattern_source.get("patterns_available"):
                patterns_detected = pattern_source.get("patterns_detected", [])
                if patterns_detected:
                    pattern_names = [p.get("name", "Unknown") if isinstance(p, dict) else str(p) for p in patterns_detected[:10]]
                    kg_patterns_section += f"\n🔍 === DESIGN PATTERNS DETECTED ({len(patterns_detected)}) ===\n{', '.join(pattern_names)}\n"
                
                code_smells = pattern_source.get("code_smells", [])
                if code_smells:
                    kg_patterns_section += f"⚠️ Code smells: {len(code_smells)} detected\n"
                
                security_issues = pattern_source.get("security_issues", [])
                if security_issues:
                    kg_patterns_section += f"🔒 Security issues: {len(security_issues)} detected\n"
        
        assembled_parts.append(_add_section(kg_patterns_section, kg_patterns_budget, "KG/Patterns"))
        
        # ============================================================
        # PRIORITY 5: Low-Priority RAG (only if space permits)
        # ============================================================
        remaining_budget = max_tokens - used_tokens
        if remaining_budget > 100 and low_priority_rag:  # Only add if > 100 tokens left
            assembled_parts.append(_add_section(low_priority_rag, min(remaining_budget, low_priority_rag_budget), "Low-Priority RAG"))
        
        # Final assembly
        assembled = "\n".join([p for p in assembled_parts if p])
        
        # Final safety check
        final_tokens = estimate_tokens(assembled)
        truncation_info["tokens_used"] = final_tokens
        
        if final_tokens > max_tokens * 1.1:  # Allow 10% overflow
            logger.warning(f"⚠️ [CONTEXT] Final context {final_tokens} tokens slightly exceeds limit {max_tokens}")
        else:
            logger.info(f"✅ [CONTEXT] Context assembled: {final_tokens} tokens (budget: {max_tokens})")
        
        if truncation_info["any_truncated"]:
            logger.info(f"⚠️ [CONTEXT] Truncation applied to sections: {[s['section'] for s in truncation_info['sections_truncated']]}")
        
        # Return both content and truncation metadata for API transparency
        return {
            "content": assembled,
            "truncation_info": truncation_info
        }
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text for graph queries."""
        # Simple extraction: words that are capitalized or common tech terms
        words = text.split()
        key_terms = []
        
        for word in words:
            # Remove punctuation
            clean_word = word.strip('.,!?;:()[]{}"\'').lower()
            
            # Skip common words
            if clean_word in ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'from']:
                continue
            
            # Add capitalized words (likely class names, components)
            if word[0].isupper() and len(word) > 2:
                key_terms.append(clean_word)
            
            # Add common tech terms
            tech_terms = ['api', 'model', 'service', 'controller', 'component', 'class', 'function', 'method']
            if clean_word in tech_terms:
                key_terms.append(clean_word)
        
        # Remove duplicates and return
        return list(dict.fromkeys(key_terms))[:10]  # Top 10 terms
    
    def _get_cache_key(self, meeting_notes: str, repo_id: Optional[str], *flags) -> str:
        """Generate cache key for context."""
        key_parts = [meeting_notes, repo_id or "", str(flags)]
        return "|".join(key_parts)
    
    async def get_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a previously built context by ID.
        
        Args:
            context_id: Context identifier (timestamp)
        
        Returns:
            Context dictionary or None if not found
        """
        return self._context_store.get(context_id)
    
    async def get_context_by_id(self, context_id: str) -> Optional[Dict[str, Any]]:
        """
        Alias for get_context for consistency.
        
        Args:
            context_id: Context identifier (timestamp)
        
        Returns:
            Context dictionary or None if not found
        """
        return await self.get_context(context_id)


# Global builder instance
_builder: Optional[ContextBuilder] = None


def get_builder() -> ContextBuilder:
    """Get or create global Context Builder instance."""
    global _builder
    if _builder is None:
        _builder = ContextBuilder()
    return _builder

