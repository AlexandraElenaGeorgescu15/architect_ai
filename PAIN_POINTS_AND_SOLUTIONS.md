# 🎯 Architectural Pain Points & Solutions

**Date:** November 24, 2025  
**Author:** User + AI Analysis  
**Priority:** HIGH - These are real production issues

---

## 🔴 CRITICAL PAIN POINTS (Will Bite in Production)

### **1. Universal Context Staleness** 🔥

**Problem:**
```
User switches branches (git checkout feature-auth)
     ↓
Universal Context still has old main branch entities
     ↓
RAG retrieves UserModel v1 (doesn't exist in feature-auth!)
     ↓
Generated artifact references deleted code
     ↓
User: "WTF, this is wrong!" 😡
```

**Current:** Cache for 6 hours, blind to git changes

**Real-World Scenario:**
```bash
# User on main branch
UniversalContext: "AuthService, UserModel, SessionManager exist"

# User switches branch
git checkout feature-redesign

# Big refactor: AuthService → AuthenticationService, UserModel deleted
# Universal Context still thinks AuthService exists! 
# Generates code referencing deleted classes!
```

---

#### **IMMEDIATE FIX (30 minutes):**

Add git-aware cache invalidation:

**File:** `backend/services/universal_context.py`

```python
import subprocess
from typing import Optional, Tuple

class UniversalContextService:
    
    def __init__(self):
        # ... existing code ...
        self._last_git_state: Optional[Tuple[str, int]] = None  # (commit_hash, diff_size)
    
    def _get_git_state(self) -> Optional[Tuple[str, int]]:
        """
        Get current git state (HEAD commit + uncommitted changes).
        
        Returns:
            (commit_hash, num_changed_files) or None if not a git repo
        """
        try:
            user_dirs = get_user_project_directories()
            if not user_dirs:
                return None
            
            project_dir = user_dirs[0]
            
            # Get HEAD commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return None  # Not a git repo
            
            commit_hash = result.stdout.strip()
            
            # Get number of changed files (staged + unstaged)
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            changed_files = len([line for line in result.stdout.split('\n') if line.strip()])
            
            return (commit_hash, changed_files)
        
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"Could not get git state: {e}")
            return None
    
    def _should_rebuild_context(self, force_rebuild: bool = False) -> bool:
        """
        Determine if Universal Context should be rebuilt.
        
        Checks:
        1. Force rebuild flag
        2. No existing context
        3. Cache TTL expired (6 hours)
        4. Git state changed (different commit OR >10 changed files)
        
        Returns:
            True if rebuild needed
        """
        # Force rebuild
        if force_rebuild:
            logger.info("🔄 Force rebuild requested")
            return True
        
        # No existing context
        if not self._universal_context or not self._last_build:
            logger.info("🔄 No existing context, rebuild needed")
            return True
        
        # Cache TTL expired
        if (datetime.now() - self._last_build) > self._cache_ttl:
            logger.info("🔄 Cache TTL expired (>6 hours), rebuild needed")
            return True
        
        # Git state changed
        current_git_state = self._get_git_state()
        if current_git_state and self._last_git_state:
            old_hash, old_changes = self._last_git_state
            new_hash, new_changes = current_git_state
            
            if old_hash != new_hash:
                logger.info(f"🔄 Git commit changed ({old_hash[:8]} → {new_hash[:8]}), rebuild needed")
                return True
            
            if new_changes > 10:  # Threshold: >10 uncommitted changes
                logger.info(f"🔄 Significant uncommitted changes ({new_changes} files), rebuild needed")
                return True
        
        # Context is fresh
        logger.debug("✅ Universal Context is fresh (no rebuild needed)")
        return False
    
    async def get_universal_context(self) -> Dict[str, Any]:
        """Get universal context with git-aware cache invalidation."""
        if self._should_rebuild_context():
            return await self.build_universal_context()
        
        return self._universal_context
    
    async def build_universal_context(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Build context and save git state."""
        # ... existing build logic ...
        
        # After successful build:
        self._last_git_state = self._get_git_state()
        logger.info(f"📌 Git state captured: {self._last_git_state}")
        
        return universal_context
```

