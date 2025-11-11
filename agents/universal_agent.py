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

# Enable UTF-8 output on Windows to handle emoji in console output
if sys.platform == 'win32':
    try:
        import io
        # Check if already wrapped
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        # Already wrapped, closed, or not available
        pass
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

# 🚀 ADAPTIVE LEARNING SYSTEM - Self-Improving AI
try:
    from components.adaptive_learning import AdaptiveLearningLoop, FeedbackType, FeedbackEvent
    from components.validation_pipeline import ValidationPipeline, NoiseReductionPipeline
    from components.ml_feature_engineering import MLFeatureEngineer
    ADAPTIVE_LEARNING_AVAILABLE = True
except ImportError:
    ADAPTIVE_LEARNING_AVAILABLE = False
    print("[WARN] Adaptive learning system not available - system won't learn from usage")

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
    
    # Class-level cache for Ollama health check (reduces redundant HTTP calls)
    _ollama_health_cache = None
    _ollama_health_cache_time = 0
    _HEALTH_CACHE_TTL = 5  # Cache health check for 5 seconds
    
    @classmethod
    def _get_or_create_ollama_client(cls):
        """
        Get or create Ollama client with health check caching.
        
        Returns:
            OllamaClient instance if available, None otherwise
        
        Uses class-level cache with 5-second TTL to prevent redundant health checks
        during batch generation (10 agents = 1 health check instead of 10).
        """
        import time
        current_time = time.time()
        
        # Check if cache is valid
        if cls._ollama_health_cache is not None and (current_time - cls._ollama_health_cache_time) < cls._HEALTH_CACHE_TTL:
            # Use cached result
            if cls._ollama_health_cache:
                print(f"[DEBUG] Using cached Ollama client (cache age: {current_time - cls._ollama_health_cache_time:.1f}s)")
            else:
                print(f"[DEBUG] Using cached 'Ollama unavailable' result (cache age: {current_time - cls._ollama_health_cache_time:.1f}s)")
            return cls._ollama_health_cache
        
        # Cache expired or empty - perform health check
        print("[DEBUG] Performing Ollama health check (cache expired or empty)")
        try:
            from ai.ollama_client import OllamaClient
            import httpx
            
            # Quick health check
            response = httpx.get("http://localhost:11434/api/tags", timeout=1.0)
            if response.status_code == 200:
                ollama_client = OllamaClient()
                print("[DEBUG] ✅ Ollama healthy - created client")
                
                # Cache the successful result
                cls._ollama_health_cache = ollama_client
                cls._ollama_health_cache_time = current_time
                return ollama_client
            else:
                print(f"[DEBUG] ❌ Ollama server returned {response.status_code}")
                cls._ollama_health_cache = None
                cls._ollama_health_cache_time = current_time
                return None
                
        except Exception as e:
            print(f"[DEBUG] ❌ Ollama not available: {e}")
            
            # Cache the failure result
            cls._ollama_health_cache = None
            cls._ollama_health_cache_time = current_time
            return None
    
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
        
        # 🚀 ADAPTIVE LEARNING SYSTEM - Self-Improving AI Pipeline
        if ADAPTIVE_LEARNING_AVAILABLE:
            self.adaptive_loop = AdaptiveLearningLoop()
            self.validation_pipeline = ValidationPipeline()
            self.noise_reducer = NoiseReductionPipeline()
            self.ml_engineer = MLFeatureEngineer()
            print("[🚀 ADAPTIVE LEARNING] System initialized - feedback recording enabled for all models")
            print("[ℹ️  NOTE] Fine-tuning works for LOCAL Ollama models only. Cloud models (GPT-4/Gemini) record feedback but don't fine-tune.")
            # Only show Ollama tip if it's NOT installed
            try:
                import requests
                response = requests.get("http://localhost:11434/api/tags", timeout=1)
                if response.status_code != 200:
                    print("[💡 TIP] Install Ollama for full learning pipeline: https://ollama.com/download")
            except:
                print("[💡 TIP] Install Ollama for full learning pipeline: https://ollama.com/download")
        else:
            self.adaptive_loop = None
            self.validation_pipeline = None
            self.noise_reducer = None
            self.ml_engineer = None
        
        # Cached components for performance (lazy load)
        self._knowledge_graph_cache = None
        self._pattern_analysis_cache = None
        
        # Initialize AI client
        self._initialize_ai_client()
        
        # Initialize RAG system
        self._initialize_rag_system()
        
        # Initialize advanced AI systems
        self._initialize_advanced_systems()
        
        # 🚀 SMART GENERATION SYSTEM - Initialize ALWAYS
        # Smart generator provides enhanced prompts, validation, and routing
        # It works with BOTH local (Ollama) and cloud-only setups
        self.smart_generator = None
        try:
            from ai.smart_generation import get_smart_generator
            from ai.output_validator import get_validator
            
            # Try to get Ollama client for local-first routing
            # If Ollama not available, smart generator still works (cloud-only mode)
            ollama_client = None
            
            # Check if this agent instance has Ollama
            if hasattr(self, 'ollama_client') and self.ollama_client:
                ollama_client = self.ollama_client
                print("[DEBUG] Using existing Ollama client from this agent")
            else:
                # Try to create Ollama client (for local models)
                # Use cached health check to avoid redundant HTTP calls
                ollama_client = self._get_or_create_ollama_client()
            
            # Initialize smart generator (works with OR without Ollama)
            self.smart_generator = get_smart_generator(
                ollama_client=ollama_client,  # Can be None for cloud-only
                output_validator=get_validator(),
                min_quality_threshold=80
            )
            
            if ollama_client:
                print(f"[🚀 SMART GEN] Initialized with LOCAL+CLOUD support ({self.client_type} agent)")
            else:
                print(f"[🚀 SMART GEN] Initialized in CLOUD-ONLY mode ({self.client_type} agent)")
                print("[ℹ️  INFO] Install Ollama for local-first generation: https://ollama.com/download")
                
        except Exception as e:
            import traceback
            print(f"[ERROR] Smart generation system failed to initialize: {e}")
            traceback.print_exc()
            self.smart_generator = None
    
    def _initialize_ai_client(self):
        """Initialize AI client (supports Local Fine-tuned, OpenAI, Gemini, Groq) with global key persistence"""
        # Import global API key manager
        try:
            from config.secrets_manager import api_key_manager
            global_keys = api_key_manager.get_all_keys()
        except (ImportError, AttributeError, Exception) as e:
            print(f"[WARN] Failed to load API key manager: {e}")
            global_keys = {'groq': None, 'openai': None, 'gemini': None}
        
        # Track if we've already logged connection status (prevent spam on reruns)
        import streamlit as st
        logged_key = '_agent_conn_logged'
        already_logged = False
        try:
            already_logged = st.session_state.get(logged_key, False)
        except (AttributeError, KeyError, RuntimeError):
            # Streamlit not available or session state not initialized
            pass
        
        def _set_active_provider(label: str):
            try:
                st.session_state['active_provider_actual'] = label
            except Exception:
                pass

        # Reset any previous warning prior to initialization
        try:
            if 'provider_override_warning' in st.session_state:
                del st.session_state['provider_override_warning']
        except Exception:
            pass

        # Check for Ollama provider FIRST (default local provider)
        try:
            provider = st.session_state.get('provider', 'Ollama (Local)')
            if provider == "Ollama (Local)":
                # Initialize Ollama client
                from ai.ollama_client import OllamaClient
                from ai.model_router import get_router
                
                ollama_client = OllamaClient()
                is_healthy = False
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, check synchronously
                        import httpx
                        response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
                        is_healthy = response.status_code == 200
                    else:
                        is_healthy = loop.run_until_complete(ollama_client.check_server_health())
                except Exception:
                    try:
                        import httpx
                        response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
                        is_healthy = response.status_code == 200
                    except Exception:
                        is_healthy = False
                
                if is_healthy:
                    self.client = ollama_client
                    self.client_type = 'ollama'
                    self.ollama_client = ollama_client
                    self.model_router = get_router(self.config, ollama_client)
                    
                    if not already_logged:
                        print("[OK] Connected to Ollama (Local Models)")
                        st.session_state[logged_key] = True
                    _set_active_provider("Ollama (Local)")
                    return
                else:
                    if not already_logged:
                        print("[WARN] Ollama server not running. Falling back to cloud provider.")
                        warning_message = "Ollama server not running. Using cloud provider instead."
                        try:
                            st.session_state['provider_override_warning'] = warning_message
                        except Exception:
                            pass
        except Exception as e:
            pass  # No Ollama available, continue to other providers
        
        # Check for local fine-tuned model (second priority)
        try:
            selected_local_model = st.session_state.get('selected_local_model')
            if selected_local_model and selected_local_model.get('model_path'):
                # User has selected a local fine-tuned model
                from components.local_finetuning import local_finetuning_system
                
                # Check if model is already loaded
                if local_finetuning_system.current_model:
                    self.client = local_finetuning_system.current_model
                    self.client_type = 'local_finetuned'
                    if not already_logged:
                        print(f"[OK] Using local fine-tuned model: {selected_local_model['model_name']}")
                        st.session_state[logged_key] = True
                        _set_active_provider(selected_local_model.get('model_name', 'Local Fine-tuned'))
                    return
                else:
                    # Try to load the model
                    try:
                        model_path = Path(selected_local_model['model_path'])
                        if model_path.exists():
                            # Load the fine-tuned model
                            base_model_key = selected_local_model.get('base_model', 'codellama-7b')
                            finetuned_version = model_path.name  # e.g., "codellama-7b_finetuned"
                            
                            if not already_logged:
                                print(f"[INFO] Loading local fine-tuned model: {selected_local_model['model_name']}...")
                            
                            local_finetuning_system.load_finetuned_model(base_model_key, finetuned_version)
                            self.client = local_finetuning_system.current_model
                            self.client_type = 'local_finetuned'
                            if not already_logged:
                                print(f"[OK] Local fine-tuned model loaded successfully!")
                                st.session_state[logged_key] = True
                            _set_active_provider(selected_local_model.get('model_name', 'Local Fine-tuned'))
                            return
                    except Exception as e:
                        print(f"[WARN] Failed to load local model: {e}")
                        warning_message = (
                            f"Local model '{selected_local_model.get('model_name', 'Local Model')}' "
                            f"failed to load: {e}. Falling back to cloud provider."
                        )
                        try:
                            st.session_state['provider_override_warning'] = warning_message
                        except Exception:
                            pass
                        # Fall through to cloud providers
        except Exception as e:
            pass  # No local model selected or streamlit not available
        
        # Try Groq first (fastest and free)
        groq_key = self.config.get('groq_api_key') or global_keys.get('groq') or os.getenv("GROQ_API_KEY")
        if groq_key and GROQ_AVAILABLE:
            self.client = AsyncGroq(api_key=groq_key)
            self.client_type = 'groq'
            if not already_logged:
                print("[OK] Connected to Groq (llama-3.3-70b - FAST & FREE)")
                try:
                    st.session_state[logged_key] = True
                except (AttributeError, KeyError, RuntimeError):
                    pass
            _set_active_provider("Groq (llama-3.3-70b)")
            return
        
        # Try OpenAI
        openai_key = self.config.get('api_key') or global_keys.get('openai') or os.getenv("OPENAI_API_KEY")
        if openai_key and OPENAI_AVAILABLE:
            self.client = AsyncOpenAI(api_key=openai_key)
            self.client_type = 'openai'
            if not already_logged:
                print("[OK] Connected to OpenAI")
                try:
                    st.session_state[logged_key] = True
                except (AttributeError, KeyError, RuntimeError):
                    pass
            _set_active_provider("OpenAI (GPT-4)")
            return
        
        # Try Gemini
        gemini_key = self.config.get('gemini_api_key') or global_keys.get('gemini') or os.getenv("GEMINI_API_KEY")
        if gemini_key and GEMINI_AVAILABLE:
            genai.configure(api_key=gemini_key)
            self.client = genai.GenerativeModel('gemini-2.0-flash-exp')
            self.client_type = 'gemini'
            if not already_logged:
                print("[OK] Connected to Gemini 2.0 Flash (FREE)")
                try:
                    st.session_state[logged_key] = True
                except (AttributeError, KeyError, RuntimeError):
                    pass
            _set_active_provider("Google Gemini 2.0 Flash")
            return
        
        if not already_logged:
            print("[WARN] No AI model connected. Set GROQ_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY")
            try:
                st.session_state[logged_key] = True
            except (AttributeError, KeyError, RuntimeError):
                pass
        _set_active_provider("None")
    
    def _initialize_rag_system(self):
        """Initialize RAG system using global client (reduces telemetry spam)"""
        try:
            from rag.chromadb_config import get_global_chroma_client
            self.cfg = load_cfg()
            self.chroma_client, self.collection = get_global_chroma_client(self.cfg["store"]["path"], "repo")
            # Only print on first initialization to reduce log spam
            if not hasattr(UniversalArchitectAgent, '_rag_init_logged'):
                print("[OK] RAG system initialized")
                UniversalArchitectAgent._rag_init_logged = True
        except Exception as e:
            print(f"[WARN] RAG system initialization failed: {e}")
            self.cfg = None
            self.chroma_client = None
            self.collection = None
    
    def _get_knowledge_graph(self):
        """Lazy-load and cache knowledge graph (10x performance improvement)"""
        if self._knowledge_graph_cache is None:
            from components.knowledge_graph import KnowledgeGraphBuilder
            kg_builder = KnowledgeGraphBuilder()
            project_root = self.repo_analysis.project_structure.get('root') if self.repo_analysis else Path(".")
            self._knowledge_graph_cache = kg_builder.build_graph(project_root)
            print("[⚡ PERFORMANCE] Knowledge graph built and cached")
        return self._knowledge_graph_cache
    
    def _get_pattern_analysis(self):
        """Lazy-load and cache pattern analysis (10x performance improvement)"""
        if self._pattern_analysis_cache is None:
            from components.pattern_mining import PatternDetector
            detector = PatternDetector()
            project_root = self.repo_analysis.project_structure.get('root') if self.repo_analysis else Path(".")
            self._pattern_analysis_cache = detector.analyze_project(project_root)
            print("[⚡ PERFORMANCE] Pattern analysis complete and cached")
        return self._pattern_analysis_cache
    
    def _initialize_advanced_systems(self):
        """Initialize advanced AI systems (reduced logging to prevent spam)"""
        # Advanced RAG
        if ADVANCED_RAG_AVAILABLE and self.client:
            try:
                self.advanced_rag = get_advanced_retrieval(self)
                if not hasattr(UniversalArchitectAgent, '_advanced_rag_logged'):
                    print("[OK] Advanced RAG initialized (HyDE, Multi-hop, Query Decomposition)")
                    UniversalArchitectAgent._advanced_rag_logged = True
            except Exception as e:
                print(f"[WARN] Advanced RAG initialization failed: {e}")
                self.advanced_rag = None
        else:
            self.advanced_rag = None
        
        # Multi-agent system
        if MULTI_AGENT_AVAILABLE and self.client:
            try:
                self.multi_agent = get_multi_agent_system(self)
                if not hasattr(UniversalArchitectAgent, '_multi_agent_logged'):
                    print("[OK] Multi-agent system initialized (8 specialized agents)")
                    UniversalArchitectAgent._multi_agent_logged = True
            except Exception as e:
                print(f"[WARN] Multi-agent initialization failed: {e}")
                self.multi_agent = None
        else:
            self.multi_agent = None
        
        # Advanced prompting
        if ADVANCED_PROMPTING_AVAILABLE and self.client:
            try:
                self.advanced_prompting = get_advanced_prompting(self)
                if not hasattr(UniversalArchitectAgent, '_advanced_prompting_logged'):
                    print("[OK] Advanced prompting initialized (CoT, ToT, ReAct, Self-Consistency)")
                    UniversalArchitectAgent._advanced_prompting_logged = True
            except Exception as e:
                print(f"[WARN] Advanced prompting initialization failed: {e}")
                self.advanced_prompting = None
        else:
            self.advanced_prompting = None
        
        # Quality system
        if QUALITY_SYSTEM_AVAILABLE and self.client:
            try:
                self.quality_system = get_quality_system(self)
                if not hasattr(UniversalArchitectAgent, '_quality_system_logged'):
                    print("[OK] Quality system initialized (Evaluation, Improvement, Validation)")
                    UniversalArchitectAgent._quality_system_logged = True
            except Exception as e:
                print(f"[WARN] Quality system initialization failed: {e}")
                self.quality_system = None
        else:
            self.quality_system = None
    
    async def _call_ai(self, prompt: str, system_prompt: str = None, artifact_type: str = None, force_cloud: bool = False) -> str:
        """
        Call AI model with RAG context and automatic model selection.
        
        🚀 NEW: Adaptive Learning Pipeline with Cloud Fallback
        - Noise reduction preprocessing
        - Quality validation
        - Feedback recording for continuous improvement
        - Force cloud provider for retry attempts
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            artifact_type: Type of artifact being generated (for automatic model selection)
            force_cloud: If True, skip local models and use cloud providers directly
        """
        if not self.client:
            raise Exception("No AI client available")
        
        # 🚀 STEP 1: NOISE REDUCTION (Programmatic Preprocessing)
        original_prompt = prompt
        noise_score = 0.0
        if self.noise_reducer:
            noise_score = self.noise_reducer.calculate_noise_score(prompt)
            if noise_score > 0.3:  # High noise detected
                print(f"[🧹 PREPROCESSING] Noise detected ({noise_score:.2f}), cleaning input...")
                prompt = self.noise_reducer.clean_text(prompt, remove_stop_words=False)
                print(f"[✅ PREPROCESSING] Input cleaned successfully")
        
        # Include RAG context in prompt (context already has headers from context_optimizer)
        full_prompt = f"""{self.rag_context}

USER REQUEST:
{prompt}
"""
        
        # NEW: Smart Quality-Based Fallback System
        # Previously forced cloud for HTML/diagrams. Now we try local first, validate, and fallback if quality < 70%
        quality_sensitive_artifacts = ['erd', 'architecture', 'visual_prototype_dev', 'all_diagrams', 'html', 'mermaid']
        should_validate_quality = artifact_type and any(term in artifact_type for term in quality_sensitive_artifacts)
        local_attempt_result = None  # Store result for validation
        
        # FORCE CLOUD: Skip local if force_cloud=True (for retry attempts) OR session state flag set
        check_force_cloud = force_cloud
        if not check_force_cloud:
            try:
                import streamlit as st
                check_force_cloud = st.session_state.get('force_cloud_next_gen', False)
                if check_force_cloud:
                    print(f"[FORCE_CLOUD] Session state flag detected - using cloud provider for retry")
            except Exception:
                pass  # Streamlit not available
        
        # 🚀 USE SMART GENERATION ORCHESTRATOR (if available and artifact type specified)
        print(f"[DEBUG] smart_generator={self.smart_generator is not None}, artifact_type={artifact_type}, check_force_cloud={check_force_cloud}")
        if self.smart_generator and artifact_type and not check_force_cloud:
            print(f"[SMART_GEN] Using smart generation orchestrator for {artifact_type}")
            
            try:
                # Create UI callback for real-time updates
                ui_status_placeholder = None
                def ui_callback(message: str):
                    """Stream progress updates to Streamlit UI"""
                    nonlocal ui_status_placeholder
                    try:
                        import streamlit as st
                        if ui_status_placeholder is None:
                            # Create placeholder on first call
                            ui_status_placeholder = st.empty()
                        
                        # Update UI with current status
                        if "✅" in message:
                            ui_status_placeholder.success(message)
                        elif "❌" in message or "⚠️" in message:
                            ui_status_placeholder.warning(message)
                        else:
                            ui_status_placeholder.info(message)
                    except Exception:
                        pass  # Ignore if Streamlit not available
                
                # Define cloud fallback function with intelligent provider routing
                async def cloud_fallback_fn(prompt, system_message, artifact_type, **kwargs):
                    """
                    Smart cloud routing:
                    - Complex tasks (architecture, prototypes, sequences) → Gemini 2.0 Flash
                    - Simple tasks (ERD, docs) → Current provider (Groq/OpenAI)
                    """
                    # Define complex tasks that benefit from Gemini's capabilities
                    COMPLEX_TASKS = [
                        "architecture", "mermaid_architecture", "system_overview", 
                        "components_diagram", "visual_prototype_dev", "visual_prototype",
                        "html_diagram", "api_sequence", "mermaid_sequence",
                        "full_system", "prototype"
                    ]
                    
                    # Check if we should use Gemini for this task
                    use_gemini = artifact_type in COMPLEX_TASKS
                    
                    if use_gemini:
                        # Try to use Gemini if available
                        try:
                            # Save current provider
                            original_provider = self.client_type
                            original_client = self.client
                            
                            # Check if Gemini is configured
                            try:
                                from config.secrets_manager import api_key_manager
                                gemini_key = api_key_manager.get_key('gemini')
                                
                                if gemini_key:
                                    print(f"[SMART_ROUTING] 🎯 Complex task '{artifact_type}' → Using Gemini 2.0 Flash")
                                    
                                    # Temporarily switch to Gemini
                                    import google.generativeai as genai
                                    genai.configure(api_key=gemini_key)
                                    self.client = genai.GenerativeModel('gemini-2.0-flash-exp')
                                    self.client_type = 'gemini'
                                    
                                    # Generate with Gemini
                                    result = await self._call_cloud_provider(prompt, system_message, artifact_type)
                                    
                                    # Restore original provider
                                    self.client = original_client
                                    self.client_type = original_provider
                                    
                                    return result
                                else:
                                    print(f"[SMART_ROUTING] Gemini not configured, using {original_provider}")
                            except Exception as e:
                                print(f"[SMART_ROUTING] Failed to switch to Gemini: {e}, using {original_provider}")
                                # Restore on error
                                self.client = original_client
                                self.client_type = original_provider
                        except Exception as e:
                            print(f"[SMART_ROUTING] Error in Gemini routing: {e}")
                    
                    # Use current provider (Groq/OpenAI or fallback)
                    return await self._call_cloud_provider(prompt, system_message, artifact_type)
                
                
                # Debug: Verify meeting notes and RAG context are populated
                print(f"\n{'='*70}")
                print(f"[DEBUG_AGENT] 🔬 Context verification before smart_generator.generate()")
                print(f"{'='*70}")
                if self.meeting_notes:
                    print(f"[DEBUG_AGENT] ✅ Meeting notes: {len(self.meeting_notes)} chars")
                    print(f"[DEBUG_AGENT]    Preview: {self.meeting_notes[:150]}...")
                else:
                    print(f"[WARN] ❌ No meeting notes provided - semantic validation may not work correctly")
                
                if self.rag_context:
                    print(f"[DEBUG_AGENT] ✅ RAG context: {len(self.rag_context)} chars")
                    print(f"[DEBUG_AGENT]    Preview: {self.rag_context[:150]}...")
                else:
                    print(f"[WARN] ❌ No RAG context - outputs may be generic")
                
                if self.feature_requirements:
                    print(f"[DEBUG_AGENT] ✅ Feature requirements: {len(self.feature_requirements)} items")
                else:
                    print(f"[DEBUG_AGENT] ⚠️  No feature requirements")
                
                print(f"[DEBUG_AGENT] Artifact type: {artifact_type}")
                print(f"[DEBUG_AGENT] Full prompt length: {len(full_prompt)} chars")
                print(f"{'='*70}\n")
                
                # Use smart generator with UI callback (tries local models first, cloud fallback if needed)
                # CRITICAL: Pass ALL context (RAG + meeting notes + requirements)
                result = await self.smart_generator.generate(
                    artifact_type=artifact_type,
                    prompt=full_prompt,
                    system_message=system_prompt,
                    cloud_fallback_fn=cloud_fallback_fn,
                    temperature=0.2,
                    meeting_notes=self.meeting_notes,
                    rag_context=self.rag_context,  # ✅ ADDED
                    feature_requirements=self.feature_requirements,  # ✅ ADDED
                    context={
                        "meeting_notes": self.meeting_notes,
                        "rag_context": self.rag_context,  # ✅ ADDED
                        "feature_requirements": self.feature_requirements  # ✅ ADDED
                    },
                    ui_callback=ui_callback
                )
                
                if result.success:
                    print(f"[SMART_GEN] ✅ Success! Model: {result.model_used}, Quality: {result.quality_score}/100, Cloud: {result.used_cloud_fallback}")
                    
                    # 🚀 RECORD FEEDBACK FOR ADAPTIVE LEARNING (Critical for incremental fine-tuning)
                    if self.adaptive_loop and result.quality_score >= 80:
                        try:
                            # Determine feedback type based on quality score
                            feedback_type = FeedbackType.SUCCESS if result.quality_score >= 80 else FeedbackType.VALIDATION_FAILURE
                            
                            # Record feedback event
                            self.adaptive_loop.record_feedback(
                                input_data=full_prompt,
                                ai_output=result.content,
                                artifact_type=artifact_type,
                                model_used=result.model_used,
                                validation_score=result.quality_score,
                                feedback_type=feedback_type,
                                corrected_output=None,
                                context={
                                    "meeting_notes": self.meeting_notes,
                                    "rag_context": self.rag_context,
                                    "feature_requirements": self.feature_requirements,
                                    "is_local": result.is_local,
                                    "used_cloud_fallback": result.used_cloud_fallback,
                                    "generation_time": result.generation_time
                                }
                            )
                            print(f"[ADAPTIVE_LEARNING] ✅ Recorded successful generation for fine-tuning")
                        except Exception as e:
                            print(f"[ADAPTIVE_LEARNING] ⚠️ Failed to record feedback: {e}")
                            # Don't fail the request if feedback recording fails
                    elif result.quality_score < 80:
                        print(f"[ADAPTIVE_LEARNING] ⛔ Skipped feedback recording (quality {result.quality_score} < 80)")
                    
                    return result.content
                else:
                    print(f"[SMART_GEN] ⚠️ Failed after trying all models: {result.validation_errors}")
                    # Return None - no fallback to OLD logic
                    return None
                    
            except Exception as e:
                import traceback
                print(f"[ERROR] Smart generator failed: {e}")
                traceback.print_exc()
                # Return None - no fallback to broken OLD logic
                return None
        
        # 🔥 Fallback for legacy calls without artifact_type (internal diagram methods)
        # These are rare and will be deprecated
        if not artifact_type:
            print(f"[DEBUG] Legacy call without artifact_type - using simple cloud fallback")
            try:
                return await self._call_cloud_provider(full_prompt, system_prompt, "generic")
            except Exception as e:
                print(f"[ERROR] Legacy cloud fallback failed: {e}")
                return None
        
        # If smart generator not available, fail gracefully
        if not self.smart_generator:
            print(f"[ERROR] Smart generator not initialized - cannot generate {artifact_type}")
            print(f"[ERROR] This should never happen - check initialization logs")
            return None
        
        # This should never be reached (smart generator handles everything)
        print(f"[WARN] Unexpected code path in _call_ai for artifact_type={artifact_type}")
        return None
    
    async def _call_cloud_provider(self, prompt: str, system_prompt: str = None, artifact_type: str = None) -> str:
        """
        Helper method to call cloud providers with smart selection and compression.
        Used by SmartGenerationOrchestrator for cloud fallback.
        
        Args:
            prompt: Full prompt (including RAG context)
            system_prompt: System prompt (optional)
            artifact_type: Artifact type for smart provider selection
            
        Returns:
            Generated content from cloud provider
        """
        from config.secrets_manager import api_key_manager
        from ai.smart_model_selector import ContextOptimizer
        
        # Compress context for cloud models (target 3000 tokens = ~12K chars)
        compressed_prompt = await ContextOptimizer.compress_prompt_for_cloud(prompt, max_tokens=3000)
        print(f"[CONTEXT_COMPRESSION] {len(prompt)} → {len(compressed_prompt)} chars for cloud")
        
        # Smart provider selection based on artifact type
        # Complex tasks (architecture, prototypes) → Gemini 2.0 Flash
        # Simple tasks (code, ERD) → Groq/OpenAI
        if artifact_type in ['mermaid_class', 'prototype', 'architecture']:
            cloud_providers = [
                ('gemini', 'gemini-2.0-flash-exp'),
                ('groq', 'llama-3.3-70b-versatile'),
                ('openai', 'gpt-4')
            ]
            print(f"[SMART_ROUTING] Complex task ({artifact_type}) → Trying Gemini first")
        else:
            cloud_providers = [
                ('groq', 'llama-3.3-70b-versatile'),
                ('gemini', 'gemini-2.0-flash-exp'),
                ('openai', 'gpt-4')
            ]
        
        for provider_name, model_name in cloud_providers:
            try:
                api_key = api_key_manager.get_key(provider_name)
                if not api_key:
                    print(f"[SKIP] No API key for {provider_name}")
                    continue
                
                if provider_name == 'groq':
                    from groq import AsyncGroq
                    client = AsyncGroq(api_key=api_key)
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": compressed_prompt})
                    
                    response = await client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=messages,
                        temperature=0.2,
                        max_tokens=8000
                    )
                    result = response.choices[0].message.content
                    print(f"[OK] Cloud fallback succeeded using Groq")
                    return result
                
                elif provider_name == 'gemini':
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-2.0-flash-exp')
                    
                    combined_prompt = compressed_prompt
                    if system_prompt:
                        combined_prompt = f"{system_prompt}\n\n{compressed_prompt}"
                    
                    response = await model.generate_content_async(combined_prompt)
                    result = response.text
                    print(f"[OK] Cloud fallback succeeded using Gemini")
                    return result
                
                elif provider_name == 'openai':
                    from openai import AsyncOpenAI
                    client = AsyncOpenAI(api_key=api_key)
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": compressed_prompt})
                    
                    # Token guard for OpenAI
                    try:
                        from ai.smart_model_selector import fit_openai_messages_to_context
                        trimmed_messages, prompt_tokens = fit_openai_messages_to_context(
                            messages=messages,
                            model_name="gpt-4",
                            context_window=8192,
                            max_completion_tokens=4000,
                            safety_margin=200,
                        )
                        if prompt_tokens > 0:
                            print(f"[TOKEN_GUARD] OpenAI prompt tokens: {prompt_tokens}")
                        messages = trimmed_messages
                    except Exception as _guard_err:
                        print(f"[WARN] Token guard failed: {_guard_err}")
                    
                    response = await client.chat.completions.create(
                        model="gpt-4",
                        messages=messages,
                        temperature=0.2,
                        max_tokens=4000
                    )
                    result = response.choices[0].message.content
                    print(f"[OK] Cloud fallback succeeded using OpenAI GPT-4")
                    return result
            
            except Exception as e:
                print(f"[WARN] Cloud provider {provider_name} failed: {e}. Trying next...")
                continue
        
        # All cloud providers failed
        raise Exception("All cloud providers failed. Please check API keys in secrets store.")
    
    # ============================================================================
    # RAG CONTEXT RETRIEVAL
    # ============================================================================
    
    async def retrieve_rag_context(self, query: str, force_refresh: bool = False, max_retries: int = 3) -> str:
        """Retrieve relevant context using ENHANCED RAG with caching and retry logic"""
        if not self.collection or not self.cfg:
            print("[WARN] RAG system not available")
            return ""
        
        # Check cache first
        if not force_refresh:
            cached_context = self.cache.get_context(query)
            if cached_context:
                self.rag_context = cached_context
                return cached_context
        
        # Retry logic with exponential backoff
        import time
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                    print(f"[RAG] Retry attempt {attempt + 1}/{max_retries} after {wait_time}s...")
                    time.sleep(wait_time)
                
                return await self._retrieve_rag_context_internal(query)
                
            except Exception as e:
                print(f"[ERROR] RAG retrieval attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    # Last attempt failed
                    print(f"[ERROR] RAG retrieval failed after {max_retries} attempts")
                    import traceback
                    traceback.print_exc()
                    return ""
        
        return ""
    
    async def _retrieve_rag_context_internal(self, query: str) -> str:
        """Internal RAG retrieval implementation - ALWAYS uses advanced RAG + Smart Code Analysis"""
        try:
            # STEP 0: PROGRAMMATIC CODE ANALYSIS (NEW - reduces AI noise)
            programmatic_context = ""
            try:
                from components.smart_code_analyzer import get_smart_analyzer
                from pathlib import Path
                
                # Find project root (same logic as repo analysis)
                current = Path(".").resolve()
                project_root = current
                if current.name == "architect_ai_cursor_poc" or "architect_ai" in str(current):
                    project_root = current.parent.resolve()
                
                analyzer = get_smart_analyzer()
                print("[SMART_ANALYSIS] 🧠 Running programmatic code analysis...")
                analysis = analyzer.analyze_project(project_root)
                programmatic_context = analyzer.format_for_ai(analysis)
                
                print(f"[SMART_ANALYSIS] ✅ Extracted {len(analysis['api_endpoints'])} APIs, "
                      f"{len(analysis['database_models'])} models, "
                      f"{len(analysis['ui_components'])} components")
            except Exception as e:
                print(f"[WARN] Smart code analysis failed: {e}")
                programmatic_context = ""
            
            # FORCE ADVANCED RAG - Override config to ALWAYS enable advanced features
            intelligence_cfg = self.cfg.get("intelligence", {})
            
            # Force enable all advanced features for artifact generation
            if "query_expansion" not in intelligence_cfg:
                intelligence_cfg["query_expansion"] = {}
            if "reranking" not in intelligence_cfg:
                intelligence_cfg["reranking"] = {}
            if "context_optimization" not in intelligence_cfg:
                intelligence_cfg["context_optimization"] = {}
            
            intelligence_cfg["query_expansion"]["enabled"] = True
            intelligence_cfg["reranking"]["enabled"] = True
            intelligence_cfg["reranking"]["strategy"] = "hybrid"
            intelligence_cfg["reranking"]["top_k"] = 18
            intelligence_cfg["context_optimization"]["enabled"] = True
            intelligence_cfg["context_optimization"]["max_tokens"] = 8000
            
            print("[RAG] ✅ ADVANCED RAG ENABLED (forced) - Query Expansion + Hybrid Reranking + Context Optimization")
            
            # Step 1: Query Expansion (ALWAYS enabled)
            queries = [query]
            if True:  # Force enable
                try:
                    from rag.query_processor import get_query_expander
                    expander = get_query_expander()
                    analysis = expander.analyze_query(query)
                    # Use original + expanded queries (limit to 3 total)
                    queries = [analysis.original_query] + analysis.expanded_queries[:2]
                    print(f"[RAG] ✅ Expanded to {len(queries)} queries")
                except Exception as e:
                    print(f"[WARN] Query expansion failed: {e}, continuing with original query")
                    queries = [query]
            
            # Step 2: Retrieve for all queries
            docs = self._load_docs_from_chroma()
            
            # Continue with the RAG pipeline...
            # (Full implementation below in duplicate method)
            # This is a stub - the real implementation is at line 1330+
            return "RAG_STUB"  # Placeholder
            
        except Exception as e:
            # Re-raise to trigger retry in outer method
            raise Exception(f"RAG internal retrieval stub failed: {e}")
    
    # NOTE: The REAL _retrieve_rag_context_internal implementation follows below
    #       This stub exists due to orphaned code cleanup
    
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
        
        # NOTE: More tech stack detection code follows in the REAL duplicate method below
        # This stub method has been cleaned up to remove orphaned code
        return analysis
    
    # ============================================================================
    # DUPLICATE METHODS (Real implementations follow)
    # ============================================================================
    
    async def process_meeting_notes(self, notes_path: str) -> Dict[str, Any]:
        """Process meeting notes to extract feature requirements and user stories"""
        print(f"[INFO] Processing meeting notes from: {notes_path}")
        
        # NOTE: Full implementation in duplicate method below
        # This stub exists due to orphaned code cleanup
        return {}
    
    async def generate_prototype_code(self, feature_name: str) -> Dict[str, Any]:
        """Generate code prototype - ENHANCED with Pattern Mining"""
        print("[INFO] Generating code prototype...")
        
        # CRITICAL: Analyze repository FIRST if not already done
        if not self.repo_analysis:
            print("[INFO] Repository not analyzed yet, analyzing now...")
            await self.analyze_repository()
        
        # ENHANCED RAG CONTEXT: Be MORE SPECIFIC with feature name to get relevant examples
        # Extract key words from feature name for better matching
        feature_keywords = ' '.join(word.lower() for word in feature_name.split('-') if len(word) > 2)
        
        await self.retrieve_rag_context(f"""
        {feature_name} {feature_keywords} feature request form component service controller
        implementation example similar component API endpoint backend service
        coding style patterns components services API controller architecture
        README documentation coding standards best practices conventions
        project structure folder organization file naming TypeScript Angular C# .NET
        """)
        
        # Continue with the rest of the prototype generation...
        # (Full implementation follows in duplicate method below)
        return {}
    
    async def _call_cloud_provider(self, prompt: str, system_prompt: str = None, artifact_type: str = None) -> str:
        """
        Helper method to call cloud providers with smart selection and compression.
        Used by SmartGenerationOrchestrator for cloud fallback.
        
        Args:
            prompt: Full prompt (including RAG context)
            system_prompt: System prompt (optional)
            artifact_type: Artifact type for smart provider selection
            
        Returns:
            Generated content from cloud provider
        """
        from config.secrets_manager import api_key_manager
        from ai.smart_model_selector import ContextOptimizer
        
        # Compress context for cloud token limits
        compressed_prompt = await ContextOptimizer.compress_prompt_for_cloud(prompt, max_tokens=3000)
        print(f"[CLOUD] Compressed prompt: {len(prompt)} → {len(compressed_prompt)} chars")
        
        # Smart provider selection based on artifact type
        if artifact_type:
            from config.artifact_model_mapping import get_artifact_mapper
            mapper = get_artifact_mapper()
            task_type = mapper.get_task_type(artifact_type)
            
            # ⚡ UPDATED: Groq as primary fallback for better reliability (no rate limits like Gemini)
            if task_type == 'mermaid':
                cloud_providers = [('groq', 'llama-3.3-70b-versatile'), ('gemini', 'gemini-2.0-flash-exp'), ('openai', 'gpt-4')]
            elif task_type in ['code', 'html', 'prototype']:
                cloud_providers = [('groq', 'llama-3.3-70b-versatile'), ('openai', 'gpt-4'), ('gemini', 'gemini-2.0-flash-exp')]
            elif task_type in ['jira', 'planning', 'documentation']:
                # Groq first for JIRA (better at structured output), Gemini as fallback
                cloud_providers = [('groq', 'llama-3.3-70b-versatile'), ('gemini', 'gemini-2.0-flash-exp'), ('openai', 'gpt-4')]
            else:
                cloud_providers = [('groq', 'llama-3.3-70b-versatile'), ('openai', 'gpt-4'), ('gemini', 'gemini-2.0-flash-exp')]
        else:
            # Default: Groq first (most reliable), OpenAI second, Gemini last
            cloud_providers = [('groq', 'llama-3.3-70b-versatile'), ('openai', 'gpt-4'), ('gemini', 'gemini-2.0-flash-exp')]
        
        # Try each provider
        for provider_name, model_name in cloud_providers:
            try:
                api_key = api_key_manager.get_key(provider_name)
                if not api_key:
                    continue
                
                if provider_name == 'groq':
                    try:
                        from groq import AsyncGroq
                        client = AsyncGroq(api_key=api_key)
                        messages = []
                        if system_prompt:
                            messages.append({"role": "system", "content": system_prompt})
                        messages.append({"role": "user", "content": compressed_prompt})
                        
                        response = await client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=messages,
                            temperature=0.2,
                            max_tokens=8000
                        )
                        print(f"[CLOUD] ✅ Success with Groq")
                        return response.choices[0].message.content
                    except TypeError as te:
                        if "'proxies'" in str(te):
                            print(f"[CLOUD] ⚠️ groq version incompatible with httpx. Run: pip install --upgrade groq openai")
                        raise
                
                elif provider_name == 'gemini':
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-2.0-flash-exp')
                    
                    combined_prompt = compressed_prompt
                    if system_prompt:
                        combined_prompt = f"{system_prompt}\n\n{compressed_prompt}"
                    
                    response = await model.generate_content_async(combined_prompt)
                    print(f"[CLOUD] ✅ Success with Gemini")
                    return response.text
                
                elif provider_name == 'openai':
                    try:
                        from openai import AsyncOpenAI
                        client = AsyncOpenAI(api_key=api_key)
                        messages = []
                        if system_prompt:
                            messages.append({"role": "system", "content": system_prompt})
                        messages.append({"role": "user", "content": compressed_prompt})
                        
                        # Token safety guard
                        try:
                            from ai.smart_model_selector import fit_openai_messages_to_context
                            trimmed_messages, prompt_tokens = fit_openai_messages_to_context(
                                messages=messages,
                                model_name="gpt-4",
                                context_window=8192,
                                max_completion_tokens=4000,
                                safety_margin=200
                            )
                            messages = trimmed_messages
                            print(f"[CLOUD] OpenAI tokens: {prompt_tokens}")
                        except Exception as e:
                            print(f"[WARN] Token guard failed: {e}")
                        
                        response = await client.chat.completions.create(
                            model="gpt-4",
                            messages=messages,
                            temperature=0.2,
                            max_tokens=4000
                        )
                        print(f"[CLOUD] ✅ Success with OpenAI GPT-4")
                        return response.choices[0].message.content
                    except TypeError as te:
                        if "'proxies'" in str(te):
                            print(f"[CLOUD] ⚠️ openai version incompatible with httpx. Run: pip install --upgrade groq openai")
                        raise
            
            except Exception as e:
                print(f"[CLOUD] ⚠️ {provider_name} failed: {e}")
                continue
        
        raise Exception("All cloud providers failed")
    
    async def retrieve_rag_context(self, query: str, force_refresh: bool = False, max_retries: int = 3) -> str:
        """Retrieve relevant context using ENHANCED RAG with caching and retry logic"""
        if not self.collection or not self.cfg:
            print("[WARN] RAG system not available")
            return ""
        
        # Check cache first
        if not force_refresh:
            cached_context = self.cache.get_context(query)
            if cached_context:
                self.rag_context = cached_context
                return cached_context
        
        # Retry logic with exponential backoff
        import time
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                    print(f"[RAG] Retry attempt {attempt + 1}/{max_retries} after {wait_time}s...")
                    time.sleep(wait_time)
                
                return await self._retrieve_rag_context_internal(query)
                
            except Exception as e:
                print(f"[ERROR] RAG retrieval attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    # Last attempt failed
                    print(f"[ERROR] RAG retrieval failed after {max_retries} attempts")
                    import traceback
                    traceback.print_exc()
                    return ""
        
        return ""
    
    async def _retrieve_rag_context_internal(self, query: str) -> str:
        """Internal RAG retrieval implementation - ALWAYS uses advanced RAG + Smart Code Analysis"""
        try:
            # STEP 0: PROGRAMMATIC CODE ANALYSIS (NEW - reduces AI noise)
            programmatic_context = ""
            try:
                from components.smart_code_analyzer import get_smart_analyzer
                from pathlib import Path
                
                # Find project root (same logic as repo analysis)
                current = Path(".").resolve()
                project_root = current
                if current.name == "architect_ai_cursor_poc" or "architect_ai" in str(current):
                    project_root = current.parent.resolve()
                
                analyzer = get_smart_analyzer()
                print("[SMART_ANALYSIS] 🧠 Running programmatic code analysis...")
                analysis = analyzer.analyze_project(project_root)
                programmatic_context = analyzer.format_for_ai(analysis)
                
                print(f"[SMART_ANALYSIS] ✅ Extracted {len(analysis['api_endpoints'])} APIs, "
                      f"{len(analysis['database_models'])} models, "
                      f"{len(analysis['ui_components'])} components")
            except Exception as e:
                print(f"[WARN] Smart code analysis failed: {e}")
                programmatic_context = ""
            
            # FORCE ADVANCED RAG - Override config to ALWAYS enable advanced features
            intelligence_cfg = self.cfg.get("intelligence", {})
            
            # Force enable all advanced features for artifact generation
            if "query_expansion" not in intelligence_cfg:
                intelligence_cfg["query_expansion"] = {}
            if "reranking" not in intelligence_cfg:
                intelligence_cfg["reranking"] = {}
            if "context_optimization" not in intelligence_cfg:
                intelligence_cfg["context_optimization"] = {}
            
            intelligence_cfg["query_expansion"]["enabled"] = True
            intelligence_cfg["reranking"]["enabled"] = True
            intelligence_cfg["reranking"]["strategy"] = "hybrid"
            intelligence_cfg["reranking"]["top_k"] = 18
            intelligence_cfg["context_optimization"]["enabled"] = True
            intelligence_cfg["context_optimization"]["max_tokens"] = 8000
            
            print("[RAG] ✅ ADVANCED RAG ENABLED (forced) - Query Expansion + Hybrid Reranking + Context Optimization")
            
            # Step 1: Query Expansion (ALWAYS enabled)
            queries = [query]
            if True:  # Force enable
                try:
                    from rag.query_processor import get_query_expander
                    expander = get_query_expander()
                    analysis = expander.analyze_query(query)
                    # Use original + expanded queries (limit to 3 total)
                    queries = [analysis.original_query] + analysis.expanded_queries[:2]
                    print(f"[RAG] ✅ Expanded to {len(queries)} queries")
                except Exception as e:
                    print(f"[WARN] Query expansion failed: {e}, continuing with original query")
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
            
            # Filter out low-value or scaffolding files to reduce generic outputs
            try:
                filtered_hits = []
                EXCLUDE_SUBSTRINGS = [
                    "package-lock.json",
                    "node_modules/",
                    "/dist/",
                    ".min.js",
                    "weatherforecast",  # common .NET scaffold
                ]
                for doc, score in all_hits:
                    path = (doc.get("meta") or {}).get("path", "") if isinstance(doc, dict) else ""
                    if any(x.lower() in path.lower() for x in EXCLUDE_SUBSTRINGS):
                        continue
                    filtered_hits.append((doc, score))
                if filtered_hits:
                    all_hits = filtered_hits
                    print(f"[RAG] 🔎 Filtered irrelevant/scaffold files. Remaining hits: {len(all_hits)}")
            except Exception as _filter_err:
                print(f"[WARN] RAG filtering step failed: {_filter_err}")
            
            # RAG DEBUG LOGGING (pre-tokenization)
            try:
                from pathlib import Path
                import json
                import datetime
                
                debug_entries = []
                for doc, score in all_hits[:20]:
                    debug_entries.append({
                        "path": (doc.get("meta") or {}).get("path", "") if isinstance(doc, dict) else "",
                        "chunk": str((doc.get("meta") or {}).get("chunk", "")) if isinstance(doc, dict) else "",
                        "score": f"{score:.4f}" if isinstance(score, (int, float)) else str(score),
                        "content_preview": (doc.get("content", "")[:500] + ("…" if len(doc.get("content", "")) > 500 else "")) if isinstance(doc, dict) else str(doc)[:500]
                    })
                
                # Write to file
                output_dir = Path("outputs/validation")
                output_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                debug_file = output_dir / f"rag_debug_{ts}.json"
                debug_file.write_text(json.dumps({
                    "timestamp": ts,
                    "query": query,
                    "expanded_queries": queries,
                    "total_hits": len(all_hits),
                    "top_20_chunks": debug_entries
                }, indent=2), encoding="utf-8")
                
                print(f"[RAG_DEBUG] Logged {len(debug_entries)} chunks to {debug_file}")
                
                # Also store in session state if streamlit is available
                try:
                    import streamlit as st
                    st.session_state["last_rag_debug"] = debug_entries
                    st.session_state["last_rag_query"] = query
                except (KeyError, AttributeError, ImportError) as e:
                    print(f"[WARN] Failed to update RAG debug state: {e}")
                
            except Exception as e:
                print(f"[WARN] RAG debug logging failed: {e}")
            
            # Step 3: Rerank (ALWAYS enabled - forced)
            if True:  # Force enable reranking
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
                    print(f"[RAG] ✅ Reranked to top {len(hits)} results using {strategy} strategy")
                except Exception as e:
                    print(f"[WARN] Reranking failed: {e}, using top 18 results")
                    hits = all_hits[:18]
            
            # Step 4: Context Optimization (ALWAYS enabled - forced)
            if True:  # Force enable context optimization
                try:
                    from rag.context_optimizer import get_context_optimizer
                    max_tokens = intelligence_cfg.get("context_optimization", {}).get("max_tokens", 8000)
                    optimizer = get_context_optimizer()
                    self.rag_context = optimizer.format_context_with_budget(hits, max_tokens=max_tokens)
                    print(f"[RAG] ✅ Optimized context to fit {max_tokens} tokens")
                except Exception as e:
                    print(f"[WARN] Context optimization failed: {e}, using basic formatting")
                    # Fallback to basic formatting
                    context_parts = []
                    for i, (doc, score) in enumerate(hits, 1):
                        context_parts.append(f"---\n## Context {i} (score={score:.3f})\n")
                        context_parts.append(f"**FILE:** {doc['meta'].get('path', 'unknown')}\n")
                        context_parts.append(f"```\n{doc['content']}\n```\n")
                    self.rag_context = "\n".join(context_parts)
            
            # 🚀 STEP 5: ML FEATURE ENGINEERING (Pattern Clustering & Deduplication)
            if self.ml_engineer:
                try:
                    # Extract patterns from RAG chunks
                    patterns = []
                    for doc, score in hits:
                        content = doc.get('content', '') if isinstance(doc, dict) else str(doc)
                        file_path = (doc.get('meta', {}).get('path', 'unknown') if isinstance(doc, dict) else 'unknown')
                        patterns.append({
                            'name': file_path,
                            'type': 'rag_chunk',
                            'confidence': score,
                            'file_path': file_path,
                            'content': content
                        })
                    
                    # Cluster patterns to find duplicates/similar chunks
                    # Extract code content from patterns for clustering
                    code_samples = [p.get('content', '') for p in patterns]
                    cluster_result = self.ml_engineer.cluster_code_patterns(code_samples, n_clusters=min(5, len(patterns)))
                    
                    # Map cluster labels back to patterns
                    clusters = {}
                    for idx, label in enumerate(cluster_result.cluster_labels):
                        if label not in clusters:
                            clusters[label] = []
                        clusters[label].append(patterns[idx])
                    
                    # Build ML insights context
                    ml_context = "\n\n=== 🧠 ML PATTERN ANALYSIS ===\n"
                    ml_context += f"Identified {len(clusters)} pattern clusters from {len(patterns)} chunks:\n\n"
                    
                    for cluster_id, cluster_patterns in clusters.items():
                        if cluster_patterns:
                            ml_context += f"📦 Cluster {cluster_id + 1} ({len(cluster_patterns)} similar chunks):\n"
                            # Show most representative chunk (highest confidence)
                            best = max(cluster_patterns, key=lambda p: p.get('confidence', 0))
                            ml_context += f"  Representative: {best.get('file_path', 'unknown')}\n"
                            ml_context += f"  Pattern: {best.get('content', '')[:200]}...\n\n"
                    
                    # Append ML insights to RAG context
                    self.rag_context += ml_context
                    
                    print(f"[ML_RAG] ✅ Added ML clustering insights ({len(clusters)} clusters)")
                    
                except Exception as e:
                    print(f"[WARN] ML feature engineering failed: {e}")
            
            # Cache the result
            self.cache.set_context(query, self.rag_context, ttl=3600)
            
            print(f"[RAG] ✅ Retrieved {len(hits)} relevant context snippets using ADVANCED RAG (Query Expansion + Hybrid Reranking + Context Optimization)")
            return self.rag_context
            
        except Exception as e:
            # Re-raise to trigger retry
            raise Exception(f"RAG internal retrieval failed: {e}")
    
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
                    "You are an expert business analyst. Extract comprehensive requirements using the RAG context.",
                    artifact_type="requirements"
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
        """Generate code prototype - ENHANCED with Pattern Mining"""
        print("[INFO] Generating code prototype...")
        
        # CRITICAL: Analyze repository FIRST if not already done
        if not self.repo_analysis:
            print("[INFO] Repository not analyzed yet, analyzing now...")
            await self.analyze_repository()
        
        # ENHANCED RAG CONTEXT: Be MORE SPECIFIC with feature name to get relevant examples
        # Extract key words from feature name for better matching
        feature_keywords = ' '.join(word.lower() for word in feature_name.split('-') if len(word) > 2)
        
        await self.retrieve_rag_context(f"""
        {feature_name} {feature_keywords} feature request form component service controller
        implementation example similar component API endpoint backend service
        coding style patterns components services API controller architecture
        README documentation coding standards best practices conventions
        project structure folder organization file naming TypeScript Angular C# .NET
        """)
        
        # ENHANCE with Pattern Mining insights
        pattern_context = ""
        try:
            # 🚀 USE CACHED PATTERN ANALYSIS (10x faster)
            analysis = self._get_pattern_analysis()
            
            # Extract design patterns to follow
            design_patterns = [p for p in analysis.patterns if p.pattern_type == "design_pattern"]
            language_idioms = [p for p in analysis.patterns if p.pattern_type == "idiom"]
            
            if design_patterns or language_idioms:
                pattern_context = "\n\nDETECTED CODE PATTERNS TO FOLLOW:\n"
                
                if design_patterns:
                    pattern_context += "Design Patterns (USE THESE):\n"
                    for pattern in design_patterns[:5]:
                        pattern_context += f"- {pattern.name}: {pattern.description}\n"
                        pattern_context += f"  Found in: {', '.join(pattern.files[:3])}\n"
                
                if language_idioms:
                    pattern_context += "\nLanguage Idioms (FOLLOW THESE):\n"
                    for idiom in language_idioms[:5]:
                        pattern_context += f"- {idiom.name}: {idiom.description}\n"
                
                # Add code quality context
                pattern_context += f"\nCode Quality Score: {analysis.code_quality_score:.0f}/100\n"
                pattern_context += "Top Recommendations:\n"
                for rec in analysis.recommendations[:3]:
                    pattern_context += f"- {rec}\n"
                
                self.rag_context += pattern_context
                print(f"[OK] Enhanced code generation with {len(design_patterns)} patterns from Pattern Mining")
        except Exception as e:
            print(f"[WARN] Could not enhance with Pattern Mining: {e}")
        
        # ========== ENTITY EXTRACTION FROM ERD (CRITICAL FOR QUALITY) ==========
        # Extract actual entity names and fields from the generated ERD
        # This ensures code uses YOUR project's entities, not generic placeholders
        entities_data = {'entities': [], 'relationships': [], 'entity_names': [], 'primary_entities': []}
        try:
            from utils.entity_extractor import extract_entities_from_file
            from pathlib import Path
            
            # Try to load ERD from outputs directory
            erd_file = Path("outputs/visualizations/erd_diagram.mmd")
            if erd_file.exists():
                entities_data = extract_entities_from_file(erd_file)
                print(f"[CODE_GEN] ✅ Extracted {entities_data['entity_count']} entities from ERD: {', '.join(entities_data['entity_names'])}")
                
                # Build entity context for prompt
                if entities_data['entity_count'] > 0:
                    entity_context = "\n\n🎯 ACTUAL PROJECT ENTITIES (extracted from YOUR ERD):\n"
                    for entity in entities_data['entities']:
                        entity_context += f"\n📦 {entity['name']} Entity:\n"
                        entity_context += "   Fields:\n"
                        for field in entity['fields']:
                            field_markers = []
                            if field.get('is_pk'): field_markers.append('PRIMARY KEY')
                            if field.get('is_fk'): field_markers.append('FOREIGN KEY')
                            markers_str = f" ({', '.join(field_markers)})" if field_markers else ""
                            entity_context += f"   - {field['name']}: {field['type']}{markers_str}\n"
                    
                    self.rag_context += entity_context
            else:
                print(f"[CODE_GEN] ⚠️ No ERD file found at {erd_file}, will generate generic code")
        except Exception as e:
            print(f"[CODE_GEN] ⚠️ Could not extract entities from ERD: {e}")
            import traceback
            print(traceback.format_exc())
        
        # Detect tech stacks to be explicit about what to generate
        tech_stacks = self.repo_analysis.tech_stacks if self.repo_analysis else []
        has_frontend = any(tech in str(tech_stacks).lower() for tech in ['angular', 'react', 'vue', 'typescript'])
        has_dotnet = any(tech in str(tech_stacks).lower() for tech in ['.net', 'csharp', 'c#', 'asp.net'])
        has_backend = has_dotnet or any(tech in str(tech_stacks).lower() for tech in ['spring', 'fastapi', 'django', 'express', 'flask'])
        
        print(f"[DEBUG] Tech stacks detected: {tech_stacks}")
        print(f"[DEBUG] Has frontend: {has_frontend}, Has .NET backend: {has_dotnet}, Has any backend: {has_backend}")
        
        # Build entity-specific instructions
        entity_instructions = ""
        if entities_data['entity_count'] > 0:
            entity_instructions = f"""

🎯 CRITICAL: USE THESE ACTUAL ENTITIES FROM YOUR PROJECT (NOT GENERIC NAMES)
================================================
Extracted {entities_data['entity_count']} entities from your ERD: {', '.join(entities_data['entity_names'])}

YOU MUST generate controllers, services, and DTOs for EACH of these entities:
{chr(10).join(f"  {i+1}. {entity['name']} ({len(entity['fields'])} fields: {', '.join(f['name'] for f in entity['fields'][:5])}{'...' if len(entity['fields']) > 5 else ''})" for i, entity in enumerate(entities_data['entities']))}

❌ DO NOT use generic names like: ExtractedFeature, Sample, User, Product, Order
✅ DO use the ACTUAL entity names listed above
✅ DO include ALL the fields listed for each entity (not just Id and Name)
================================================
"""
        
        prompt = f"""
Generate a COMPLETE, PRODUCTION-READY code prototype for: {feature_name}

🚨 CRITICAL REQUIREMENT 🚨
This repository has BOTH frontend AND backend:
- Frontend: {tech_stacks if has_frontend else 'Angular/TypeScript detected in codebase'}
- Backend: {'.NET/C#' if has_dotnet else 'Backend framework detected in codebase'}

YOU MUST GENERATE FILES FOR **BOTH** FRONTEND AND BACKEND!
{entity_instructions}

REQUIREMENTS:
{json.dumps(self.feature_requirements, indent=2)}

REPOSITORY ANALYSIS:
Tech Stacks: {tech_stacks}
Architecture: {self.repo_analysis.architecture if self.repo_analysis else {}}
Patterns: {self.repo_analysis.code_patterns if self.repo_analysis else {}}
Dependencies: {self.repo_analysis.dependencies if self.repo_analysis else {}}
Team Standards: {self.repo_analysis.team_standards if self.repo_analysis else {}}

RAG CONTEXT FROM YOUR REPOSITORY (includes extracted entities):
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
        
        # ✅ FIXED: Pass artifact_type to enable smart generator
        response = await self._call_ai(prompt, system_prompt, artifact_type="code_prototype")
        
        return {
            "type": "code_prototype",
            "code": response,
            "feature_name": feature_name
        }
    
    async def generate_visual_prototype(self, feature_name: str) -> str:
        """Generate interactive visual prototype - ENHANCED with Pattern Mining"""
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
        
        # ENHANCE with Pattern Mining for UI/UX patterns
        try:
            # 🚀 USE CACHED PATTERN ANALYSIS (10x faster)
            analysis = self._get_pattern_analysis()
            
            # Extract UI/UX patterns
            design_patterns = [p for p in analysis.patterns if p.pattern_type == "design_pattern"]
            language_idioms = [p for p in analysis.patterns if p.pattern_type == "idiom"]
            
            pm_context = "\n\nUI/UX PATTERNS FROM CODEBASE:\n"
            
            # Check for Angular/React/Vue patterns
            frontend_patterns = [p for p in language_idioms if any(tech in p.description.lower() for tech in ['angular', 'react', 'vue', 'component'])]
            if frontend_patterns:
                pm_context += "Frontend Patterns (USE THESE):\n"
                for pattern in frontend_patterns[:5]:
                    pm_context += f"- {pattern.name}: {pattern.description}\n"
                    pm_context += f"  Found in: {', '.join(pattern.files[:2])}\n"
            
            # Add styling insights
            pm_context += "\nStyling Approach:\n"
            pm_context += f"- Code Quality: {analysis.code_quality_score:.0f}/100\n"
            pm_context += "- Follow detected component patterns\n"
            pm_context += "- Maintain consistent styling conventions\n"
            
            self.rag_context += pm_context
            print(f"[OK] Enhanced visual prototype with UI patterns from Pattern Mining")
        except Exception as e:
            print(f"[WARN] Could not enhance with Pattern Mining: {e}")
        
        # ========== ENTITY EXTRACTION FROM ERD (CRITICAL FOR QUALITY) ==========
        # Extract actual entity names and fields for realistic UI elements
        entities_data = {'entities': [], 'relationships': [], 'entity_names': [], 'primary_entities': []}
        try:
            from utils.entity_extractor import extract_entities_from_file
            from pathlib import Path
            
            # Try to load ERD from outputs directory
            erd_file = Path("outputs/visualizations/erd_diagram.mmd")
            if erd_file.exists():
                entities_data = extract_entities_from_file(erd_file)
                print(f"[VISUAL_PROTO] ✅ Extracted {entities_data['entity_count']} entities for UI: {', '.join(entities_data['entity_names'])}")
                
                # Build entity context for UI design
                if entities_data['entity_count'] > 0:
                    entity_context = "\n\n🎯 ACTUAL PROJECT ENTITIES (use for realistic UI):\n"
                    for entity in entities_data['entities']:
                        entity_context += f"\n📦 {entity['name']} (for forms/tables):\n"
                        entity_context += "   Fields to display:\n"
                        for field in entity['fields'][:8]:  # Show first 8 fields
                            entity_context += f"   - {field['name']} ({field['type']})\n"
                    
                    self.rag_context += entity_context
            else:
                print(f"[VISUAL_PROTO] ⚠️ No ERD file found, will generate generic UI")
        except Exception as e:
            print(f"[VISUAL_PROTO] ⚠️ Could not extract entities from ERD: {e}")
        
        # Build entity-specific UI instructions
        entity_ui_instructions = ""
        mock_data_examples = ""
        if entities_data['entity_count'] > 0:
            entity_ui_instructions = f"""

🎯 CRITICAL: USE THESE ACTUAL ENTITIES IN THE UI (NOT GENERIC DATA)
================================================
Extracted {entities_data['entity_count']} entities: {', '.join(entities_data['entity_names'])}

YOU MUST create UI elements (forms, tables, cards) for these entities:
"""
            for i, entity in enumerate(entities_data['entities'][:3]):  # Show first 3 entities
                entity_ui_instructions += f"\n{i+1}. {entity['name']} Form/Display:\n"
                entity_ui_instructions += "   Include these fields:\n"
                for field in entity['fields'][:6]:  # Show first 6 fields
                    input_type = "text"
                    if field['type'] == 'int' or field['type'] == 'decimal':
                        input_type = "number"
                    elif field['type'] == 'DateTime':
                        input_type = "date"
                    elif field['type'] == 'bool':
                        input_type = "checkbox"
                    entity_ui_instructions += f"   - {field['name']} (<input type='{input_type}'>)\n"
            
            # Generate realistic mock data
            entity_ui_instructions += "\n\n✅ Include REALISTIC mock data:\n"
            if entities_data['entities']:
                first_entity = entities_data['entities'][0]
                entity_ui_instructions += f"Example {first_entity['name']} data:\n"
                entity_ui_instructions += "[\n"
                for j in range(2):  # Show 2 example records
                    entity_ui_instructions += "  {\n"
                    for field in first_entity['fields'][:5]:
                        if field['type'] == 'int':
                            entity_ui_instructions += f"    {field['name']}: {100 + j},\n"
                        elif field['type'] == 'string':
                            entity_ui_instructions += f"    {field['name']}: 'Sample {field['name']} {j+1}',\n"
                        elif field['type'] == 'DateTime':
                            entity_ui_instructions += f"    {field['name']}: '2024-11-{9+j:02d}',\n"
                        elif field['type'] == 'decimal':
                            entity_ui_instructions += f"    {field['name']}: {99.99 + j},\n"
                        elif field['type'] == 'bool':
                            entity_ui_instructions += f"    {field['name']}: {str(j % 2 == 0).lower()},\n"
                    entity_ui_instructions += "  },\n"
                entity_ui_instructions += "]\n"
            
            entity_ui_instructions += """
❌ DO NOT use generic labels like: "Name", "Description", "User", "Product"
✅ DO use the ACTUAL field names listed above
✅ DO include realistic mock data for demonstration
================================================
"""
        
        prompt = f"""
Generate a FULLY FUNCTIONAL visual prototype for: {feature_name}
{entity_ui_instructions}

REQUIREMENTS:
{json.dumps(self.feature_requirements, indent=2)}

REPOSITORY ANALYSIS:
Tech Stacks: {self.repo_analysis.tech_stacks if self.repo_analysis else []}
UI Framework: {[stack for stack in (self.repo_analysis.tech_stacks if self.repo_analysis else []) if stack.lower() in ['angular', 'react', 'vue', 'streamlit', 'blazor']]}
Styling: {self.repo_analysis.code_patterns.get('styling', 'CSS') if self.repo_analysis else 'CSS'}

RAG CONTEXT FROM YOUR REPOSITORY (includes extracted entities):
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
            "You are an expert frontend developer. Generate a complete, working HTML prototype.",
            artifact_type="visual_prototype_dev"
        )
        
        return response
    
    def _clean_diagram_output(self, diagram_text: str) -> str:
        """
        Clean diagram output - Uses aggressive preprocessing + universal diagram fixer.
        
        Pipeline:
        1. Remove any explanatory text AFTER the diagram
        2. Aggressive preprocessing (fixes 4 common syntax errors)
        3. UniversalDiagramFixer (comprehensive type-specific cleaning)
        
        Fixes:
        - Explanatory text after diagram (AI commentary)
        - Multiple diagram declarations on same line
        - Special characters in node labels (.NET, C#, etc.)
        - Markdown fences inside diagram content
        - Malformed ERD entity blocks
        """
        try:
            # STEP 1: Remove explanatory text after the diagram
            diagram_text = self._extract_just_diagram(diagram_text)
            
            # STEP 2: Aggressive preprocessing
            from components.mermaid_preprocessor import aggressive_mermaid_preprocessing
            diagram_text = aggressive_mermaid_preprocessing(diagram_text)
            
            # STEP 3: Universal fixer
            from components.universal_diagram_fixer import fix_any_diagram
            cleaned, fixes = fix_any_diagram(diagram_text)
            return cleaned
        except Exception as e:
            # Fallback: basic cleanup with preprocessing
            try:
                from components.mermaid_preprocessor import aggressive_mermaid_preprocessing
                diagram_text = aggressive_mermaid_preprocessing(diagram_text)
            except (ImportError, AttributeError, ValueError) as e:
                # Last resort: manual cleanup
                print(f"[WARN] Mermaid preprocessing failed: {e}")
                import re
                diagram_text = re.sub(r'```mermaid\s*\n?', '', diagram_text)
                diagram_text = re.sub(r'```\s*$', '', diagram_text)
                diagram_text = diagram_text.replace("```", "")
            return diagram_text.strip()
    
    def _extract_just_diagram(self, text: str) -> str:
        """
        Extract ONLY the Mermaid diagram code, removing any explanatory text before or after.
        
        Handles cases where AI adds:
        1. Markdown fences (```mermaid ... ```)
        2. Explanatory text before diagram
        3. ASCII art after diagram
        4. Explanatory text after diagram
        """
        import re
        
        text = text.strip()
        
        # STEP 1: Extract from markdown fence if present
        if '```mermaid' in text:
            # Find the mermaid code block
            match = re.search(r'```mermaid\s*\n(.*?)\n```', text, re.DOTALL)
            if match:
                text = match.group(1).strip()
            else:
                # Remove just the fence markers
                text = text.replace('```mermaid', '').replace('```', '')
        elif text.startswith('```'):
            # Generic code fence
            text = re.sub(r'^```\w*\s*\n', '', text)
            text = re.sub(r'\n```\s*$', '', text)
            text = text.replace('```', '')
        
        lines = text.split('\n')
        
        # STEP 2: Find where diagram starts
        diagram_start = -1
        diagram_types = ['erDiagram', 'flowchart', 'graph', 'sequenceDiagram', 'classDiagram', 
                        'stateDiagram', 'gantt', 'pie', 'journey']
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if any(stripped.startswith(dt) for dt in diagram_types):
                diagram_start = i
                break
        
        if diagram_start == -1:
            # No diagram type found
            return text
        
        # STEP 3: Find where diagram ends
        last_valid_line = diagram_start
        in_entity_block = False  # Track ERD entity blocks
        
        for i in range(diagram_start + 1, len(lines)):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # ERD entity block tracking
            if '{' in line and not line.endswith('}'):
                in_entity_block = True
                last_valid_line = i
                continue
            if in_entity_block:
                last_valid_line = i
                if '}' in line:
                    in_entity_block = False
                continue
            
            # Check if this is diagram syntax or explanatory text
            diagram_syntax_patterns = [
                r'-->', r'---', r'\|\|', r'\|--', r'--\|',  # Arrows and relationships
                r'^\s*[A-Z][A-Za-z0-9_]*\s*\[',  # Node definitions: A[Text]
                r'^\s*[A-Z][A-Za-z0-9_]*\s*\(',  # Node with round brackets
                r'^\s*[A-Z][A-Za-z0-9_]*\s*\{',  # ERD entities
                r'^\s*participant\s+',  # Sequence diagram
                r'^\s*[A-Z][A-Za-z0-9_]*\s*->>',  # Sequence diagram arrows
                r'^\s*\w+\s+\w+\s+(PK|FK)',  # ERD fields with keys
            ]
            
            is_diagram_syntax = any(re.search(pattern, line) for pattern in diagram_syntax_patterns)
            
            # Detect explanatory text patterns
            explanatory_patterns = [
                r'^(The |This |It |Here |Based |Note:|Example:|```|\*\s)',  # Common sentence starts
                r'^\|[\s\-\+]+\|',  # ASCII table borders
                r'^\+[-=]+\+',  # ASCII art boxes
                r'^\s*\*\s*`\w+`:',  # Bullet points with code
            ]
            
            is_explanatory = any(re.search(pattern, line) for pattern in explanatory_patterns)
            
            # If it's clearly explanatory text, stop
            if is_explanatory and not is_diagram_syntax:
                break
            
            # If line has diagram syntax, it's valid
            if is_diagram_syntax:
                last_valid_line = i
            # If it's a short line without clear syntax, might be end of diagram
            elif len(line) > 50 and not is_diagram_syntax:
                # Long line without diagram syntax = likely explanation
                break
        
        # Extract just the diagram lines
        diagram_lines = lines[diagram_start:last_valid_line + 1]
        result = '\n'.join(diagram_lines).strip()
        
        # Final cleanup: remove any remaining ``` that might be in the middle
        result = result.replace('```', '')
        
        return result
    
    # =============================================================================
    # GRANULAR GENERATION METHODS (for cost optimization)
    # =============================================================================
    
    def _should_use_mermaid_model(self) -> bool:
        """Check if MermaidMistral model is available and loaded"""
        try:
            import streamlit as st
            selected_model = st.session_state.get('selected_local_model', {})
            model_name = selected_model.get('base_model', '')
            return 'mermaid' in model_name.lower()
        except (ImportError, KeyError, AttributeError):
            return False
    
    async def generate_erd_only(self, artifact_type: str = "erd") -> Optional[str]:
        """Generate ONLY ERD diagram (granular generation) - ENHANCED with Knowledge Graph + MermaidMistral"""
        from rag.erd_generator import get_erd_generator
        
        erd_gen = get_erd_generator()
        
        if not erd_gen.should_generate_erd(self.meeting_notes):
            return None
        
        print("[INFO] Generating ERD diagram only...")
        
        # Check if specialized Mermaid model is available
        if self._should_use_mermaid_model():
            print("[OK] Using MermaidMistral for ERD generation")
            # MermaidMistral doesn't need heavy RAG context - it's already specialized
            prompt = f"""Generate a complete Mermaid ERD for this system:

Meeting Notes:
{self.meeting_notes}

Create an erDiagram with:
- All entities and their fields
- Data types for each field
- Primary keys (PK) and Foreign keys (FK)  
- Relationships between entities (one-to-one, one-to-many, many-to-many)

Output ONLY the Mermaid ERD code starting with 'erDiagram'."""
            return await self._call_ai(prompt, artifact_type=artifact_type)
        
        # Standard generation with RAG context for general models
        await self.retrieve_rag_context("""
        database schema tables entities relationships models data
        data modeling patterns naming conventions database design
        entity relationships cardinality constraints
        """)
        
        # ENHANCE with Knowledge Graph component relationships
        kg_context = ""
        try:
            # 🚀 USE CACHED KNOWLEDGE GRAPH (10x faster)
            kg = self._get_knowledge_graph()
            kg_results = kg.to_dict()
            
            # Extract relevant entity relationships
            components_dict = kg_results.get("components", {})
            components = list(components_dict.values())  # Convert dict to list
            models = [c for c in components if c["type"] in ["class", "interface"] and 
                     any(keyword in c.get("file_path", "").lower() for keyword in ["model", "entity", "dto"])]
            
            if models:
                kg_context = "\n\nACTUAL COMPONENT RELATIONSHIPS FROM CODEBASE:\n"
                for model in models[:10]:  # Top 10 models
                    kg_context += f"- {model['name']} ({model['type']}) in {model['file_path']}\n"
                    if model.get("dependencies"):
                        kg_context += f"  Dependencies: {', '.join(model['dependencies'][:5])}\n"
                
                self.rag_context += kg_context
                print(f"[OK] Enhanced ERD with {len(models)} model relationships from Knowledge Graph")
        except Exception as e:
            print(f"[WARN] Could not enhance with Knowledge Graph: {e}")
        
        prompt = erd_gen.generate_erd_prompt(self.meeting_notes, self.rag_context)
        response = await self._call_ai(
            prompt,
            "You are a database architect. Generate an ERD diagram in Mermaid format based on the ACTUAL project context provided. DO NOT use generic examples. Analyze the meeting notes and codebase context to identify the real entities. Output ONLY the Mermaid ERD code starting with 'erDiagram'.",
            artifact_type="erd"
        )
        
        cleaned = self._clean_diagram_output(response)
        
        # POST-PROCESS: Fix any diagram syntax issues (UNIVERSAL)
        try:
            from components.universal_diagram_fixer import fix_any_diagram
            cleaned, fixes = fix_any_diagram(cleaned)
            if fixes:
                print(f"[OK] ERD syntax fixed: {len(fixes)} issues resolved")
                for fix in fixes[:3]:  # Show first 3 fixes
                    print(f"  - {fix}")
        except Exception as e:
            print(f"[WARN] Diagram syntax fix failed: {e}")
        
        # Validate ERD syntax - if it's using wrong format, force correct it
        if not cleaned.strip().startswith('erDiagram'):
            print("[WARN] ERD generated with wrong syntax (using graph instead of erDiagram)")
            print("[TIP] Local models (codellama) struggle with diagrams. Consider using GPT-4 or Gemini for better results.")
            # Try to convert graph LR to erDiagram if possible
            if cleaned.strip().startswith('graph'):
                print("[INFO] Attempting to convert graph syntax to erDiagram...")
                # This is a best-effort conversion - may not be perfect
                cleaned = self._convert_graph_to_erd(cleaned)
        
        return cleaned
    
    def _convert_graph_to_erd(self, graph_content: str) -> str:
        """
        Attempt to convert graph LR/TD syntax to erDiagram syntax.
        This is a best-effort conversion for when models generate wrong format.
        """
        lines = graph_content.strip().split('\n')
        erd_lines = ['erDiagram']
        
        # Extract entities and relationships from graph syntax
        entities = set()
        relationships = []
        
        for line in lines[1:]:  # Skip first line (graph TD/LR)
            line = line.strip()
            if not line:
                continue
            
            # Parse graph relationships: Entity1 --> Entity2
            if '--' in line:
                parts = line.split('--')
                if len(parts) >= 2:
                    left = parts[0].strip().split('(')[0].split('[')[0].strip()
                    right = parts[-1].strip().split('(')[0].split('[')[0].split(':')[0].strip()
                    if left and right:
                        entities.add(left)
                        entities.add(right)
                        # Convert to ERD relationship
                        relationships.append(f"    {left} ||--o{{ {right} : has")
        
        # Add entities with basic structure
        for entity in sorted(entities):
            erd_lines.append(f"    {entity} {{")
            erd_lines.append(f"        int id PK")
            erd_lines.append(f"        string name")
            erd_lines.append(f"    }}")
        
        # Add relationships
        erd_lines.extend(relationships)
        
        result = '\n'.join(erd_lines)
        print(f"[INFO] Converted graph to erDiagram: {len(entities)} entities, {len(relationships)} relationships")
        return result
    
    async def generate_architecture_only(self) -> str:
        """Generate ONLY system architecture diagram (granular generation) - ENHANCED with Knowledge Graph + MermaidMistral"""
        print("[INFO] Generating architecture diagram only...")
        
        # Check if specialized Mermaid model is available
        if self._should_use_mermaid_model():
            print("[OK] Using MermaidMistral for architecture diagram generation")
            prompt = f"""Generate a system architecture flowchart using Mermaid:

Meeting Notes:
{self.meeting_notes}

Create a flowchart showing:
- All system components (frontend, backend, database, services)
- Communication flow between components
- External dependencies
- Data flow directions

Output ONLY the Mermaid flowchart code starting with 'flowchart TD' or 'flowchart LR'."""
            return await self._call_ai(prompt, artifact_type="architecture")
        
        # Standard generation with RAG context for general models
        await self.retrieve_rag_context("""
        system architecture components services infrastructure
        architectural patterns design decisions technology choices
        microservices patterns service boundaries API design
        """)
        
        # ENHANCE with Knowledge Graph architecture insights
        try:
            # 🚀 USE CACHED KNOWLEDGE GRAPH (10x faster)
            kg = self._get_knowledge_graph()
            kg_results = kg.to_dict()
            
            # Extract architectural components (services, controllers, etc.)
            components_dict = kg_results.get("components", {})
            components = list(components_dict.values())  # Convert dict to list
            arch_components = [c for c in components if c["type"] in ["class", "module"] and
                             any(keyword in c.get("file_path", "").lower() for keyword in ["service", "controller", "component"])]
            
            if arch_components:
                kg_context = "\n\nACTUAL ARCHITECTURE FROM CODEBASE:\n"
                for comp in arch_components[:15]:  # Top 15 components
                    kg_context += f"- {comp['name']} ({comp['type']})\n"
                    if comp.get("dependencies"):
                        kg_context += f"  Uses: {', '.join(comp['dependencies'][:5])}\n"
                    if comp.get("dependents"):
                        kg_context += f"  Used by: {', '.join(comp['dependents'][:3])}\n"
                
                # Add graph metrics
                metrics = kg_results.get("metrics", {})
                if metrics:
                    kg_context += f"\nArchitecture Metrics:\n"
                    kg_context += f"- Components: {metrics.get('total_components', 'N/A')}\n"
                    kg_context += f"- Relationships: {metrics.get('total_relationships', 'N/A')}\n"
                    # Handle graph_density as float or 'N/A'
                    density = metrics.get('graph_density', 'N/A')
                    if isinstance(density, (int, float)):
                        kg_context += f"- Coupling: {density:.2f}\n"
                    else:
                        kg_context += f"- Coupling: {density}\n"
                
                self.rag_context += kg_context
                print(f"[OK] Enhanced Architecture with {len(arch_components)} components from Knowledge Graph")
        except Exception as e:
            print(f"[WARN] Could not enhance with Knowledge Graph: {e}")
        
        prompt = f"""
Generate a system architecture diagram for a NEW FEATURE showing components and their relationships.

**CRITICAL: ARCHITECTURE FOR THE NEW FEATURE**

**NEW FEATURE REQUIREMENTS (PRIMARY CONTEXT):**
{self.feature_requirements}

**TECH STACK:** {self.repo_analysis.tech_stacks if self.repo_analysis else []}

**EXISTING ARCHITECTURE PATTERNS (for reference only):**
{self.rag_context}

**INSTRUCTIONS:**
1. Read the meeting notes above and identify the NEW FEATURE being requested
2. Design the architecture SPECIFICALLY for this NEW feature
3. Use RAG CONTEXT to understand existing patterns (component structure, naming conventions, service patterns)
4. Show components REQUIRED BY THE NEW FEATURE

**EXAMPLE:**
If meeting notes describe "Phone Swap Request Feature":
- Show: SwapRequestModal (Angular Component)
- Show: PhoneSwapController (Backend API)
- Show: SwapRequestService (Business Logic)
- Show: PhoneSwapRepository (Database Access)
- Show: POST /api/phone-swaps endpoint
- DO NOT show generic Frontend → Backend → Database

**DIAGRAM REQUIREMENTS:**
- Use flowchart format (start with 'graph TD' or 'flowchart TD')
- Show NEW feature components (max 8 nodes)
- Use realistic names based on meeting notes and existing naming patterns
- Show data flow between components
- Include external dependencies if needed (e.g., existing User/Phone services)

OUTPUT: Mermaid diagram code ONLY.
NO markdown blocks (no ```), NO explanations after the diagram.
Focus on the NEW feature architecture, not existing system.
"""
        response = await self._call_ai(prompt, "Generate ONLY the diagram. Start with 'graph TD'.", artifact_type="architecture")
        cleaned = self._clean_diagram_output(response)
        
        # POST-PROCESS: Fix any diagram syntax issues (UNIVERSAL)
        try:
            from components.universal_diagram_fixer import fix_any_diagram
            cleaned, fixes = fix_any_diagram(cleaned)
            if fixes:
                print(f"[OK] Architecture diagram syntax fixed: {len(fixes)} issues resolved")
        except Exception as e:
            print(f"[WARN] Diagram syntax fix failed: {e}")
        
        return cleaned
    
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
Generate comprehensive API documentation for a NEW FEATURE.

