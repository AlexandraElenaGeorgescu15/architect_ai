"""
Universal Architect Agent - PRODUCTION-GRADE with Advanced AI Techniques

This agent provides comprehensive analysis and generation including:
1. Repository analysis (tech stack, patterns, architecture)
2. RAG-powered context retrieval with HyDE, multi-hop reasoning
3. Multi-agent system with specialized experts
4. Advanced prompting (Chain-of-Thought, Tree-of-Thought, ReAct)
5. Quality metrics and self-improvement
6. Embedding optimization and context compression
7. Prototype generation (code + visual HTML)
8. Multiple specific diagrams with validation
9. Separate documentation (API, design, architecture)
10. JIRA task generation
11. Workflows and deployment guides
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

# RAG imports
import sys
sys.path.append(str(Path(__file__).parent.parent))
from rag.retrieve import vector_search, bm25_search, merge_rerank
from rag.utils import chroma_client, BM25Index
from rag.filters import load_cfg
from rag.cache import get_cache

# Advanced RAG imports
try:
    from rag.advanced_retrieval import get_advanced_retrieval
    ADVANCED_RAG_AVAILABLE = True
except ImportError:
    ADVANCED_RAG_AVAILABLE = False

# Multi-agent imports
try:
    from agents.multi_agent_system import get_multi_agent_system
    MULTI_AGENT_AVAILABLE = True
except ImportError:
    MULTI_AGENT_AVAILABLE = False

# Advanced prompting imports
try:
    from agents.advanced_prompting import get_advanced_prompting
    ADVANCED_PROMPTING_AVAILABLE = True
except ImportError:
    ADVANCED_PROMPTING_AVAILABLE = False

# Quality system imports
try:
    from agents.quality_metrics import get_quality_system
    QUALITY_SYSTEM_AVAILABLE = True
except ImportError:
    QUALITY_SYSTEM_AVAILABLE = False

# Monitoring imports
from monitoring import get_metrics, timer, counter, histogram

# AI client imports
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from groq import AsyncGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

@dataclass
class RepositoryAnalysis:
    """Comprehensive repository analysis"""
    tech_stacks: List[str] = field(default_factory=list)
    project_structure: Dict[str, Any] = field(default_factory=dict)
    code_patterns: Dict[str, Any] = field(default_factory=dict)
    architecture: Dict[str, Any] = field(default_factory=dict)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    team_standards: Dict[str, Any] = field(default_factory=dict)
    data_models: List[Dict[str, str]] = field(default_factory=list)
    api_endpoints: List[Dict[str, str]] = field(default_factory=list)

@dataclass
class GenerationResult:
    """Result of complete generation"""
    success: bool
    repository_analysis: Optional[RepositoryAnalysis] = None
    prototypes: Dict[str, Any] = field(default_factory=dict)
    visual_prototype: str = ""
    visualizations: Dict[str, Any] = field(default_factory=dict)
    documentation: Dict[str, Any] = field(default_factory=dict)
    jira_tasks: str = ""
    workflows: str = ""
    rag_context: str = ""
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class UniversalArchitectAgent:
    """Full-featured universal architect agent with RAG"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.client = None
        self.client_type = None
        self.rag_context = ""
        self.meeting_notes = ""
        self.feature_requirements = {}
        self.repo_analysis = None
        
        # Initialize caching
        cache_backend = self.config.get('cache_backend', 'memory')
        redis_url = self.config.get('redis_url', 'redis://localhost:6379/0')
        self.cache = get_cache(cache_backend, redis_url)
        
        # Initialize metrics
        self.metrics = get_metrics()
        
        # Initialize AI client
        self._initialize_ai_client()
        
        # Initialize RAG system
        self._initialize_rag_system()
        
        # Initialize advanced AI systems
        self._initialize_advanced_systems()
    
    def _initialize_ai_client(self):
        """Initialize AI client (supports OpenAI, Gemini, Groq)"""
        # Try Groq first (fastest and free)
        groq_key = self.config.get('groq_api_key') or os.getenv("GROQ_API_KEY")
        if groq_key and GROQ_AVAILABLE:
            self.client = AsyncGroq(api_key=groq_key)
            self.client_type = 'groq'
            print("[OK] Connected to Groq (llama-3.3-70b - FAST & FREE)")
            return
        
        # Try OpenAI
        openai_key = self.config.get('api_key') or os.getenv("OPENAI_API_KEY")
        if openai_key and OPENAI_AVAILABLE:
            self.client = AsyncOpenAI(api_key=openai_key)
            self.client_type = 'openai'
            print("[OK] Connected to OpenAI")
            return
        
        # Try Gemini
        gemini_key = self.config.get('gemini_api_key') or os.getenv("GEMINI_API_KEY")
        if gemini_key and GEMINI_AVAILABLE:
            genai.configure(api_key=gemini_key)
            self.client = genai.GenerativeModel('gemini-2.0-flash-exp')
            self.client_type = 'gemini'
            print("[OK] Connected to Gemini 2.0 Flash (FREE)")
            return
        
        print("[WARN] No AI model connected. Set GROQ_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY")
    
    def _initialize_rag_system(self):
        """Initialize RAG system"""
        try:
            self.cfg = load_cfg()
            self.chroma_client = chroma_client(self.cfg["store"]["path"])
            self.collection = self.chroma_client.get_or_create_collection("repo", metadata={"hnsw:space":"cosine"})
            print("[OK] RAG system initialized")
        except Exception as e:
            print(f"[WARN] RAG system initialization failed: {e}")
            self.cfg = None
            self.chroma_client = None
            self.collection = None
    
    def _initialize_advanced_systems(self):
        """Initialize advanced AI systems"""
        # Advanced RAG
        if ADVANCED_RAG_AVAILABLE and self.client:
            try:
                self.advanced_rag = get_advanced_retrieval(self)
                print("[OK] Advanced RAG initialized (HyDE, Multi-hop, Query Decomposition)")
            except Exception as e:
                print(f"[WARN] Advanced RAG initialization failed: {e}")
                self.advanced_rag = None
        else:
            self.advanced_rag = None
        
        # Multi-agent system
        if MULTI_AGENT_AVAILABLE and self.client:
            try:
                self.multi_agent = get_multi_agent_system(self)
                print("[OK] Multi-agent system initialized (8 specialized agents)")
            except Exception as e:
                print(f"[WARN] Multi-agent initialization failed: {e}")
                self.multi_agent = None
        else:
            self.multi_agent = None
        
        # Advanced prompting
        if ADVANCED_PROMPTING_AVAILABLE and self.client:
            try:
                self.advanced_prompting = get_advanced_prompting(self)
                print("[OK] Advanced prompting initialized (CoT, ToT, ReAct, Self-Consistency)")
            except Exception as e:
                print(f"[WARN] Advanced prompting initialization failed: {e}")
                self.advanced_prompting = None
        else:
            self.advanced_prompting = None
        
        # Quality system
        if QUALITY_SYSTEM_AVAILABLE and self.client:
            try:
                self.quality_system = get_quality_system(self)
                print("[OK] Quality system initialized (Evaluation, Improvement, Validation)")
            except Exception as e:
                print(f"[WARN] Quality system initialization failed: {e}")
                self.quality_system = None
        else:
            self.quality_system = None
    
    async def _call_ai(self, prompt: str, system_prompt: str = None) -> str:
        """Call AI model with RAG context"""
        if not self.client:
            raise Exception("No AI client available")
        
        # Include RAG context in prompt
        full_prompt = f"""
RAG RETRIEVED CONTEXT:
{self.rag_context}

USER REQUEST:
{prompt}
"""
        
        if self.client_type == 'groq':
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": full_prompt})
            
            response = await self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Fast and powerful
                messages=messages,
                temperature=0.2,
                max_tokens=8000
            )
            return response.choices[0].message.content
        
        elif self.client_type == 'openai':
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": full_prompt})
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.2
            )
            return response.choices[0].message.content
        
        elif self.client_type == 'gemini':
            full_system_prompt = f"{system_prompt}\n\n{full_prompt}" if system_prompt else full_prompt
            response = self.client.generate_content(full_system_prompt)
            return response.text
        
        else:
            raise Exception(f"Unknown client type: {self.client_type}")
    
    async def retrieve_rag_context(self, query: str, force_refresh: bool = False) -> str:
        """Retrieve relevant context using ENHANCED RAG with caching"""
        if not self.collection or not self.cfg:
            print("[WARN] RAG system not available")
            return ""
        
        # Check cache first
        if not force_refresh:
            cached_context = self.cache.get_context(query)
            if cached_context:
                self.rag_context = cached_context
                return cached_context
        
        try:
            # ENHANCED: Use query expansion and reranking if enabled
            intelligence_cfg = self.cfg.get("intelligence", {})
            
            # Step 1: Query Expansion (if enabled)
            queries = [query]
            if intelligence_cfg.get("query_expansion", {}).get("enabled", True):
                try:
                    from rag.query_processor import get_query_expander
                    expander = get_query_expander()
                    analysis = expander.analyze_query(query)
                    # Use original + expanded queries (limit to 3 total)
                    queries = [analysis.original_query] + analysis.expanded_queries[:2]
                    print(f"[OK] Expanded to {len(queries)} queries")
                except Exception as e:
                    print(f"[WARN] Query expansion failed: {e}")
                    queries = [query]
            
            # Step 2: Retrieve for all queries
            docs = self._load_docs_from_chroma()
            bm25 = BM25Index(docs)
            
            all_hits = []
            for q in queries:
                vec_hits = vector_search(self.collection, q, self.cfg["hybrid"]["k_vector"])
                bm25_hits = bm25_search(bm25, q, self.cfg["hybrid"]["k_bm25"])
                merged = merge_rerank(vec_hits, bm25_hits, self.cfg["hybrid"]["k_final"])
                all_hits.extend(merged)
            
            # Step 3: Rerank (if enabled)
            if intelligence_cfg.get("reranking", {}).get("enabled", True):
                try:
                    from rag.reranker import get_reranker
                    strategy = intelligence_cfg.get("reranking", {}).get("strategy", "hybrid")
                    top_k = intelligence_cfg.get("reranking", {}).get("top_k", 18)
                    reranker = get_reranker(strategy=strategy)
                    
                    # Convert tuples (doc, score) to dicts for reranker
                    hits_as_dicts = []
                    for hit in all_hits:
                        doc, score = hit
                        hits_as_dicts.append({
                            'content': doc.get('content', '') if isinstance(doc, dict) else str(doc),
                            'meta': doc.get('meta', {}) if isinstance(doc, dict) else {},
                            'score': float(score)
                        })
                    
                    reranked_dicts = reranker.rerank(query, hits_as_dicts, top_k=top_k)
                    
                    # Convert back to tuples (doc, score) for consistency
                    hits = [(doc, doc['final_score']) for doc in reranked_dicts]
                    print(f"[OK] Reranked to top {len(hits)} results")
                except Exception as e:
                    print(f"[WARN] Reranking failed: {e}")
                    hits = all_hits[:18]
            else:
                hits = all_hits[:18]
            
            # Step 4: Context Optimization (if enabled)
            if intelligence_cfg.get("context_optimization", {}).get("enabled", True):
                try:
                    from rag.context_optimizer import get_context_optimizer
                    max_tokens = intelligence_cfg.get("context_optimization", {}).get("max_tokens", 8000)
                    optimizer = get_context_optimizer()
                    self.rag_context = optimizer.format_context_with_budget(hits, max_tokens=max_tokens)
                    print(f"[OK] Optimized context to fit {max_tokens} tokens")
                except Exception as e:
                    print(f"[WARN] Context optimization failed: {e}")
                    # Fallback to basic formatting
                    context_parts = []
                    for i, (doc, score) in enumerate(hits, 1):
                        context_parts.append(f"---\n## Context {i} (score={score:.3f})\n")
                        context_parts.append(f"**FILE:** {doc['meta'].get('path', 'unknown')}\n")
                        context_parts.append(f"```\n{doc['content']}\n```\n")
                    self.rag_context = "\n".join(context_parts)
            else:
                # Basic formatting
                context_parts = []
                for i, (doc, score) in enumerate(hits, 1):
                    context_parts.append(f"---\n## Context {i} (score={score:.3f})\n")
                    context_parts.append(f"**FILE:** {doc['meta'].get('path', 'unknown')}\n")
                    context_parts.append(f"```\n{doc['content']}\n```\n")
                self.rag_context = "\n".join(context_parts)
            
            # Cache the result
            self.cache.set_context(query, self.rag_context, ttl=3600)
            
            print(f"[OK] Retrieved {len(hits)} relevant context snippets (ENHANCED RAG)")
            return self.rag_context
            
        except Exception as e:
            print(f"[ERROR] RAG retrieval failed: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def _load_docs_from_chroma(self):
        """Load documents from Chroma"""
        try:
            res = self.collection.get(include=["documents","metadatas","embeddings"], limit=100000)
            docs = [{"id":i, "content":d, "meta":m} for i,(d,m) in enumerate(zip(res["documents"], res["metadatas"]))]
            return docs
        except Exception as e:
            print(f"[ERROR] Failed to load docs: {e}")
            return []
    
    async def analyze_repository(self, repo_path: str = ".") -> RepositoryAnalysis:
        """Comprehensive repository analysis - ALWAYS uses deterministic detection"""
        print("[INFO] Analyzing repository...")
        
        # CRITICAL: Resolve the path to get absolute path
        repo_path = Path(repo_path).resolve()
        
        # ALWAYS use deterministic detection - it's reliable and fast
        # AI is too unreliable for tech stack detection
        analysis = self._fallback_tech_stack_detection(repo_path)
        
        # Still retrieve RAG context for other purposes (code patterns, etc.)
        # ENHANCED RAG CONTEXT: Include comprehensive project context
        await self.retrieve_rag_context("""
        components services controllers models architecture patterns
        coding style conventions naming patterns project structure
        README documentation definition of done definition of ready
        coding standards best practices design patterns
        """)
        
        self.repo_analysis = analysis
        print(f"[OK] Repository analysis complete: {len(analysis.tech_stacks)} tech stacks detected")
        print(f"[DEBUG] Final tech stacks: {analysis.tech_stacks}")
        return analysis
    
    def _fallback_tech_stack_detection(self, repo_path: Path) -> RepositoryAnalysis:
        """Deterministic tech stack detection - EXCLUDES the tool itself"""
        analysis = RepositoryAnalysis()
        
        # SMART ROOT DETECTION: Find actual project root (same logic as RAG ingest)
        search_path = repo_path
        check_path = repo_path
        
        # If we're in architect_ai_cursor_poc, ALWAYS go to parent
        if check_path.name == "architect_ai_cursor_poc" or "architect_ai" in str(check_path):
            search_path = check_path.parent.resolve()
            print(f"[DEBUG] Detected tool directory, searching parent: {search_path}")
        else:
            # Check up to 3 levels up for other cases
            for _ in range(3):
                parent = check_path.parent
                if parent != check_path:
                    subdirs = [d for d in parent.iterdir() if d.is_dir() and not d.name.startswith('.')]
                    if len(subdirs) >= 2 and check_path.name in [d.name for d in subdirs]:
                        search_path = parent
                        break
                check_path = parent
        
        print(f"[DEBUG] Searching for tech stacks in: {search_path}")
        
        # GENERIC TECH STACK DETECTION - recursively search for markers
        # BUT EXCLUDE the tool directory itself
        detected = []
        
        # Search for Angular (angular.json anywhere) - EXCLUDE tool dir
        for angular_json in search_path.rglob("angular.json"):
            angular_str = str(angular_json)
            if ("node_modules" not in angular_str and 
                "architect_ai_cursor_poc" not in angular_str and
                "rag/" not in angular_str and
                "components/" not in angular_str and
                "agents/" not in angular_str):
                detected.append(("Angular", "TypeScript", angular_json.parent))
                print(f"[DEBUG] Found Angular at: {angular_json}")
                break
        
        # Search for React (package.json with react dependency) - EXCLUDE tool dir
        for pkg_json in search_path.rglob("package.json"):
            pkg_str = str(pkg_json)
            if ("node_modules" not in pkg_str and 
                "architect_ai_cursor_poc" not in pkg_str and
                "rag/" not in pkg_str and
                "components/" not in pkg_str and
                "agents/" not in pkg_str):
                try:
                    import json
                    pkg_data = json.loads(pkg_json.read_text(encoding='utf-8'))
                    deps = {**pkg_data.get('dependencies', {}), **pkg_data.get('devDependencies', {})}
                    if 'react' in deps:
                        detected.append(("React", "TypeScript", pkg_json.parent))
                        print(f"[DEBUG] Found React at: {pkg_json}")
                        break
                    elif 'vue' in deps:
                        detected.append(("Vue", "TypeScript", pkg_json.parent))
                        print(f"[DEBUG] Found Vue at: {pkg_json}")
                        break
                except Exception:
                    pass
        
        # Search for .NET (.sln or .csproj files anywhere) - EXCLUDE tool dir
        for sln_file in search_path.rglob("*.sln"):
            sln_str = str(sln_file)
            if ("architect_ai_cursor_poc" not in sln_str and
                "rag/" not in sln_str and
                "components/" not in sln_str and
                "agents/" not in sln_str):
                detected.append((".NET", "C#", sln_file.parent))
                print(f"[DEBUG] Found .NET solution at: {sln_file}")
                break
        
        if not any(t[0] == ".NET" for t in detected):
            for csproj in search_path.rglob("*.csproj"):
                csproj_str = str(csproj)
                if ("obj" not in csproj_str and "bin" not in csproj_str and 
                    "architect_ai_cursor_poc" not in csproj_str and
                    "rag/" not in csproj_str and
                    "components/" not in csproj_str and
                    "agents/" not in csproj_str):
                    detected.append((".NET", "C#", csproj.parent))
                    print(f"[DEBUG] Found .NET project at: {csproj}")
                    break
        
        # Search for Python (requirements.txt, setup.py, pyproject.toml) - EXCLUDE tool dir
        for py_file in search_path.rglob("requirements.txt"):
            py_file_str = str(py_file)
            # EXCLUDE: tool directories, virtual envs, and the tool's own requirements.txt
            if (".venv" not in py_file_str and 
                "architect_ai_cursor_poc" not in py_file_str and
                "rag/" not in py_file_str and
                "components/" not in py_file_str and
                "agents/" not in py_file_str and
                "utils/" not in py_file_str and
                "app/" not in py_file_str and
                "monitoring/" not in py_file_str and
                "services/" not in py_file_str and
                "suggestions/" not in py_file_str and
                "tenants/" not in py_file_str and
                "validation/" not in py_file_str and
                "versioning/" not in py_file_str and
                "workers/" not in py_file_str and
                not py_file_str.endswith("architect_ai_cursor_poc/requirements.txt")):
                detected.append(("Python", "Python", py_file.parent))
                print(f"[DEBUG] Found Python project at: {py_file}")
                break
        
        # Search for Java (pom.xml, build.gradle) - EXCLUDE tool dir
        for pom in search_path.rglob("pom.xml"):
            pom_str = str(pom)
            if ("architect_ai_cursor_poc" not in pom_str and
                "rag/" not in pom_str and
                "components/" not in pom_str and
                "agents/" not in pom_str):
                detected.append(("Java", "Spring Boot", pom.parent))
                print(f"[DEBUG] Found Java/Spring project at: {pom}")
                break
        
        # Populate analysis
        for tech, lang, path in detected:
            if tech not in analysis.tech_stacks:
                analysis.tech_stacks.append(tech)
            if lang not in analysis.tech_stacks:
                analysis.tech_stacks.append(lang)
            
            # Categorize as frontend or backend
            if tech in ["Angular", "React", "Vue"]:
                analysis.project_structure["frontend"] = path.name
            elif tech in [".NET", "Java", "Spring Boot", "Python"]:
                analysis.project_structure["backend"] = path.name
        
        # Set architecture type
        has_frontend = any(t in analysis.tech_stacks for t in ["Angular", "React", "Vue"])
        has_backend = any(t in analysis.tech_stacks for t in [".NET", "Java", "Python", "Spring Boot"])
        
        if has_frontend and has_backend:
            analysis.architecture = {"type": "full-stack", "pattern": "spa-api"}
        elif has_frontend:
            analysis.architecture = {"type": "frontend", "pattern": "spa"}
        elif has_backend:
            analysis.architecture = {"type": "backend", "pattern": "api"}
        else:
            analysis.architecture = {"type": "unknown"}
        
        analysis.code_patterns = {
            "frontend": "component-based" if has_frontend else "none",
            "backend": "mvc" if has_backend else "none"
        }
        
        print(f"[DEBUG] Fallback detection found: {analysis.tech_stacks}")
        print(f"[DEBUG] Architecture: {analysis.architecture}")
        return analysis
    
    async def process_meeting_notes(self, notes_path: str) -> Dict[str, Any]:
        """Process meeting notes with RAG"""
        print("[INFO] Processing meeting notes...")
        
        notes_file = Path(notes_path)
        if not notes_file.exists():
            raise FileNotFoundError(f"Meeting notes not found: {notes_path}")
        
        self.meeting_notes = notes_file.read_text(encoding="utf-8")
        
        # Retrieve context for meeting notes
        await self.retrieve_rag_context(self.meeting_notes)
        
        if self.client:
            requirements_prompt = f"""
Extract detailed feature requirements from these meeting notes:
            
            MEETING NOTES:
            {self.meeting_notes}
            
Extract:
1. Feature name and description
2. Technology requirements
3. Specific functionality needed
4. Data models and interfaces
5. UI/UX requirements
6. API endpoints needed
7. Performance requirements
8. Testing requirements
9. Acceptance criteria
10. Team assignments

Return as detailed JSON.
            """
            
            try:
                response = await self._call_ai(
                    requirements_prompt,
                    "You are an expert business analyst. Extract comprehensive requirements using the RAG context."
                )
                self.feature_requirements = json.loads(response)
            except Exception as e:
                print(f"[WARN] Could not parse requirements: {e}")
                self.feature_requirements = {
                    "name": "extracted-feature",
                    "description": self.meeting_notes[:200],
                    "raw_response": response if 'response' in locals() else ""
            }
        
        return self.feature_requirements
    
    async def generate_prototype_code(self, feature_name: str) -> Dict[str, Any]:
        """Generate code prototype"""
        print("[INFO] Generating code prototype...")
        
        # CRITICAL: Analyze repository FIRST if not already done
        if not self.repo_analysis:
            print("[INFO] Repository not analyzed yet, analyzing now...")
            await self.analyze_repository()
        
        # ENHANCED RAG CONTEXT: Include coding style, conventions, architecture patterns
        await self.retrieve_rag_context(f"""
        prototype {feature_name} implementation code patterns components services API controller backend
        coding style conventions architecture patterns design patterns
        README documentation definition of done definition of ready
        coding standards best practices naming conventions
        project structure folder organization file naming
        """)
        
        # Detect tech stacks to be explicit about what to generate
        tech_stacks = self.repo_analysis.tech_stacks if self.repo_analysis else []
        has_frontend = any(tech in str(tech_stacks).lower() for tech in ['angular', 'react', 'vue', 'typescript'])
        has_dotnet = any(tech in str(tech_stacks).lower() for tech in ['.net', 'csharp', 'c#', 'asp.net'])
        has_backend = has_dotnet or any(tech in str(tech_stacks).lower() for tech in ['spring', 'fastapi', 'django', 'express', 'flask'])
        
        print(f"[DEBUG] Tech stacks detected: {tech_stacks}")
        print(f"[DEBUG] Has frontend: {has_frontend}, Has .NET backend: {has_dotnet}, Has any backend: {has_backend}")
        
        prompt = f"""
Generate a COMPLETE, PRODUCTION-READY code prototype for: {feature_name}

🚨 CRITICAL REQUIREMENT 🚨
This repository has BOTH frontend AND backend:
- Frontend: {tech_stacks if has_frontend else 'Angular/TypeScript detected in codebase'}
- Backend: {'.NET/C#' if has_dotnet else 'Backend framework detected in codebase'}

YOU MUST GENERATE FILES FOR **BOTH** FRONTEND AND BACKEND!

REQUIREMENTS:
{json.dumps(self.feature_requirements, indent=2)}

REPOSITORY ANALYSIS:
Tech Stacks: {tech_stacks}
Architecture: {self.repo_analysis.architecture if self.repo_analysis else {}}
Patterns: {self.repo_analysis.code_patterns if self.repo_analysis else {}}
Dependencies: {self.repo_analysis.dependencies if self.repo_analysis else {}}
Team Standards: {self.repo_analysis.team_standards if self.repo_analysis else {}}

RAG CONTEXT FROM YOUR REPOSITORY:
{self.rag_context}

CRITICAL - STUDY THE RAG CONTEXT ABOVE:
The RAG context contains ACTUAL CODE from your repository. Study it carefully to:
1. Match the EXACT coding style (indentation, naming conventions, etc.)
2. Follow the SAME patterns (how components are structured, how services are organized)
3. Use the SAME libraries and imports
4. Follow the SAME file organization
5. Match the SAME architectural patterns
6. Use the SAME error handling approaches
7. Follow the SAME documentation style

CRITICAL REQUIREMENTS:
1. Use the EXACT tech stack from the repository
2. Follow the EXACT patterns and conventions found in the codebase
3. Generate COMPLETE, WORKING code - not snippets or placeholders
4. Include ALL necessary files with full implementations
5. Add comprehensive comments explaining the code
6. Include realistic mock data
7. Add proper error handling and validation
8. Follow best practices for the tech stack

OUTPUT FORMAT - CRITICAL:
For each file, use this EXACT structure:
=== FILE: path/to/file.ext ===
[complete file content]
=== END FILE ===

🚨 MANDATORY FILES - YOU MUST GENERATE ALL OF THESE 🚨

{'### FRONTEND FILES (Angular/TypeScript) ###' if has_frontend else ''}
{'=== FILE: frontend/src/app/components/feature.component.ts ===' if has_frontend else ''}
{'=== FILE: frontend/src/app/components/feature.component.html ===' if has_frontend else ''}
{'=== FILE: frontend/src/app/services/feature.service.ts ===' if has_frontend else ''}

{'### BACKEND FILES (.NET/C#) - MANDATORY! ###' if has_dotnet else ''}
{'🚨 REQUIRED: You MUST generate these backend files:' if has_dotnet else ''}
{'=== FILE: backend/Controllers/FeatureController.cs ===' if has_dotnet else ''}
{'[Complete C# controller with endpoints]' if has_dotnet else ''}
{'=== END FILE ===' if has_dotnet else ''}

{'=== FILE: backend/Models/FeatureDto.cs ===' if has_dotnet else ''}
{'[Complete C# DTO/model classes]' if has_dotnet else ''}
{'=== END FILE ===' if has_dotnet else ''}

{'=== FILE: backend/Services/FeatureService.cs ===' if has_dotnet else ''}
{'[Complete C# service with business logic]' if has_dotnet else ''}
{'=== END FILE ===' if has_dotnet else ''}

{'=== FILE: backend/Data/FeatureRepository.cs ===' if has_dotnet else ''}
{'[Complete C# repository for data access]' if has_dotnet else ''}
{'=== END FILE ===' if has_dotnet else ''}

EXAMPLE STRUCTURE:
=== FILE: backend/Controllers/PhoneSwapController.cs ===
using Microsoft.AspNetCore.Mvc;
using YourNamespace.Services;
using YourNamespace.Models;

namespace YourNamespace.Controllers
{{{{
    [ApiController]
    [Route("api/[controller]")]
    public class PhoneSwapController : ControllerBase
    {{{{
        private readonly IPhoneSwapService _service;
        
        [HttpPost("request")]
        public async Task<IActionResult> CreateRequest([FromBody] PhoneSwapRequestDto request)
        {{{{
            // Implementation
        }}}}
    }}}}
}}}}
=== END FILE ===

ALWAYS include:
=== FILE: README.md ===
(setup instructions for BOTH frontend and backend)
=== END FILE ===

🎯 CHECKLIST BEFORE SUBMITTING:
- [ ] Generated at least 3 frontend files (.ts, .html, .scss)
- [ ] Generated at least 4 backend files (Controller, Model, Service, Repository)
- [ ] All files have complete implementations (no placeholders)
- [ ] Backend files use C# and .NET conventions
- [ ] Frontend files use Angular/TypeScript conventions

Make it DETAILED and COMPLETE - this should be ready to copy-paste and run!
        """
        
        # Build system prompt based on detected stacks
        system_prompt = "You are an expert full-stack developer. "
        if has_frontend and has_dotnet:
            system_prompt += "This is a FULL-STACK project with Angular frontend and .NET backend. YOU MUST generate files for BOTH. "
        elif has_frontend and has_backend:
            system_prompt += "This is a FULL-STACK project with frontend and backend. YOU MUST generate files for BOTH. "
        system_prompt += "Generate COMPLETE, production-ready code with NO placeholders. Follow the exact file format with === FILE: === markers."
        
        response = await self._call_ai(prompt, system_prompt)
        
        return {
            "type": "code_prototype",
            "code": response,
            "feature_name": feature_name
        }
    
    async def generate_visual_prototype(self, feature_name: str) -> str:
        """Generate interactive visual prototype"""
        print("[INFO] Generating visual prototype...")
        
        # CRITICAL: Analyze repository FIRST if not already done
        if not self.repo_analysis:
            print("[INFO] Repository not analyzed yet, analyzing now...")
            await self.analyze_repository()
        
        # ENHANCED RAG CONTEXT: Include UI/UX patterns, design system, styling conventions
        await self.retrieve_rag_context(f"""
        UI design prototype interface components styling {feature_name}
        design system UI patterns UX conventions styling guidelines
        component library theme colors typography spacing
        responsive design mobile patterns accessibility
        """)
        
        prompt = f"""
Generate a BEAUTIFUL, FULLY FUNCTIONAL visual prototype for: {feature_name}

REQUIREMENTS:
{json.dumps(self.feature_requirements, indent=2)}

REPOSITORY ANALYSIS:
Tech Stacks: {self.repo_analysis.tech_stacks if self.repo_analysis else []}
UI Framework: {[stack for stack in (self.repo_analysis.tech_stacks if self.repo_analysis else []) if stack.lower() in ['angular', 'react', 'vue', 'streamlit', 'blazor']]}
Styling: {self.repo_analysis.code_patterns.get('styling', 'CSS') if self.repo_analysis else 'CSS'}

RAG CONTEXT FROM YOUR REPOSITORY:
{self.rag_context}

CRITICAL - STUDY THE RAG CONTEXT ABOVE:
The RAG context contains ACTUAL UI CODE from your repository. Study it carefully to:
1. Match the EXACT UI framework and patterns (Angular components, React hooks, etc.)
2. Follow the SAME styling approach (SCSS, CSS modules, styled-components, etc.)
3. Use the SAME component structure and organization
4. Match the SAME naming conventions for classes, IDs, variables
5. Follow the SAME layout patterns (grid, flexbox, etc.)
6. Use the SAME color scheme and design tokens
7. Match the SAME interaction patterns (how buttons work, form validation, etc.)
8. Follow the SAME file structure for UI components

DESIGN REQUIREMENTS:
1. **Modern UI/UX**: Use modern design principles (Material Design, Tailwind-style, Streamlit, or Bootstrap depending on the tech stack)
2. **Professional Look**: Clean, polished, production-ready appearance
3. **Fully Interactive**: All buttons, forms, and interactions should work
4. **Realistic Data**: Include realistic mock data that demonstrates the feature
5. **Responsive**: Mobile-first, works on all screen sizes
6. **Complete**: Not a wireframe - a fully styled, working prototype

MUST INCLUDE:
- Beautiful color scheme and typography
- Proper spacing and layout
- Icons (use Font Awesome CDN or similar)
- Smooth animations and transitions
- Form validation (if applicable)
- Loading states and feedback
- Error handling UI
- Success messages
- Realistic mock data in the UI

TECHNICAL REQUIREMENTS:
- Single prototype file (depending on the tech stack)
- Use CDN for any libraries (Bootstrap, Tailwind, Font Awesome, Streamlit, etc.)
- Include comments explaining key sections
- Make it look like a real production app, not a demo

OUTPUT: Make it a complete, working prototype that demonstrates the feature.
Include realistic mock data and make it visually appealing.
"""
        
        response = await self._call_ai(
            prompt,
            "You are an expert frontend developer. Generate a complete, working HTML prototype."
        )
        
        return response
    
    def _clean_diagram_output(self, diagram_text: str) -> str:
        """Clean diagram output - AGGRESSIVE cleaning to ensure valid Mermaid"""
        import re
        
        # Remove markdown code blocks
        diagram_text = re.sub(r'```mermaid\s*\n?', '', diagram_text)
        diagram_text = re.sub(r'```\s*$', '', diagram_text)
        diagram_text = diagram_text.replace("```", "")
        
        # Split into lines
        lines = [l.strip() for l in diagram_text.strip().split('\n')]
        cleaned_lines = []
        diagram_type = None
        header_count = 0
        
        for line in lines:
            if not line or line.startswith('%%'):  # Skip empty and comments
                continue
            
            # Detect and enforce SINGLE diagram header
            if line.startswith('graph '):
                if header_count == 0:
                    cleaned_lines.append(line)
                    diagram_type = 'graph'
                    header_count += 1
                # else: skip duplicate header
                continue
            elif line.startswith('sequenceDiagram'):
                if header_count == 0:
                    cleaned_lines.append(line)
                    diagram_type = 'sequence'
                    header_count += 1
                # else: skip duplicate header
                continue
            elif line.startswith('flowchart '):
                if header_count == 0:
                    cleaned_lines.append(line)
                    diagram_type = 'flowchart'
                    header_count += 1
                # else: skip duplicate header
                continue
            
            # Skip invalid syntax
            if any(keyword in line.lower() for keyword in ['subgraph', 'style ', 'classdef', 'click ']):
                continue
            
            # Skip lines that don't look like diagram syntax
            if diagram_type in ['graph', 'flowchart']:
                if not any(marker in line for marker in ['-->', '[', '{', '|', '(']):
                    continue
            elif diagram_type == 'sequence':
                if not any(marker in line for marker in ['->>', '-->', 'participant', 'actor']):
                    continue
            
            # Fix double braces {{...}} -> {...}
            line = re.sub(r'\{\{([^}]+)\}\}', r'{\1}', line)
            
            cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines).strip()
        
        # Final validation: ensure we have a header
        if not any(result.startswith(t) for t in ['graph ', 'sequenceDiagram', 'flowchart ']):
            # Prepend default header
            result = f"graph TD\n{result}"
        
        return result
    
    # =============================================================================
    # GRANULAR GENERATION METHODS (for cost optimization)
    # =============================================================================
    
    async def generate_erd_only(self) -> Optional[str]:
        """Generate ONLY ERD diagram (granular generation)"""
        from rag.erd_generator import get_erd_generator
        
        erd_gen = get_erd_generator()
        
        if not erd_gen.should_generate_erd(self.meeting_notes):
            return None
        
        print("[INFO] Generating ERD diagram only...")
        # ENHANCED RAG CONTEXT: Include data modeling patterns and conventions
        await self.retrieve_rag_context("""
        database schema tables entities relationships models data
        data modeling patterns naming conventions database design
        entity relationships cardinality constraints
        """)
        
        prompt = erd_gen.generate_erd_prompt(self.meeting_notes, self.rag_context)
        response = await self._call_ai(
            prompt,
            "Generate ONLY the ERD diagram in Mermaid format. Start with 'erDiagram'."
        )
        
        return self._clean_diagram_output(response)
    
    async def generate_architecture_only(self) -> str:
        """Generate ONLY system architecture diagram (granular generation)"""
        print("[INFO] Generating architecture diagram only...")
        # ENHANCED RAG CONTEXT: Include architectural patterns and design decisions
        await self.retrieve_rag_context("""
        system architecture components services infrastructure
        architectural patterns design decisions technology choices
        microservices patterns service boundaries API design
        """)
        
        prompt = f"""
Generate a system architecture diagram showing the high-level components and their relationships.

REQUIREMENTS: {self.feature_requirements}
TECH STACK: {self.repo_analysis.tech_stacks if self.repo_analysis else []}

RAG CONTEXT: {self.rag_context}

OUTPUT: Mermaid graph diagram (start with 'graph TD'), max 8 nodes, show component relationships.
"""
        response = await self._call_ai(prompt, "Generate ONLY the diagram. Start with 'graph TD'.")
        return self._clean_diagram_output(response)
    
    async def generate_api_docs_only(self) -> str:
        """Generate ONLY API documentation (granular generation)"""
        print("[INFO] Generating API documentation only...")
        # ENHANCED RAG CONTEXT: Include API design patterns and conventions
        await self.retrieve_rag_context("""
        API endpoints routes controllers services REST
        API design patterns REST conventions HTTP methods
        request response patterns error handling authentication
        """)
        
        prompt = f"""
Generate comprehensive API documentation.

REQUIREMENTS: {self.feature_requirements}
RAG CONTEXT: {self.rag_context}

Include:
1. API Overview
2. Base URL
3. Authentication
4. Endpoints (method, path, description, request/response)
5. Error codes
6. Rate limiting

Match the style and patterns from the RAG context above.
"""
        response = await self._call_ai(prompt, "Generate comprehensive API documentation in Markdown.")
        return response
    
    async def generate_jira_only(self) -> str:
        """Generate ONLY JIRA tasks (granular generation)"""
        print("[INFO] Generating JIRA tasks only...")
        # ENHANCED RAG CONTEXT: Include project management context and conventions
        await self.retrieve_rag_context("""
        project management tasks stories epics
        definition of done definition of ready acceptance criteria
        user story format task estimation story points
        """)
        
        prompt = f"""
Generate JIRA-ready tasks (Epic, Stories, Subtasks).

REQUIREMENTS: {self.feature_requirements}
RAG CONTEXT: {self.rag_context}

Format:
# EPIC: [Title]
## Story 1: [Title]
### Subtask 1.1: [Title]
...

Include acceptance criteria (Given/When/Then) for each story.
Match the team's style from the RAG context.
"""
        response = await self._call_ai(prompt, "Generate JIRA tasks in Markdown format.")
        return response
    
    async def generate_workflows_only(self) -> str:
        """Generate ONLY workflows (granular generation)"""
        print("[INFO] Generating workflows only...")
        # ENHANCED RAG CONTEXT: Include development workflow patterns
        await self.retrieve_rag_context("""
        workflow CI/CD deployment testing development
        development process git workflow branching strategy
        testing strategy deployment patterns environment setup
        """)
        
        prompt = f"""
Generate development, testing, and deployment workflows.

REQUIREMENTS: {self.feature_requirements}
TECH STACK: {self.repo_analysis.tech_stacks if self.repo_analysis else []}
RAG CONTEXT: {self.rag_context}

Include:
1. Development Workflow
2. Testing Workflow
3. Deployment Workflow
4. Code Review Process

Match the team's actual workflows from the RAG context.
"""
        response = await self._call_ai(prompt, "Generate workflows in Markdown format.")
        return response
    
    async def generate_erd_diagram(self) -> Optional[str]:
        """Generate ERD diagram if database discussion detected (used in full workflow)"""
        return await self.generate_erd_only()
    
    async def generate_specific_diagrams(self) -> Dict[str, str]:
        """Generate specific diagrams for each section"""
        print("[INFO] Generating specific diagrams...")
        
        await self.retrieve_rag_context("architecture system flow data user components API")
        
        diagrams = {}
        
        # Try to generate ERD first
        erd = await self.generate_erd_diagram()
        if erd:
            diagrams['erd'] = erd
        
        # System Overview
        overview_prompt = f"""
You are a Mermaid diagram generator. Generate ONLY valid Mermaid code.

REQUIREMENTS: {self.feature_requirements}
TECH STACKS: {self.repo_analysis.tech_stacks if self.repo_analysis else []}

OUTPUT RULES (CRITICAL - FOLLOW EXACTLY):
1. First line MUST be: graph TD
2. NO markdown blocks (NO ```, NO ```mermaid)
3. NO subgraphs (NO "subgraph" keyword)
4. NO style declarations (NO "style" keyword)
5. NO classDef (NO "classDef" keyword)
6. Maximum 7 nodes (A through G)
7. Use ONLY square brackets: [Text]
8. Use ONLY --> for arrows
9. NO parentheses, NO curly braces except for decisions
10. Each line format: NodeID[Label] --> NodeID[Label]

VALID EXAMPLE:
graph TD
    A[Angular Frontend] --> B[API Server]
    B --> C[MongoDB]
    B --> D[Auth Service]
    A --> E[User Browser]

Generate a simple system overview with max 7 nodes following these EXACT rules.
"""
        raw_overview = await self._call_ai(overview_prompt, "Output ONLY the diagram. Start with 'graph TD'. No text before or after.")
        diagrams['overview'] = self._clean_diagram_output(raw_overview)
        
        # Data Flow
        dataflow_prompt = f"""
You are a Mermaid diagram generator. Generate ONLY valid Mermaid code.

REQUIREMENTS: {self.feature_requirements}

OUTPUT RULES (CRITICAL - FOLLOW EXACTLY):
1. First line MUST be: graph TD
2. NO markdown blocks (NO ```, NO ```mermaid)
3. NO subgraphs
4. NO style, NO classDef
5. Maximum 6 nodes (A through F)
6. Use ONLY square brackets: [Text]
7. Use ONLY --> for arrows
8. Show data flow: Input -> Process -> Store -> Output

VALID EXAMPLE:
graph TD
    A[User Input] --> B[Validation]
    B --> C[Process Data]
    C --> D[Save to DB]
    D --> E[Generate Response]
    E --> F[Update UI]

Generate a simple data flow with max 6 nodes following these EXACT rules.
"""
        raw_dataflow = await self._call_ai(dataflow_prompt, "Output ONLY the diagram. Start with 'graph TD'. No text before or after.")
        diagrams['dataflow'] = self._clean_diagram_output(raw_dataflow)
        
        # User Flow
        userflow_prompt = f"""
You are a Mermaid diagram generator. Generate ONLY valid Mermaid code.

REQUIREMENTS: {self.feature_requirements}

OUTPUT RULES (CRITICAL - FOLLOW EXACTLY):
1. First line MUST be: graph TD
2. NO markdown blocks (NO ```, NO ```mermaid)
3. NO subgraphs
4. NO style, NO classDef
5. Maximum 7 nodes
6. Use [Text] for actions, {{{{Text}}}} for decisions
7. Use ONLY --> for arrows, -->|Label| for conditional arrows
8. Show user journey with one decision point

VALID EXAMPLE:
graph TD
    A[Start] --> B[Login Page]
    B --> C{{{{Authenticated?}}}}
    C -->|Yes| D[Dashboard]
    C -->|No| B
    D --> E[View Content]

Generate a simple user flow with max 7 nodes following these EXACT rules.
"""
        raw_userflow = await self._call_ai(userflow_prompt, "Output ONLY the diagram. Start with 'graph TD'. No text before or after.")
        diagrams['userflow'] = self._clean_diagram_output(raw_userflow)
        
        # Component Relationships
        components_prompt = f"""
You are a Mermaid diagram generator. Generate ONLY valid Mermaid code.

REQUIREMENTS: {self.feature_requirements}
TECH STACK: {self.repo_analysis.tech_stacks if self.repo_analysis else []}

OUTPUT RULES (CRITICAL - FOLLOW EXACTLY):
1. First line MUST be: graph LR
2. NO markdown blocks (NO ```, NO ```mermaid)
3. NO subgraphs
4. NO style, NO classDef
5. Maximum 7 nodes (A through G)
6. Use ONLY square brackets: [Text]
7. Use ONLY --> for arrows
8. Show component relationships

VALID EXAMPLE:
graph LR
    A[App Component] --> B[Auth Module]
    A --> C[Data Module]
    B --> D[Auth Service]
    C --> E[Data Service]
    D --> F[HTTP Client]
    E --> F

Generate a simple component diagram with max 7 nodes following these EXACT rules.
"""
        raw_components = await self._call_ai(components_prompt, "Output ONLY the diagram. Start with 'graph LR'. No text before or after.")
        diagrams['components'] = self._clean_diagram_output(raw_components)
        
        # API Integration
        api_prompt = f"""
You are a Mermaid diagram generator. Generate ONLY valid Mermaid code.

REQUIREMENTS: {self.feature_requirements}

OUTPUT RULES (CRITICAL - FOLLOW EXACTLY):
1. First line MUST be: sequenceDiagram
2. NO markdown blocks (NO ```, NO ```mermaid)
3. NO "participant" keyword with spaces in names
4. Use simple participant names: Client, API, DB (NO SPACES!)
5. Maximum 6 interactions
6. Use ->> for requests, -->> for responses
7. Format: Participant->>Participant: Message

VALID EXAMPLE:
sequenceDiagram
    Client->>API: POST /login
    API->>DB: Verify user
    DB-->>API: User data
    API-->>Client: JWT token
    Client->>API: GET /data
    API-->>Client: Response

Generate a simple API sequence with max 6 interactions following these EXACT rules.
"""
        raw_api = await self._call_ai(api_prompt, "Output ONLY the diagram. Start with 'sequenceDiagram'. No text before or after.")
        diagrams['api'] = self._clean_diagram_output(raw_api)
        
        return diagrams
    
    async def generate_design_document(self) -> str:
        """Generate design document"""
        print("[INFO] Generating design document...")
        
        await self.retrieve_rag_context("design requirements UI UX acceptance criteria")
        
        prompt = f"""
Generate a comprehensive design document:

REQUIREMENTS: {self.feature_requirements}

REPOSITORY ANALYSIS:
Tech Stacks: {self.repo_analysis.tech_stacks if self.repo_analysis else []}
Architecture: {self.repo_analysis.architecture if self.repo_analysis else {}}
Project Structure: {self.repo_analysis.project_structure if self.repo_analysis else {}}
Team Standards: {self.repo_analysis.team_standards if self.repo_analysis else {}}

RAG CONTEXT FROM YOUR REPOSITORY:
{self.rag_context}

CRITICAL - USE THE RAG CONTEXT:
The RAG context shows how your repository is structured and what patterns you follow.
Base ALL design decisions on the actual codebase patterns shown above.

Include:
1. Feature scope and goals (aligned with repo architecture)
2. User experience design (matching existing UI patterns)
3. Data models and interfaces (following repo conventions)
4. UI/UX requirements (consistent with current design)
5. Acceptance criteria (based on repo standards)
6. Technical constraints (from actual tech stack)
7. Integration points (with existing components)
8. Success metrics

Make it specific to YOUR actual repository and follow YOUR conventions.
"""
        
        return await self._call_ai(
            prompt,
            "You are an expert UX designer and technical writer. Generate detailed design documentation."
        )
    
    async def generate_architecture_document(self) -> str:
        """Generate architecture document"""
        print("[INFO] Generating architecture document...")
        
        await self.retrieve_rag_context("architecture technical design patterns components")
        
        prompt = f"""
Generate a technical architecture document:

REQUIREMENTS: {self.feature_requirements}
        
        REPOSITORY ANALYSIS:
Tech Stacks: {self.repo_analysis.tech_stacks if self.repo_analysis else []}
Architecture: {self.repo_analysis.architecture if self.repo_analysis else {}}
Code Patterns: {self.repo_analysis.code_patterns if self.repo_analysis else {}}
Dependencies: {self.repo_analysis.dependencies if self.repo_analysis else {}}

RAG CONTEXT FROM YOUR REPOSITORY:
{self.rag_context}

CRITICAL - USE THE RAG CONTEXT:
The RAG context shows your ACTUAL architecture, components, and patterns.
Document the architecture that EXTENDS and INTEGRATES with what's shown above.

Include:
1. System overview (how it fits into existing architecture)
2. Component architecture (following existing patterns)
3. Data flow (integrating with current data layer)
4. API design (consistent with existing APIs)
5. Security (following current security patterns)
6. Performance (aligned with current approach)
7. Integration patterns (with existing services)
8. Deployment (fitting current deployment model)
9. Scalability (extending current architecture)
10. Technology decisions (justified by repo context)

Base this on YOUR actual repository architecture shown in the RAG context.
        """
        
        return await self._call_ai(
            prompt,
            "You are an expert software architect. Generate detailed technical architecture."
        )
    
    async def generate_api_documentation(self) -> str:
        """Generate API documentation"""
        print("[INFO] Generating API documentation...")
        
        await self.retrieve_rag_context("API endpoints routes controllers services")
        
        prompt = f"""
Generate comprehensive API documentation:

REQUIREMENTS: {self.feature_requirements}

REPOSITORY ANALYSIS:
Tech Stacks: {self.repo_analysis.tech_stacks if self.repo_analysis else []}
Existing API Endpoints: {self.repo_analysis.api_endpoints if self.repo_analysis else []}
Data Models: {self.repo_analysis.data_models if self.repo_analysis else []}

RAG CONTEXT FROM YOUR REPOSITORY:
{self.rag_context}

CRITICAL - USE THE RAG CONTEXT:
The RAG context shows your ACTUAL API patterns, controllers, and data models.
Follow the EXACT same patterns, naming conventions, and structure.

Include:
1. Base URL and authentication (matching existing APIs)
2. Endpoint specifications (following repo conventions)
3. Request/response examples (using actual data structures from repo)
4. Data models and schemas (consistent with existing models)
5. Error handling (following repo error patterns)
6. Rate limiting and security (matching current approach)
7. Mock data (realistic based on repo data models)
8. Integration examples (showing how to call from existing code)
9. Postman collection (formatted like existing APIs)

Base this on YOUR actual API patterns shown in the RAG context.
        """
        
        return await self._call_ai(
            prompt,
            "You are an expert API designer. Generate comprehensive API documentation."
        )
    
    async def generate_jira_tasks(self) -> str:
        """Generate JIRA-ready tasks"""
        print("[INFO] Generating JIRA tasks...")
        
        await self.retrieve_rag_context("tasks user stories epic subtasks estimates")
        
        prompt = f"""
Generate JIRA-ready tasks:

REQUIREMENTS: {self.feature_requirements}

REPOSITORY ANALYSIS:
Tech Stacks: {self.repo_analysis.tech_stacks if self.repo_analysis else []}
Team Standards: {self.repo_analysis.team_standards if self.repo_analysis else {}}
Architecture: {self.repo_analysis.architecture if self.repo_analysis else {}}

RAG CONTEXT FROM YOUR REPOSITORY:
{self.rag_context}

CRITICAL - USE THE RAG CONTEXT:
The RAG context shows your actual codebase structure and complexity.
Create tasks that are REALISTIC based on the actual code patterns shown above.

Create comprehensive JIRA tasks including:

1. EPIC:
   - Epic name and description
   - Business value
   - Story points estimate
   - Acceptance criteria

2. USER STORIES (3-5 stories):
   - As a [user], I want [goal] so that [benefit]
   - Acceptance criteria (Given/When/Then format)
   - Story points
   - Priority
   - Dependencies

3. TECHNICAL TASKS (5-10 tasks):
   - Task title and description
   - Technical details
   - Estimated hours
   - Dependencies
   - Assignee recommendations
   - Definition of done

4. SUBTASKS for each story:
   - Frontend tasks
   - Backend tasks
   - Database tasks
   - Testing tasks
   - Documentation tasks

5. SPRINT PLANNING:
   - Sprint 1 tasks
   - Sprint 2 tasks
   - Sprint 3 tasks

6. RISK ASSESSMENT:
   - Technical risks
   - Mitigation strategies

Format in Markdown with proper JIRA syntax.
Make tasks specific and actionable based on the actual requirements.
        """
        
        return await self._call_ai(
            prompt,
            "You are an expert Scrum master and project manager. Generate detailed, actionable JIRA tasks."
        )
    
    async def generate_workflows(self) -> str:
        """Generate workflows"""
        print("[INFO] Generating workflows...")
        
        await self.retrieve_rag_context("workflow deployment testing CI/CD development process")
        
        prompt = f"""
Generate comprehensive workflows:

REQUIREMENTS: {self.feature_requirements}

REPOSITORY ANALYSIS:
Tech Stacks: {self.repo_analysis.tech_stacks if self.repo_analysis else []}
Architecture: {self.repo_analysis.architecture if self.repo_analysis else {}}
Team Standards: {self.repo_analysis.team_standards if self.repo_analysis else {}}

RAG CONTEXT FROM YOUR REPOSITORY:
{self.rag_context}

CRITICAL - USE THE RAG CONTEXT:
The RAG context shows your actual development setup, build process, and team practices.
Create workflows that match YOUR actual development environment shown above.

Create detailed workflows for:

1. DEVELOPMENT WORKFLOW:
   - Local setup steps
   - Branch strategy
   - Code review process
   - Commit conventions

2. TESTING WORKFLOW:
   - Unit testing approach
   - Integration testing
   - E2E testing
   - Test data management

3. DEPLOYMENT WORKFLOW:
   - Build process
   - Environment setup
   - Deployment steps
   - Rollback procedures

4. CODE REVIEW PROCESS:
   - Review checklist
   - Approval requirements
   - Merge strategy

5. FEATURE RELEASE PROCESS:
   - Feature flags
   - Gradual rollout
   - Monitoring
   - Rollback plan

Make workflows specific to the actual tech stack and team practices.
        """
        
        return await self._call_ai(
            prompt,
            "You are an expert DevOps engineer. Generate detailed workflows."
        )
    
    async def validate_outputs(self) -> Dict[str, Any]:
        """Validate all generated outputs"""
        print("[INFO] Validating outputs...")
        
        try:
            from validation.output_validator import ArtifactValidator
            validator = ArtifactValidator()
            results = validator.validate_all_outputs("outputs/")
            
            print(f"[OK] Validation complete: {results['valid_files']}/{results['total_files']} files valid")
            print(f"[OK] Average quality: {results['average_quality']:.2f}")
            
            return results
        except Exception as e:
            print(f"[WARN] Validation failed: {e}")
            return {"error": str(e)}
    
    async def generate_code_analysis(self) -> Dict[str, Any]:
        """Generate code review and security scan reports"""
        print("[INFO] Analyzing generated code...")
        
        try:
            from analysis.security_scanner import get_security_scanner
            
            scanner = get_security_scanner()
            
            # Scan outputs directory
            security_results = scanner.scan_directory("outputs/prototypes/")
            
            # Generate analysis report
            report = f"""# Code Analysis Report

## Security Scan Results

**Overall Risk Score**: {security_results['overall_risk_score']}/100
**Files Scanned**: {security_results['scanned_files']}
**Total Vulnerabilities**: {security_results['total_vulnerabilities']}

### Vulnerabilities by Severity
- **CRITICAL**: {security_results['vulnerabilities_by_severity']['CRITICAL']}
- **HIGH**: {security_results['vulnerabilities_by_severity']['HIGH']}
- **MEDIUM**: {security_results['vulnerabilities_by_severity']['MEDIUM']}
- **LOW**: {security_results['vulnerabilities_by_severity']['LOW']}

### Top Vulnerability Types
"""
            
            for vuln_type, count in list(security_results['vulnerabilities_by_type'].items())[:10]:
                report += f"- **{vuln_type}**: {count} occurrence(s)\n"
            
            report += "\n### Prioritized Recommendations\n\n"
            for i, rec in enumerate(security_results['recommendations'][:10], 1):
                report += f"{i}. {rec}\n"
            
            # Save analysis report
            Path("outputs/analysis").mkdir(parents=True, exist_ok=True)
            Path("outputs/analysis/code_analysis.md").write_text(report, encoding="utf-8")
            
            print(f"[OK] Code analysis complete - Risk Score: {security_results['overall_risk_score']}/100")
            
            if security_results['overall_risk_score'] > 50:
                print("[WARN] ⚠️ HIGH RISK - Review security issues immediately!")
            
            return security_results
            
        except Exception as e:
            print(f"[WARN] Code analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    async def run_complete_workflow(self, meeting_notes_path: str, feature_name: str = None) -> GenerationResult:
        """Run the complete workflow with parallel execution"""
        with timer('workflow_generation_duration_seconds', feature_type=feature_name or 'default'):
            try:
                counter('workflow_generation_total', status='started')
                print("[INFO] Starting complete workflow with parallel execution...")
                start_time = datetime.now()
                
                # Step 1: Analyze repository (must run first)
                print("[STEP 1/8] Analyzing repository...")
                repo_analysis = await self.analyze_repository()
                
                # Step 2: Process meeting notes (must run second)
                print("[STEP 2/8] Processing meeting notes...")
                await self.process_meeting_notes(meeting_notes_path)
                
                # Steps 3-5: Generate prototypes and diagrams in parallel
                print("[STEP 3-5/8] Generating prototypes and diagrams (parallel)...")
                code_task = asyncio.create_task(self.generate_prototype_code(feature_name))
                visual_task = asyncio.create_task(self.generate_visual_prototype(feature_name))
                diagrams_task = asyncio.create_task(self.generate_specific_diagrams())
                
                code_prototype, visual_prototype, diagrams = await asyncio.gather(
                    code_task, visual_task, diagrams_task,
                    return_exceptions=True
                )
                
                # Handle exceptions from parallel tasks
                if isinstance(code_prototype, Exception):
                    print(f"[WARN] Code prototype generation failed: {code_prototype}")
                    code_prototype = None
                if isinstance(visual_prototype, Exception):
                    print(f"[WARN] Visual prototype generation failed: {visual_prototype}")
                    visual_prototype = None
                if isinstance(diagrams, Exception):
                    print(f"[WARN] Diagram generation failed: {diagrams}")
                    diagrams = {}
                
                # Steps 6-8: Generate documentation in parallel
                print("[STEP 6-8/8] Generating documentation (parallel)...")
                design_task = asyncio.create_task(self.generate_design_document())
                arch_task = asyncio.create_task(self.generate_architecture_document())
                api_task = asyncio.create_task(self.generate_api_documentation())
                jira_task = asyncio.create_task(self.generate_jira_tasks())
                workflows_task = asyncio.create_task(self.generate_workflows())
                
                design_doc, architecture_doc, api_doc, jira_tasks, workflows = await asyncio.gather(
                    design_task, arch_task, api_task, jira_task, workflows_task,
                    return_exceptions=True
                )
                
                # Handle exceptions from parallel tasks
                if isinstance(design_doc, Exception):
                    print(f"[WARN] Design doc generation failed: {design_doc}")
                    design_doc = None
                if isinstance(architecture_doc, Exception):
                    print(f"[WARN] Architecture doc generation failed: {architecture_doc}")
                    architecture_doc = None
                if isinstance(api_doc, Exception):
                    print(f"[WARN] API doc generation failed: {api_doc}")
                    api_doc = None
                if isinstance(jira_tasks, Exception):
                    print(f"[WARN] JIRA tasks generation failed: {jira_tasks}")
                    jira_tasks = None
                if isinstance(workflows, Exception):
                    print(f"[WARN] Workflows generation failed: {workflows}")
                    workflows = None
                
                # Save all artifacts
                await self._save_all_artifacts(
                    code_prototype, visual_prototype, diagrams,
                    design_doc, architecture_doc, api_doc,
                    jira_tasks, workflows
                )
                
                # NEW: Step 9: Validate outputs (if enabled)
                validation_results = None
                if self.cfg.get("intelligence", {}).get("validation", {}).get("enabled", True):
                    print("[STEP 9/10] Validating outputs...")
                    validation_results = await self.validate_outputs()
                
                # NEW: Step 10: Code analysis (if enabled)
                analysis_results = None
                if self.cfg.get("analysis", {}).get("security_scan", {}).get("enabled", True):
                    print("[STEP 10/10] Running security analysis...")
                    analysis_results = await self.generate_code_analysis()
                
                elapsed = (datetime.now() - start_time).total_seconds()
                histogram('workflow_generation_time_seconds', elapsed)
                counter('workflow_generation_total', status='success')
                print(f"[OK] Workflow completed in {elapsed:.1f}s (parallel execution + validation + analysis)")
                
                return GenerationResult(
                    success=True,
                    repository_analysis=repo_analysis,
                    prototypes=code_prototype,
                    visual_prototype=visual_prototype,
                    visualizations=diagrams,
                    documentation={
                        "design": design_doc,
                        "architecture": architecture_doc,
                        "api": api_doc
                    },
                    jira_tasks=jira_tasks,
                    workflows=workflows,
                    rag_context=self.rag_context,
                    metadata={
                        "generated_at": datetime.now().isoformat(),
                        "feature_name": feature_name,
                        "tech_stacks": repo_analysis.tech_stacks,
                        "rag_used": len(self.rag_context) > 0
                    }
                )
                
            except Exception as e:
                counter('workflow_generation_total', status='error')
                return GenerationResult(
                    success=False,
                    errors=[str(e)],
                    rag_context=self.rag_context
                )
    
    async def _save_all_artifacts(self, code_prototype, visual_prototype, diagrams,
                                  design_doc, architecture_doc, api_doc,
                                  jira_tasks, workflows):
        """Save all generated artifacts"""
        outputs_dir = Path("outputs")
        outputs_dir.mkdir(exist_ok=True)
        
        # Save code prototype
        if code_prototype and "code" in code_prototype:
            prototype_dir = outputs_dir / "prototypes"
            prototype_dir.mkdir(exist_ok=True)
            (prototype_dir / "prototype_code.txt").write_text(code_prototype["code"], encoding="utf-8")
        
        # Save visual prototype
        if visual_prototype:
            prototype_dir = outputs_dir / "prototypes"
            prototype_dir.mkdir(exist_ok=True)
            (prototype_dir / "visual_prototype.html").write_text(visual_prototype, encoding="utf-8")
        
        # Save diagrams with validation
        if diagrams:
            viz_dir = outputs_dir / "visualizations"
            viz_dir.mkdir(exist_ok=True)
            
            # Validate and clean all diagrams
            from rag.diagram_validator import get_diagram_validator
            validator = get_diagram_validator()
            cleaned_diagrams, validation_errors = validator.validate_diagram_set(diagrams)
            
            if validation_errors:
                print(f"[WARN] Diagram validation issues:")
                for error in validation_errors:
                    print(f"  - {error}")
            
            # Save individual diagrams and create links
            diagram_links = []
            for name, content in cleaned_diagrams.items():
                # Save cleaned diagram
                (viz_dir / f"{name}_diagram.mmd").write_text(content, encoding="utf-8")
                
                # Create Mermaid Live link with pako compression (official method)
                import base64
                import json
                import zlib
                
                # Mermaid Live Editor expects pako-compressed data
                # Format: {"code": "diagram code", "mermaid": {"theme": "default"}}
                state = {
                    "code": content,
                    "mermaid": {"theme": "default"},
                    "autoSync": True,
                    "updateDiagram": True
                }
                state_json = json.dumps(state)
                
                # Compress with zlib (pako compatible)
                compressed = zlib.compress(state_json.encode('utf-8'))
                # Base64 encode
                encoded = base64.urlsafe_b64encode(compressed).decode('utf-8')
                
                live_link = f"https://mermaid.live/edit#pako:{encoded}"
                diagram_links.append((name, live_link, content))
            
            # Create simple markdown with links to Mermaid Live
            links_md = "# 📊 View Diagrams in Mermaid Live Editor\n\n"
            links_md += "**Click the links below to view and edit your diagrams:**\n\n"
            links_md += "*Note: Diagrams are validated and cleaned before saving.*\n\n"
            for name, link, content in diagram_links:
                links_md += f"## {name.replace('_', ' ').title()} Diagram\n\n"
                links_md += f"[🔗 **Open in Mermaid Live Editor**]({link})\n\n"
                links_md += f"<details>\n<summary>View Code</summary>\n\n```mermaid\n{content}\n```\n</details>\n\n"
                links_md += "---\n\n"
            
            (viz_dir / "VIEW_DIAGRAMS.md").write_text(links_md, encoding="utf-8")
            
            # Note: Interactive HTML viewer removed - use VIEW_DIAGRAMS.md instead
            # which provides direct links to Mermaid Live Editor for better rendering
        
        # Save documentation
            docs_dir = outputs_dir / "documentation"
            docs_dir.mkdir(exist_ok=True)
            
        if design_doc:
            (docs_dir / "design.md").write_text(design_doc, encoding="utf-8")
        if architecture_doc:
            (docs_dir / "architecture.md").write_text(architecture_doc, encoding="utf-8")
        if api_doc:
            (docs_dir / "api.md").write_text(api_doc, encoding="utf-8")
        
        # Save JIRA tasks
        if jira_tasks:
            (docs_dir / "jira_tasks.md").write_text(jira_tasks, encoding="utf-8")
        
        # Save workflows
        if workflows:
            workflow_dir = outputs_dir / "workflows"
            workflow_dir.mkdir(exist_ok=True)
            (workflow_dir / "workflows.md").write_text(workflows, encoding="utf-8")
        
        # Save RAG context
        if self.rag_context:
            context_dir = outputs_dir / "context"
            context_dir.mkdir(exist_ok=True)
            (context_dir / "rag_context.md").write_text(self.rag_context, encoding="utf-8")
        
        print("[OK] All artifacts saved to outputs/ directory")
    
    # Note: _create_interactive_viewer method removed
    # HTML interactive viewer doesn't work well - use VIEW_DIAGRAMS.md instead
    
# Convenience function
async def run_universal_workflow(meeting_notes_path: str, feature_name: str = None, 
                                 openai_api_key: str = None, gemini_api_key: str = None, groq_api_key: str = None):
    """Run the complete universal workflow"""
    try:
        config = {}
        if groq_api_key:
            config["groq_api_key"] = groq_api_key
        if openai_api_key:
            config["api_key"] = openai_api_key
        if gemini_api_key:
            config["gemini_api_key"] = gemini_api_key
        
        agent = UniversalArchitectAgent(config)
        result = await agent.run_complete_workflow(meeting_notes_path, feature_name)
        
        return result
        
    except Exception as e:
        print(f"[ERROR] Workflow error: {e}")
        import traceback
        traceback.print_exc()
        return GenerationResult(
            success=False,
            errors=[f"Workflow error: {str(e)}"]
        )

if __name__ == "__main__":
    async def main():
        result = await run_universal_workflow("inputs/meeting_notes.md", "Universal Feature")
        if result.success:
            print("[SUCCESS] Complete generation finished!")
            print(f"[INFO] Check outputs/ for all artifacts")
        else:
            print("[ERROR] Generation failed:")
            for error in result.errors:
                print(f"  - {error}")
    
    asyncio.run(main())