**Benefits:**
- ✅ Auto-invalidates on branch switch
- ✅ Catches big refactors (>10 changed files)
- ✅ Still caches for speed (if no git changes)
- ✅ Gracefully handles non-git projects

**Test:**
```bash
# Build context
curl http://localhost:8000/api/universal-context/status
# Should show: commit abc123, 0 changed files

# Switch branch
git checkout feature-branch

# Get context again
curl http://localhost:8000/api/universal-context/status
# Should detect change and rebuild! 🎉
```

---

#### **ADVANCED FIX (2 hours): Delta Context Layer**

For frequent small changes (e.g., editing one file), full rebuild is overkill.

**Concept:**
```
Universal Context (baseline, cached 6 hours)
    +
Delta Context (recent changes, cached 5 minutes)
    =
Smart Context (always fresh!)
```

**Implementation:**

```python
class DeltaContextLayer:
    """
    Tracks recently changed files and provides incremental context updates.
    """
    
    def __init__(self, ttl_minutes: int = 5):
        self._delta_cache: Dict[str, Any] = {}
        self._cache_ttl = timedelta(minutes=ttl_minutes)
        self._last_update: Optional[datetime] = None
    
    def get_changed_files_since_commit(self, commit_hash: str) -> List[Path]:
        """Get files changed since given commit."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", commit_hash, "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            changed_files = [
                Path(f.strip()) 
                for f in result.stdout.split('\n') 
                if f.strip()
            ]
            
            return changed_files
        except Exception as e:
            logger.error(f"Error getting changed files: {e}")
            return []
    
    async def build_delta_context(
        self, 
        base_commit: str,
        rag_ingester: RAGIngester
    ) -> Dict[str, Any]:
        """
        Build delta context for recently changed files.
        
        This is FAST because it only processes changed files, not entire project.
        """
        changed_files = self.get_changed_files_since_commit(base_commit)
        
        if not changed_files:
            return {"changed_files": [], "snippets": []}
        
        logger.info(f"🔄 Building delta context for {len(changed_files)} changed files")
        
        # Re-index only changed files (incremental)
        for file_path in changed_files:
            if file_path.exists():
                await rag_ingester.index_file(file_path)
        
        # Extract snippets from changed files
        snippets = []
        for file_path in changed_files[:10]:  # Limit to 10 most recent
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    snippets.append({
                        "file": str(file_path),
                        "content": content[:500],  # First 500 chars
                        "change_type": "modified"
                    })
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")
        
        return {
            "changed_files": [str(f) for f in changed_files],
            "snippets": snippets,
            "updated_at": datetime.now().isoformat()
        }
```

**Usage in Context Builder:**
```python
async def build_context(...):
    # 1. Get Universal Context (baseline, cached)
    universal = await universal_service.get_universal_context()
    
    # 2. Get Delta Context (recent changes, fast)
    if universal.get("git_commit"):
        delta = await delta_layer.build_delta_context(
            base_commit=universal["git_commit"],
            rag_ingester=self.rag_ingester
        )
    else:
        delta = {}
    
    # 3. Combine: Delta takes precedence (more recent)
    context = {
        "universal_baseline": universal,
        "recent_changes": delta,  # ← Overrides stale baseline!
        "sources": {}
    }
```

**Benefits:**
- ✅ Fast (only processes changed files)
- ✅ Always fresh (5-minute cache)
- ✅ Overlays on top of universal baseline
- ✅ No full rebuild for small edits

---

### **2. Knowledge Graph Confidence Scoring** 🎯