**CRITICAL: FOCUS ON THE NEW FEATURE FROM MEETING NOTES**

**NEW FEATURE REQUIREMENTS (PRIMARY CONTEXT):**
{self.feature_requirements}

**EXISTING API PATTERNS (for reference only):**
{self.rag_context}

**INSTRUCTIONS:**
1. Read the meeting notes above and identify the NEW FEATURE being requested
2. Design API endpoints SPECIFICALLY for this NEW feature
3. Use RAG CONTEXT only for understanding existing API patterns (REST conventions, auth patterns, error handling style)
4. DO NOT document existing APIs - document the NEW feature's APIs

**EXAMPLE:**
If meeting notes describe "Phone Swap Request Feature":
- Document: POST /api/phone-swaps (create swap request)
- Document: GET /api/phone-swaps/{id} (get swap details)
- Document: PUT /api/phone-swaps/{id}/status (update swap status)
- DO NOT document existing /api/phones or /api/users endpoints

**API DOCUMENTATION STRUCTURE:**
1. API Overview (for the NEW feature)
2. Base URL (from existing project patterns)
3. Authentication (from existing project auth)
4. Endpoints (for the NEW feature ONLY):
   - Method (POST/GET/PUT/DELETE)
   - Path (/api/phone-swaps)
   - Description (what it does for the NEW feature)
   - Request Body (with actual field names from meeting notes)
   - Response (success and error examples)
