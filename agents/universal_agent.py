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
        """Initialize AI client (supports Local Fine-tuned, OpenAI, Gemini, Groq) with global key persistence"""
        # Import global API key manager
        try:
            from config.api_key_manager import api_key_manager
            global_keys = api_key_manager.get_all_keys()
        except:
            global_keys = {'groq': None, 'openai': None, 'gemini': None}
        
        # Track if we've already logged connection status (prevent spam on reruns)
        import streamlit as st
        logged_key = '_agent_conn_logged'
        already_logged = False
        try:
            already_logged = st.session_state.get(logged_key, False)
        except:
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
                except:
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
                except:
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
                except:
                    pass
            _set_active_provider("Google Gemini 2.0 Flash")
            return
        
        if not already_logged:
            print("[WARN] No AI model connected. Set GROQ_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY")
            try:
                st.session_state[logged_key] = True
            except:
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
    
    async def _call_ai(self, prompt: str, system_prompt: str = None, artifact_type: str = None) -> str:
        """
        Call AI model with RAG context and automatic model selection.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            artifact_type: Type of artifact being generated (for automatic model selection)
        """
        if not self.client:
            raise Exception("No AI client available")
        
        # Include RAG context in prompt (context already has headers from context_optimizer)
        full_prompt = f"""{self.rag_context}

USER REQUEST:
{prompt}
"""
        
        # Ollama provider with automatic model selection
        if self.client_type == 'ollama' and hasattr(self, 'model_router') and artifact_type:
            from config.artifact_model_mapping import get_artifact_mapper
            
            mapper = get_artifact_mapper()
            task_type = mapper.get_task_type(artifact_type)
            model_name = mapper.get_model_name(artifact_type, prefer_fine_tuned=True)
            
            # Try local model first
            try:
                response = await self.model_router.generate(
                    task_type=task_type,
                    prompt=full_prompt,
                    system_message=system_prompt,
                    temperature=0.2
                )
                
                if response.success:
                    return response.content
                else:
                    # Local model failed, try cloud fallback
                    print(f"[WARN] Local model failed: {response.error_message}. Falling back to cloud...")
                    # Fall through to cloud providers below
            except Exception as e:
                print(f"[WARN] Ollama generation failed: {e}. Falling back to cloud...")
                # Fall through to cloud providers
        
        # Cloud fallback: Try cloud providers when local fails
        if self.client_type == 'ollama' or (self.client_type == 'local_finetuned' and not hasattr(self, 'client')):
            # Local failed, try cloud providers in order of preference
            from config.artifact_model_mapping import get_artifact_mapper
            from config.api_key_manager import api_key_manager
            
            mapper = get_artifact_mapper()
            
            # Select best cloud model for artifact type
            if artifact_type:
                task_type = mapper.get_task_type(artifact_type)
                
                # Smart cloud model selection based on artifact type
                cloud_providers = []
                
                # Diagrams: Gemini Flash (free, fast)
                if task_type == 'mermaid':
                    cloud_providers = [
                        ('gemini', 'gemini-2.0-flash-exp'),
                        ('groq', 'llama-3.3-70b-versatile'),
                        ('openai', 'gpt-4')
                    ]
                # Code/HTML: Groq (fast, free) or GPT-4 (quality)
                elif task_type in ['code', 'html']:
                    cloud_providers = [
                        ('groq', 'llama-3.3-70b-versatile'),
                        ('gemini', 'gemini-2.0-flash-exp'),
                        ('openai', 'gpt-4')
                    ]
                # Documentation: Gemini (free) or Groq (fast)
                elif task_type == 'documentation':
                    cloud_providers = [
                        ('gemini', 'gemini-2.0-flash-exp'),
                        ('groq', 'llama-3.3-70b-versatile'),
                        ('openai', 'gpt-4')
                    ]
                # JIRA/Workflows: Groq (fast) or Gemini (free)
                elif task_type in ['jira', 'planning']:
                    cloud_providers = [
                        ('groq', 'llama-3.3-70b-versatile'),
                        ('gemini', 'gemini-2.0-flash-exp'),
                        ('openai', 'gpt-4')
                    ]
                else:
                    # Default: Try all in order
                    cloud_providers = [
                        ('groq', 'llama-3.3-70b-versatile'),
                        ('gemini', 'gemini-2.0-flash-exp'),
                        ('openai', 'gpt-4')
                    ]
                
                # Try each cloud provider until one works
                for provider_name, model_name in cloud_providers:
                    try:
                        api_key = api_key_manager.get_key(provider_name)
                        if not api_key:
                            continue  # Skip if no API key
                        
                        # Try this cloud provider
                        if provider_name == 'groq':
                            from groq import AsyncGroq
                            client = AsyncGroq(api_key=api_key)
                            messages = []
                            if system_prompt:
                                messages.append({"role": "system", "content": system_prompt})
                            messages.append({"role": "user", "content": full_prompt})
                            
                            response = await client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=messages,
                                temperature=0.2,
                                max_tokens=8000
                            )
                            print(f"[OK] Cloud fallback succeeded using Groq")
                            return response.choices[0].message.content
                        
                        elif provider_name == 'gemini':
                            import google.generativeai as genai
                            genai.configure(api_key=api_key)
                            model = genai.GenerativeModel('gemini-2.0-flash-exp')
                            
                            # Build prompt
                            combined_prompt = full_prompt
                            if system_prompt:
                                combined_prompt = f"{system_prompt}\n\n{full_prompt}"
                            
                            response = await model.generate_content_async(combined_prompt)
                            print(f"[OK] Cloud fallback succeeded using Gemini")
                            return response.text
                        
                        elif provider_name == 'openai':
                            from openai import AsyncOpenAI
                            client = AsyncOpenAI(api_key=api_key)
                            messages = []
                            if system_prompt:
                                messages.append({"role": "system", "content": system_prompt})
                            messages.append({"role": "user", "content": full_prompt})
                            
                            response = await client.chat.completions.create(
                                model="gpt-4",
                                messages=messages,
                                temperature=0.2,
                                max_tokens=8000
                            )
                            print(f"[OK] Cloud fallback succeeded using OpenAI GPT-4")
                            return response.choices[0].message.content
                    except Exception as e:
                        print(f"[WARN] Cloud provider {provider_name} failed: {e}. Trying next...")
                        continue
                
                # All cloud providers failed
                raise Exception("All cloud providers failed. Please check API keys in secrets store.")
        
        if self.client_type == 'ollama' and hasattr(self, 'ollama_client'):
            # Direct Ollama call (fallback if router not available)
            try:
                # Use default model or get from mapper
                if artifact_type:
                    from config.artifact_model_mapping import get_artifact_mapper
                    mapper = get_artifact_mapper()
                    model_name = mapper.get_model_name(artifact_type)
                else:
                    model_name = "codellama:7b-instruct-q4_K_M"  # Default
                
                response = await self.ollama_client.generate(
                    model_name=model_name,
                    prompt=full_prompt,
                    system_message=system_prompt,
                    temperature=0.2
                )
                
                if response.success:
                    return response.content
                else:
                    raise Exception(f"Ollama generation failed: {response.error_message}")
            except Exception as e:
                print(f"[WARN] Ollama generation failed: {e}. Falling back to cloud...")
                # Fall through to cloud providers
        
        if self.client_type == 'local_finetuned':
            # Use local fine-tuned model
            import torch
            
            model = self.client['model']
            tokenizer = self.client['tokenizer']
            
            # Format prompt for instruction-following
            instruction_prompt = f"""### Instruction:
{system_prompt if system_prompt else 'You are an expert software architect. Generate high-quality technical documentation and code.'}

### Input:
{full_prompt}

### Output:
"""
            
            # Tokenize
            inputs = tokenizer(instruction_prompt, return_tensors="pt", truncation=True, max_length=4096)
            
            # Move to GPU if available
            if self.client.get('cuda_available'):
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # Stream tokens for user feedback
            try:
                from transformers import TextIteratorStreamer
                import threading
                streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
                generation_kwargs = dict(
                    **inputs,
                    max_new_tokens=4096,  # Increased from 2048 for full prototypes
                    temperature=0.2,
                    do_sample=True,
                    top_p=0.95,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                    streamer=streamer,
                )
            
                # Prepare optional Streamlit placeholder for live logs
                log_placeholder = None
                try:
                    import streamlit as st
                    log_placeholder = st.empty()
                    log_placeholder.info("🧠 Generating with local Codellama…")
                except Exception:
                    log_placeholder = None

                generated_chunks = []
                generation_error: Dict[str, Exception] = {}

                def _generate_async():
                    try:
                        with torch.no_grad():
                            model.generate(**generation_kwargs)
                    except Exception as exc:  # noqa: BLE001
                        generation_error["error"] = exc

                thread = threading.Thread(target=_generate_async)
                thread.start()

                for token in streamer:
                    generated_chunks.append(token)
                    partial_text = "".join(generated_chunks)
                    if log_placeholder is not None:
                        log_placeholder.markdown(f"```\n{partial_text[-2000:]}\n```")
                    else:
                        print(f"[LOCAL_GEN] {partial_text[-120:]}" if len(partial_text) > 120 else f"[LOCAL_GEN] {partial_text}")

                thread.join()

                if generation_error:
                    raise generation_error["error"]

                generated_text = "".join(generated_chunks)

            except Exception as stream_err:
                # Fallback to non-streaming generation
                print(f"[WARN] Streaming generation failed: {stream_err}. Retrying without streamer...")
                try:
                    with torch.no_grad():
                        outputs = model.generate(
                            **inputs,
                            max_new_tokens=4096,  # Increased from 2048 for full prototypes
                            temperature=0.0,
                            do_sample=False,
                            top_p=0.95,
                            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                            eos_token_id=tokenizer.eos_token_id,
                        )
                    prompt_length = inputs["input_ids"].shape[-1]
                    generated_ids = outputs[0][prompt_length:]
                    generated_text = tokenizer.decode(generated_ids.detach().cpu(), skip_special_tokens=True)
                except Exception as final_err:  # noqa: BLE001
                    if log_placeholder is not None:
                        try:
                            log_placeholder.error("❌ Local model generation failed. Swapping to cloud provider.")
                        except Exception:  # noqa: BLE001
                            pass
                    # Clear CUDA error state to keep app responsive
                    if self.client.get('cuda_available'):
                        try:
                            torch.cuda.empty_cache()
                        except Exception:  # noqa: BLE001
                            pass
                    # Fine-tuned model failed, try cloud fallback
                    print(f"[WARN] Local fine-tuned model failed: {final_err}. Falling back to cloud...")
                    # Fall through to cloud fallback below
            
            cleaned_text = generated_text.strip()
            if "### Output:" in cleaned_text:
                result = cleaned_text.split("### Output:", 1)[-1].strip()
            else:
                result = cleaned_text
            
            # Clear live log placeholder once finished
            try:
                if log_placeholder is not None:
                    log_placeholder.empty()
            except Exception:
                pass

            return result
        
        elif self.client_type == 'groq':
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
            
            # Add retry logic for rate limiting (429 errors)
            import time
            import random
            max_retries = 3
            base_delay = 5  # Base delay in seconds
            
            for attempt in range(max_retries):
                try:
                    response = self.client.generate_content(full_system_prompt)
                    return response.text
                except Exception as e:
                    error_str = str(e)
                    # Check if it's a 429 rate limit error
                    if "429" in error_str or "Resource exhausted" in error_str or "ResourceExhausted" in error_str:
                        if attempt < max_retries - 1:
                            # Exponential backoff with jitter
                            delay = base_delay * (2 ** attempt) + random.uniform(1, 3)
                            print(f"[WARN] Rate limit hit (429). Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})...")
                            time.sleep(delay)
                            continue
                        else:
                            print(f"[ERROR] Rate limit exceeded after {max_retries} attempts. Please wait before trying again.")
                            raise Exception(f"429 Rate limit exceeded. Please wait a few minutes before trying again. Error: {error_str}")
                    else:
                        # Not a rate limit error, re-raise immediately
                        raise
        
        else:
            # Unknown client type - try cloud fallback
            print(f"[WARN] Unknown client type: {self.client_type}. Attempting cloud fallback...")
            # Fall through to cloud fallback logic above
            raise Exception(f"Unknown client type: {self.client_type}. No cloud fallback available.")
    
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
                except:
                    pass
            except Exception as e:
                print(f"[WARN] RAG debug logging failed: {e}")
            
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
            from components.pattern_mining import PatternDetector
            import os
            from pathlib import Path
            
            # SMART ROOT DETECTION: Find the actual USER's project root, not Architect.AI
            current = Path(".").resolve()
            project_root = current
            check_path = current
            for _ in range(3):  # Check up to 3 levels up
                parent = check_path.parent
                if parent != check_path:
                    subdirs = [d for d in parent.iterdir() if d.is_dir() and not d.name.startswith('.')]
                    if len(subdirs) >= 2 and check_path.name in [d.name for d in subdirs]:
                        project_root = parent
                        break
                check_path = parent
            
            detector = PatternDetector()
            analysis = detector.analyze_project(project_root)
            
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
            from components.pattern_mining import PatternDetector
            import os
            from pathlib import Path
            
            # SMART ROOT DETECTION: Find the actual USER's project root, not Architect.AI
            current = Path(".").resolve()
            project_root = current
            check_path = current
            for _ in range(3):  # Check up to 3 levels up
                parent = check_path.parent
                if parent != check_path:
                    subdirs = [d for d in parent.iterdir() if d.is_dir() and not d.name.startswith('.')]
                    if len(subdirs) >= 2 and check_path.name in [d.name for d in subdirs]:
                        project_root = parent
                        break
                check_path = parent
            
            detector = PatternDetector()
            analysis = detector.analyze_project(project_root)
            
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
        
        prompt = f"""
Generate a FULLY FUNCTIONAL visual prototype for: {feature_name}

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
            "You are an expert frontend developer. Generate a complete, working HTML prototype.",
            artifact_type="visual_prototype_dev"
        )
        
        return response
    
    def _clean_diagram_output(self, diagram_text: str) -> str:
        """
        Clean diagram output - Uses aggressive preprocessing + universal diagram fixer.
        
        Pipeline:
        1. Aggressive preprocessing (fixes 4 common syntax errors)
        2. UniversalDiagramFixer (comprehensive type-specific cleaning)
        
        Fixes:
        - Multiple diagram declarations on same line
        - Special characters in node labels (.NET, C#, etc.)
        - Markdown fences inside diagram content
        - Malformed ERD entity blocks
        """
        try:
            # CRITICAL: Aggressive preprocessing BEFORE universal fixer
            from components.mermaid_preprocessor import aggressive_mermaid_preprocessing
            diagram_text = aggressive_mermaid_preprocessing(diagram_text)
            
            from components.universal_diagram_fixer import fix_any_diagram
            cleaned, fixes = fix_any_diagram(diagram_text)
            return cleaned
        except Exception as e:
            # Fallback: basic cleanup with preprocessing
            try:
                from components.mermaid_preprocessor import aggressive_mermaid_preprocessing
                diagram_text = aggressive_mermaid_preprocessing(diagram_text)
            except:
                # Last resort: manual cleanup
                import re
                diagram_text = re.sub(r'```mermaid\s*\n?', '', diagram_text)
                diagram_text = re.sub(r'```\s*$', '', diagram_text)
                diagram_text = diagram_text.replace("```", "")
            return diagram_text.strip()
    
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
        except:
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
            from components.knowledge_graph import KnowledgeGraphBuilder
            import os
            from pathlib import Path
            
            # SMART ROOT DETECTION: Find the actual USER's project root, not Architect.AI
            current = Path(".").resolve()
            project_root = current
            check_path = current
            for _ in range(3):  # Check up to 3 levels up
                parent = check_path.parent
                if parent != check_path:
                    subdirs = [d for d in parent.iterdir() if d.is_dir() and not d.name.startswith('.')]
                    # If parent has multiple project-like directories (e.g., final_project, architect_ai_cursor_poc)
                    if len(subdirs) >= 2 and check_path.name in [d.name for d in subdirs]:
                        project_root = parent
                        print(f"[INFO] Detected user project root at: {project_root}")
                        break
                check_path = parent
            
            kg_builder = KnowledgeGraphBuilder()
            kg = kg_builder.build_graph(project_root)
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
            "Generate ONLY the ERD diagram in Mermaid format. Start with 'erDiagram' (NOT graph TD).",
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
        
        return cleaned
    
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
            return await self._call_ai(prompt)
        
        # Standard generation with RAG context for general models
        await self.retrieve_rag_context("""
        system architecture components services infrastructure
        architectural patterns design decisions technology choices
        microservices patterns service boundaries API design
        """)
        
        # ENHANCE with Knowledge Graph architecture insights
        try:
            from components.knowledge_graph import KnowledgeGraphBuilder
            import os
            from pathlib import Path
            
            # SMART ROOT DETECTION: Find the actual USER's project root, not Architect.AI
            current = Path(".").resolve()
            project_root = current
            check_path = current
            for _ in range(3):  # Check up to 3 levels up
                parent = check_path.parent
                if parent != check_path:
                    subdirs = [d for d in parent.iterdir() if d.is_dir() and not d.name.startswith('.')]
                    # If parent has multiple project-like directories (e.g., final_project, architect_ai_cursor_poc)
                    if len(subdirs) >= 2 and check_path.name in [d.name for d in subdirs]:
                        project_root = parent
                        print(f"[INFO] Detected user project root at: {project_root}")
                        break
                check_path = parent
            
            kg_builder = KnowledgeGraphBuilder()
            kg = kg_builder.build_graph(project_root)
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
                    kg_context += f"- Coupling: {metrics.get('graph_density', 'N/A'):.2f}\n"
                
                self.rag_context += kg_context
                print(f"[OK] Enhanced Architecture with {len(arch_components)} components from Knowledge Graph")
        except Exception as e:
            print(f"[WARN] Could not enhance with Knowledge Graph: {e}")
        
        prompt = f"""
Generate a system architecture diagram showing the high-level components and their relationships.

REQUIREMENTS: {self.feature_requirements}
TECH STACK: {self.repo_analysis.tech_stacks if self.repo_analysis else []}

RAG CONTEXT: {self.rag_context}

OUTPUT: Mermaid graph diagram (start with 'graph TD'), max 8 nodes, show component relationships.
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
        response = await self._call_ai(prompt, "Generate workflows in Markdown format.", artifact_type="workflows")
        return response
    
    async def generate_erd_diagram(self) -> Optional[str]:
        """Generate ERD diagram if database discussion detected (used in full workflow)"""
        return await self.generate_erd_only()
    
    async def generate_system_overview_diagram(self) -> Optional[str]:
        """Generate ONLY system overview diagram (Bug Fix #2: don't generate all)"""
        await self.retrieve_rag_context("architecture system overview")
        overview_prompt = f"""
You are a Mermaid diagram generator. Generate ONLY valid Mermaid code.

REQUIREMENTS: {self.feature_requirements}
TECH STACKS: {self.repo_analysis.tech_stacks if self.repo_analysis else []}

OUTPUT RULES (CRITICAL - FOLLOW EXACTLY):
1. First line MUST be: graph TD
2. NO markdown blocks (NO ```, NO ```mermaid)
3. NO subgraphs
4. Maximum 7 nodes
5. Use ONLY square brackets: [Text]
6. Use ONLY --> for arrows

Generate a simple system overview with max 7 nodes following these EXACT rules.
"""
        raw_overview = await self._call_ai(overview_prompt, "Output ONLY the diagram. Start with 'graph TD'.")
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
You are a Mermaid diagram generator. Generate ONLY valid Mermaid code.

REQUIREMENTS: {self.feature_requirements}

OUTPUT RULES: graph TD, max 6 nodes, square brackets, --> arrows only.
Show: Input -> Process -> Store -> Output
"""
        raw = await self._call_ai(prompt, "Output ONLY the diagram. Start with 'graph TD'.")
        return self._clean_diagram_output(raw)
    
    async def generate_user_flow_diagram(self) -> Optional[str]:
        """Generate ONLY user flow diagram (Bug Fix #2: don't generate all)"""
        await self.retrieve_rag_context("user flow journey")
        prompt = f"""
You are a Mermaid diagram generator. Generate ONLY valid Mermaid code.

REQUIREMENTS: {self.feature_requirements}

OUTPUT RULES: graph TD, max 7 nodes, [Text] for actions, {{{{Text}}}} for decisions.
Show user journey with decision points.
"""
        raw = await self._call_ai(prompt, "Output ONLY the diagram. Start with 'graph TD'.")
        return self._clean_diagram_output(raw)
    
    async def generate_components_diagram(self) -> Optional[str]:
        """Generate ONLY components diagram (Bug Fix #2: don't generate all)"""
        await self.retrieve_rag_context("components modules architecture")
        prompt = f"""
You are a Mermaid diagram generator. Generate ONLY valid Mermaid code.

REQUIREMENTS: {self.feature_requirements}
TECH STACK: {self.repo_analysis.tech_stacks if self.repo_analysis else []}

OUTPUT RULES: graph LR, max 7 nodes, square brackets, --> arrows.
Show component relationships.
"""
        raw = await self._call_ai(prompt, "Output ONLY the diagram. Start with 'graph LR'.")
        return self._clean_diagram_output(raw)
    
    async def generate_api_sequence_diagram(self) -> Optional[str]:
        """Generate ONLY API sequence diagram (Bug Fix #2: don't generate all)"""
        await self.retrieve_rag_context("API endpoints sequence")
        prompt = f"""
You are a Mermaid diagram generator. Generate ONLY valid Mermaid code.

REQUIREMENTS: {self.feature_requirements}

OUTPUT RULES: sequenceDiagram, max 4 participants, ->> arrows.
Show API request/response flow.
"""
        raw = await self._call_ai(prompt, "Output ONLY the diagram. Start with 'sequenceDiagram'.")
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

VALID EXAMPLE:
graph TD
    A[Angular Frontend] --> B[API Server]
    B --> C[MongoDB]
    B --> D[Auth Service]
    A --> E[User Browser]

Generate a simple system overview with max 7 nodes following these EXACT rules.
"""
        raw_overview = await self._call_ai(overview_prompt, "Output ONLY the diagram. Start with 'graph TD'. No text before or after.")
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
        """Generate API documentation - ENHANCED with Knowledge Graph"""
        print("[INFO] Generating API documentation...")
        
        await self.retrieve_rag_context("API endpoints routes controllers services")
        
        # ENHANCE with Knowledge Graph for actual API structure
        try:
            from components.knowledge_graph import KnowledgeGraphBuilder
            import os
            from pathlib import Path
            
            # SMART ROOT DETECTION: Find the actual USER's project root, not Architect.AI
            current = Path(".").resolve()
            project_root = current
            check_path = current
            for _ in range(3):  # Check up to 3 levels up
                parent = check_path.parent
                if parent != check_path:
                    subdirs = [d for d in parent.iterdir() if d.is_dir() and not d.name.startswith('.')]
                    # If parent has multiple project-like directories (e.g., final_project, architect_ai_cursor_poc)
                    if len(subdirs) >= 2 and check_path.name in [d.name for d in subdirs]:
                        project_root = parent
                        print(f"[INFO] Detected user project root at: {project_root}")
                        break
                check_path = parent
            
            kg_builder = KnowledgeGraphBuilder()
            kg = kg_builder.build_graph(project_root)
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
            "You are an expert API designer. Generate comprehensive API documentation."
        )
    
    async def generate_jira_tasks(self) -> str:
        """Generate JIRA-ready tasks - ENHANCED with Pattern Mining"""
        print("[INFO] Generating JIRA tasks...")
        
        await self.retrieve_rag_context("tasks user stories epic subtasks estimates")
        
        # ENHANCE with Pattern Mining for realistic complexity estimates
        try:
            from components.pattern_mining import PatternDetector
            import os
            from pathlib import Path
            
            # SMART ROOT DETECTION: Find the actual USER's project root, not Architect.AI
            current = Path(".").resolve()
            project_root = current
            check_path = current
            for _ in range(3):  # Check up to 3 levels up
                parent = check_path.parent
                if parent != check_path:
                    subdirs = [d for d in parent.iterdir() if d.is_dir() and not d.name.startswith('.')]
                    if len(subdirs) >= 2 and check_path.name in [d.name for d in subdirs]:
                        project_root = parent
                        break
                check_path = parent
            
            detector = PatternDetector()
            analysis = detector.analyze_project(project_root)
            
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
            "You are an expert Scrum master and project manager. Generate detailed, actionable JIRA tasks."
        )
    
    async def generate_workflows(self) -> str:
        """Generate workflows - ENHANCED with Knowledge Graph & Pattern Mining"""
        print("[INFO] Generating workflows...")
        
        await self.retrieve_rag_context("workflow deployment testing CI/CD development process")
        
        # ENHANCE with Knowledge Graph for component dependencies
        try:
            from components.knowledge_graph import KnowledgeGraphBuilder
            import os
            from pathlib import Path
            
            # SMART ROOT DETECTION: Find the actual USER's project root, not Architect.AI
            current = Path(".").resolve()
            project_root = current
            check_path = current
            for _ in range(3):  # Check up to 3 levels up
                parent = check_path.parent
                if parent != check_path:
                    subdirs = [d for d in parent.iterdir() if d.is_dir() and not d.name.startswith('.')]
                    # If parent has multiple project-like directories (e.g., final_project, architect_ai_cursor_poc)
                    if len(subdirs) >= 2 and check_path.name in [d.name for d in subdirs]:
                        project_root = parent
                        print(f"[INFO] Detected user project root at: {project_root}")
                        break
                check_path = parent
            
            kg_builder = KnowledgeGraphBuilder()
            kg = kg_builder.build_graph(project_root)
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
            from components.pattern_mining import PatternDetector
            from pathlib import Path
            
            # SMART ROOT DETECTION: Find the actual USER's project root
            current = Path(".").resolve()
            project_root = current
            check_path = current
            for _ in range(3):
                parent = check_path.parent
                if parent != check_path:
                    subdirs = [d for d in parent.iterdir() if d.is_dir() and not d.name.startswith('.')]
                    if len(subdirs) >= 2 and check_path.name in [d.name for d in subdirs]:
                        project_root = parent
                        break
                check_path = parent
            
            detector = PatternDetector()
            analysis = detector.analyze_project(project_root)
            
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