**Problem:**
```python
# Python with dynamic imports
auth_module = __import__(f'services.{service_name}')  # ← KG can't track!

# TypeScript with dependency injection
@Injectable()
class UserService {
  constructor(private authService: AuthService) {}  # ← Decorator magic!
}

# C# with reflection
Type.GetType("MyApp.AuthService").GetMethod("Validate").Invoke(...)  # ← Runtime!
```

**KG extracts:** `UserService → uses → AuthService`  
**Reality:** Relationship is IMPLIED, not explicit in AST

**Result:** KG treats implied edges as gospel → hallucinated relationships → wrong context

---

#### **IMMEDIATE FIX (1 hour):**

Add confidence scoring to Knowledge Graph edges:

**File:** `backend/services/knowledge_graph.py`

```python
class KnowledgeGraphBuilder:
    
    def _add_relationship(
        self, 
        source: str, 
        target: str, 
        rel_type: str,
        confidence: float = 1.0,  # ← NEW: confidence score
        evidence: Optional[str] = None  # ← NEW: source code evidence
    ):
        """
        Add relationship with confidence scoring.
        
        Confidence levels:
        - 1.0: Explicit (direct import, extends, implements)
        - 0.8: Strong inference (constructor injection, field)
        - 0.6: Weak inference (method call, string reference)
        - 0.3: Speculative (reflection, dynamic import)
        """
        self.graph.add_edge(
            source, 
            target,
            type=rel_type,
            confidence=confidence,
            evidence=evidence,
            added_at=datetime.now().isoformat()
        )
    
    def _parse_python_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse Python with confidence-scored relationships."""
        # ... existing parsing ...
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._add_relationship(
                        source=current_class or file_path.stem,
                        target=alias.name,
                        rel_type="imports",
                        confidence=1.0,  # ← Explicit import
                        evidence=f"import {alias.name}"
                    )
            
            elif isinstance(node, ast.Call):
                # Method call → weak inference
                if isinstance(node.func, ast.Attribute):
                    self._add_relationship(
                        source=current_class,
                        target=node.func.attr,
                        rel_type="calls",
                        confidence=0.6,  # ← Inferred, not explicit
                        evidence=f"{node.func.attr}()"
                    )
            
            elif isinstance(node, ast.Str) and "import" in node.s:
                # Dynamic import (string)
                self._add_relationship(
                    source=current_class,
                    target=node.s,
                    rel_type="dynamic_import",
                    confidence=0.3,  # ← Very speculative
                    evidence=f'"{node.s}"'
                )
    
    def get_high_confidence_neighbors(
        self, 
        node: str, 
        min_confidence: float = 0.8
    ) -> List[Tuple[str, Dict]]:
        """
        Get neighbors with confidence filtering.
        
        Use this instead of graph.neighbors() to avoid low-confidence edges.
        """
        neighbors = []
        for neighbor in self.graph.neighbors(node):
            edge_data = self.graph[node][neighbor]
            if edge_data.get("confidence", 1.0) >= min_confidence:
                neighbors.append((neighbor, edge_data))
        
        return neighbors
```

**Usage in Context Builder:**
```python
# OLD (treats all edges equally)
all_neighbors = list(kg.graph.neighbors("UserService"))

# NEW (filters by confidence)
high_conf_neighbors = kg.get_high_confidence_neighbors(
    "UserService",
    min_confidence=0.8  # Only explicit relationships
)
```

**Benefits:**
- ✅ KG doesn't hallucinate relationships
- ✅ Context builder can filter by confidence
- ✅ Low-confidence edges still available for exploration
- ✅ Evidence trails for debugging

---

### **3. Pattern Mining False Positives** ⚠️

**Problem:**
```python
# Pattern Miner detects "Singleton"
class Config:
    instance = None  # ← Only one instance in repo!
    
    def __init__(self):
        Config.instance = self

# Pattern Miner: "This is a Singleton! 🎉"
# Reality: It's just a regular class that happens to have one instance.
```

**Result:**
```
Context Builder adds: "Project uses Singleton pattern for Config"
Model generates: "Following the Singleton pattern, create..."
User: "WTF, I don't use Singletons!" 😡
```