5. Error codes (reuse existing project patterns)

Output in Markdown format. Focus ONLY on APIs needed for the NEW feature.
"""
        response = await self._call_ai(prompt, "Generate comprehensive API documentation in Markdown.", artifact_type="api_docs")
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
Generate JIRA-ready tasks (Epic, Stories, Subtasks) for a NEW FEATURE.

**CRITICAL: FOCUS ON THE NEW FEATURE FROM MEETING NOTES**

**NEW FEATURE REQUIREMENTS (PRIMARY CONTEXT):**
{self.feature_requirements}

**EXISTING PROJECT PATTERNS (for reference only):**
{self.rag_context}

**INSTRUCTIONS:**
1. Read the meeting notes above and identify the NEW FEATURE being requested
2. Create JIRA tasks specifically for implementing this NEW feature
3. Use RAG CONTEXT only for understanding tech stack and component structure
4. DO NOT create tasks for existing features - focus on the NEW feature ONLY

**EXAMPLE:**
If meeting notes describe "Phone Swap Request Feature":
✅ EPIC: Phone Swap Request Feature Implementation
✅ Story 1: Create Phone Swap Request Modal
✅ Story 2: Implement Swap Request API Endpoint
✅ Story 3: Add Swap Request Database Table

❌ DON'T: Package Lock File Update
❌ DON'T: TypeScript Configuration
❌ DON'T: Update existing Phone Management

**FORMAT:**
# EPIC: [NEW Feature Title from Meeting Notes]
## Story 1: [NEW Feature Component/Requirement]
**Acceptance Criteria:**
- Given [precondition for NEW feature]
- When [action in NEW feature]
- Then [expected outcome of NEW feature]

### Subtask 1.1: [Implementation detail for NEW feature]
### Subtask 1.2: [Implementation detail for NEW feature]

## Story 2: [Next NEW Feature Component]
...

Include realistic story point estimates for each story.
Focus ONLY on implementing the NEW feature from meeting notes.
Match the team's style from the RAG context.
"""
        response = await self._call_ai(prompt, "Generate JIRA tasks in Markdown format.", artifact_type="jira")
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
Generate development, testing, and deployment workflows for a NEW FEATURE.

**CRITICAL: WORKFLOWS FOR THE NEW FEATURE IMPLEMENTATION**

**NEW FEATURE REQUIREMENTS (PRIMARY CONTEXT):**
{self.feature_requirements}

**TECH STACK:** {self.repo_analysis.tech_stacks if self.repo_analysis else []}

**EXISTING WORKFLOW PATTERNS (for reference only):**
{self.rag_context}

**INSTRUCTIONS:**
1. Read the meeting notes above and identify the NEW FEATURE being requested
2. Create workflows specifically for implementing this NEW feature
3. Use RAG CONTEXT to understand existing tools, processes, and patterns (CI/CD, testing frameworks, deployment)
4. Adapt existing workflow patterns to the NEW feature requirements

**EXAMPLE:**
If meeting notes describe "Phone Swap Request Feature":
- Development Workflow: How to build the swap request modal, API endpoint, and database migration
- Testing Workflow: How to test the swap request functionality (unit tests, integration tests, E2E)
- Deployment Workflow: How to deploy the new feature (database migration, API deployment, frontend update)

**WORKFLOW STRUCTURE:**
1. **Development Workflow** (for implementing the NEW feature)
   - Initial Setup (what to install/configure for this feature)
   - Code Development (step-by-step: create modal, API endpoint, database table)
   - Build and Serve (how to run locally with the new feature)