**Root cause:** Pattern detection is like horoscopes - finds patterns everywhere!

---

#### **IMMEDIATE FIX (30 minutes):**

Add confidence + weight to pattern detection:

**File:** `backend/services/pattern_mining.py`

```python
class PatternMiner:
    
    def detect_singleton(self, class_node: ast.ClassDef) -> Optional[Dict]:
        """Detect Singleton with confidence scoring."""
        has_instance_var = False
        has_get_instance = False
        has_private_init = False
        
        for node in ast.walk(class_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if hasattr(target, 'id') and target.id == 'instance':
                        has_instance_var = True
            
            if isinstance(node, ast.FunctionDef):
                if node.name == 'get_instance':
                    has_get_instance = True
                if node.name == '__init__' and node.name.startswith('_'):
                    has_private_init = True
        
        # Calculate confidence
        confidence = 0.0
        if has_instance_var:
            confidence += 0.3
        if has_get_instance:
            confidence += 0.5  # Strong signal
        if has_private_init:
            confidence += 0.2
        
        if confidence < 0.6:
            return None  # Don't report low-confidence patterns
        
        return {
            "pattern": "Singleton",
            "class": class_node.name,
            "confidence": confidence,
            "evidence": {
                "instance_var": has_instance_var,
                "get_instance": has_get_instance,
                "private_init": has_private_init
            }
        }
```

**File:** `backend/services/context_builder.py`

```python
def _assemble_context(self, context: Dict[str, Any]) -> str:
    parts = []
    
    # ... universal context, meeting notes ...
    
    # Add Pattern Mining with LOW WEIGHT
    if "patterns" in context.get("sources", {}):
        pattern_source = context["sources"]["patterns"]
        
        # Filter: only high-confidence patterns
        high_conf_patterns = [
            p for p in pattern_source.get("patterns", [])
            if p.get("confidence", 0.5) >= 0.7
        ]
        
        if high_conf_patterns:
            parts.append("\n=== DESIGN PATTERNS (Advisory) ===\n")
            parts.append("Note: These are suggestions based on code analysis, not requirements.\n")
            
            for pattern in high_conf_patterns[:5]:  # Limit to 5
                parts.append(f"  - {pattern['pattern']} (confidence: {pattern['confidence']:.2f})")
            
            parts.append("\n")
```

**Key Change:** Patterns are **advisory**, not gospel!

---

### **4. Validation Scoring Drift** 📊

**Problem:**
```python
# ERD Validator: "Completeness" = has entities + relationships (20 points)
result = validate_erd(artifact)
# Score: 85/100 ✅

# Sequence Diagram Validator: uses SAME "Completeness" check!
result = validate_sequence_diagram(artifact)
# But "completeness" means different things!
# ERD: entities + relationships
# Sequence: actors + messages + lifelines
```

**Result:** Validation scores aren't comparable across artifact types

---

#### **IMMEDIATE FIX (1 hour):**

Artifact-specific validator weights:

**File:** `backend/services/validation_service.py`

```python
# Validation weights per artifact type
ARTIFACT_WEIGHTS = {
    "mermaid_erd": {
        "syntax": 15,
        "completeness": 25,  # Entities + relationships critical
        "semantic": 20,
        "context_alignment": 20,
        "best_practices": 10,
        "security": 5,
        "consistency": 3,
        "formatting": 2
    },
    "mermaid_sequence": {
        "syntax": 15,
        "completeness": 20,  # Actors + messages
        "semantic": 25,  # Flow logic critical
        "context_alignment": 20,
        "best_practices": 10,
        "security": 3,  # Less critical
        "consistency": 5,
        "formatting": 2
    },
    "code_prototype": {
        "syntax": 20,  # Code must compile
        "completeness": 15,
        "semantic": 20,
        "context_alignment": 15,
        "best_practices": 15,
        "security": 10,  # Very critical
        "consistency": 3,
        "formatting": 2
    },
    # ... more artifact types
}

class ArtifactValidator:
    
    def validate_artifact(
        self,
        content: str,
        artifact_type: str,
        context: Dict[str, Any]
    ) -> ValidationResult:
        """Validate with artifact-specific weights."""
        
        # Get weights for this artifact type
        weights = ARTIFACT_WEIGHTS.get(
            artifact_type,
            ARTIFACT_WEIGHTS["default"]  # Fallback
        )
        
        # Run validators
        results = {
            "syntax": self._validate_syntax(content, artifact_type),
            "completeness": self._validate_completeness(content, artifact_type),
            # ... more validators
        }
        
        # Calculate weighted score
        total_score = 0.0
        for validator_name, weight in weights.items():
            validator_score = results.get(validator_name, 0.0)
            weighted_score = (validator_score / 100.0) * weight
            total_score += weighted_score
        
        return ValidationResult(
            score=total_score,
            is_valid=total_score >= 60,
            details=results,
            weights_used=weights
        )
```

**Benefits:**
- ✅ ERD focuses on entities/relationships
- ✅ Code focuses on syntax/security
- ✅ Sequence focuses on flow logic
- ✅ Scores are now comparable within artifact type

---

### **5. Mega-Context Token Bloat** 💥

**Problem:**
```
Universal Context (5000 tokens)
  + Targeted RAG (18 snippets × 500 tokens = 9000 tokens)
  + KG insights (1000 tokens)
  + Pattern Mining (500 tokens)
  + Meeting Notes (500 tokens)
  = 16,000 tokens total!

Local 7B model context window: 4096 tokens 😱
Model chokes, generates garbage, or just repeats prompt.
```

**Real-World:**
- GPT-4: 128k context (fine)
- Gemini 2.0: 1M context (fine)
- deepseek-coder:7b: 16k context (MIGHT be okay)
- codellama:7b: 4k context (WILL FAIL)

---

#### **IMMEDIATE FIX (1 hour): Budget-Aware Context Assembly**

**File:** `backend/services/context_builder.py`

```python
class ContextBuilder:
    
    # Token budgets per model size
    CONTEXT_BUDGETS = {
        "7b": 3000,   # Leave room for generation
        "13b": 6000,
        "34b": 12000,
        "70b": 24000,
        "cloud": 50000  # Cloud models have huge context
    }
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 chars)."""
        return len(text) // 4
    
    def _compress_universal_context(
        self, 
        universal_ctx: Dict[str, Any],
        budget: int
    ) -> str:
        """
        Compress universal context into a concise summary.
        
        Instead of full context (5000 tokens), create a gist (500-1000 tokens).
        """
        key_entities = universal_ctx.get("key_entities", [])[:10]
        project_dirs = universal_ctx.get("project_directories", [])
        total_files = universal_ctx.get("total_files", 0)
        
        summary = f"""Project: {', '.join([Path(d).name for d in project_dirs])}
Files: {total_files}
Key Components: {', '.join([e.get('name', '') for e in key_entities[:5]])}
"""
        return summary
    
    async def build_context_with_budget(
        self,
        meeting_notes: str,
        artifact_type: str,
        model_size: str = "7b",  # ← NEW: model size parameter
        **kwargs
    ) -> Dict[str, Any]:
        """
        Build context respecting token budget for model size.
        """
        # Get budget
        budget = self.CONTEXT_BUDGETS.get(model_size, 3000)
        logger.info(f"Building context with {budget} token budget for {model_size} model")
        
        # Start with meeting notes (always include)
        tokens_used = self._estimate_tokens(meeting_notes)
        remaining_budget = budget - tokens_used
        
        # Get universal context (compressed)
        universal = await self.universal_context_service.get_universal_context()
        universal_summary = self._compress_universal_context(universal, remaining_budget // 3)
        tokens_used += self._estimate_tokens(universal_summary)
        remaining_budget = budget - tokens_used
        
        # Get RAG snippets (budget-aware)
        max_snippets = remaining_budget // 500  # Assume 500 tokens per snippet
        max_snippets = min(max_snippets, 18)  # Cap at 18
        
        logger.info(f"Budget allows {max_snippets} RAG snippets")
        
        targeted_snippets = await self.rag_retriever.retrieve(
            query=meeting_notes,
            k=max_snippets,
            artifact_type=artifact_type
        )
        
        # Add snippets until budget exhausted
        selected_snippets = []
        for snippet in targeted_snippets:
            snippet_tokens = self._estimate_tokens(snippet["content"])
            if tokens_used + snippet_tokens > budget:
                break  # Stop adding, budget exhausted
            
            selected_snippets.append(snippet)
            tokens_used += snippet_tokens
        
        logger.info(f"Selected {len(selected_snippets)} snippets, {tokens_used}/{budget} tokens used")
        
        # Assemble context
        return {
            "meeting_notes": meeting_notes,
            "universal_summary": universal_summary,  # ← Compressed!
            "snippets": selected_snippets,  # ← Budget-filtered
            "tokens_used": tokens_used,
            "tokens_budget": budget
        }
```