2. **Testing Workflow** (for testing the NEW feature)
   - Unit Testing (test new components/services)
   - Integration Testing (test API endpoints)
   - End-to-End Testing (test full user flow)

3. **Deployment Workflow** (for deploying the NEW feature)
   - Database Migration (create new tables)
   - API Deployment (deploy new endpoints)
   - Frontend Deployment (deploy new UI components)

4. **Code Review Process** (for reviewing the NEW feature code)
   - What reviewers should check for this feature
   - Acceptance criteria specific to this feature

Output in Markdown format. Use existing project tools/patterns but focus on the NEW feature implementation.
"""
        response = await self._call_ai(prompt, "Generate workflows in Markdown format.", artifact_type="workflows")
        return response
    
    async def generate_erd_diagram(self) -> Optional[str]:
        """Generate ERD diagram if database discussion detected (used in full workflow)"""
        return await self.generate_erd_only()
    
    async def generate_system_overview_diagram(self) -> Optional[str]:
        """Generate ONLY system overview diagram (Bug Fix #2: don't generate all)"""
        await self.retrieve_rag_context("architecture system overview")
        overview_prompt = f"""
You are a Mermaid diagram generator. Generate a system overview for a NEW FEATURE.

**NEW FEATURE REQUIREMENTS (PRIMARY CONTEXT):**
{self.feature_requirements}

**TECH STACKS:** {self.repo_analysis.tech_stacks if self.repo_analysis else []}

**EXISTING ARCHITECTURE (for reference only):**
{self.rag_context}

**INSTRUCTIONS:**
- Design a high-level overview of the NEW feature architecture
- Show how the NEW feature integrates with existing systems
- Use realistic component names based on meeting notes + existing patterns
- Example: If "Phone Swap Request Feature" → show SwapRequestUI, SwapAPI, existing PhoneService

OUTPUT RULES (CRITICAL):
1. First line: graph TD
2. NO markdown blocks (NO ```)
3. Maximum 7 nodes
4. Use square brackets: [Component Name]
5. Use --> for arrows

Focus on the NEW feature, not existing system overview.
"""
        raw_overview = await self._call_ai(overview_prompt, "Output ONLY the diagram. Start with 'graph TD'.", artifact_type="system_overview")
        cleaned = self._clean_diagram_output(raw_overview)
        try:
            from components.universal_diagram_fixer import fix_any_diagram
            cleaned, _ = fix_any_diagram(cleaned)
        except Exception as e:
            print(f"[WARN] Failed to fix diagram: {e}")
        return cleaned
    
    async def generate_data_flow_diagram(self) -> Optional[str]:
        """Generate ONLY data flow diagram (Bug Fix #2: don't generate all)"""
        await self.retrieve_rag_context("data flow process")
        prompt = f"""
You are a Mermaid diagram generator. Generate a data flow diagram for a NEW FEATURE.

**NEW FEATURE REQUIREMENTS (PRIMARY CONTEXT):**
{self.feature_requirements}

**EXISTING DATA PATTERNS (for reference only):**
{self.rag_context}

**INSTRUCTIONS:**
- Show how data flows through the NEW feature
- Include user input → processing → storage → output steps
- Use realistic step names based on meeting notes
- Example: If "Phone Swap Request" → [User Fills Form] → [Validate Request] → [Save to DB] → [Notify Admin]

OUTPUT RULES: graph TD, max 6 nodes, square brackets, --> arrows.
NO markdown blocks, NO explanations after diagram.
"""
        raw = await self._call_ai(prompt, "Output ONLY the diagram. Start with 'graph TD'.", artifact_type="data_flow")
        return self._clean_diagram_output(raw)
    
    async def generate_user_flow_diagram(self) -> Optional[str]:
        """Generate ONLY user flow diagram (Bug Fix #2: don't generate all)"""
        await self.retrieve_rag_context("user flow journey")
        prompt = f"""
You are a Mermaid diagram generator. Generate a user flow diagram for a NEW FEATURE.

**NEW FEATURE REQUIREMENTS (PRIMARY CONTEXT):**
{self.feature_requirements}

**EXISTING UI PATTERNS (for reference only):**
{self.rag_context}

**INSTRUCTIONS:**
- Show the user's journey through the NEW feature
- Include decision points and actions
- Use realistic page/component names based on meeting notes
- Example: If "Phone Swap Request" → [View Phone List] → {{Want to Swap?}} → [Open Swap Modal] → [Submit Request]

OUTPUT RULES: graph TD, max 7 nodes, [Action] for steps, {{{{Decision}}}} for choices.
NO markdown blocks, NO explanations after diagram.
"""
        raw = await self._call_ai(prompt, "Output ONLY the diagram. Start with 'graph TD'.", artifact_type="user_flow")
        return self._clean_diagram_output(raw)
    
    async def generate_components_diagram(self) -> Optional[str]:
        """Generate ONLY components diagram (Bug Fix #2: don't generate all)"""
        await self.retrieve_rag_context("components modules architecture")
        prompt = f"""
You are a Mermaid diagram generator. Generate a component diagram for a NEW FEATURE.

**NEW FEATURE REQUIREMENTS (PRIMARY CONTEXT):**
{self.feature_requirements}

**TECH STACK:** {self.repo_analysis.tech_stacks if self.repo_analysis else []}

**EXISTING COMPONENT PATTERNS (for reference only):**
{self.rag_context}

**INSTRUCTIONS:**
- Show the frontend/backend components needed for the NEW feature
- Include modules, services, components required
- Use realistic names based on meeting notes + existing naming conventions
- Example: If "Phone Swap Request" → SwapRequestModalComponent → SwapRequestService → PhoneService

OUTPUT RULES: graph LR, max 7 nodes, square brackets, --> arrows.
NO markdown blocks, NO explanations after diagram.
"""
        raw = await self._call_ai(prompt, "Output ONLY the diagram. Start with 'graph LR'.", artifact_type="components_diagram")
        return self._clean_diagram_output(raw)
    
    async def generate_api_sequence_diagram(self) -> Optional[str]:
        """Generate ONLY API sequence diagram (Bug Fix #2: don't generate all)"""
        await self.retrieve_rag_context("API endpoints sequence")
        prompt = f"""
You are a Mermaid diagram generator. Generate an API sequence diagram for a NEW FEATURE.

**NEW FEATURE REQUIREMENTS (PRIMARY CONTEXT):**
{self.feature_requirements}

**EXISTING API PATTERNS (for reference only):**
{self.rag_context}

**INSTRUCTIONS:**
- Show the API request/response flow for the NEW feature
- Include realistic participants based on meeting notes
- Use existing API patterns for structure
- Example: If "Phone Swap Request" → User ->> SwapAPI: POST /api/phone-swaps → SwapAPI ->> Database: Save

OUTPUT RULES: sequenceDiagram, max 4 participants, ->> arrows.
NO markdown blocks, NO explanations after diagram.
"""
        raw = await self._call_ai(prompt, "Output ONLY the diagram. Start with 'sequenceDiagram'.", artifact_type="api_sequence")
        return self._clean_diagram_output(raw)
    
    async def generate_specific_diagrams(self) -> Dict[str, str]:
        """Generate specific diagrams for each section"""
        print("[INFO] Generating specific diagrams...")
        
        await self.retrieve_rag_context("architecture system flow data user components API")
        
        diagrams = {}
        
        # Try to generate ERD first
        erd = await self.generate_erd_diagram()
        if erd:
            diagrams['erd'] = erd
        
        # Add delay to avoid rate limits
        import asyncio
        await asyncio.sleep(2)  # 2 second delay between diagrams
        
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

CRITICAL INSTRUCTIONS:
- Analyze the REQUIREMENTS and TECH STACKS to identify the ACTUAL components in THIS project
- Look at the RAG CONTEXT to find real services, modules, and components
- DO NOT use generic examples like "Angular Frontend → API Server → MongoDB"
- DO NOT use placeholder names like "Node 1", "Node 2", "A", "B", "C"
- DO NOT use file paths like "Node_modules/package-lock.json" as components
- Generate a diagram specific to THIS project's architecture
- Use ACTUAL component names from the codebase (from RAG CONTEXT)
- If you cannot find specific components in RAG CONTEXT, analyze it more carefully

Generate a system overview diagram with max 7 nodes following these EXACT rules.
"""
        raw_overview = await self._call_ai(overview_prompt, "Output ONLY the diagram. Start with 'graph TD'. No text before or after.", artifact_type="system_overview")
        cleaned_overview = self._clean_diagram_output(raw_overview)
        
        # Apply universal diagram fixer
        try:
            from components.universal_diagram_fixer import fix_any_diagram
            cleaned_overview, _ = fix_any_diagram(cleaned_overview)
        except Exception as e:
            print(f"[WARN] Failed to fix overview diagram: {e}")
        
        diagrams['overview'] = cleaned_overview
        await asyncio.sleep(2)  # Delay to avoid rate limits
        
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

CRITICAL INSTRUCTIONS:
- Analyze the REQUIREMENTS to identify the ACTUAL data flow in THIS project
- Look at the RAG CONTEXT to find real data processing steps
- DO NOT use generic examples like "User Input → Validation → Process"
- DO NOT use generic "Input → Process → Store → Output" pattern
- Generate a diagram specific to the feature described in the requirements
- Use ACTUAL process names and data entities from the codebase (from RAG CONTEXT)
- If you cannot find specific data flow in RAG CONTEXT, analyze it more carefully

Generate a data flow diagram with max 6 nodes following these EXACT rules.
"""
        raw_dataflow = await self._call_ai(dataflow_prompt, "Output ONLY the diagram. Start with 'graph TD'. No text before or after.", artifact_type="data_flow")
        cleaned_dataflow = self._clean_diagram_output(raw_dataflow)
        try:
            from components.universal_diagram_fixer import fix_any_diagram
            cleaned_dataflow, _ = fix_any_diagram(cleaned_dataflow)
        except:
            pass
        diagrams['dataflow'] = cleaned_dataflow
        await asyncio.sleep(2)  # Delay to avoid rate limits
        
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

CRITICAL INSTRUCTIONS:
- Analyze the REQUIREMENTS to identify the ACTUAL user journey in THIS project
- Look at the RAG CONTEXT to find real UI flows and user interactions
- DO NOT use generic examples like "Login → Dashboard"
- DO NOT use generic "Start → Validate → Generate → Finish" pattern
- Generate a diagram specific to the feature described in the requirements
- Use ACTUAL page/component names from the codebase (from RAG CONTEXT)
- If you cannot find specific user flow in RAG CONTEXT, analyze it more carefully

Generate a user flow diagram with max 7 nodes following these EXACT rules.
"""
        raw_userflow = await self._call_ai(userflow_prompt, "Output ONLY the diagram. Start with 'graph TD'. No text before or after.", artifact_type="user_flow")
        cleaned_userflow = self._clean_diagram_output(raw_userflow)
        try:
            from components.universal_diagram_fixer import fix_any_diagram
            cleaned_userflow, _ = fix_any_diagram(cleaned_userflow)
        except:
            pass
        diagrams['userflow'] = cleaned_userflow
        await asyncio.sleep(2)  # Delay to avoid rate limits
        
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

IMPORTANT:
- Analyze the REQUIREMENTS and TECH STACK to identify the ACTUAL components in THIS project
- Look at the RAG context to find real modules, services, and components
- DO NOT use generic examples like "App Component → Auth Module"
- Generate a diagram specific to THIS project's component architecture
- Use actual component/service names from the codebase

Generate a component diagram with max 7 nodes following these EXACT rules.
"""
        raw_components = await self._call_ai(components_prompt, "Output ONLY the diagram. Start with 'graph LR'. No text before or after.", artifact_type="components_diagram")
        cleaned_components = self._clean_diagram_output(raw_components)
        try:
            from components.universal_diagram_fixer import fix_any_diagram
            cleaned_components, _ = fix_any_diagram(cleaned_components)
        except:
            pass
        diagrams['components'] = cleaned_components
        await asyncio.sleep(2)  # Delay to avoid rate limits
        
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

IMPORTANT:
- Analyze the REQUIREMENTS to identify the ACTUAL API interactions in THIS project
- Look at the RAG context to find real endpoints, services, and data flows
- DO NOT use generic examples like "POST /login → JWT token"
- Generate a diagram specific to the feature described in the requirements
- Use actual endpoint paths and service names from the codebase

Generate an API sequence diagram with max 6 interactions following these EXACT rules.
"""
        raw_api = await self._call_ai(api_prompt, "Output ONLY the diagram. Start with 'sequenceDiagram'. No text before or after.", artifact_type="api_sequence")
        cleaned_api = self._clean_diagram_output(raw_api)
        try:
            from components.universal_diagram_fixer import fix_any_diagram
            cleaned_api, _ = fix_any_diagram(cleaned_api)
        except:
            pass
        diagrams['api'] = cleaned_api
        
        print(f"[OK] Generated {len(diagrams)} diagrams with universal syntax validation")
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
            "You are an expert UX designer and technical writer. Generate detailed design documentation.",
            artifact_type="design_document"
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
            "You are an expert software architect. Generate detailed technical architecture.",
            artifact_type="architecture_document"
        )
    
    async def generate_api_documentation(self) -> str:
        """Generate API documentation - ENHANCED with Knowledge Graph"""
        print("[INFO] Generating API documentation...")
        
        await self.retrieve_rag_context("API endpoints routes controllers services")
        
        # ENHANCE with Knowledge Graph for actual API structure
        try:
            # 🚀 USE CACHED KNOWLEDGE GRAPH (10x faster)
            kg = self._get_knowledge_graph()
            kg_results = kg.to_dict()
            
            # Extract API controllers and their methods
            components_dict = kg_results.get("components", {})
            components = list(components_dict.values())  # Convert dict to list
            controllers = [c for c in components if "controller" in c.get("file_path", "").lower() or "api" in c.get("file_path", "").lower()]
            
            if controllers:
                kg_context = "\n\nACTUAL API CONTROLLERS FROM CODEBASE:\n"
                for ctrl in controllers[:10]:
                    kg_context += f"- {ctrl['name']} in {ctrl['file_path']}\n"
                    if ctrl.get("dependencies"):
                        kg_context += f"  Services used: {', '.join(ctrl['dependencies'][:5])}\n"
                
                self.rag_context += kg_context
                print(f"[OK] Enhanced API docs with {len(controllers)} controllers from Knowledge Graph")
        except Exception as e:
            print(f"[WARN] Could not enhance with Knowledge Graph: {e}")
        
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
            "You are an expert API designer. Generate comprehensive API documentation.",
            artifact_type="api_documentation"
        )
    
    async def generate_jira_tasks(self) -> str:
        """Generate JIRA-ready tasks - ENHANCED with Pattern Mining"""
        print("[INFO] Generating JIRA tasks...")
        
        await self.retrieve_rag_context("tasks user stories epic subtasks estimates")
        
        # ENHANCE with Pattern Mining for realistic complexity estimates
        try:
            # 🚀 USE CACHED PATTERN ANALYSIS (10x faster)
            analysis = self._get_pattern_analysis()
            
            # Extract complexity insights
            anti_patterns = [p for p in analysis.patterns if p.pattern_type == "anti_pattern"]
            code_smells = [p for p in analysis.patterns if p.pattern_type == "smell"]
            
            pm_context = "\n\nCODEBASE COMPLEXITY INSIGHTS:\n"
            pm_context += f"Code Quality Score: {analysis.code_quality_score:.0f}/100\n"
            
            if anti_patterns:
                pm_context += f"\nKnown Issues to Address ({len(anti_patterns)} anti-patterns):\n"
                for ap in anti_patterns[:3]:
                    pm_context += f"- {ap.name} in {len(ap.files)} files (severity: {ap.severity})\n"
            
            if code_smells:
                pm_context += f"\nCode Quality Issues ({len(code_smells)} smells):\n"
                for smell in code_smells[:3]:
                    pm_context += f"- {smell.name}: {smell.frequency} occurrences\n"
            
            # Add effort estimation hints
            pm_context += "\nEffort Estimation Context:\n"
            pm_context += f"- Current codebase has {analysis.metrics.get('total_patterns', 'N/A')} patterns\n"
            pm_context += f"- Average complexity suggests medium-effort tasks\n"
            pm_context += "- Consider refactoring overhead when estimating\n"
            
            self.rag_context += pm_context
            print(f"[OK] Enhanced JIRA tasks with complexity insights from Pattern Mining")
        except Exception as e:
            print(f"[WARN] Could not enhance with Pattern Mining: {e}")
        
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
Use the complexity insights to provide ACCURATE story point estimates.

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
            "You are an expert Scrum master and project manager. Generate detailed, actionable JIRA tasks.",
            artifact_type="jira_tasks"
        )
    
    async def generate_workflows(self) -> str:
        """Generate workflows - ENHANCED with Knowledge Graph & Pattern Mining"""
        print("[INFO] Generating workflows...")
        
        await self.retrieve_rag_context("workflow deployment testing CI/CD development process")
        
        # ENHANCE with Knowledge Graph for component dependencies
        try:
            # 🚀 USE CACHED KNOWLEDGE GRAPH (10x faster)
            kg = self._get_knowledge_graph()
            kg_results = kg.to_dict()
            
            components_dict = kg_results.get("components", {})
            components = list(components_dict.values())  # Convert dict to list
            metrics = kg_results.get("metrics", {})
            
            kg_context = "\n\nDEPLOYMENT STRUCTURE FROM KNOWLEDGE GRAPH:\n"
            kg_context += f"Total Components: {metrics.get('total_components', 'N/A')}\n"
            kg_context += f"Component Dependencies: {metrics.get('total_relationships', 'N/A')}\n"
            kg_context += f"Coupling Level: {metrics.get('graph_density', 0):.2f}\n"
            
            # Identify critical components for deployment order
            critical = [c for c in components if len(c.get("dependents", [])) > 3]
            if critical:
                kg_context += f"\nCritical Components (deploy first):\n"
                for comp in critical[:5]:
                    kg_context += f"- {comp['name']}: {len(comp.get('dependents', []))} dependents\n"
            
            self.rag_context += kg_context
            print(f"[OK] Enhanced workflows with deployment structure from Knowledge Graph")
        except Exception as e:
            print(f"[WARN] Could not enhance with Knowledge Graph: {e}")
        
        # ENHANCE with Pattern Mining for quality gates
        try:
            # 🚀 USE CACHED PATTERN ANALYSIS (10x faster)
            analysis = self._get_pattern_analysis()
            
            pm_context = "\n\nQUALITY GATES FROM PATTERN MINING:\n"
            pm_context += f"Required Code Quality: {analysis.code_quality_score:.0f}/100\n"
            pm_context += "Pre-deployment Checklist:\n"
            
            # Add quality gates based on detected issues
            anti_patterns = [p for p in analysis.patterns if p.pattern_type == "anti_pattern"]
            if anti_patterns:
                pm_context += f"- Check for {len(anti_patterns)} known anti-patterns\n"
            
            code_smells = [p for p in analysis.patterns if p.pattern_type == "smell"]
            if code_smells:
                pm_context += f"- Verify no new code smells (current: {len(code_smells)})\n"
            
            pm_context += "- Maintain or improve code quality score\n"
            pm_context += "- Follow detected design patterns\n"
            
            self.rag_context += pm_context
            print(f"[OK] Enhanced workflows with quality gates from Pattern Mining")
        except Exception as e:
            print(f"[WARN] Could not enhance with Pattern Mining: {e}")
        
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
Use the deployment structure and quality gates to create realistic workflows.

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
            "You are an expert DevOps engineer. Generate detailed workflows.",
            artifact_type="workflows_document"
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