**Usage in Generation Service:**
```python
# Detect model size
if "7b" in model_name or "8b" in model_name:
    model_size = "7b"
elif "13b" in model_name:
    model_size = "13b"
else:
    model_size = "cloud"

# Build context with budget
context = await context_builder.build_context_with_budget(
    meeting_notes=meeting_notes,
    artifact_type=artifact_type,
    model_size=model_size  # ← Budget-aware!
)
```

**Benefits:**
- ✅ 7B models get condensed context (3k tokens)
- ✅ 70B/cloud models get full context (50k tokens)
- ✅ No more "model chokes on huge prompt"
- ✅ Prioritizes meeting notes + high-relevance snippets

---

## 🚀 SPICY UPGRADES (Elite Tier)

### **A) Feedback → Learning Loop** 🔥

**Concept:** Track which snippets led to successful generations.

**Implementation:**

```python
class FeedbackLearningService:
    """
    Learns from feedback to improve retrieval over time.
    """
    
    def __init__(self):
        self.snippet_scores: Dict[str, float] = {}  # file_path → score
        self.load_snippet_scores()
    
    def record_successful_generation(
        self,
        artifact: Dict,
        context_used: Dict,
        feedback_score: int  # 1-5 stars or thumbs up/down
    ):
        """
        When artifact gets positive feedback, boost snippets that were used.
        """
        if feedback_score < 4:  # Only learn from good feedback
            return
        
        snippets_used = context_used.get("snippets", [])
        
        for snippet in snippets_used:
            file_path = snippet.get("metadata", {}).get("file_path")
            if file_path:
                # Boost this file's importance
                current_score = self.snippet_scores.get(file_path, 0.5)
                new_score = min(current_score + 0.05, 1.0)  # Increment, cap at 1.0
                self.snippet_scores[file_path] = new_score
                
                logger.info(f"📈 Boosted {file_path} importance: {current_score:.2f} → {new_score:.2f}")
        
        self.save_snippet_scores()
    
    def get_learned_importance(self, file_path: str) -> float:
        """Get learned importance for a file (from feedback)."""
        return self.snippet_scores.get(file_path, 0.5)
```

**Integration with RAG:**
```python
# In RAGRetriever or UniversalContext
for snippet in results:
    file_path = snippet["metadata"]["file_path"]
    
    # Static importance (from Universal Context)
    static_importance = self.importance_scores.get(file_path, 0.5)
    
    # Learned importance (from feedback)
    learned_importance = feedback_service.get_learned_importance(file_path)
    
    # Combined: 70% static, 30% learned
    combined_importance = static_importance * 0.7 + learned_importance * 0.3
    
    snippet["importance"] = combined_importance
```

**Benefits:**
- ✅ System learns which files are actually useful
- ✅ Self-improving over time
- ✅ Project-specific adaptation

---

### **B) Diff-Aware RAG** 🔥

**Concept:** Prioritize recently modified files.

```python
class DiffAwareRAG:
    """
    Boost relevance of recently modified files.
    """
    
    def get_recent_changes(self, days: int = 7) -> Dict[str, float]:
        """
        Get files modified in last N days with recency scores.
        
        Returns:
            {file_path: recency_score (0.0-1.0)}
        """
        try:
            # Git log for last N days
            result = subprocess.run(
                ["git", "log", f"--since={days}.days.ago", "--name-only", "--pretty=format:"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            file_counts = {}
            
            for f in files:
                file_counts[f] = file_counts.get(f, 0) + 1
            
            # Normalize to 0.0-1.0
            max_count = max(file_counts.values()) if file_counts else 1
            recency_scores = {
                f: count / max_count 
                for f, count in file_counts.items()
            }
            
            return recency_scores
        
        except Exception as e:
            logger.error(f"Error getting recent changes: {e}")
            return {}
    
    def apply_recency_boost(self, snippets: List[Dict]) -> List[Dict]:
        """Boost recently modified files in retrieval results."""
        recent_changes = self.get_recent_changes(days=7)
        
        for snippet in snippets:
            file_path = snippet.get("metadata", {}).get("file_path", "")
            recency = recent_changes.get(file_path, 0.0)
            
            if recency > 0:
                # Boost score by recency
                original_score = snippet.get("score", 0.5)
                boosted_score = original_score * (1 + recency * 0.3)  # Up to +30%
                snippet["score"] = boosted_score
                snippet["recency_boost"] = recency
        
        # Re-sort by boosted scores
        snippets.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return snippets
```

**Benefits:**
- ✅ Prioritizes active development areas
- ✅ Catches recent refactors
- ✅ Context matches current work

---

### **C) Artifact Templates** 🎨

**Concept:** House style templates per project.

```python
class ArtifactTemplateService:
    """
    Manages artifact templates for consistent project style.
    """
    
    def __init__(self):
        self.templates_dir = Path("data/templates")
        self.templates_dir.mkdir(parents=True, exist_ok=True)
    
    def save_template(
        self, 
        artifact_type: str,
        template_content: str,
        metadata: Dict[str, Any]
    ):
        """
        Save an artifact as a template.
        
        Template content includes placeholders like {{ENTITIES}}, {{RELATIONSHIPS}}.
        """
        template_file = self.templates_dir / f"{artifact_type}_template.md"
        
        template_data = {
            "artifact_type": artifact_type,
            "template": template_content,
            "placeholders": self._extract_placeholders(template_content),
            "metadata": metadata,
            "created_at": datetime.now().isoformat()
        }
        
        template_file.write_text(json.dumps(template_data, indent=2), encoding='utf-8')
    
    def fill_template(
        self,
        artifact_type: str,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Fill template with context data.
        
        Example ERD template:
        ```
        erDiagram
          {{ENTITIES}}
          
          {{RELATIONSHIPS}}
        ```
        
        Filled with context:
        ```
        erDiagram
          USER ||--o{ SESSION : has
          USER ||--o{ ROLE : has
        ```
        """
        template_file = self.templates_dir / f"{artifact_type}_template.md"
        
        if not template_file.exists():
            return None  # No template, use full generation
        
        template_data = json.loads(template_file.read_text(encoding='utf-8'))
        template = template_data["template"]
        
        # Fill placeholders using LLM
        # (This is still AI-generated, but constrained by template structure)
        filled = self._fill_placeholders(template, context)
        
        return filled
```

**Benefits:**
- ✅ Consistent style across project
- ✅ Faster generation (template + fill)
- ✅ Fewer validation failures
- ✅ Better quality (template is pre-validated)

---

### **D) Local Model Specialization** 🎯

**Concept:** Tag models as "good for this repo."

```python
class ModelReputationService:
    """
    Tracks which models perform best for which repos/artifact types.
    """
    
    def __init__(self):
        self.reputations: Dict[str, Dict[str, float]] = {}  # {repo_id: {model: score}}
        self.load_reputations()
    
    def record_generation_result(
        self,
        repo_id: str,
        model_id: str,
        artifact_type: str,
        validation_score: float,
        user_feedback: Optional[int] = None  # 1-5 stars
    ):
        """Track model performance per repo."""
        if repo_id not in self.reputations:
            self.reputations[repo_id] = {}
        
        key = f"{model_id}:{artifact_type}"
        
        # Combined score: validation (70%) + user feedback (30%)
        score = validation_score * 0.7
        if user_feedback:
            score += (user_feedback / 5.0) * 100 * 0.3
        
        # Exponential moving average
        current = self.reputations[repo_id].get(key, 50.0)
        new_score = current * 0.8 + score * 0.2  # 80% old, 20% new
        
        self.reputations[repo_id][key] = new_score
        self.save_reputations()
    
    def get_best_model_for_repo(
        self,
        repo_id: str,
        artifact_type: str,
        available_models: List[str]
    ) -> str:
        """Get best model for this repo based on past performance."""
        repo_reputations = self.reputations.get(repo_id, {})
        
        # Score each available model
        model_scores = []
        for model in available_models:
            key = f"{model}:{artifact_type}"
            score = repo_reputations.get(key, 50.0)  # Default: 50/100
            model_scores.append((model, score))
        
        # Sort by score
        model_scores.sort(key=lambda x: x[1], reverse=True)
        
        best_model = model_scores[0][0]
        logger.info(f"Best model for {repo_id}/{artifact_type}: {best_model} (score: {model_scores[0][1]:.1f})")
        
        return best_model
```

**Integration:**
```python
# In model routing
repo_id = get_repo_id()
available_models = model_service.get_models_for_artifact(artifact_type)

# Get best model for THIS repo
best_model = reputation_service.get_best_model_for_repo(
    repo_id=repo_id,
    artifact_type=artifact_type,
    available_models=available_models
)

# Try best model first
models_to_try = [best_model] + [m for m in available_models if m != best_model]
```

**Benefits:**
- ✅ Learns which models work best for each repo
- ✅ Different codebases → different model preferences
- ✅ Optimizes over time

---

## 📋 Implementation Priority

### **Phase 1: Critical Fixes (1 week)**
1. ✅ Git-aware cache invalidation (Universal Context)
2. ✅ KG confidence scoring
3. ✅ Pattern mining weights (advisory)
4. ✅ Budget-aware context assembly

### **Phase 2: Advanced Fixes (2 weeks)**
5. ✅ Delta Context Layer
6. ✅ Artifact-specific validation weights
7. ✅ Feedback learning loop

### **Phase 3: Elite Upgrades (1 month)**
8. ✅ Diff-aware RAG
9. ✅ Artifact templates
10. ✅ Model reputation/specialization

---

## 🎯 Expected Impact

### **Before Fixes:**
- Universal Context stale after git changes
- KG hallucinated relationships
- Pattern Mining over-confident
- 7B models choked on huge prompts
- Validation scores not comparable

### **After Phase 1:**
- ✅ Context auto-refreshes on branch switch
- ✅ KG edges have confidence scores
- ✅ Patterns are advisory, not gospel
- ✅ 7B models get budget-appropriate context
- ✅ Validation weights per artifact type

### **After Phase 3:**
- ✅ System learns from feedback
- ✅ Prioritizes recent changes
- ✅ Consistent artifact style (templates)
- ✅ Model selection adapts to repo

**From good → production-grade → elite!** 🚀

---

**Version:** 1.0.0  
**Date:** November 24, 2025  
**Status:** Roadmap defined, Phase 1 specs ready

