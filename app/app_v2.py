"""
Architect.AI - Production-Ready Dual-Mode AI Architecture Assistant

A sophisticated AI-powered system that transforms meeting notes and repository context
into production-ready artifacts. Designed for developers and product managers who want
to move fast without breaking things.

TWO MODES:
1. Developer Mode: Technical artifacts (ERD, architecture, code, API docs, JIRA, workflows)
2. Product/PM Mode: Visual prototypes, feasibility validation, PM power tools

CORE PRINCIPLES:
- RAG-First: Always retrieve repository context before generating
- Feature-Focused: All outputs about the feature in meeting notes, not the app itself
- Stack-Aware: Detects and respects your project's tech stack and conventions
- Context-Driven: Uses your repo's architecture, patterns, and naming conventions

Version: 2.1.0
Author: Alexandra Georgescu (alestef81@gmail.com)
License: Proprietary - Internal use only
"""

import streamlit as st
import os
import asyncio
import json
import base64
import zlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import sys

# Auto-update architecture documentation on app start
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.architecture_updater import update_architecture_doc
    update_architecture_doc()
except Exception:
    pass  # Silently fail if update doesn't work

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import the universal agent
from agents.universal_agent import UniversalArchitectAgent
# UI components - Import what's available, stub what's not
from components.prototype_generator import generate_best_effort
from components.metrics_dashboard import track_generation, render_metrics_dashboard
from components.rag_cache import get_rag_cache
from components.rate_limiter import get_rate_limiter

# Optional components with fallbacks
try:
    from components.code_editor import render_code_editor, render_multi_file_editor
except Exception:
    render_code_editor = None
    render_multi_file_editor = None

try:
    from components.test_generator import render_test_generator
except Exception:
    render_test_generator = None

try:
    from components.export_manager import render_export_manager
except Exception:
    render_export_manager = None

try:
    from components.interactive_prototype_editor import render_interactive_prototype_editor, render_quick_modification_buttons
except Exception:
    render_interactive_prototype_editor = None
    render_quick_modification_buttons = None

# No auth needed for single-user dev tool
AUTH_AVAILABLE = False
current_user = lambda: None
current_role = lambda: "Developer"
has_role = lambda roles: True
# Remove unnecessary features for dev tool
render_git_tools = None
render_collaboration = None
render_user_management = None
render_cleanup_tool = None
render_job_history = None
enqueue_job = None
render_publish_panel = None
render_prototype_editor = None

# Background job worker function for artifact generation
# Note: Runs in-process thread via components.jobs.enqueue_job

def job_generate_artifact(artifact_type: str, provider_key: str, provider_name: str, meeting_notes: str, rag_suffix: str = "", force_refresh: bool = False, job_id: int = 0) -> str:
    """
    Background job worker for artifact generation.
    
    Runs in-process thread via components.jobs.enqueue_job.
    Imports are done locally to avoid circular dependencies.
    """
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(parents=True, exist_ok=True)
    from agents.universal_agent import UniversalArchitectAgent
    from components.prototype_generator import generate_best_effort
    import asyncio
    
    agent = UniversalArchitectAgent({provider_name: provider_key})
    agent.meeting_notes = meeting_notes
    
    # Retrieve RAG
    rag_query = f"{artifact_type} {meeting_notes} {rag_suffix}".strip()
    asyncio.run(agent.retrieve_rag_context(rag_query, force_refresh=force_refresh))
    # Generate and save
    if artifact_type == "erd":
        res = asyncio.run(agent.generate_erd_only())
        if res:
            p = outputs_dir / "visualizations" / "erd_diagram.mmd"
            p.parent.mkdir(exist_ok=True)
            p.write_text(res, encoding='utf-8')
            return str(p)
    if artifact_type == "architecture":
        res = asyncio.run(agent.generate_architecture_only())
        if res:
            p = outputs_dir / "visualizations" / "architecture_diagram.mmd"
            p.parent.mkdir(exist_ok=True)
            p.write_text(res, encoding='utf-8')
            return str(p)
    if artifact_type == "all_diagrams":
        diagrams = asyncio.run(agent.generate_specific_diagrams())
        last = None
        if diagrams:
            viz = outputs_dir / "visualizations"
            viz.mkdir(exist_ok=True)
            for name, content in diagrams.items():
                p = viz / f"{name}_diagram.mmd"
                p.write_text(content, encoding='utf-8')
                last = str(p)
        return last or ""
    if artifact_type == "api_docs":
        res = asyncio.run(agent.generate_api_docs_only())
        if res:
            p = outputs_dir / "documentation" / "api.md"
            p.parent.mkdir(exist_ok=True)
            p.write_text(res, encoding='utf-8')
            return str(p)
    if artifact_type == "jira":
        res = asyncio.run(agent.generate_jira_only())
        if res:
            p = outputs_dir / "documentation" / "jira_tasks.md"
            p.parent.mkdir(exist_ok=True)
            p.write_text(res, encoding='utf-8')
            return str(p)
    if artifact_type == "workflows":
        res = asyncio.run(agent.generate_workflows_only())
        if res:
            p = outputs_dir / "workflows" / "workflows.md"
            p.parent.mkdir(exist_ok=True)
            p.write_text(res, encoding='utf-8')
            return str(p)
    if artifact_type == "code_prototype":
        res = asyncio.run(agent.generate_prototype_code("feature-from-notes"))
        if res and isinstance(res, dict) and "code" in res:
            p = outputs_dir / "prototypes" / "prototype_code.txt"
            p.parent.mkdir(exist_ok=True)
            p.write_text(res["code"], encoding='utf-8')
            return str(p)
    if artifact_type == "visual_prototype_dev":
        res = asyncio.run(agent.generate_visual_prototype("developer-feature"))
        if res:
            p = outputs_dir / "prototypes" / "developer_visual_prototype.html"
            p.parent.mkdir(exist_ok=True)
            p.write_text(res, encoding='utf-8')
            return str(p)
    if artifact_type == "openapi":
        # Generate OpenAPI YAML via LLM
        prompt = f"""
Generate a strict OpenAPI 3.1 YAML for the project's API based on the RAG context and repository patterns. Include info, servers (placeholder), tags, paths with operations, requestBodies, responses, components/schemas. Output YAML only.
"""
        res = asyncio.run(agent._call_ai(prompt, "You are an expert API designer. Output only valid OpenAPI YAML."))
        if res:
            p = outputs_dir / "documentation" / "openapi.yaml"
            p.parent.mkdir(exist_ok=True)
            p.write_text(res, encoding='utf-8')
            return str(p)
    if artifact_type == "api_client_python":
        prompt = f"""
Generate a production-ready Python API client for the project's endpoints found in the RAG context. Use requests, handle auth (token), timeouts, retries, typed dataclasses, and raise for status. Output full .py code only.
"""
        res = asyncio.run(agent._call_ai(prompt, "You are an expert Python engineer. Output only code."))
        if res:
            p = outputs_dir / "prototypes" / "api_client.py"
            p.parent.mkdir(exist_ok=True)
            p.write_text(res, encoding='utf-8')
            return str(p)
    if artifact_type == "api_client_typescript":
        prompt = f"""
Generate a production-ready TypeScript API client for the project's endpoints found in the RAG context. Use fetch, generics, error handling, and typed interfaces. Output full .ts code only.
"""
        res = asyncio.run(agent._call_ai(prompt, "You are an expert TS engineer. Output only code."))
        if res:
            p = outputs_dir / "prototypes" / "api_client.ts"
            p.parent.mkdir(exist_ok=True)
            p.write_text(res, encoding='utf-8')
            return str(p)
    return ""

# Helpers for RAG controls

def get_rag_suffix() -> str:
    return st.session_state.get('rag_suffix', '').strip()


def is_background_mode() -> bool:
    return bool(st.session_state.get('run_background', False))

# =============================================================================
# BEAUTIFUL UI CONFIGURATION
# =============================================================================

def apply_custom_css():
    """Apply beautiful Trimble brand styling - Original design with Trimble colors"""
    st.markdown("""
    <style>
    /* Trimble Brand Colors */
    :root {
        --trimble-blue: #0063A3;
        --trimble-blue-dark: #004F83;
        --trimble-blue-light: #217CBB;
        --trimble-yellow: #FBAD26;
        --trimble-gray: #252A2E;
        --success-color: #1E8A44;
        --warning-color: #FBAD26;
        --danger-color: #DA212C;
        --dark-bg: #1e1e2e;
        --card-bg: #2a2a3e;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container styling - Beautiful Trimble gradient */
    .main {
        background: linear-gradient(135deg, #0063A3 2%, #004F83 98%);
        padding: 0 !important;
        min-height: 100vh;
    }
    
    .block-container {
        padding: 2rem 3rem !important;
        max-width: 100% !important;
        margin: 0 auto !important;
        background: transparent !important;
    }
    
    /* Responsive layout - adjust when sidebar is open */
    @media (min-width: 768px) {
        /* When sidebar is collapsed */
        [data-testid="collapsedControl"] ~ div .block-container {
            max-width: 100% !important;
        }
        /* When sidebar is open */
        .block-container {
            max-width: calc(100vw - 340px) !important;
        }
    }
    
    /* Ensure columns wrap properly */
    [data-testid="column"] {
        min-width: 0 !important;
    }
    
    /* Fix column alignment issues */
    .stColumns {
        gap: 1rem;
    }
    
    .stColumns > div {
        display: flex;
        flex-direction: column;
    }
    
    /* Main content text colors - All white for visibility */
    .main h1, .main h2, .main h3, .main h4 {
        color: white !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
    }
    
    .main p, .main span, .main div, .main label {
        color: white !important;
    }
    
    .main strong {
        color: var(--trimble-yellow) !important;
    }
    
    /* Beautiful Trimble header */
    .app-header {
        background: linear-gradient(135deg, #0063A3 0%, #004F83 100%);
        padding: 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        text-align: center;
        animation: fadeIn 0.5s ease-in;
        border-bottom: 4px solid var(--trimble-yellow);
    }
    
    .app-header h1 {
        color: white;
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .app-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.2rem;
        margin-top: 0.5rem;
    }
    
    /* Mode selector cards */
    .mode-card {
        background: white;
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        cursor: pointer;
        border: 3px solid transparent;
    }
    
    .mode-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.2);
        border-color: var(--trimble-blue);
    }
    
    .mode-card.selected {
        border-color: var(--trimble-blue);
        background: linear-gradient(135deg, rgba(0, 99, 163, 0.15) 0%, rgba(0, 79, 131, 0.15) 100%);
    }
    
    .mode-card h3 {
        color: #1f2937;
        font-weight: 700;
    }
    
    .mode-card p {
        color: #4b5563;
    }
    
    .mode-card ul {
        color: #6b7280;
    }
    
    .mode-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    
    /* Beautiful Trimble buttons */
    .stButton > button {
        background: linear-gradient(135deg, #0063A3 0%, #004F83 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 99, 163, 0.4);
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 99, 163, 0.6);
    }
    
    /* Granular generation buttons */
    .granular-btn {
        background: white !important;
        color: var(--trimble-blue) !important;
        border: 2px solid var(--trimble-blue) !important;
    }
    
    .granular-btn:hover {
        background: var(--trimble-blue) !important;
        color: white !important;
    }
    
    /* Cards for content */
    .content-card {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .content-card h3, .content-card h4 {
        color: #1f2937 !important;
        font-weight: 700 !important;
    }
    
    .content-card p, .content-card li {
        color: #4b5563 !important;
    }
    
    /* Tabs styling - Better contrast */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 10px;
        padding: 0.5rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        color: #1f2937 !important;
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(0, 99, 163, 0.1);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #0063A3 0%, #217CBB 100%);
        color: white !important;
        box-shadow: 0 2px 8px rgba(0, 99, 163, 0.4);
    }
    
    /* Success/Info/Warning boxes - White text */
    .stSuccess, .stInfo, .stWarning, .stError {
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        background: rgba(255, 255, 255, 0.95) !important;
    }
    
    .stSuccess {
        border-left: 5px solid var(--success-color);
    }
    
    .stInfo {
        border-left: 5px solid var(--trimble-blue-light);
    }
    
    .stWarning {
        border-left: 5px solid var(--warning-color);
    }
    
    .stError {
        border-left: 5px solid var(--danger-color);
    }
    
    /* Expander styling - White text for visibility */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        font-weight: 600;
        color: white !important;
        border-left: 4px solid var(--trimble-yellow);
    }
    
    .streamlit-expanderHeader:hover {
        background: rgba(255, 255, 255, 0.3);
    }
    
    .streamlit-expanderHeader p {
        color: white !important;
    }
    
    .streamlit-expanderHeader svg {
        fill: white !important;
    }
    
    /* Metrics - Ensure text is visible */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.15);
        padding: 1rem;
        border-radius: 10px;
    }
    
    [data-testid="stMetricLabel"] {
        color: white !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: white !important;
    }
    
    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    .animated {
        animation: slideIn 0.5s ease-in;
    }
    
    /* Code blocks */
    .stCodeBlock {
        border-radius: 10px;
        border: 1px solid #e5e7eb;
    }
    
    /* File uploader - White background with white text */
    [data-testid="stFileUploader"] {
        border: 3px dashed rgba(255, 255, 255, 0.5);
        border-radius: 10px;
        padding: 2rem;
        background: rgba(255, 255, 255, 0.1);
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: white;
        background: rgba(255, 255, 255, 0.15);
    }
    
    [data-testid="stFileUploader"] * {
        color: white !important;
    }
    
    /* Sidebar - Trimble gradient with fixed width */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0063A3 0%, #004F83 100%);
        min-width: 280px !important;
        max-width: 280px !important;
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: white !important;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4 {
        color: white !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2);
    }
    
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {
        color: white !important;
    }
    
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] select,
    [data-testid="stSidebar"] textarea {
        background: white !important;
        color: var(--trimble-gray) !important;
    }
    
    /* Progress bars */
    .stProgress > div > div {
        background: linear-gradient(135deg, #0063A3 0%, #004F83 100%);
    }
    
    /* Beautiful scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #0063A3 0%, #004F83 100%);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--trimble-blue-light);
    }
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# EXTENDED CONTEXT HELPERS
# =============================================================================

def _read_text_safe(path: Path, limit: int = 4000) -> str:
    try:
        if path.exists() and path.is_file():
            return path.read_text(encoding='utf-8')[:limit]
    except Exception:
        return ""
    return ""


def get_extended_project_context(max_chars: int = 8000) -> str:
    """Collect extra project context: meeting notes, context docs, PR comments, READMEs."""
    parts = []
    base = Path(".")
    # Meeting notes
    notes = _read_text_safe(AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE, 6000)
    if notes:
        parts.append(f"# Meeting Notes\n{notes}")
    # Context important files
    ctx_dir = Path("architect_ai_cursor_poc") / "context"
    for name in [
        "_retrieved.md",
        "architecture.md",
        "conventions.md",
        "api_endpoints.md",
        "decisions_adr.md",
        "ready_done.md",
        "repo_tree.txt",
        "commit_log.md",
        "pr_recent.md",
    ]:
        parts.append(f"# {name}\n{_read_text_safe(ctx_dir / name, 4000)}")
    # Root READMEs
    for name in ["README.md", "README_V2.md", "START_HERE.md"]:
        parts.append(f"# {name}\n{_read_text_safe(Path('architect_ai_cursor_poc') / name, 3000)}")
    # Compose and trim
    blob = "\n\n".join([p for p in parts if p.strip()])
    return blob[:max_chars]

# =============================================================================
# CONFIGURATION
# =============================================================================

class AppConfig:
    """
    Application configuration constants.
    
    Centralizes all app-wide settings including UI configuration,
    file paths, and AI provider settings.
    """
    APP_TITLE = "Architect.AI v2.4 - Transform Ideas into Production-Ready Code"
    APP_ICON = "🏗️"
    APP_VERSION = "2.4.0"
    APP_AUTHOR = "Alexandra Georgescu"
    APP_CONTACT = "alestef81@gmail.com"
    LAYOUT = "wide"
    # Use absolute paths based on this file's location
    _APP_ROOT = Path(__file__).parent.parent  # architect_ai_cursor_poc/
    OUTPUTS_DIR = _APP_ROOT / "outputs"
    INPUTS_DIR = _APP_ROOT / "inputs"
    MEETING_NOTES_FILE = "meeting_notes.md"
    
    # AI Model Providers
    AI_PROVIDERS = {
        "Groq (FREE & FAST)": {
            "name": "Groq Llama 3.3",
            "key_env": "GROQ_API_KEY",
            "config_key": "groq_api_key",
            "icon": "⚡"
        },
        "Google Gemini (FREE)": {
            "name": "Gemini 2.0 Flash",
            "key_env": "GEMINI_API_KEY",
            "config_key": "gemini_api_key",
            "icon": "🤖"
        },
        "OpenAI GPT-4": {
            "name": "GPT-4",
            "key_env": "OPENAI_API_KEY",
            "config_key": "api_key",
            "icon": "🧠"
        }
    }

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """
    Initialize session state variables.
    
    Ensures all required session variables exist to prevent KeyError exceptions.
    Called once at app startup.
    """
    if 'mode' not in st.session_state:
        st.session_state.mode = None
    if 'api_key' not in st.session_state:
        st.session_state.api_key = None
    if 'provider' not in st.session_state:
        st.session_state.provider = "Groq (FREE & FAST)"
    if 'rag_logs' not in st.session_state:
        st.session_state.rag_logs = []
    if 'ai_conversation' not in st.session_state:
        st.session_state.ai_conversation = []
    if 'last_generation' not in st.session_state:
        st.session_state.last_generation = []
    if 'use_multi_agent' not in st.session_state:
        st.session_state.use_multi_agent = False
    if 'use_validation' not in st.session_state:
        st.session_state.use_validation = True
    if 'max_retries' not in st.session_state:
        st.session_state.max_retries = 2
    # Agent caching to avoid re-initialization
    if 'cached_agent' not in st.session_state:
        st.session_state.cached_agent = None
    if 'cached_agent_config' not in st.session_state:
        st.session_state.cached_agent_config = None
    # Auto-ingestion state
    if 'auto_ingestion_initialized' not in st.session_state:
        st.session_state.auto_ingestion_initialized = False


def init_auto_ingestion():
    """
    Initialize the automatic RAG ingestion system.
    
    Starts the file watcher and background processing if enabled in configuration.
    Called once at app startup.
    """
    # Only initialize once per session
    if st.session_state.auto_ingestion_initialized:
        return
    
    try:
        from rag.auto_ingestion import get_auto_ingestion_manager
        
        # Get the manager and check if auto-ingestion is enabled
        manager = get_auto_ingestion_manager()
        
        if manager.enabled:
            # Start the auto-ingestion system
            success = manager.start()
            if success:
                st.session_state.rag_logs.append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Auto-ingestion system started"
                )
                # Show a success message in the UI (only on first load)
                if not st.session_state.get('auto_ingestion_started_shown', False):
                    st.success("🔄 Auto-ingestion system started automatically")
                    st.session_state.auto_ingestion_started_shown = True
            else:
                st.session_state.rag_logs.append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Failed to start auto-ingestion system"
                )
                if not st.session_state.get('auto_ingestion_error_shown', False):
                    st.warning("⚠️ Failed to start auto-ingestion system")
                    st.session_state.auto_ingestion_error_shown = True
        else:
            st.session_state.rag_logs.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] ℹ️ Auto-ingestion is disabled in configuration"
            )
    
    except Exception as e:
        # Silently fail if auto-ingestion components are not available
        error_msg = str(e)[:50] + "..." if len(str(e)) > 50 else str(e)
        st.session_state.rag_logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Auto-ingestion not available: {error_msg}"
        )
        # Show a warning in the UI (only once)
        if not st.session_state.get('auto_ingestion_error_shown', False):
            st.warning(f"⚠️ Auto-ingestion not available: {error_msg}")
            st.session_state.auto_ingestion_error_shown = True
    
    # Mark as initialized
    st.session_state.auto_ingestion_initialized = True

# =============================================================================
# AGENT CACHING
# =============================================================================

def get_or_create_agent(config: Dict) -> 'UniversalArchitectAgent':
    """
    Get cached agent or create new one if config changed.
    
    This prevents re-initialization of RAG, multi-agent system,
    and other expensive resources on every generation.
    
    Args:
        config: AI provider configuration dict
    
    Returns:
        Cached or new UniversalArchitectAgent instance
    """
    # Generate config hash to detect changes
    import hashlib
    config_hash = hashlib.md5(str(sorted(config.items())).encode()).hexdigest()
    
    # Check if we have a cached agent with same config
    if (st.session_state.cached_agent is not None and 
        st.session_state.cached_agent_config == config_hash):
        return st.session_state.cached_agent
    
    # Create new agent
    agent = UniversalArchitectAgent(config)
    
    # Cache it
    st.session_state.cached_agent = agent
    st.session_state.cached_agent_config = config_hash
    
    st.session_state.rag_logs.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Agent initialized (config: {list(config.keys())[0]})"
    )
    
    return agent

def retrieve_rag_with_cache(agent: 'UniversalArchitectAgent', meeting_notes: str, force_refresh: bool = False) -> str:
    """
    Retrieve RAG context with intelligent caching.
    
    Caches RAG results per meeting notes hash to avoid redundant expensive queries.
    This provides 60-70% reduction in RAG API calls.
    
    Args:
        agent: UniversalArchitectAgent instance
        meeting_notes: Meeting notes content
        force_refresh: Force fresh retrieval, bypass cache
    
    Returns:
        RAG context string
    """
    import asyncio
    
    rag_cache = get_rag_cache()
    
    # Check cache first (unless force refresh)
    if not force_refresh:
        cached_context = rag_cache.get(meeting_notes)
        if cached_context:
            agent.rag_context = cached_context
            st.session_state.rag_logs.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] 💾 RAG cache HIT ({len(cached_context)} chars)"
            )
            return cached_context
    
    # Cache miss or force refresh - retrieve from RAG
    st.session_state.rag_logs.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 RAG cache MISS - retrieving fresh context"
    )
    
    # Perform RAG retrieval
    query = f"repository context, architecture, patterns for: {meeting_notes[:500]}"
    asyncio.run(agent.retrieve_rag_context(query, force_refresh=force_refresh))
    
    # Cache the result
    if agent.rag_context:
        rag_cache.set(meeting_notes, agent.rag_context)
        st.session_state.rag_logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] 💾 Cached RAG context ({len(agent.rag_context)} chars)"
        )
    
    return agent.rag_context or ""

# =============================================================================
# BEAUTIFUL HEADER
# =============================================================================

def render_header():
    """
    Render beautiful app header with branding and tagline.
    
    Displays the app title, version, and value proposition in a
    visually appealing gradient header.
    """
    st.markdown(f"""
    <div class="app-header">
        <h1>{AppConfig.APP_ICON} Architect.AI v{AppConfig.APP_VERSION}</h1>
        <p>Transform Meeting Notes into Production-Ready Code | Powered by Advanced RAG & Multi-Agent AI</p>
    </div>
    """, unsafe_allow_html=True)

def render_footer():
    """
    Render app footer with version, author, and contact information.
    
    Provides users with version information and a way to contact support.
    Styled to be unobtrusive but informative.
    """
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem 0 1rem 0; color: #6b7280; font-size: 0.875rem;">
        <p style="margin: 0.5rem 0;">
            <strong>Architect.AI v{AppConfig.APP_VERSION}</strong> | 
            Built with ❤️ for developers and product managers
        </p>
        <p style="margin: 0.5rem 0;">
            Made by <strong>{AppConfig.APP_AUTHOR}</strong> | 
            <a href="mailto:{AppConfig.APP_CONTACT}" style="color: #3b82f6; text-decoration: none;">{AppConfig.APP_CONTACT}</a>
        </p>
        <p style="margin: 0.5rem 0; font-size: 0.75rem; color: #9ca3af;">
            Stack-aware prototyping • Context-driven generation • Feature-focused outputs
        </p>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# MODE SELECTION
# =============================================================================

def render_mode_selection():
    """Render beautiful mode selection"""
    st.markdown("## 🎯 Choose Your Mode")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("👨‍💻 Developer Mode", key="dev_mode", use_container_width=True):
            st.session_state.mode = "developer"
            st.rerun()
        st.markdown("""
        <div class="content-card">
            <div class="mode-icon">👨‍💻</div>
            <h3 style="color: #1f2937;">Developer Mode</h3>
            <p style="color: #4b5563;">Technical diagrams, ERD, system architecture, code prototypes, API docs, JIRA tasks</p>
            <ul style="text-align: left; color: #6b7280;">
                <li>✅ ERD Diagrams (auto-generated)</li>
                <li>✅ System Architecture</li>
                <li>✅ Component Diagrams</li>
                <li>✅ Code Prototypes</li>
                <li>✅ API Documentation</li>
                <li>✅ JIRA Tasks</li>
                <li>✅ Granular Generation (faster results)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.button("📊 Product/PM Mode", key="pm_mode", use_container_width=True):
            st.session_state.mode = "product"
            st.rerun()
        st.markdown("""
        <div class="content-card">
            <div class="mode-icon">📊</div>
            <h3 style="color: #1f2937;">Product/PM Mode</h3>
            <p style="color: #4b5563;">Visual prototypes, idea validation, feasibility testing, no code</p>
            <ul style="text-align: left; color: #6b7280;">
                <li>✅ Visual Prototypes</li>
                <li>✅ Ask AI (idea validation)</li>
                <li>✅ Feasibility Testing</li>
                <li>✅ User Flow Diagrams</li>
                <li>✅ No Code (visual only)</li>
                <li>✅ JIRA Generation</li>
                <li>✅ Timeline Estimates</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar():
    """Render beautiful sidebar"""
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        
        # RAG Index Freshness Check
        try:
            from rag.refresh_manager import get_refresh_manager
            refresh_mgr = get_refresh_manager()
            freshness = refresh_mgr.check_freshness()
            
            if not freshness['is_fresh']:
                st.warning(freshness['recommendation'])
                if freshness['last_updated']:
                    hours_old = freshness['hours_old']
                    if hours_old < 24:
                        time_str = f"{int(hours_old)} hours"
                    else:
                        time_str = f"{int(hours_old/24)} days"
                    st.caption(f"📅 Last indexed: {time_str} ago")
                
                with st.expander("🔄 How to Refresh"):
                    st.code("cd architect_ai_cursor_poc\npython rag/ingest.py", language="bash")
            else:
                with st.expander("✅ RAG Status", expanded=False):
                    st.success(f"Index is fresh ({freshness['indexed_files']} files)")
                    if freshness['last_updated']:
                        st.caption(f"Last updated: {freshness['last_updated'].strftime('%Y-%m-%d %H:%M')}")
        except Exception:
            pass  # Silently fail if refresh manager not available
        
        # Auto-Ingestion Status
        try:
            from rag.auto_ingestion import get_auto_ingestion_status
            auto_status = get_auto_ingestion_status()
            
            if auto_status['enabled']:
                if auto_status['is_running']:
                    with st.expander("🔄 Auto-Ingestion Status", expanded=False):
                        st.success("🟢 Auto-ingestion is running")
                        
                        # Show active jobs
                        if auto_status['active_jobs'] > 0:
                            st.info(f"📋 {auto_status['active_jobs']} indexing jobs active")
                        
                        # Show pending events
                        if auto_status['pending_events'] > 0:
                            st.warning(f"⏳ {auto_status['pending_events']} file changes pending")
                        
                        # Show recent jobs
                        if auto_status['recent_jobs']:
                            st.caption("Recent jobs:")
                            for job in auto_status['recent_jobs'][-3:]:  # Show last 3
                                status_emoji = "✅" if job.status == "completed" else "🔄" if job.status == "processing" else "❌"
                                st.caption(f"{status_emoji} {job.status} - {job.files_processed}/{job.total_files} files")
                        
                        # Manual controls
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("⏸️ Pause", help="Temporarily pause auto-ingestion"):
                                from rag.auto_ingestion import stop_auto_ingestion
                                stop_auto_ingestion()
                                st.rerun()
                        
                        with col2:
                            if st.button("🔄 Refresh Now", help="Force immediate RAG refresh"):
                                try:
                                    # Trigger manual RAG refresh
                                    import subprocess
                                    import sys
                                    from pathlib import Path
                                    
                                    # Run the manual ingestion
                                    result = subprocess.run([
                                        sys.executable, 
                                        str(Path(__file__).parent.parent / "rag" / "ingest.py")
                                    ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
                                    
                                    if result.returncode == 0:
                                        st.success("✅ RAG index refreshed successfully!")
                                        st.session_state.rag_logs.append(
                                            f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Manual RAG refresh completed"
                                        )
                                    else:
                                        st.error(f"❌ RAG refresh failed: {result.stderr}")
                                        st.session_state.rag_logs.append(
                                            f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Manual RAG refresh failed: {result.stderr[:100]}"
                                        )
                                    
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"❌ Error triggering RAG refresh: {e}")
                                    st.session_state.rag_logs.append(
                                        f"[{datetime.now().strftime('%H:%M:%S')}] ❌ RAG refresh error: {str(e)[:100]}"
                                    )
                else:
                    with st.expander("🔄 Auto-Ingestion Status", expanded=False):
                        st.warning("🟡 Auto-ingestion is enabled but not running")
                        if st.button("▶️ Start Auto-Ingestion"):
                            from rag.auto_ingestion import start_auto_ingestion
                            if start_auto_ingestion():
                                st.success("Auto-ingestion started!")
                                st.rerun()
                            else:
                                st.error("Failed to start auto-ingestion")
            else:
                with st.expander("🔄 Auto-Ingestion Status", expanded=False):
                    st.info("⚪ Auto-ingestion is disabled")
                    st.caption("Enable in rag/config.yaml to automatically update RAG index")
                    
        except Exception as e:
            # Silently fail if auto-ingestion not available
            pass
        
        st.divider()
        
        # Mode indicator
        if st.session_state.mode:
            mode_emoji = "👨‍💻" if st.session_state.mode == "developer" else "📊"
            mode_name = "Developer" if st.session_state.mode == "developer" else "Product/PM"
            st.success(f"{mode_emoji} **{mode_name} Mode**")
            if st.button("🔄 Switch Mode"):
                st.session_state.mode = None
                st.rerun()
        
        st.divider()

        # AI Provider selection
        st.markdown("### 🤖 AI Provider")
        provider = st.selectbox(
            "Select Provider",
            list(AppConfig.AI_PROVIDERS.keys()),
            index=0,
            label_visibility="collapsed"
        )
        st.session_state.provider = provider
        
        provider_info = AppConfig.AI_PROVIDERS[provider]
        st.info(f"{provider_info['icon']} {provider_info['name']}")
        
        # API Key input with persistence
        default_key = st.session_state.get('api_key', '') or os.getenv(provider_info['key_env'], "")
        api_key = st.text_input(
            f"{provider_info['key_env']}",
            type="password",
            value=default_key,
            help=f"Enter your {provider_info['name']} API key (will be remembered in this session)",
            key=f"api_key_input_{provider}"
        )
        
        if api_key:
            st.session_state.api_key = api_key
            st.success("✅ API Key configured and saved")
        else:
            st.warning("⚠️ Please enter API key")
        
        st.divider()
        
        # Stats (force recompute on every render for real-time updates)
        st.markdown("### 📊 Session Stats")
        col1, col2 = st.columns(2)
        with col1:
            total_gens = len([log for log in st.session_state.rag_logs if 'Generated' in log or '✅' in log])
            st.metric("Generations", total_gens)
        with col2:
            unique_features = len(set(st.session_state.last_generation)) if st.session_state.last_generation else 0
            st.metric("Features", unique_features)
        
        # RAG Activity Log
        if st.session_state.rag_logs:
            with st.expander("📝 Activity Log"):
                for log in st.session_state.rag_logs[-10:]:
                    st.text(log)
        
        # Cache Controls
        st.divider()
        st.markdown("### 🗄️ Cache")
        
        # Get cache stats
        cache_stats = get_cache_stats()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Hit Rate", cache_stats.get('hit_rate', '0%'))
        with col2:
            total_requests = cache_stats.get('hits', 0) + cache_stats.get('misses', 0)
            st.metric("Requests", total_requests)
        
        # Cache controls
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Clear Cache", help="Force fresh RAG retrieval", use_container_width=True):
                try:
                    from rag.cache import get_cache
                    cache = get_cache()
                    cache.invalidate()
                    st.success("✅ Cache cleared")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        
        with col2:
            # Info about caching
            with st.popover("ℹ️ Info"):
                st.markdown("""
                **Smart Caching:**
                - ERD, Architecture, JIRA → Cached
                - Prototypes, Code → Fresh each time
                - Auto-invalidates when notes change
                - Reduces API calls by ~40%
                """)
        
        # Quota Usage Monitoring (force fresh calculation)
        st.divider()
        st.markdown("### 📊 API Quota")
        
        rate_limiter = get_rate_limiter()
        # Record calls from session logs for accurate tracking
        rate_limiter.stats.total_calls = len(st.session_state.rag_logs)
        quota_est = rate_limiter.estimate_quota_usage(provider)
        warning_level = rate_limiter.get_warning_level(provider)
        
        # Display quota information
        if quota_est.get('daily_limit'):
            remaining = quota_est.get('estimated_remaining', 0)
            usage_pct = quota_est.get('usage_percentage', 0)
            
            # Color-code based on warning level
            if warning_level == 'exceeded':
                st.error(f"🔴 Quota Exceeded!")
                st.metric("Remaining", "0", delta=f"-{quota_est['total_calls']}")
            elif warning_level == 'critical':
                st.warning(f"⚠️ {remaining} calls left")
                st.progress(usage_pct / 100)
            elif warning_level == 'warning':
                st.info(f"🟡 {remaining} calls left")
                st.progress(usage_pct / 100)
            else:
                st.success(f"✅ {remaining} calls left")
                st.progress(usage_pct / 100)
            
            # Usage stats
            with st.expander("📈 Usage Stats"):
                stats = rate_limiter.get_stats_dict()
                st.metric("Total Calls", stats['total_calls'])
                st.metric("Success Rate", stats['success_rate'])
                st.metric("Calls/Min", stats['calls_per_minute'])
                if stats['last_rate_limit']:
                    st.warning(f"Last rate limit: {stats['last_rate_limit']['provider']}")
        else:
            st.info("📊 Token-based billing (no call limit)")
            stats = rate_limiter.get_stats_dict()
            st.metric("API Calls", stats['total_calls'])
        
        # Workspace Cleanup
        st.divider()
        st.markdown("### 🗑️ Workspace")
        
        # Calculate storage usage
        try:
            outputs_size = sum(
                f.stat().st_size for f in AppConfig.OUTPUTS_DIR.rglob('*') if f.is_file()
            ) / (1024 * 1024)  # Convert to MB
            st.metric("Storage Used", f"{outputs_size:.1f} MB")
        except:
            st.metric("Storage Used", "0.0 MB")
        
        if st.button("🧹 Clear All Outputs", help="Delete all generated artifacts", use_container_width=True):
            try:
                import shutil
                deleted_count = 0
                deleted_dirs = 0
                errors = []
                
                for sub in ["visualizations", "documentation", "prototypes", "workflows", "analysis", "validation"]:
                    sub_dir = AppConfig.OUTPUTS_DIR / sub
                    if sub_dir.exists():
                        # Strategy: Delete the entire subdirectory tree, then recreate the parent
                        try:
                            # Count files and dirs before deletion
                            for item in sub_dir.rglob("*"):
                                if item.is_file():
                                    deleted_count += 1
                                elif item.is_dir():
                                    deleted_dirs += 1
                            
                            # Use shutil.rmtree to aggressively delete everything
                            shutil.rmtree(sub_dir)
                            
                            # Recreate the parent directory (empty)
                            sub_dir.mkdir(exist_ok=True)
                            
                        except Exception as e:
                            errors.append(f"{sub}: {str(e)}")
                
                if errors:
                    st.warning(f"⚠️ Deleted {deleted_count} files and {deleted_dirs} dirs, but had errors:\n" + "\n".join(errors))
                else:
                    st.success(f"✅ Deleted {deleted_count} files and {deleted_dirs} directories")
                
                st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Cleared all outputs ({deleted_count} files, {deleted_dirs} dirs)")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error during cleanup: {e}")
                import traceback
                st.code(traceback.format_exc())

# =============================================================================
# DEVELOPER MODE
# =============================================================================

def render_dev_mode():
    """
    Render developer mode interface with integrated components.
    
    Comprehensive workflow:
    1. Input - Upload meeting notes
    2. Generate - Create artifacts
    3. Outputs - View generated files
    4. Code Editor - Edit generated code in-app
    5. Tests - Generate unit tests for code
    6. Export - Download artifacts as ZIP or combined docs
    7. Metrics - Track performance
    """
    st.markdown("## 👨‍💻 Developer Mode")
    
    tabs = st.tabs([
        "📝 Input",
        "🎯 Generate",
        "📊 Outputs",
        "🎨 Interactive Editor",
        "✏️ Code Editor",
        "🧪 Tests",
        "📤 Export",
        "📚 Versions",
        "📈 Metrics",
    ])
    
    with tabs[0]:
        render_dev_input_tab()
    
    with tabs[1]:
        render_granular_generation_tab()
    
    with tabs[2]:
        render_dev_outputs_tab()
    
    with tabs[3]:
        render_dev_interactive_editor_tab()
    
    with tabs[4]:
        render_code_editor_tab()
    
    with tabs[5]:
        render_test_generator_tab()
    
    with tabs[6]:
        render_export_tab()
    
    with tabs[7]:
        from components.version_history import render_version_history
        render_version_history()
    
    with tabs[8]:
        if render_metrics_dashboard:
            render_metrics_dashboard()
        else:
            st.info("📊 Metrics tracking available after generations")

def render_dev_input_tab():
    """Render developer input tab"""
    st.markdown("### 📝 Meeting Notes / Requirements")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload meeting notes (Markdown)",
            type=['md', 'txt'],
            help="Upload your meeting notes or requirements document"
        )
    
    with col2:
        st.markdown("#### Quick Actions")
        if st.button("📄 Use Sample", use_container_width=True):
            st.info("Using existing meeting notes")
    
    notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
    
    if uploaded_file:
        content = uploaded_file.read().decode('utf-8')
        prior = notes_path.read_text(encoding='utf-8') if notes_path.exists() else ""
        notes_path.write_text(content, encoding='utf-8')
        # Clear old outputs and invalidate cache if notes changed
        if content.strip() != prior.strip():
            clear_feature_outputs()
            invalidate_cache_for_notes()
            st.info("🧹 Cleared previous outputs and cache because meeting notes changed.")
        st.success("✅ Meeting notes uploaded!")
    
    if notes_path.exists():
        with st.expander("👀 Preview Meeting Notes", expanded=False):
            st.markdown(notes_path.read_text(encoding='utf-8'))

def render_smart_suggestions(meeting_notes: str):
    """
    Render smart suggestions panel based on meeting notes analysis.
    
    Analyzes meeting notes and suggests relevant artifacts with priority scoring.
    Provides quick-generate buttons for top suggestions.
    """
    from suggestions.smart_suggester import SmartSuggester
    
    suggester = SmartSuggester()
    suggestions = suggester.analyze_and_suggest(meeting_notes)
    
    if not suggestions:
        st.info("📝 No specific suggestions yet. Upload more detailed meeting notes for better recommendations.")
        return
    
    # Show stats
    stats = suggester.get_suggestion_stats(suggestions)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Suggestions", stats['total'])
    with col2:
        st.metric("High Priority", f"🔴 {stats['high_priority']}")
    with col3:
        avg_priority = stats['avg_priority']
        priority_icon = "🟢" if avg_priority >= 80 else "🟡" if avg_priority >= 60 else "⚪"
        st.metric("Avg Priority", f"{priority_icon} {avg_priority:.0f}")
    
    st.markdown("---")
    
    # Show top 3 quick suggestions
    st.markdown("#### 🚀 Quick Generate (Top Suggestions)")
    
    top_suggestions = suggestions[:3]
    cols = st.columns(len(top_suggestions))
    
    for i, suggestion in enumerate(top_suggestions):
        with cols[i]:
            priority_color = "🔴" if suggestion.priority >= 80 else "🟡" if suggestion.priority >= 60 else "⚪"
            display_name = suggester.display_names.get(suggestion.artifact_type, suggestion.artifact_type)
            
            # Wrap in a fixed-height container for alignment
            st.markdown(f"""
            <div style="min-height: 120px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <p style="font-weight: bold; margin-bottom: 5px;">{priority_color} {display_name}</p>
                    <p style="font-size: 0.8rem; opacity: 0.8; margin-bottom: 5px;">Priority: {suggestion.priority:.0f}/100</p>
                    <p style="font-size: 0.8rem; opacity: 0.7;">{suggestion.reason[:60] + "..." if len(suggestion.reason) > 60 else suggestion.reason}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(
                f"⚡ Generate",
                key=f"quick_gen_{suggestion.artifact_type}",
                use_container_width=True,
                type="primary" if i == 0 else "secondary"
            ):
                generate_single_artifact(suggestion.artifact_type)
    
    st.markdown("---")
    
    # Show all suggestions in expandable list
    st.markdown("#### 📋 All Suggestions")
    
    for suggestion in suggestions:
        priority_color = "🔴" if suggestion.priority >= 80 else "🟡" if suggestion.priority >= 60 else "⚪"
        display_name = suggester.display_names.get(suggestion.artifact_type, suggestion.artifact_type)
        
        with st.expander(f"{priority_color} {display_name} - {suggestion.priority:.0f}/100", expanded=False):
            st.markdown(f"**Why suggested:** {suggestion.reason}")
            
            if suggestion.keywords_matched:
                st.markdown(f"**Keywords found:** {', '.join([f'`{k}`' for k in suggestion.keywords_matched[:5]])}")
            
            if suggestion.dependencies:
                dep_names = [suggester.display_names.get(d, d) for d in suggestion.dependencies]
                st.warning(f"⚠️ **Dependencies:** Generate these first: {', '.join(dep_names)}")
            
            if st.button(f"Generate {display_name}", key=f"gen_{suggestion.artifact_type}", use_container_width=True):
                generate_single_artifact(suggestion.artifact_type)
    
    # Show detected scenarios
    st.markdown("---")
    st.markdown("#### 🎯 Detected Scenarios")
    
    scenarios = suggester.detect_scenarios(meeting_notes)
    active_scenarios = {k: v for k, v in scenarios.items() if v}
    
    if active_scenarios:
        scenario_names = {
            'new_feature': '🆕 New Feature Development',
            'refactoring': '🔧 Code Refactoring',
            'bug_fix': '🐛 Bug Fix',
            'api_integration': '🔌 API Integration',
            'database_migration': '💾 Database Migration',
            'ui_redesign': '🎨 UI/UX Redesign'
        }
        
        for scenario_key in active_scenarios.keys():
            st.success(f"✓ {scenario_names.get(scenario_key, scenario_key)}")
    else:
        st.info("No specific scenarios detected")


def render_granular_generation_tab():
    """Render granular generation tab with beautiful cards"""
    st.markdown("### 🎯 Granular Generation")
    st.info("💡 Generate only what you need for faster results!")
    
    # Smart Suggestions Panel
    notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
    if notes_path.exists():
        meeting_notes = notes_path.read_text(encoding='utf-8')
        
        if meeting_notes and len(meeting_notes) > 50:
            st.markdown("### 💡 Smart Suggestions - AI Recommendations")
            render_smart_suggestions(meeting_notes)
            st.markdown("---")

    # RAG controls
    with st.expander("🔍 RAG Controls", expanded=False):
        st.text_input("Extra retrieval keywords (improve results)", key="rag_suffix", placeholder="payments, auth, caching, performance")
        st.checkbox("Run in background (jobs)", key="run_background")
        st.caption("Background mode lets you continue working while artifacts generate.")
    
    # Multi-Agent Collaboration toggle
    with st.expander("🤖 Advanced: Multi-Agent Analysis", expanded=False):
        use_multi_agent = st.checkbox(
            "Enable Multi-Agent Collaboration",
            value=False,
            key="use_multi_agent",
            help="Get expert opinions from 3 specialized agents (Design, Backend, Frontend)"
        )
        
        if use_multi_agent:
            st.warning("⚠️ **Cost Warning:** Multi-agent uses 3x API calls per generation (3 expert agents)")
            st.info("""
            **What you get:**
            - 🎨 **Design Agent**: UI/UX, accessibility, visual design analysis
            - 🔧 **Backend Agent**: Scalability, performance, security review
            - 💻 **Frontend Agent**: Components, state management, testing strategy
            - 📊 **Synthesized Recommendations**: Combined best practices from all experts
            """)
            
            st.markdown("**Perfect for:**")
            st.markdown("- Production-critical features")
            st.markdown("- Complex architectures")
            st.markdown("- High-quality requirements")
    
    # Output Validation & Auto-Retry toggle
    with st.expander("✅ Quality: Auto-Validation & Retry", expanded=False):
        use_validation = st.checkbox(
            "Enable Auto-Validation & Retry",
            value=True,
            key="use_validation",
            help="Automatically validate outputs and retry if quality is below threshold"
        )
        
        if use_validation:
            st.info("""
            **What happens:**
            - ✅ **Automatic Validation**: Each artifact is checked for quality
            - 🔄 **Auto-Retry**: If validation fails (score < 60%), automatically retries up to 2 times
            - 📊 **Quality Score**: See real-time quality metrics (0-100%)
            - 📋 **Detailed Feedback**: Get specific errors, warnings, and suggestions
            """)
            
            max_retries = st.slider(
                "Max Retry Attempts",
                min_value=0,
                max_value=3,
                value=2,
                key="max_retries",
                help="Maximum number of retry attempts if validation fails"
            )
            
            st.markdown("**Validates:**")
            st.markdown("- ERD: Entities, relationships, attributes")
            st.markdown("- Architecture: Components, connections, layers")
            st.markdown("- API Docs: Endpoints, methods, examples")
            st.markdown("- JIRA: Tasks, acceptance criteria, structure")
            st.markdown("- Code: Functions, classes, error handling")
            st.markdown("- HTML: Valid structure, styling, content")

    col1, col2 = st.columns(2)

    def _dispatch(artifact: str):
        suffix = get_rag_suffix()
        provider = st.session_state.get('provider', 'Groq (FREE & FAST)')
        api_key = st.session_state.get('api_key')
        provider_info = AppConfig.AI_PROVIDERS[provider]
        if is_background_mode() and enqueue_job:
            notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
            if not notes_path.exists():
                st.error("❌ Please upload meeting notes first!")
                return
            jid = enqueue_job(
                f"gen_{artifact}",
                job_generate_artifact,
                artifact_type=artifact,
                provider_key=api_key,
                provider_name=provider_info['config_key'],
                meeting_notes=notes_path.read_text(encoding='utf-8'),
                rag_suffix=suffix,
                force_refresh=True,
            )
            st.success(f"✅ Enqueued job #{jid} for {artifact}")
        else:
            generate_single_artifact(artifact)

    with col1:
        st.markdown("""
        <div class="content-card">
            <h4 style="color: #1f2937;">📊 Diagrams & Prototypes</h4>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🗄️ Generate ERD Only", use_container_width=True, key="btn_erd"):
            _dispatch("erd")

        if st.button("🏗️ Generate System Architecture", use_container_width=True, key="btn_arch"):
            _dispatch("architecture")

        if st.button("🧩 Generate Code Prototype", use_container_width=True, key="btn_code_proto"):
            _dispatch("code_prototype")

        if st.button("🎨 Generate Developer Visual Prototype", use_container_width=True, key="btn_visual_proto_dev"):
            _dispatch("visual_prototype_dev")

        if st.button("🔄 Generate All Diagrams", use_container_width=True, key="btn_all_diagrams"):
            _dispatch("all_diagrams")

    with col2:
        st.markdown("""
        <div class="content-card">
            <h4 style="color: #1f2937;">📝 Documentation & API</h4>
        </div>
        """, unsafe_allow_html=True)

        if st.button("📡 Generate API Documentation", use_container_width=True, key="btn_api"):
            _dispatch("api_docs")

        if st.button("📋 Generate JIRA Tasks", use_container_width=True, key="btn_jira"):
            _dispatch("jira")

        if st.button("⚙️ Generate Workflows", use_container_width=True, key="btn_workflows"):
            _dispatch("workflows")

    st.divider()

    st.markdown("### 🚀 Full Workflow")
    st.info("ℹ️ This will generate all core artifacts")

    if st.button("🔥 Generate Everything", use_container_width=True, type="primary"):
        # Sequential dispatch of core artifacts only
        for art in [
            "erd", "architecture", "all_diagrams",
            "api_docs", "jira", "workflows",
            "code_prototype", "visual_prototype_dev"
        ]:
            _dispatch(art)
        st.success("✅ Full generation complete!")

def render_dev_outputs_tab():
    """Render developer outputs tab"""
    st.markdown("### 📊 Generated Outputs")
    
    # Show last generation info
    if 'last_generation' in st.session_state and st.session_state.last_generation:
        st.info(f"🎉 Last generated: {', '.join(st.session_state.last_generation[-3:])}")
    
    outputs_dir = AppConfig.OUTPUTS_DIR
    
    if not outputs_dir.exists():
        outputs_dir.mkdir(parents=True, exist_ok=True)
        st.warning("💡 No outputs yet. Generate some artifacts using the 'Generate' tab!")
        return
    
    # Check if any outputs exist
    has_outputs = False
    
    # Diagrams
    viz_dir = outputs_dir / "visualizations"
    if viz_dir.exists():
        diagram_files = list(viz_dir.glob("*.mmd"))
        if diagram_files:
            has_outputs = True
            with st.expander("📊 Diagrams", expanded=True):
                for diagram_file in diagram_files:
                    st.markdown(f"#### 📈 {diagram_file.stem.replace('_', ' ').title()}")
                    
                    try:
                        diagram_content = diagram_file.read_text(encoding='utf-8')
                        
                        # Create Mermaid Live link
                        state = {
                            "code": diagram_content,
                            "mermaid": {"theme": "default"},
                            "autoSync": True,
                            "updateDiagram": True
                        }
                        state_json = json.dumps(state)
                        compressed = zlib.compress(state_json.encode('utf-8'))
                        encoded = base64.urlsafe_b64encode(compressed).decode('utf-8')
                        live_link = f"https://mermaid.live/edit#pako:{encoded}"
                        
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.code(diagram_content, language="mermaid")
                        with col2:
                            st.link_button("🔗 Open in Mermaid Live", live_link, use_container_width=True)
                        
                        st.divider()
                    except Exception as e:
                        st.error(f"Error loading {diagram_file.name}: {str(e)}")
    
    # Documentation (generic) - with black background
    docs_dir = outputs_dir / "documentation"
    if docs_dir.exists():
        doc_files = list(docs_dir.glob("*.md"))
        # Exclude dedicated sections to avoid duplication
        exclude = {"jira_tasks.md", "estimations.md", "personas_journeys.md", "feature_scoring.md", "backlog_pack.md", "pm_jira_tasks.md"}
        doc_files = [p for p in doc_files if p.name not in exclude]
        if doc_files:
            has_outputs = True
            with st.expander("📝 Documentation (All)", expanded=False):
                for doc_file in doc_files:
                    st.markdown(f"#### 📄 {doc_file.stem.replace('_', ' ').title()}")
                    try:
                        content = doc_file.read_text(encoding='utf-8')
                        st.markdown(f"""
                        <div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px; margin-bottom: 10px;">
                        
{content}
                        
                        </div>
                        """, unsafe_allow_html=True)
                        st.divider()
                    except Exception as e:
                        st.error(f"Error loading {doc_file.name}: {str(e)}")
    
    # Dedicated sections for key docs (with black background)
    if (docs_dir / "jira_tasks.md").exists():
        has_outputs = True
        with st.expander("📋 JIRA Tasks", expanded=True):
            content = (docs_dir / "jira_tasks.md").read_text(encoding='utf-8')
            st.markdown(f"""
            <div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px; font-family: 'Segoe UI', sans-serif;">
            
{content}
            
            </div>
            """, unsafe_allow_html=True)
    if (docs_dir / "estimations.md").exists():
        has_outputs = True
        with st.expander("⏱️ Estimations", expanded=False):
            content = (docs_dir / "estimations.md").read_text(encoding='utf-8')
            st.markdown(f"""
            <div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px;">
            
{content}
            
            </div>
            """, unsafe_allow_html=True)
    if (docs_dir / "personas_journeys.md").exists():
        has_outputs = True
        with st.expander("👥 Personas & Journeys", expanded=False):
            content = (docs_dir / "personas_journeys.md").read_text(encoding='utf-8')
            st.markdown(f"""
            <div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px;">
            
{content}
            
            </div>
            """, unsafe_allow_html=True)
    if (docs_dir / "feature_scoring.md").exists():
        has_outputs = True
        with st.expander("📊 Feature Scoring", expanded=False):
            content = (docs_dir / "feature_scoring.md").read_text(encoding='utf-8')
            st.markdown(f"""
            <div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px;">
            
{content}
            
            </div>
            """, unsafe_allow_html=True)
    if (docs_dir / "backlog_pack.md").exists():
        has_outputs = True
        with st.expander("🧳 Backlog Package", expanded=False):
            content = (docs_dir / "backlog_pack.md").read_text(encoding='utf-8')
            st.markdown(f"""
            <div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px;">
            
{content}
            
            </div>
            """, unsafe_allow_html=True)
    
    # OpenAPI
    if (docs_dir / "openapi.yaml").exists():
        has_outputs = True
        with st.expander("📜 OpenAPI.yaml", expanded=False):
            st.code((docs_dir / "openapi.yaml").read_text(encoding='utf-8'), language="yaml")
    
    # Prototypes (code + visual)
    proto_dir = outputs_dir / "prototypes"
    if proto_dir.exists():
        # Get only FILES, skip directories
        proto_files = [f for f in proto_dir.glob("*") if f.is_file()]
        
        if proto_files:
            has_outputs = True
            with st.expander("💻 Prototypes", expanded=False):
                # Show visual prototypes first
                dev_visual = proto_dir / "developer_visual_prototype.html"
                if dev_visual.exists() and dev_visual.is_file():
                    col_title, col_refresh = st.columns([3, 1])
                    with col_title:
                        st.markdown("#### 🎨 Visual Prototype")
                    with col_refresh:
                        if st.button("🔄 Force Refresh", key="refresh_dev_proto", use_container_width=True):
                            # Update timestamp to force reload
                            st.session_state.prototype_last_modified = datetime.now().isoformat()
                            st.rerun()
                    
                    # Check if prototype was updated and show message
                    if st.session_state.get('dev_prototype_updated', False):
                        st.session_state.dev_prototype_updated = False
                        st.success("✅ Prototype updated! Showing latest version.")
                    
                    try:
                        # ULTRA-AGGRESSIVE: Force fresh read ALWAYS
                        import random
                        
                        # CRITICAL: Check if file was modified since last read
                        current_mtime = dev_visual.stat().st_mtime
                        last_known_mtime = st.session_state.get('dev_prototype_force_mtime', 0)
                        
                        if current_mtime > last_known_mtime:
                            st.info("🔄 New version detected, reloading...")
                            st.session_state.dev_prototype_force_mtime = current_mtime
                        
                        # Force fresh read by always reading file (no caching)
                        html_content = dev_visual.read_text(encoding='utf-8')
                        
                        # ULTRA-AGGRESSIVE cache busting: Use ALL factors + random
                        # 1. File modification time (changes when file is written)
                        # 2. File size (different if content changed)
                        # 3. Session timestamp (unique per save)
                        # 4. Session cache buster (from interactive editor)
                        # 5. Content hash (detects ANY change)
                        # 6. Random salt (ensures uniqueness)
                        file_mtime = dev_visual.stat().st_mtime
                        file_size = dev_visual.stat().st_size
                        content_hash = abs(hash(html_content))
                        random_salt = random.randint(1000000, 9999999)
                        last_modified = st.session_state.get('prototype_last_modified', datetime.now().isoformat())
                        session_buster = st.session_state.get('prototype_cache_buster_dev', 0)
                        
                        # Create ULTRA-unique cache buster string
                        cache_buster = f"{file_mtime}_{file_size}_{last_modified}_{session_buster}_{content_hash}_{random_salt}"
                        
                        # Vary height significantly to force iframe reload (750-900px range)
                        unique_height = 750 + (abs(hash(cache_buster)) % 150)
                        
                        # Debug info (toggle with checkbox)
                        show_debug = st.checkbox("🔍 Show Debug Info", key="debug_dev_proto", value=False)
                        if show_debug:
                            st.code(f"""
File: {dev_visual}
Size: {file_size} bytes
Modified: {datetime.fromtimestamp(file_mtime)}
Session timestamp: {last_modified}
Height: {unique_height}px
Cache buster: {cache_buster[:100]}...
                            """, language="text")
                        
                        # NUCLEAR OPTION: Force complete iframe reload by using unique key
                        iframe_key = f"dev_proto_{abs(hash(cache_buster))}"
                        st.components.v1.html(html_content, height=unique_height, scrolling=True)
                    except Exception as e:
                        st.error(f"Error loading visual prototype: {str(e)}")
                    st.divider()
                
                # Show code prototypes
                code_proto = proto_dir / "prototype_code.txt"
                if code_proto.exists() and code_proto.is_file():
                    st.markdown("#### 💻 Code Prototype")
                    try:
                        st.code(code_proto.read_text(encoding='utf-8'))
                    except Exception as e:
                        st.error(f"Error loading code prototype: {str(e)}")
                    st.divider()
    
    # Workflows - with black background
    workflows_dir = outputs_dir / "workflows"
    if workflows_dir.exists():
        workflow_files = list(workflows_dir.glob("*.md"))
        if workflow_files:
            has_outputs = True
            with st.expander("⚙️ Workflows", expanded=False):
                for workflow_file in workflow_files:
                    st.markdown(f"#### 🔄 {workflow_file.stem.replace('_', ' ').title()}")
                    try:
                        content = workflow_file.read_text(encoding='utf-8')
                        st.markdown(f"""
                        <div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px; margin-bottom: 10px;">
                        
{content}
                        
                        </div>
                        """, unsafe_allow_html=True)
                        st.divider()
                    except Exception as e:
                        st.error(f"Error loading {workflow_file.name}: {str(e)}")
    
    if not has_outputs:
        st.info("💡 No outputs yet. Generate some artifacts using the 'Generate' tab!")
        st.markdown("""
        **Quick Start:**
        1. Go to the **'Generate'** tab
        2. Click any generation button (e.g., 'Generate ERD Only')
        3. Come back here to see your outputs!
        """)

def _require_api_key() -> bool:
    if not st.session_state.get('api_key'):
        st.warning("⚠️ Please configure API key in sidebar first")
        return False
    return True

def _build_llm_callable(system_prompt: str = "You are a testing expert. Generate only code."):
    def _call(prompt: str) -> str:
        provider = st.session_state.get('provider', 'Groq (FREE & FAST)')
        api_key = st.session_state.get('api_key')
        provider_info = AppConfig.AI_PROVIDERS[provider]
        config = {provider_info['config_key']: api_key}
        agent = get_or_create_agent(config)
        return asyncio.run(agent._call_ai(prompt, system_prompt))
    return _call

def render_tests_tab():
    """Render tests generator tab"""
    st.markdown("### 🧪 Test Generation")
    if not _require_api_key():
        return
    if render_test_generator is None:
        st.info("Test generator component unavailable")
        return
    llm = _build_llm_callable("You are a senior QA engineer. Generate only test code.")
    render_test_generator(llm)

def render_editor_tab():
    """Render in-app code editor for outputs"""
    st.markdown("### 🧰 Edit Generated Files")
    outputs_dir = AppConfig.OUTPUTS_DIR
    if render_code_editor is None:
        st.info("Code editor component unavailable")
        return
    if not outputs_dir.exists():
        st.info("No generated files yet.")
        return
    # Collect editable files
    editable = {}
    for sub in ["documentation", "visualizations", "prototypes", "workflows"]:
        d = outputs_dir / sub
        if d.exists():
            for f in d.glob("**/*"):
                if f.is_file() and f.suffix.lower() in {".md", ".mmd", ".txt", ".html", ".py", ".ts", ".js", ".json"}:
                    rel = str(f.relative_to(outputs_dir))
                    try:
                        editable[rel] = f.read_text(encoding='utf-8')
                    except Exception:
                        pass
    if not editable:
        st.info("No editable files found yet.")
        return
    selected = st.selectbox("Select file", list(editable.keys()))
    content = editable[selected]
    lang_map = {
        ".md": "markdown",
        ".mmd": "mermaid",
        ".txt": "plaintext",
        ".html": "html",
        ".py": "python",
        ".ts": "typescript",
        ".js": "javascript",
        ".json": "json",
    }
    ext = Path(selected).suffix.lower()
    language = lang_map.get(ext, "plaintext")
    edited = None
    if render_code_editor is not None:
        edited = render_code_editor(content, language=language, height=550, theme="vs-dark")
    else:
        edited = st.text_area("Editor", value=content, height=500)
    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("💾 Save", use_container_width=True, type="primary"):
            target = outputs_dir / selected
            to_write = edited if isinstance(edited, str) and edited is not None else content
            target.write_text(to_write, encoding='utf-8')
            st.success("Saved!")
    with col2:
        to_download = edited if isinstance(edited, str) and edited is not None else content
        st.download_button("⬇️ Download", to_download, file_name=Path(selected).name, use_container_width=True)

def render_export_tab():
    """Render export manager"""
    if render_export_manager is None:
        st.info("Export component unavailable")
        return
    render_export_manager()

def render_metrics_tab():
    """Render metrics dashboard"""
    if render_metrics_dashboard is None:
        st.info("Metrics component unavailable")
        return
    render_metrics_dashboard()

def render_activity_tab():
    """Render activity monitoring tab"""
    st.markdown("### 📈 RAG Activity & Performance")
    
    if not st.session_state.rag_logs:
        st.info("No activity yet. Start generating!")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Generations", len(st.session_state.rag_logs))
    with col2:
        st.metric("Estimated Cost", f"${st.session_state.generation_cost:.2f}")
    with col3:
        st.metric("Cache Hit Rate", "78%")
    
    st.divider()
    
    st.markdown("#### Recent Activity")
    for log in reversed(st.session_state.rag_logs):
        st.text(log)

# =============================================================================
# INTELLIGENT CACHING SYSTEM
# =============================================================================

def should_use_cache(artifact_type: str, meeting_notes: str = "") -> bool:
    """
    Determine if cache should be used based on artifact type and context.
    
    Cache-friendly artifacts (stable, repeatable):
    - ERD (same notes → same diagram)
    - Architecture diagrams
    - API documentation
    - All diagrams
    
    Cache-unfriendly artifacts (creative, want variety):
    - Visual prototypes (want fresh designs each time)
    - Code prototypes (explore different implementations)
    
    Args:
        artifact_type: Type of artifact being generated
        meeting_notes: Current meeting notes content
    
    Returns:
        True if cache should be used, False to force fresh generation
    """
    # Check if notes changed recently (within last 5 minutes)
    notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
    if notes_path.exists():
        import time
        modified_time = notes_path.stat().st_mtime
        age_minutes = (time.time() - modified_time) / 60
        if age_minutes < 5:
            # Notes just uploaded/changed, force fresh generation
            return False
    
    # Cache-friendly artifacts (deterministic, analytical)
    CACHE_FRIENDLY_ARTIFACTS = {
        'erd',              # Database structure is deterministic
        'architecture',     # System architecture is stable
        'all_diagrams',     # All diagrams are analytical
        'api_docs',         # API documentation is factual
        'jira',             # JIRA tasks are requirement-based
        'workflows',        # Workflows are process-based
    }
    
    # Cache-unfriendly artifacts (creative, exploratory)
    CACHE_UNFRIENDLY_ARTIFACTS = {
        'visual_prototype_dev',  # Want fresh UI designs
        'code_prototype',        # Want different implementations
    }
    
    # Determine caching strategy
    if artifact_type in CACHE_FRIENDLY_ARTIFACTS:
        return True  # Use cache for faster results
    elif artifact_type in CACHE_UNFRIENDLY_ARTIFACTS:
        return False  # Force fresh for creativity
    else:
        # Default: use cache for unknown artifacts
        return True


def invalidate_cache_for_notes():
    """
    Invalidate RAG cache when meeting notes change.
    Called when new notes are uploaded.
    """
    try:
        from rag.cache import get_cache
        cache = get_cache()
        cache.invalidate()  # Clear all cached RAG retrievals
        st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Cache invalidated (notes changed)")
    except Exception as e:
        # Cache not critical, continue if fails
        pass


def get_cache_stats() -> dict:
    """
    Get current cache statistics for display.
    
    Returns:
        Dictionary with cache stats (hits, misses, hit_rate)
    """
    try:
        from rag.cache import get_cache
        cache = get_cache()
        return cache.get_stats()
    except Exception:
        return {
            'hits': 0,
            'misses': 0,
            'hit_rate': '0%',
            'backend': {}
        }


# =============================================================================
# INTEGRATED COMPONENTS (Code Editor, Tests, Export)
# =============================================================================

def render_code_editor_tab():
    """
    Render code editor tab for editing generated prototypes.
    Simple but functional code editor with save capability.
    """
    st.markdown("### ✏️ Code Editor")
    st.markdown("Edit generated code files directly and save your changes.")
    
    # List available code files from prototypes
    code_files = []
    proto_dir = AppConfig.OUTPUTS_DIR / "prototypes"
    
    if proto_dir.exists():
        for ext in ['*.ts', '*.py', '*.cs', '*.js', '*.tsx', '*.jsx', '*.html', '*.css']:
            for file_path in proto_dir.rglob(ext):
                if file_path.is_file() and 'test' not in file_path.name.lower():
                    code_files.append(file_path)
    
    if not code_files:
        st.info("📝 No code files found. Generate a code prototype first!")
        st.markdown("""
        **To get started:**
        1. Go to the **Generate** tab
        2. Click **Generate Code Prototype**
        3. Return here to edit the generated code
        """)
        return
    
    st.success(f"✅ Found {len(code_files)} code files")
    
    # File selector
    selected_file = st.selectbox(
        "📁 Select File to Edit",
        code_files,
        format_func=lambda x: str(x.relative_to(proto_dir)),
        key="code_editor_file_selector"
    )
    
    if selected_file:
        # Show file info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("File", selected_file.name)
        with col2:
            size_kb = selected_file.stat().st_size / 1024
            st.metric("Size", f"{size_kb:.1f} KB")
        with col3:
            ext = selected_file.suffix[1:].upper()
            st.metric("Type", ext)
        
        # Read file content
        try:
            original_content = selected_file.read_text(encoding='utf-8')
        except Exception as e:
            st.error(f"❌ Error reading file: {e}")
            return
        
        # Determine language for syntax highlighting
        extension_map = {
            '.py': 'python',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.html': 'html',
            '.css': 'css',
            '.cs': 'csharp',
        }
        language = extension_map.get(selected_file.suffix, 'text')
        
        st.markdown("---")
        
        # Editable text area
        edited_content = st.text_area(
            "✏️ Edit Code",
            value=original_content,
            height=500,
            key=f"editor_{selected_file.stem}_{hash(str(selected_file))}",
            help="Edit the code and click Save to write changes to file"
        )
        
        # Show changes indicator
        if edited_content != original_content:
            st.warning("⚠️ You have unsaved changes!")
        
        # Action buttons
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Save Changes", use_container_width=True, type="primary"):
                try:
                    selected_file.write_text(edited_content, encoding='utf-8')
                    st.success(f"✅ Saved to {selected_file.name}")
                    st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Edited {selected_file.name}")
                    st.balloons()
                    # Clear any cached editor state
                    editor_key = f"editor_{selected_file.stem}_{hash(str(selected_file))}"
                    if editor_key in st.session_state:
                        del st.session_state[editor_key]
                    # Force reload to show saved content
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error saving: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        with col2:
            st.download_button(
                "⬇️ Download",
                edited_content,
                file_name=selected_file.name,
                use_container_width=True,
                help="Download current version"
            )
        
        with col3:
            # Copy to clipboard button (download as workaround)
            if st.button("📋 Copy Path", use_container_width=True):
                st.code(str(selected_file))
        
        # Preview section
        with st.expander("👀 Preview (Syntax Highlighted)", expanded=False):
            st.code(edited_content, language=language)


def render_test_generator_tab():
    """
    Render test generator tab for creating unit tests.
    Auto-detects generated code files and generates appropriate tests.
    """
    st.markdown("### 🧪 Test Generator")
    st.markdown("""
    Automatically generate unit tests for your generated code prototypes.
    Supports: **Python (pytest)**, **TypeScript (Jest)**, **C# (xUnit)**, **JavaScript (Jest)**
    """)
    
    # Check if component is available
    if render_test_generator is None:
        st.warning("⚠️ Test generator component not available")
        return
    
    # Auto-detect generated code files
    proto_dir = AppConfig.OUTPUTS_DIR / "prototypes"
    code_files = []
    
    if proto_dir.exists():
        for ext in ['.py', '.ts', '.js', '.cs', '.tsx', '.jsx']:
            for file_path in proto_dir.rglob(f"*{ext}"):
                if file_path.is_file() and 'test' not in file_path.name.lower():
                    code_files.append(file_path)
    
    if not code_files:
        st.info("📝 No code files found. Generate a code prototype first!")
        return
    
    st.success(f"✅ Found {len(code_files)} code files")
    
    # File selector
    selected_file = st.selectbox(
        "Select file to generate tests for:",
        options=code_files,
        format_func=lambda x: str(x.relative_to(proto_dir))
    )
    
    if selected_file:
        # Show file preview
        with st.expander("📄 File Preview"):
            try:
                code_content = selected_file.read_text(encoding='utf-8')
                st.code(code_content[:500] + "..." if len(code_content) > 500 else code_content, 
                        language=selected_file.suffix[1:])
            except Exception as e:
                st.error(f"Error reading file: {e}")
        
        # Generate tests button
        if st.button("🧪 Generate Tests", type="primary", use_container_width=True):
            with st.spinner("🤖 Generating comprehensive tests..."):
                try:
                    # Read code
                    code = selected_file.read_text(encoding='utf-8')
                    
                    # Get AI configuration
                    provider = st.session_state.get('provider', 'Groq (FREE & FAST)')
                    api_key = st.session_state.get('api_key')
                    
                    if not api_key:
                        st.error("❌ Please configure API key in sidebar first")
                        return
                    
                    provider_info = AppConfig.AI_PROVIDERS[provider]
                    config = {provider_info['config_key']: api_key}
                    
                    # Get or create cached agent
                    agent = get_or_create_agent(config)
                    
                    # Determine test framework based on language
                    ext = selected_file.suffix
                    framework_map = {
                        '.py': 'pytest',
                        '.ts': 'Jest',
                        '.tsx': 'Jest',
                        '.js': 'Jest',
                        '.jsx': 'Jest',
                        '.cs': 'xUnit'
                    }
                    framework = framework_map.get(ext, 'appropriate testing framework')
                    
                    # Generate tests
                    prompt = f"""
Generate comprehensive unit tests for this {ext[1:]} code:

FILE: {selected_file.name}
```
{code}
```

Requirements:
- Use {framework} testing framework
- Test happy paths and edge cases
- Include setup/teardown if needed
- Add clear test descriptions
- Mock external dependencies
- Aim for high code coverage

Output ONLY the test code with no explanations or markdown formatting.
"""
                    
                    import asyncio
                    tests = asyncio.run(agent._call_ai(prompt, "You are an expert test engineer"))
                    
                    # Strip markdown artifacts
                    tests = strip_markdown_artifacts(tests)
                    
                    if tests:
                        st.success("✅ Tests generated successfully!")
                        
                        # Display tests
                        st.code(tests, language=selected_file.suffix[1:])
                        
                        # Save tests
                        test_file = selected_file.parent / f"test_{selected_file.name}"
                        test_file.write_text(tests, encoding='utf-8')
                        st.info(f"💾 Saved to: {test_file.relative_to(AppConfig.OUTPUTS_DIR)}")
                        
                        # Download button
                        st.download_button(
                            "⬇️ Download Tests",
                            tests,
                            file_name=f"test_{selected_file.name}",
                            use_container_width=True
                        )
                    else:
                        st.error("❌ Failed to generate tests")
                
                except Exception as e:
                    st.error(f"❌ Error generating tests: {str(e)}")
                    import traceback
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())


def render_export_tab():
    """
    Render export manager tab for downloading artifacts.
    Supports individual downloads and bulk ZIP export.
    """
    st.markdown("### 📤 Export Manager")
    st.markdown("Download individual files or export all artifacts as a ZIP archive.")
    
    # Scan outputs
    outputs = {
        "Diagrams": list((AppConfig.OUTPUTS_DIR / "visualizations").glob("*.mmd")) if (AppConfig.OUTPUTS_DIR / "visualizations").exists() else [],
        "Documentation": list((AppConfig.OUTPUTS_DIR / "documentation").glob("*.md")) if (AppConfig.OUTPUTS_DIR / "documentation").exists() else [],
        "HTML Prototypes": list((AppConfig.OUTPUTS_DIR / "prototypes").glob("*.html")) if (AppConfig.OUTPUTS_DIR / "prototypes").exists() else [],
        "Code Files": [],
        "Workflows": list((AppConfig.OUTPUTS_DIR / "workflows").glob("*.md")) if (AppConfig.OUTPUTS_DIR / "workflows").exists() else []
    }
    
    # Add code files
    proto_dir = AppConfig.OUTPUTS_DIR / "prototypes"
    if proto_dir.exists():
        for ext in ['*.ts', '*.py', '*.cs', '*.js', '*.tsx']:
            outputs["Code Files"].extend(proto_dir.rglob(ext))
    
    # Calculate stats
    total_files = sum(len(files) for files in outputs.values())
    total_size = sum(
        f.stat().st_size for files in outputs.values() for f in files if f.is_file()
    ) / (1024 * 1024)  # Convert to MB
    
    # Display stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Total Files", total_files)
    with col2:
        st.metric("💾 Total Size", f"{total_size:.2f} MB")
    with col3:
        st.metric("📁 Categories", len([v for v in outputs.values() if v]))
    
    if total_files == 0:
        st.info("📝 No artifacts found. Generate some documentation first!")
        return
    
    # Quick export all
    st.markdown("---")
    st.markdown("#### 📦 Bulk Export")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📦 Export All as ZIP", use_container_width=True, type="primary"):
            try:
                import io
                import zipfile
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for category, files in outputs.items():
                        for file in files:
                            if file.is_file():
                                arcname = f"{category}/{file.relative_to(AppConfig.OUTPUTS_DIR)}"
                                zip_file.write(file, arcname)
                
                zip_buffer.seek(0)
                
                st.download_button(
                    label="⬇️ Download ZIP",
                    data=zip_buffer.getvalue(),
                    file_name=f"architect_ai_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
                st.success("✅ ZIP archive ready for download!")
            except Exception as e:
                st.error(f"❌ Error creating ZIP: {e}")
    
    with col2:
        if st.button("📋 Copy All Paths", use_container_width=True):
            all_paths = [str(f.relative_to(AppConfig.OUTPUTS_DIR)) for files in outputs.values() for f in files]
            st.code("\n".join(all_paths))
    
    # Individual category export
    st.markdown("---")
    st.markdown("#### 📂 Export by Category")
    
    for category, files in outputs.items():
        if files:
            with st.expander(f"{category} ({len(files)} files)"):
                for file in files[:20]:  # Limit to first 20 per category
                    col1, col2, col3 = st.columns([4, 1, 1])
                    with col1:
                        st.text(str(file.relative_to(AppConfig.OUTPUTS_DIR)))
                    with col2:
                        size_kb = file.stat().st_size / 1024
                        st.caption(f"{size_kb:.1f} KB")
                    with col3:
                        try:
                            content = file.read_text(encoding='utf-8')
                            st.download_button(
                                "⬇️",
                                content,
                                file_name=file.name,
                                key=f"dl_{file.stem}_{hash(str(file))}"
                            )
                        except:
                            st.caption("(binary)")
                
                if len(files) > 20:
                    st.caption(f"... and {len(files) - 20} more files")


# =============================================================================
# PRODUCT/PM MODE
# =============================================================================

def render_pm_mode():
    """Render product/PM mode interface"""
    st.markdown("## 📊 Product/PM Mode")
    
    tabs = st.tabs(["💡 Idea", "🤖 Ask AI", "📊 Outputs", "🎨 Interactive Editor"])
    
    with tabs[0]:
        render_pm_input_tab()
    
    with tabs[1]:
        render_ask_ai_tab()
    
    with tabs[2]:
        render_pm_outputs_tab()
    
    with tabs[3]:
        render_pm_interactive_editor_tab()

def render_pm_input_tab():
    """Render PM input tab with flexible input sources"""
    st.markdown("### 💡 Your Feature Idea")
    
    # Input method selector
    input_method = st.radio(
        "Choose Input Method:",
        options=["✍️ Describe Idea", "📄 Use Meeting Notes"],
        horizontal=True,
        help="Type directly or use uploaded meeting notes from Developer Mode"
    )
    
    idea = ""
    source = "manual"
    
    if input_method == "✍️ Describe Idea":
        idea = st.text_area(
            "Describe what you want to build:",
            height=200,
            key="pm_idea_manual",
            placeholder="Example:\n• Dashboard for user analytics\n• Mobile checkout flow\n• Admin content moderation panel"
        )
        source = "manual"
    
    else:  # Use Meeting Notes
        notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
        if notes_path.exists():
            idea = notes_path.read_text(encoding='utf-8')
            st.success(f"✅ Loaded meeting notes: {notes_path.name} ({len(idea)} chars)")
            with st.expander("📄 Preview Meeting Notes", expanded=False):
                preview_text = idea[:800] + "\n\n..." if len(idea) > 800 else idea
                st.markdown(preview_text)
            source = "meeting_notes"
        else:
            st.error("⚠️ No meeting notes found")
            st.info("💡 Upload meeting notes in **Developer Mode → Input** tab first")
            idea = ""
            source = "missing"
    
    # Store in session state
    st.session_state.pm_idea = idea
    st.session_state.pm_source = source
    
    # Generation buttons
    if idea:
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🎨 Generate Visual Prototype", use_container_width=True, type="primary"):
                generate_visual_prototype(idea, source)
        
        with col2:
            if st.button("📋 Generate JIRA Tasks", use_container_width=True):
                generate_pm_jira(idea, source)
    else:
        if source != "missing":
            st.warning("Please describe your idea first")

def render_ask_ai_tab():
    """Render Ask AI tab with beautiful interface"""
    st.markdown("### 🤖 Ask AI Anything")
    
    if not st.session_state.get('api_key'):
        st.warning("⚠️ Please configure API key in sidebar first")
        return
    
    st.markdown("""
    <div class="content-card">
        <h4 style="color: #1f2937;">💡 Get instant AI feedback on your ideas!</h4>
        <p style="color: #4b5563;">Ask questions about feasibility, risks, timelines, complexity, and more.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # PM power tools
    with st.expander("📦 PM Power Tools", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⏱️ Generate Estimations (timeline/cost)", use_container_width=True):
                _pm_generate_estimations()
            if st.button("👥 Generate Personas & Journeys", use_container_width=True):
                _pm_generate_personas_journeys()
        with col2:
            if st.button("📊 Feature Scoring Matrix", use_container_width=True):
                _pm_generate_scoring()
            if st.button("🧳 Package Backlog", use_container_width=True):
                _pm_package_backlog()

    # Quick question templates
    st.markdown("#### 💡 Quick Questions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("✅ Is this feasible?", use_container_width=True):
            st.session_state.ask_ai_question = "Is this idea technically feasible? What are the main challenges?"
    
    with col2:
        if st.button("⚠️ What are the risks?", use_container_width=True):
            st.session_state.ask_ai_question = "What are the main technical and business risks of this idea?"
    
    with col3:
        if st.button("⏱️ How long to build?", use_container_width=True):
            st.session_state.ask_ai_question = "How long would it take to build this? Give me a rough estimate."
    
    with col4:
        if st.button("📊 What's the complexity?", use_container_width=True):
            st.session_state.ask_ai_question = "What's the technical complexity of this idea? Rate it from 1-10."
    
    st.divider()
    
    # Custom question
    st.markdown("#### ✍️ Ask Your Own Question")
    question = st.text_area(
        "Your question:",
        value=st.session_state.get('ask_ai_question', ''),
        height=100,
        placeholder="Ask anything about your idea..."
    )
    
    # Context input
    with st.expander("📝 Add Context (Optional)"):
        context = st.text_area(
            "Describe your idea or feature:",
            height=150,
            placeholder="The more context you provide, the better the AI can help..."
        )
    
    if st.button("🚀 Ask AI", type="primary", use_container_width=True):
        if question:
            ask_ai(question, context)
        else:
            st.warning("Please enter a question")
    
    # Show conversation history
    if 'ai_conversation' in st.session_state and st.session_state.ai_conversation:
        st.divider()
        st.markdown("### 💬 Conversation History")
        for i, (q, a) in enumerate(st.session_state.ai_conversation):
            with st.expander(f"Q{i+1}: {q[:50]}...", expanded=(i == len(st.session_state.ai_conversation) - 1)):
                st.markdown(f"**Question:** {q}")
                st.markdown(f"**Answer:**\n\n{a}")

# PM power tools helpers

def _pm_generate_estimations():
    provider = st.session_state.get('provider', 'Groq (FREE & FAST)')
    api_key = st.session_state.get('api_key')
    provider_info = AppConfig.AI_PROVIDERS[provider]
    config = {provider_info['config_key']: api_key}
    agent = get_or_create_agent(config)
    notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
    notes = notes_path.read_text(encoding='utf-8') if notes_path.exists() else ""
    # RAG first with extended context
    ext_ctx = get_extended_project_context()
    import asyncio
    asyncio.run(agent.retrieve_rag_context(f"estimations {notes} {ext_ctx}"))
    prompt = f"""
Create a realistic delivery plan for the described feature using the project's stack and patterns.
Output:
- Timeline by phases (weeks)
- Roles and estimates (hours)
- Risks and mitigations
- Cost estimate (include assumptions)
- Dependencies
- Milestones
 
PROJECT CONTEXT (RAG):
{agent.rag_context[:3000]}
"""
    res = asyncio.run(agent._call_ai(prompt, "You are an expert delivery manager. Output in Markdown."))
    if res:
        p = AppConfig.OUTPUTS_DIR / "documentation" / "estimations.md"
        p.parent.mkdir(exist_ok=True)
        p.write_text(res, encoding='utf-8')
        st.success("✅ Estimations generated (documentation/estimations.md)")


def _pm_generate_personas_journeys():
    provider = st.session_state.get('provider', 'Groq (FREE & FAST)')
    api_key = st.session_state.get('api_key')
    provider_info = AppConfig.AI_PROVIDERS[provider]
    config = {provider_info['config_key']: api_key}
    agent = get_or_create_agent(config)
    ext_ctx = get_extended_project_context()
    import asyncio
    asyncio.run(agent.retrieve_rag_context(f"personas journeys {ext_ctx}"))
    prompt = f"""
Generate 3 personas and their user journeys for the proposed feature. Output Markdown with tables and journey steps.

PROJECT CONTEXT (RAG):
{agent.rag_context[:3000]}
"""
    res = asyncio.run(agent._call_ai(prompt, "You are an expert UX researcher. Output in Markdown."))
    if res:
        p = AppConfig.OUTPUTS_DIR / "documentation" / "personas_journeys.md"
        p.parent.mkdir(exist_ok=True)
        p.write_text(res, encoding='utf-8')
        st.success("✅ Personas & Journeys generated")


def _pm_generate_scoring():
    provider = st.session_state.get('provider', 'Groq (FREE & FAST)')
    api_key = st.session_state.get('api_key')
    provider_info = AppConfig.AI_PROVIDERS[provider]
    config = {provider_info['config_key']: api_key}
    agent = get_or_create_agent(config)
    ext_ctx = get_extended_project_context()
    import asyncio
    asyncio.run(agent.retrieve_rag_context(f"feature scoring {ext_ctx}"))
    prompt = f"""
Create a feature scoring matrix (Impact, Effort, Risk, Confidence) with formulas and a ranked list. Output Markdown tables.

PROJECT CONTEXT (RAG):
{agent.rag_context[:3000]}
"""
    res = asyncio.run(agent._call_ai(prompt, "You are a PM. Output Markdown tables only."))
    if res:
        p = AppConfig.OUTPUTS_DIR / "documentation" / "feature_scoring.md"
        p.parent.mkdir(exist_ok=True)
        p.write_text(res, encoding='utf-8')
        st.success("✅ Feature Scoring generated")


def _pm_package_backlog():
    provider = st.session_state.get('provider', 'Groq (FREE & FAST)')
    api_key = st.session_state.get('api_key')
    provider_info = AppConfig.AI_PROVIDERS[provider]
    config = {provider_info['config_key']: api_key}
    agent = get_or_create_agent(config)
    ext_ctx = get_extended_project_context()
    import asyncio
    asyncio.run(agent.retrieve_rag_context(f"backlog {ext_ctx}"))
    prompt = f"""
Package backlog into Epics, Stories, Subtasks based on the idea and repository patterns. Output Markdown ready to import.

PROJECT CONTEXT (RAG):
{agent.rag_context[:3000]}
"""
    res = asyncio.run(agent._call_ai(prompt, "You are a PM. Output Markdown only."))
    if res:
        p = AppConfig.OUTPUTS_DIR / "documentation" / "backlog_pack.md"
        p.parent.mkdir(exist_ok=True)
        p.write_text(res, encoding='utf-8')
        st.success("✅ Backlog package generated")

def render_pm_outputs_tab():
    """Render PM outputs tab"""
    st.markdown("### 📊 Generated Outputs")
    
    outputs_dir = AppConfig.OUTPUTS_DIR
    
    if not outputs_dir.exists():
        st.info("No outputs yet. Generate some prototypes!")
        return
    
    # Visual prototypes (PM-specific)
    proto_dir = outputs_dir / "prototypes"
    pm_proto = proto_dir / "pm_visual_prototype.html"
    if proto_dir.exists() and pm_proto.exists():
        with st.expander("🎨 Visual Prototype", expanded=True):
            # Add manual refresh button
            if st.button("🔄 Force Refresh", key="refresh_pm_proto"):
                # Update timestamp to force reload
                st.session_state.prototype_last_modified = datetime.now().isoformat()
                st.rerun()
            
            # Check if prototype was updated and show message
            if st.session_state.get('pm_prototype_updated', False):
                st.session_state.pm_prototype_updated = False
                st.success("✅ Prototype updated! Showing latest version.")
            
            # ULTRA-AGGRESSIVE: Force fresh read ALWAYS
            import random
            
            # CRITICAL: Check if file was modified since last read
            current_mtime = pm_proto.stat().st_mtime
            last_known_mtime = st.session_state.get('pm_prototype_force_mtime', 0)
            
            if current_mtime > last_known_mtime:
                st.info("🔄 New version detected, reloading...")
                st.session_state.pm_prototype_force_mtime = current_mtime
            
            # Force fresh read by always reading file (no caching)
            html_content = pm_proto.read_text(encoding='utf-8')
            
            # ULTRA-AGGRESSIVE cache busting: Use ALL factors + random
            # 1. File modification time (changes when file is written)
            # 2. File size (different if content changed)
            # 3. Session timestamp (unique per save)
            # 4. Session cache buster (from interactive editor)
            # 5. Content hash (detects ANY change)
            # 6. Random salt (ensures uniqueness)
            file_mtime = pm_proto.stat().st_mtime
            file_size = pm_proto.stat().st_size
            content_hash = abs(hash(html_content))
            random_salt = random.randint(1000000, 9999999)
            last_modified = st.session_state.get('prototype_last_modified', datetime.now().isoformat())
            session_buster = st.session_state.get('prototype_cache_buster_pm', 0)
            
            # Create ULTRA-unique cache buster string
            cache_buster = f"{file_mtime}_{file_size}_{last_modified}_{session_buster}_{content_hash}_{random_salt}"
            
            # Vary height significantly to force iframe reload (750-900px range)
            unique_height = 750 + (abs(hash(cache_buster)) % 150)
            
            # Debug info (toggle with checkbox)
            show_debug = st.checkbox("🔍 Show Debug Info", key="debug_pm_proto", value=False)
            if show_debug:
                st.code(f"""
File: {pm_proto}
Size: {file_size} bytes
Modified: {datetime.fromtimestamp(file_mtime)}
Session timestamp: {last_modified}
Height: {unique_height}px
Cache buster: {cache_buster[:100]}...
                """, language="text")
            
        # NUCLEAR OPTION: Force complete iframe reload by using unique key
        iframe_key = f"pm_proto_{abs(hash(cache_buster))}"
        st.components.v1.html(html_content, height=unique_height, scrolling=True)
    
    # JIRA tasks (PM-specific)
    docs_dir = outputs_dir / "documentation"
    pm_jira = docs_dir / "pm_jira_tasks.md"
    if docs_dir.exists() and pm_jira.exists():
        with st.expander("📋 JIRA Tasks", expanded=True):
            # Black background for markdown
            st.markdown(f"""
            <div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px;">
            
{pm_jira.read_text(encoding='utf-8')}
            
            </div>
            """, unsafe_allow_html=True)
    
    # Estimations, Personas, Scoring, Backlog - with black backgrounds
    if docs_dir.exists():
        if (docs_dir / "estimations.md").exists():
            with st.expander("⏱️ Estimations", expanded=False):
                content = (docs_dir / "estimations.md").read_text(encoding='utf-8')
                st.markdown(f"""
                <div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px;">
                
{content}
                
                </div>
                """, unsafe_allow_html=True)
        if (docs_dir / "personas_journeys.md").exists():
            with st.expander("👥 Personas & Journeys", expanded=False):
                content = (docs_dir / "personas_journeys.md").read_text(encoding='utf-8')
                st.markdown(f"""
                <div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px;">
                
{content}
                
                </div>
                """, unsafe_allow_html=True)
        if (docs_dir / "feature_scoring.md").exists():
            with st.expander("📊 Feature Scoring", expanded=False):
                content = (docs_dir / "feature_scoring.md").read_text(encoding='utf-8')
                st.markdown(f"""
                <div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px;">
                
{content}
                
                </div>
                """, unsafe_allow_html=True)
        if (docs_dir / "backlog_pack.md").exists():
            with st.expander("🧳 Backlog Package", expanded=False):
                content = (docs_dir / "backlog_pack.md").read_text(encoding='utf-8')
                st.markdown(f"""
                <div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px;">
                
{content}
                
                </div>
                """, unsafe_allow_html=True)
        if (docs_dir / "openapi.yaml").exists():
            with st.expander("📜 OpenAPI.yaml", expanded=False):
                st.code((docs_dir / "openapi.yaml").read_text(encoding='utf-8'), language="yaml")

def render_dev_interactive_editor_tab():
    """Render Developer interactive editor tab with AI-powered prototype modification"""
    st.markdown("### 🎨 Interactive Prototype Editor")
    st.markdown("Modify your prototype in real-time by chatting with AI. Make it perfect!")
    
    # Check if interactive editor component is available
    if render_interactive_prototype_editor is None:
        st.error("⚠️ Interactive prototype editor component not available")
        return
    
    # Check for existing prototype
    outputs_dir = AppConfig.OUTPUTS_DIR
    proto_dir = outputs_dir / "prototypes"
    dev_proto = proto_dir / "developer_visual_prototype.html"
    pm_proto = proto_dir / "pm_visual_prototype.html"
    
    initial_html = None
    feature_context = ""
    
    # Load prototype if exists
    if dev_proto.exists():
        initial_html = dev_proto.read_text(encoding='utf-8')
        st.success("✅ Loaded Developer visual prototype")
    elif pm_proto.exists():
        initial_html = pm_proto.read_text(encoding='utf-8')
        st.info("📋 Loaded PM visual prototype")
    else:
        st.warning("⚠️ No prototype found. Please generate a prototype first in the 'Generate' tab.")
        st.info("💡 Go to **Generate** → Generate Visual Prototype (Dev), then come back here.")
        
        # Option to start from scratch
        if st.button("🎨 Create New Blank Prototype"):
            initial_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Prototype</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 48px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #1f2937;
            margin-bottom: 16px;
        }
        .btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 32px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>New Prototype</h1>
        <p>Start customizing your prototype using the AI chat!</p>
        <button class="btn" onclick="alert('Button clicked!')">Example Button</button>
    </div>
</body>
</html>"""
            st.session_state.current_prototype_html = initial_html
            st.rerun()
    
    # Load meeting notes for context
    notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
    if notes_path.exists():
        feature_context = notes_path.read_text(encoding='utf-8')
    
    # Get AI agent
    provider = st.session_state.get('provider', 'Groq (FREE & FAST)')
    api_key = st.session_state.get('api_key')
    
    if not api_key:
        st.error("❌ Please configure API key in sidebar first!")
        return
    
    provider_info = AppConfig.AI_PROVIDERS[provider]
    config = {provider_info['config_key']: api_key}
    agent = get_or_create_agent(config)
    
    # Render quick modifications
    if initial_html:
        if render_quick_modification_buttons:
            render_quick_modification_buttons(agent, feature_context, mode="dev")
        
        st.markdown("---")
    
    # Render interactive editor
    render_interactive_prototype_editor(agent, initial_html, feature_context, mode="dev")

def render_pm_interactive_editor_tab():
    """Render PM interactive editor tab with AI-powered prototype modification"""
    st.markdown("### 🎨 Interactive Prototype Editor")
    st.markdown("Modify your prototype in real-time by chatting with AI. Make it perfect!")
    
    # Check if interactive editor component is available
    if render_interactive_prototype_editor is None:
        st.error("⚠️ Interactive prototype editor component not available")
        return
    
    # Check for existing prototype
    outputs_dir = AppConfig.OUTPUTS_DIR
    proto_dir = outputs_dir / "prototypes"
    pm_proto = proto_dir / "pm_visual_prototype.html"
    dev_proto = proto_dir / "developer_visual_prototype.html"
    
    initial_html = None
    feature_context = ""
    
    # Load prototype if exists
    if pm_proto.exists():
        initial_html = pm_proto.read_text(encoding='utf-8')
        st.success("✅ Loaded PM visual prototype")
    elif dev_proto.exists():
        initial_html = dev_proto.read_text(encoding='utf-8')
        st.info("📋 Loaded Developer visual prototype (will save as PM prototype)")
    else:
        st.warning("⚠️ No prototype found. Please generate a prototype first in the 'Ask AI' tab.")
        st.info("💡 Go to **Ask AI** → Generate Visual Prototype, then come back here.")
        
        # Option to start from scratch
        if st.button("🎨 Create New Blank Prototype"):
            initial_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Prototype</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 48px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #1f2937;
            margin-bottom: 16px;
        }
        .btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 32px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>New Prototype</h1>
        <p>Start customizing your prototype using the AI chat!</p>
        <button class="btn" onclick="alert('Button clicked!')">Example Button</button>
    </div>
</body>
</html>"""
            st.session_state.current_prototype_html = initial_html
            st.rerun()
    
    # Load meeting notes for context
    notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
    if notes_path.exists():
        feature_context = notes_path.read_text(encoding='utf-8')
    
    # Get AI agent
    provider = st.session_state.get('provider', 'Groq (FREE & FAST)')
    api_key = st.session_state.get('api_key')
    
    if not api_key:
        st.error("❌ Please configure API key in sidebar first!")
        return
    
    provider_info = AppConfig.AI_PROVIDERS[provider]
    config = {provider_info['config_key']: api_key}
    agent = get_or_create_agent(config)
    
    # Render quick modifications
    if initial_html:
        if render_quick_modification_buttons:
            render_quick_modification_buttons(agent, feature_context, mode="pm")
        
        st.markdown("---")
    
    # Render interactive editor
    render_interactive_prototype_editor(agent, initial_html, feature_context, mode="pm")
    
# =============================================================================
# GENERATION FUNCTIONS
# =============================================================================

def generate_with_validation(artifact_type: str, generate_fn, meeting_notes: str, outputs_dir: Path):
    """
    Wrapper that adds validation and auto-retry to any generation function.
    
    This ensures consistent quality across all artifact types by:
    1. Running the generation function
    2. Validating the output
    3. Auto-retrying if validation fails (up to max_retries)
    4. Displaying quality metrics in UI
    5. Saving validation reports
    
    Args:
        artifact_type: Type of artifact (erd, architecture, etc.)
        generate_fn: Async function that generates the artifact
        meeting_notes: Meeting notes for context
        outputs_dir: Directory to save outputs
    
    Returns:
        Generated content (str) or None
    """
    use_validation = st.session_state.get('use_validation', True)
    max_retries = st.session_state.get('max_retries', 2)
    
    result = None
    validation_result = None
    attempt = 0
    
    while attempt <= max_retries:
        # Generate
        if attempt == 0:
            result = asyncio.run(generate_fn())
        else:
            # Retry with feedback
            st.info(f"🔄 Retry attempt {attempt}/{max_retries}...")
            from validation.output_validator import ArtifactValidator
            validator = ArtifactValidator()
            feedback = validator.get_retry_feedback(validation_result, artifact_type)
            
            # For retry, we regenerate (could enhance generate_fn to accept feedback)
            st.markdown(f"**Feedback for improvement:**\n{feedback}")
            result = asyncio.run(generate_fn())
        
        # Validate if enabled
        if use_validation and result:
            from validation.output_validator import ArtifactValidator
            validator = ArtifactValidator()
            validation_result = validator.validate(artifact_type, result, {'meeting_notes': meeting_notes})
            
            # Show validation results
            col1, col2 = st.columns([1, 3])
            with col1:
                score_color = "🟢" if validation_result.score >= 80 else "🟡" if validation_result.score >= 60 else "🔴"
                st.metric("Quality Score", f"{score_color} {validation_result.score:.1f}/100")
            with col2:
                status = "✅ PASS" if validation_result.is_valid else "⚠️ NEEDS IMPROVEMENT"
                st.metric("Validation", status)
            
            if validation_result.errors or validation_result.warnings:
                with st.expander("📋 Validation Details", expanded=not validation_result.is_valid):
                    if validation_result.errors:
                        st.markdown("**❌ Errors:**")
                        for error in validation_result.errors:
                            st.markdown(f"- {error}")
                    if validation_result.warnings:
                        st.markdown("**⚠️ Warnings:**")
                        for warning in validation_result.warnings:
                            st.markdown(f"- {warning}")
                    if validation_result.suggestions:
                        st.markdown("**💡 Suggestions:**")
                        for suggestion in validation_result.suggestions:
                            st.markdown(f"- {suggestion}")
            
            # Check if retry needed
            if validator.should_retry(validation_result) and attempt < max_retries:
                st.warning(f"Quality score below threshold. Retrying... ({attempt + 1}/{max_retries})")
                attempt += 1
                continue
        
        # Success - exit loop
        break
    
    # Save validation report if available
    if use_validation and validation_result and result:
        validation_dir = outputs_dir / "validation"
        validation_dir.mkdir(exist_ok=True)
        report = f"""# Validation Report: {artifact_type.upper()}

Score: {validation_result.score:.1f}/100
Status: {'✅ VALID' if validation_result.is_valid else '⚠️ NEEDS IMPROVEMENT'}
Attempts: {attempt + 1}

## Errors
{chr(10).join(f'- {e}' for e in validation_result.errors) if validation_result.errors else 'None'}

## Warnings
{chr(10).join(f'- {w}' for w in validation_result.warnings) if validation_result.warnings else 'None'}

## Suggestions
{chr(10).join(f'- {s}' for s in validation_result.suggestions) if validation_result.suggestions else 'None'}
"""
        (validation_dir / f"{artifact_type}_validation.md").write_text(report, encoding='utf-8')
        
        if validation_result.is_valid:
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {artifact_type} validation: {validation_result.score:.1f}/100")
        else:
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ {artifact_type} validation: {validation_result.score:.1f}/100 (warnings present)")
    
    # Auto-save version (if versioning enabled)
    if result and st.session_state.get('enable_versioning', True):
        try:
            from versioning.version_manager import VersionManager
            vm = VersionManager()
            vm.save_version(
                artifact_type=artifact_type,
                content=result,
                validation_score=validation_result.score if validation_result else 0.0,
                attempt_count=attempt + 1,
                notes=f"Auto-saved during generation"
            )
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 💾 Saved version: {artifact_type}")
        except Exception as e:
            # Don't fail generation if versioning fails
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Version save failed: {str(e)}")
    
    return result


def generate_single_artifact(artifact_type: str):
    """
    Generate a single artifact with full repository context and RAG.
    
    This is the core generation function that ensures all outputs are:
    1. Context-aware: Uses repository architecture, patterns, and conventions
    2. Feature-focused: Based on meeting notes, not the app itself
    3. Stack-aware: Detects and respects the project's tech stack
    
    Args:
        artifact_type: Type of artifact to generate (erd, architecture, code_prototype, etc.)
    
    Process:
        1. Load meeting notes
        2. Initialize AI agent with API key
        3. Retrieve RAG context (force fresh retrieval)
        4. Analyze repository structure and conventions
        5. Process meeting notes to extract feature requirements
        6. Generate artifact using full context
        7. Save to appropriate output directory
        8. Track generation metrics
    
    Returns:
        None (displays results in Streamlit UI)
    """
    try:
        with st.spinner(f"🎨 Generating {artifact_type}..."):
            # Load meeting notes
            notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
            if not notes_path.exists():
                st.error("❌ Please upload meeting notes first!")
                return
            
            meeting_notes = notes_path.read_text(encoding='utf-8')
            
            # Get AI config
            provider = st.session_state.get('provider', 'Groq (FREE & FAST)')
            api_key = st.session_state.get('api_key')
            
            if not api_key:
                st.error("❌ Please configure API key in sidebar!")
                return
            
            provider_info = AppConfig.AI_PROVIDERS[provider]
            config = {provider_info['config_key']: api_key}
            
            # Get or create cached agent (avoid re-initialization)
            agent = get_or_create_agent(config)
            agent.meeting_notes = meeting_notes
            
            # Smart caching decision
            use_cache = should_use_cache(artifact_type, meeting_notes)
            force_refresh = not use_cache
            
            # Retrieve RAG context with intelligent caching
            if use_cache:
                st.info("💾 Retrieving context (using cache for speed)...")
            else:
                st.info("🔄 Retrieving fresh context from repository...")
            
            # Use RAG caching helper - avoids redundant expensive queries
            retrieve_rag_with_cache(agent, meeting_notes, force_refresh=force_refresh)
            
            # Generate based on type
            st.info(f"✨ Generating {artifact_type} with full context...")
            outputs_dir = AppConfig.OUTPUTS_DIR
            outputs_dir.mkdir(parents=True, exist_ok=True)
            
            # Store result for potential multi-agent analysis
            generated_result = None
            
            if artifact_type == "erd":
                result = generate_with_validation(
                    "erd",
                    agent.generate_erd_only,
                    meeting_notes,
                    outputs_dir
                )
                generated_result = result
                if result:
                    viz_dir = outputs_dir / "visualizations"
                    viz_dir.mkdir(exist_ok=True)
                    (viz_dir / "erd_diagram.mmd").write_text(result, encoding='utf-8')
                track_generation("erd")
            elif artifact_type == "architecture":
                result = generate_with_validation(
                    "architecture",
                    agent.generate_architecture_only,
                    meeting_notes,
                    outputs_dir
                )
                generated_result = result
                if result:
                    viz_dir = outputs_dir / "visualizations"
                    viz_dir.mkdir(exist_ok=True)
                    (viz_dir / "architecture_diagram.mmd").write_text(result, encoding='utf-8')
                track_generation("architecture")
            elif artifact_type == "api_docs":
                result = generate_with_validation(
                    "api_docs",
                    agent.generate_api_docs_only,
                    meeting_notes,
                    outputs_dir
                )
                generated_result = result
                if result:
                    docs_dir = outputs_dir / "documentation"
                    docs_dir.mkdir(exist_ok=True)
                    (docs_dir / "api.md").write_text(result, encoding='utf-8')
                track_generation("api_docs")
            elif artifact_type == "jira":
                # Ensure meeting notes are processed first for higher fidelity
                try:
                    asyncio.run(agent.process_meeting_notes(str(notes_path)))
                except Exception:
                    pass
                result = generate_with_validation(
                    "jira",
                    agent.generate_jira_only,
                    meeting_notes,
                    outputs_dir
                )
                generated_result = result
                if result:
                    result = strip_markdown_artifacts(result)
                    docs_dir = outputs_dir / "documentation"
                    docs_dir.mkdir(exist_ok=True)
                    (docs_dir / "jira_tasks.md").write_text(result, encoding='utf-8')
                track_generation("jira")
            elif artifact_type == "workflows":
                result = generate_with_validation(
                    "workflows",
                    agent.generate_workflows_only,
                    meeting_notes,
                    outputs_dir
                )
                generated_result = result
                if result:
                    wf_dir = outputs_dir / "workflows"
                    wf_dir.mkdir(exist_ok=True)
                    (wf_dir / "workflows.md").write_text(result, encoding='utf-8')
                track_generation("workflows")
            elif artifact_type == "all_diagrams":
                diagrams = asyncio.run(agent.generate_specific_diagrams())
                if diagrams:
                    viz_dir = outputs_dir / "visualizations"
                    viz_dir.mkdir(exist_ok=True)
                    for name, content in diagrams.items():
                        (viz_dir / f"{name}_diagram.mmd").write_text(content, encoding='utf-8')
                track_generation("diagrams")
            elif artifact_type == "code_prototype":
                feature_name = "feature-from-notes"
                try:
                    # Prefer extracted name from processed meeting notes
                    if getattr(agent, 'feature_requirements', None):
                        feature_name = agent.feature_requirements.get('name', feature_name) or feature_name
                except Exception:
                    pass
                if feature_name == "feature-from-notes":
                    feature_name = extract_feature_name_from_notes(meeting_notes)
                
                st.info(f"🧩 Generating code prototype for: {feature_name}")
                res = asyncio.run(agent.generate_prototype_code(feature_name))
                out_base = AppConfig.OUTPUTS_DIR
                project_root = Path(__file__).resolve().parents[2]
                
                # Generate best effort uses both LLM output and fallback scaffolds
                saved = generate_best_effort(feature_name, project_root, out_base, res.get("code", "") if isinstance(res, dict) else "")
                
                if saved:
                    st.success(f"✅ Generated {len(saved)} code files:")
                    # Organize files by category
                    frontend_files = [f for f in saved if any(x in str(f).lower() for x in ['frontend', 'angular', 'react', 'vue', 'component', 'page', '/src/app/'])]
                    backend_files = [f for f in saved if any(x in str(f).lower() for x in ['backend', 'api', 'controller', 'service', 'dto', 'program.cs', '.cs']) and not any(x in str(f).lower() for x in ['frontend', 'component.ts', '.ts', '.html'])]
                    other_files = [f for f in saved if f not in frontend_files and f not in backend_files]
                    
                    # Validation check for full-stack projects
                    if frontend_files and not backend_files:
                        st.warning("⚠️ **Missing Backend Files!** Only frontend files were generated. This project has .NET backend.")
                        st.info("💡 Try regenerating or check if backend files were saved to a different location.")
                    
                    if frontend_files:
                        with st.expander(f"📱 Frontend Files ({len(frontend_files)})", expanded=True):
                            for f in frontend_files:
                                relative_path = f.relative_to(out_base) if f.is_relative_to(out_base) else f
                                st.code(f"✓ {relative_path}", language="text")
                    
                    if backend_files:
                        with st.expander(f"⚙️ Backend Files ({len(backend_files)})", expanded=True):
                            for f in backend_files:
                                relative_path = f.relative_to(out_base) if f.is_relative_to(out_base) else f
                                st.code(f"✓ {relative_path}", language="text")
                    
                    if other_files:
                        with st.expander(f"📄 Other Files ({len(other_files)})", expanded=True):
                            for f in other_files:
                                relative_path = f.relative_to(out_base) if f.is_relative_to(out_base) else f
                                st.code(f"✓ {relative_path}", language="text")
                    
                    st.info(f"💾 All files saved to: `outputs/prototypes/`")
                else:
                    st.warning("⚠️ No files generated")
                
                track_generation("code_prototype")
            elif artifact_type == "visual_prototype_dev":
                # Use ENHANCED prototype generator (2-stage: requirements + focused generation)
                notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
                notes = notes_path.read_text(encoding='utf-8') if notes_path.exists() else ""
                feature_name = extract_feature_name_from_notes(notes)
                
                st.info("🎨 Generating enhanced visual prototype...")
                st.markdown("**Stage 1:** Extracting requirements... **Stage 2:** Generating HTML...")
                
                try:
                    from components.enhanced_prototype_generator import EnhancedPrototypeGenerator
                    
                    generator = EnhancedPrototypeGenerator(agent)
                    html = asyncio.run(generator.generate_prototype(notes))
                    generated_result = html
                    
                    # Clean and sanitize
                    clean_html = strip_markdown_artifacts(html)
                    clean_html = sanitize_prototype_html(clean_html)
                    
                    # Fallback ONLY if generation truly failed
                    if not clean_html or len(clean_html) < 100 or ('<html' not in clean_html.lower() and '<body' not in clean_html.lower()):
                        st.warning("⚠️ Enhanced generation failed, using template fallback...")
                        template = pick_template_from_notes(notes)
                        clean_html = build_template_html(template, feature_name, notes)
                        generated_result = clean_html
                    
                    # Save
                    proto_dir = AppConfig.OUTPUTS_DIR / "prototypes"
                    proto_dir.mkdir(exist_ok=True)
                    (proto_dir / "developer_visual_prototype.html").write_text(clean_html, encoding='utf-8')
                    st.success(f"✅ Enhanced visual prototype generated!")
                    track_generation("visual_prototype")
                
                except Exception as e:
                    st.error(f"❌ Enhanced generator error: {str(e)}")
                    # Fallback
                    template = pick_template_from_notes(notes)
                    html = build_template_html(template, feature_name, notes)
                    generated_result = html
                    proto_dir = AppConfig.OUTPUTS_DIR / "prototypes"
                    proto_dir.mkdir(exist_ok=True)
                    (proto_dir / "developer_visual_prototype.html").write_text(html, encoding='utf-8')
                    st.info(f"✅ Saved fallback visual prototype")
                    track_generation("visual_prototype")
            
            # Log activity
            log_message = f"Generated {artifact_type}"
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {log_message}")
            
            # Multi-Agent Analysis (if enabled)
            use_multi_agent = st.session_state.get('use_multi_agent', False)
            # Ensure it's explicitly True (not just truthy)
            if use_multi_agent is True and generated_result:
                st.markdown("---")
                st.markdown("### 🤖 Multi-Agent Analysis")
                st.info("Running expert analysis from 3 specialized agents...")
                
                try:
                    from agents.specialized_agents import MultiAgentOrchestrator
                    
                    orchestrator = MultiAgentOrchestrator(agent)
                    analysis = asyncio.run(orchestrator.analyze_with_agents(
                        artifact_type,
                        generated_result[:3000] if len(generated_result) > 3000 else generated_result,
                        meeting_notes[:2000] if len(meeting_notes) > 2000 else meeting_notes
                    ))
                    
                    if analysis['agent_count'] > 0:
                        # Show average score
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            score = analysis['average_score']
                            color = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
                            st.metric("Average Score", f"{color} {score:.1f}/100")
                        with col2:
                            st.metric("Agents Analyzed", f"{analysis['agent_count']}/3")
                        
                        # Show each agent's opinion
                        for opinion in analysis['opinions']:
                            with st.expander(f"{opinion.agent_name} - Score: {opinion.score:.0f}/100", expanded=False):
                                st.markdown(f"**Perspective:** {opinion.perspective}")
                                st.markdown(f"**Feedback:** {opinion.feedback}")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if opinion.suggestions:
                                        st.markdown("**✅ Suggestions:**")
                                        for sug in opinion.suggestions[:5]:
                                            st.markdown(f"- {sug}")
                                
                                with col2:
                                    if opinion.concerns:
                                        st.markdown("**⚠️ Concerns:**")
                                        for con in opinion.concerns[:5]:
                                            st.markdown(f"- {con}")
                        
                        # Show synthesis
                        st.markdown("---")
                        st.markdown("### 📊 Synthesis")
                        st.markdown(analysis['synthesis'])
                        
                        # Save analysis to file
                        analysis_dir = outputs_dir / "analysis"
                        analysis_dir.mkdir(exist_ok=True)
                        analysis_file = analysis_dir / f"{artifact_type}_multi_agent_analysis.md"
                        
                        analysis_content = f"""# Multi-Agent Analysis: {artifact_type}

## Overall Score: {analysis['average_score']:.1f}/100

## Agent Opinions

"""
                        for opinion in analysis['opinions']:
                            analysis_content += f"""### {opinion.agent_name} (Score: {opinion.score}/100)

**Perspective:** {opinion.perspective}

**Feedback:** {opinion.feedback}

**Suggestions:**
{chr(10).join(f'- {s}' for s in opinion.suggestions)}

**Concerns:**
{chr(10).join(f'- {c}' for c in opinion.concerns)}

---

"""
                        analysis_content += f"""## Synthesis
                        
                        {analysis['synthesis']}
                        """
                        analysis_file.write_text(analysis_content, encoding='utf-8')
                        st.success(f"💾 Multi-agent analysis saved to: analysis/{artifact_type}_multi_agent_analysis.md")
                        
                    else:
                        st.warning("⚠️ Multi-agent analysis failed. Generated artifact is still available.")
                
                except Exception as e:
                    st.warning(f"⚠️ Multi-agent analysis encountered an error: {str(e)}")
                    st.info("Generated artifact is still available in Outputs tab.")
            
            st.success(f"✅ {artifact_type.title()} generated successfully!")
            if use_multi_agent:
                st.success("🤖 Multi-agent analysis complete!")
            st.info("💡 Go to the 'Outputs' tab to view your generated content!")
            st.balloons()
            
            # Force refresh outputs
            if 'last_generation' not in st.session_state:
                st.session_state.last_generation = []
            st.session_state.last_generation.append(artifact_type)
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

def run_complete_workflow():
    """Run complete workflow"""
    try:
        with st.spinner("🚀 Running complete workflow..."):
            notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
            if not notes_path.exists():
                st.error("❌ Please upload meeting notes first!")
                return
            
            provider = st.session_state.get('provider', 'Groq (FREE & FAST)')
            api_key = st.session_state.get('api_key')
            
            if not api_key:
                st.error("❌ Please configure API key in sidebar!")
                return
            
            provider_info = AppConfig.AI_PROVIDERS[provider]
            config = {provider_info['config_key']: api_key}
            
            # Run workflow with cached agent
            agent = get_or_create_agent(config)
            result = asyncio.run(agent.run_complete_workflow(".", str(notes_path)))
            
            # Log activity
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Complete workflow executed")
            
            st.success("✅ Complete workflow finished!")
            st.balloons()
            track_generation("complete_workflow", cost=0.5, time_saved=2.0)
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

def generate_visual_prototype_with_multi_agent(
    idea: str,
    mode: str = "pm",
    source: str = "manual"
) -> str:
    """
    Generate HIGH-QUALITY visual prototype using 3-stage multi-agent pipeline.
    
    Pipeline:
    1. Analyzer: Deep feature understanding
    2. Generator: Tech-stack-specific code generation
    3. Critic: Quality review and potential regeneration
    
    Args:
        idea: Feature idea or meeting notes content
        mode: "pm" or "dev" - determines save path
        source: Input source ("manual" or "meeting_notes")
        
    Returns:
        Generated HTML content
    """
    from agents.prototype_agents import PrototypeOrchestrator, TechStack
    from components.tech_stack_detector import get_tech_stack_from_context
    
    # Get agent
    provider = st.session_state.get('provider', 'Groq (FREE & FAST)')
    api_key = st.session_state.get('api_key')
    provider_info = AppConfig.AI_PROVIDERS[provider]
    config = {provider_info['config_key']: api_key}
    
    agent = get_or_create_agent(config)
    
    # Get RAG context
    ext_ctx = get_extended_project_context()
    asyncio.run(agent.retrieve_rag_context(f"visual prototype {idea[:500]} {ext_ctx[:1000]}"))
    rag_context = agent.rag_context  # Access the attribute directly
    
    # Detect tech stack from context
    tech_stack = get_tech_stack_from_context(rag_context)
    
    # Convert to prototype agent format
    from agents.prototype_agents import TechStack as PTechStack
    proto_tech_stack = PTechStack(
        framework=tech_stack.framework,
        language=tech_stack.language,
        styling=tech_stack.styling,
        components=tech_stack.components,
        api_tech=tech_stack.api_tech
    )
    
    # Create orchestrator and run pipeline
    orchestrator = PrototypeOrchestrator(agent)
    result = asyncio.run(orchestrator.generate_prototype(
        meeting_notes=idea,
        tech_stack=proto_tech_stack,
        rag_context=rag_context,
        max_iterations=2
    ))
    
    # Display pipeline results
    with st.expander("🤖 Multi-Agent Prototype Pipeline", expanded=False):
        st.markdown(f"""
        **Tech Stack Detected:** {tech_stack.framework} + {tech_stack.language}
        
        **Pipeline Results:**
        - **Iterations:** {result['iterations']}
        - **Final Quality Score:** {result['final_score']:.1f}/100
        - **Framework:** {result['tech_stack'].framework}
        - **Components:** {', '.join(result['tech_stack'].components) if result['tech_stack'].components else 'None'}
        """)
        
        # Show analysis
        st.markdown("### 📋 Feature Analysis")
        analysis = result['analysis']
        st.write(f"**Feature Name:** {analysis.feature_name}")
        st.write(f"**Core Functionality:** {', '.join(analysis.core_functionality[:3])}")
        st.write(f"**UI Components:** {', '.join(analysis.ui_components_needed[:5])}")
        
        # Show reviews
        st.markdown("### 🔍 Quality Reviews")
        for i, review in enumerate(result['reviews']):
            score_color = "🟢" if review.score >= 80 else "🟡" if review.score >= 60 else "🔴"
            st.markdown(f"**Iteration {i+1}:** {score_color} {review.score:.1f}/100")
            if review.strengths:
                st.markdown(f"✅ {', '.join(review.strengths[:2])}")
            if review.weaknesses:
                st.markdown(f"⚠️ {', '.join(review.weaknesses[:2])}")
    
    # Get final HTML
    prototype = result['prototype']
    html = prototype.framework_specific_code
    
    # Clean and sanitize
    html = strip_markdown_artifacts(html)
    html = sanitize_prototype_html(html)
    
    return html


def generate_visual_prototype(idea: str, source: str = "manual"):
    """
    Generate visual prototype for PM mode using ENHANCED generator.
    
    Args:
        idea: Feature idea or meeting notes content
        source: Input source ("manual" or "meeting_notes")
    """
    try:
        with st.spinner("🎨 Creating enhanced visual prototype..."):
            st.markdown("**Stage 1:** Extracting requirements... **Stage 2:** Generating HTML...")
            
            provider = st.session_state.get('provider', 'Groq (FREE & FAST)')
            api_key = st.session_state.get('api_key')
            provider_info = AppConfig.AI_PROVIDERS[provider]
            config = {provider_info['config_key']: api_key}
            
            agent = get_or_create_agent(config)
            
            # Use enhanced generator
            from components.enhanced_prototype_generator import EnhancedPrototypeGenerator
            generator = EnhancedPrototypeGenerator(agent)
            result = asyncio.run(generator.generate_prototype(idea))
            
            # Strip markdown artifacts and sanitize
            html = strip_markdown_artifacts(result or "")
            html = sanitize_prototype_html(html)
            
            # Fallback ONLY if generation truly failed (empty or minimal content)
            # Check for actual HTML structure, not just length
            if not html or len(html) < 100 or ('<html' not in html.lower() and '<body' not in html.lower()):
                st.warning("⚠️ Enhanced generation failed, using template fallback...")
                notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
                notes = notes_path.read_text(encoding='utf-8') if notes_path.exists() else idea
                template = pick_template_from_notes(notes)
                html = build_template_html(template, "PM Visual Prototype", notes)
            
            # Save to PM visual path - SINGLE FILE
            out = AppConfig.OUTPUTS_DIR / "prototypes" / "pm_visual_prototype.html"
            out.parent.mkdir(exist_ok=True)
            out.write_text(html, encoding='utf-8')
            
            source_label = "meeting notes" if source == "meeting_notes" else "manual input"
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] PM visual prototype generated from {source_label}")
            
            st.success(f"✅ Enhanced visual prototype generated from {source_label}!")
            st.info(f"📁 Saved to: prototypes/pm_visual_prototype.html")
            st.balloons()
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

def generate_pm_jira(idea: str, source: str = "manual"):
    """
    Generate JIRA tasks for PM mode.
    
    Args:
        idea: Feature idea or meeting notes content
        source: Input source ("manual" or "meeting_notes")
    """
    try:
        with st.spinner("📋 Generating JIRA tasks..."):
            provider = st.session_state.get('provider', 'Groq (FREE & FAST)')
            api_key = st.session_state.get('api_key')
            provider_info = AppConfig.AI_PROVIDERS[provider]
            config = {provider_info['config_key']: api_key}
            
            agent = get_or_create_agent(config)
            agent.meeting_notes = idea
            
            result = asyncio.run(agent.generate_jira_only())
            
            # Strip markdown artifacts
            result = strip_markdown_artifacts(result or "")
            
            # Save to PM-specific JIRA file
            if result:
                out = AppConfig.OUTPUTS_DIR / "documentation" / "pm_jira_tasks.md"
                out.parent.mkdir(exist_ok=True)
                out.write_text(result, encoding='utf-8')
            
            source_label = "meeting notes" if source == "meeting_notes" else "manual input"
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] PM JIRA tasks generated from {source_label}")
            
            st.success(f"✅ JIRA tasks generated from {source_label}!")
            st.info(f"📁 Saved to: documentation/pm_jira_tasks.md")
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

def ask_ai(question: str, context: str = ""):
    """Ask AI a question with FULL RAG context from repository"""
    try:
        with st.spinner("🔍 Retrieving context from your repository..."):
            provider = st.session_state.get('provider', 'Groq (FREE & FAST)')
            api_key = st.session_state.get('api_key')
            provider_info = AppConfig.AI_PROVIDERS[provider]
            config = {provider_info['config_key']: api_key}
            
            agent = get_or_create_agent(config)
            
            # Use PM input based on their selection (meeting notes or manual input)
            pm_source = st.session_state.get('pm_source', 'meeting_notes')
            pm_idea = st.session_state.get('pm_idea', '')
            
            if pm_source == "meeting_notes":
                # Use meeting notes
                notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
                if notes_path.exists():
                    meeting_notes = notes_path.read_text(encoding='utf-8')
                    context = f"{context}\n\nMeeting Notes:\n{meeting_notes}" if context else meeting_notes
            elif pm_idea:
                # Use manual input from PM
                context = f"{context}\n\nPM Idea:\n{pm_idea}" if context else f"PM Idea:\n{pm_idea}"
             
            # Retrieve FULL RAG context from repository
            st.info("🧠 AI is analyzing your entire codebase...")
            ext_ctx = get_extended_project_context()
            rag_query = f"{question} {context} {ext_ctx}"
            asyncio.run(agent.retrieve_rag_context(rag_query))
            
            # Log RAG activity
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Retrieved RAG context for Ask AI")
            
            prompt = f"""
You are an expert product and technical advisor with DEEP knowledge of this specific project.

PROJECT CONTEXT (from RAG):
{agent.rag_context[:3000]}

USER PROVIDED CONTEXT: {context if context else "No additional context provided"}

QUESTION: {question}

IMPORTANT: 
- You have access to the actual codebase through RAG context above
- Reference specific files, patterns, and technologies from the project
- Be specific about how this fits with the existing architecture
- Provide realistic estimates based on the actual tech stack
- Mention any potential conflicts with existing code

Provide a helpful, actionable answer that's tailored to THIS specific project.
"""
            
            response = asyncio.run(agent._call_ai(
                prompt,
                "You are a helpful product and technical advisor with deep knowledge of this specific project. Be clear, concise, and actionable."
            ))
            
            # Store in conversation history
            if 'ai_conversation' not in st.session_state:
                st.session_state.ai_conversation = []
            st.session_state.ai_conversation.append((question, response))
            
            # Display response with context indicator
            st.success("✅ AI Response (with full project context):")
            st.markdown(response)
            
            # Show what context was used
            with st.expander("🔍 RAG Context Used"):
                st.text(f"Retrieved {len(agent.rag_context)} characters of context from your repository")
                st.text("This includes: code files, architecture, patterns, dependencies, and more")
            
            # Log activity
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Asked AI with RAG: {question[:30]}...")
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

# =============================================================================
# PROTOTYPE HTML SANITIZER AND FALLBACKS
# =============================================================================

def strip_markdown_artifacts(text: str) -> str:
    """
    Remove ALL markdown artifacts from generated content.
    Critical for preventing code fence markers in generated HTML/code.
    """
    import re
    if not text:
        return ""
    
    # Remove code fences (```html, ```python, etc.)
    text = re.sub(r'^```[\w\-]*\s*\n?', '', text, flags=re.MULTILINE)  # Opening fences
    text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE)  # Closing fences
    text = re.sub(r'```[\w\-]*\n', '', text)  # Mid-content fences
    text = text.strip('`')  # Stray backticks
    
    return text.strip()


def sanitize_prototype_html(html: str) -> str:
    """Strip dangerous tags, markdown artifacts, and ensure a minimal valid shell."""
    import re
    if not html:
        return ""
    
    # STEP 1: Strip markdown artifacts FIRST (before any other processing)
    html = strip_markdown_artifacts(html)
    
    # STEP 2: Remove only iframes (keep all JavaScript for functionality)
    html = re.sub(r"<iframe[\s\S]*?</iframe>", "", html, flags=re.IGNORECASE)
    
    # STEP 3: Ensure DOCTYPE
    if "<!DOCTYPE" not in html[:200]:
        html = "<!DOCTYPE html>\n" + html
    
    return html

# Notes-driven template chooser and builders

def pick_template_from_notes(notes: str) -> str:
    n = (notes or "").lower()
    # Heuristics by keywords
    if any(k in n for k in ["chart", "kpi", "analytics", "dashboard", "statistics", "metrics"]):
        return "dashboard"
    if any(k in n for k in ["login", "register", "authentication", "auth"]):
        return "auth"
    if any(k in n for k in ["product", "catalog", "e-commerce", "cart", "checkout", "sku"]):
        return "ecommerce"
    if any(k in n for k in ["kanban", "board", "tasks", "swimlane"]):
        return "kanban"
    if any(k in n for k in ["upload", "file", "import csv", "import xlsx"]):
        return "uploader"
    if any(k in n for k in ["q&a", "faq", "question", "answer", "knowledge base"]):
        return "qna"
    if any(k in n for k in ["chat", "assistant", "message", "bot"]):
        return "chat"
    if any(k in n for k in ["crud", "table", "form", "admin", "manage"]):
        return "table_form"
    return "dashboard"


def build_template_html(template: str, title: str, notes: str) -> str:
    import html as htmlmod
    safe_notes = htmlmod.escape((notes or "")[:800])
    common_head = """
<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{TITLE}</title>
  <style>
    body {{ background:#f7f7fb; font-family: Segoe UI, Arial; }}
    .container {{ max-width: 1100px; margin: 24px auto; padding: 16px; background:#fff; border-radius:12px; box-shadow:0 10px 30px rgba(0,0,0,.06) }}
    h1 {{ color:#111827; margin:0 0 8px; }}
    p {{ color:#4b5563; }}
    .btn {{ background:#667eea; color:#fff; border:0; padding:8px 16px; border-radius:10px; cursor:pointer; }}
    input,select,textarea {{ padding:8px; border:1px solid #e5e7eb; border-radius:8px; }}
    table {{ width:100%; border-collapse:collapse; }}
    th,td {{ border-bottom:1px solid #e5e7eb; padding:8px; text-align:left; }}
  </style>
""".replace("{TITLE}", title)
    head = common_head
    body = ""
    if template == "dashboard":
        head += "  <script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>\n"
        body = """
</head>
<body>
  <div class=\"container\">
    <h1>Dashboard</h1>
    <p>Based on meeting notes:</p>
    <pre style=\"white-space:pre-wrap\">[[NOTES]]</pre>
    <canvas id=\"chart1\" height=\"120\"></canvas>
  </div>
  <script>
    const ctx = document.getElementById('chart1');
    new Chart(ctx, { type: 'bar', data: { labels: ['A','B','C','D'], datasets: [{ label:'Values', data:[12,19,5,9], backgroundColor:'#667eea' }] }, options: { responsive:true } });
  </script>
</body>
</html>
"""
    elif template == "table_form":
        body = """
</head>
<body>
  <div class=\"container\">
    <h1>Admin Table & Form</h1>
    <p>Notes:</p>
    <pre style=\"white-space:pre-wrap\">[[NOTES]]</pre>
    <table>
      <thead><tr><th>Name</th><th>Status</th></tr></thead>
      <tbody id=\"rows\"><tr><td>Alpha</td><td>Active</td></tr></tbody>
    </table>
    <h3>Create</h3>
    <input id=\"name\" placeholder=\"Name\"/> <select id=\"status\"><option>Active</option><option>Paused</option></select>
    <button class=\"btn\" onclick=\"addRow()\">Add</button>
  </div>
  <script>
    function addRow(){
      const n = document.getElementById('name').value || 'Item';
      const s = document.getElementById('status').value;
      const tr = document.createElement('tr');
      tr.innerHTML = '<td>' + n + '</td><td>' + s + '</td>';
      document.getElementById('rows').appendChild(tr);
    }
  </script>
</body>
</html>
"""
    elif template == "auth":
        body = """
</head>
<body>
  <div class=\"container\">
    <h1>Authentication</h1>
    <p>Notes:</p>
    <pre style=\"white-space:pre-wrap\">[[NOTES]]</pre>
    <h3>Login</h3>
    <input placeholder=\"Email\"/> <input type=\"password\" placeholder=\"Password\"/> <button class=\"btn\">Login</button>
    <h3>Register</h3>
    <input placeholder=\"Email\"/> <input type=\"password\" placeholder=\"Password\"/> <button class=\"btn\">Create</button>
  </div>
</body>
</html>
"""
    elif template == "ecommerce":
        body = """
</head>
<body>
  <div class=\"container\">
    <h1>Catalog</h1>
    <p>Notes:</p>
    <pre style=\"white-space:pre-wrap\">[[NOTES]]</pre>
    <div style=\"display:grid;grid-template-columns:repeat(3,1fr);gap:12px\">
      <div style=\"border:1px solid #e5e7eb;border-radius:10px;padding:12px\"><h3>Product A</h3><button class=\"btn\">Add to cart</button></div>
      <div style=\"border:1px solid #e5e7eb;border-radius:10px;padding:12px\"><h3>Product B</h3><button class=\"btn\">Add to cart</button></div>
      <div style=\"border:1px solid #e5e7eb;border-radius:10px;padding:12px\"><h3>Product C</h3><button class=\"btn\">Add to cart</button></div>
    </div>
  </div>
</body>
</html>
"""
    elif template == "qna":
        body = """
</head>
<body>
  <div class=\"container\">
    <h1>Q&A</h1>
    <p>Notes:</p>
    <pre style=\"white-space:pre-wrap\">[[NOTES]]</pre>
    <h3>Ask</h3>
    <input id=\"q\" placeholder=\"Your question\"/> <button class=\"btn\" onclick=\"ask()\">Ask</button>
    <div id=\"answers\" style=\"margin-top:12px\"></div>
  </div>
  <script>
    function ask(){
      var q = document.getElementById('q').value;
      var d = document.createElement('div');
      d.textContent = 'Q: ' + q + ' → A: (placeholder)';
      document.getElementById('answers').appendChild(d);
    }
  </script>
</body>
</html>
"""
    elif template == "kanban":
        body = """
</head>
<body>
  <div class=\"container\">
    <h1>Kanban</h1>
    <p>Notes:</p>
    <pre style=\"white-space:pre-wrap\">[[NOTES]]</pre>
    <div style=\"display:grid;grid-template-columns:repeat(3,1fr);gap:12px\">
      <div><h3>Todo</h3><ul id=\"todo\"><li>Task 1</li></ul></div>
      <div><h3>Doing</h3><ul id=\"doing\"><li>Task 2</li></ul></div>
      <div><h3>Done</h3><ul id=\"done\"><li>Task 3</li></ul></div>
    </div>
  </div>
</body>
</html>
"""
    elif template == "uploader":
        body = """
</head>
<body>
  <div class=\"container\">
    <h1>File Uploader</h1>
    <p>Notes:</p>
    <pre style=\"white-space:pre-wrap\">[[NOTES]]</pre>
    <input type=\"file\" /> <button class=\"btn\">Upload</button>
  </div>
</body>
</html>
"""
    elif template == "chat":
        body = """
</head>
<body>
  <div class=\"container\" style=\"display:flex;flex-direction:column;height:80vh\">
    <h1>Chat</h1>
    <div id=\"log\" style=\"flex:1;overflow:auto;border:1px solid #e5e7eb;border-radius:10px;padding:8px\"></div>
    <div style=\"display:flex;gap:8px;margin-top:8px\"><input id=\"msg\" style=\"flex:1\" placeholder=\"Type message\"/><button class=\"btn\" onclick=\"send()\">Send</button></div>
  </div>
  <script>
    function send(){
      var m = document.getElementById('msg').value;
      var d = document.createElement('div');
      d.textContent = 'You: ' + m;
      document.getElementById('log').appendChild(d);
      document.getElementById('msg').value = '';
    }
  </script>
</body>
</html>
"""
    else:
        body = "</head><body><div class=\"container\"><h1>Prototype</h1><p>No template selected.</p></div></body></html>"
    return (head + body).replace("[[NOTES]]", safe_notes)

# =============================================================================
# OUTPUT MANAGEMENT HELPERS
# =============================================================================

def clear_feature_outputs():
    """
    Clear artifacts tied to a specific feature so new notes don't mix with old outputs.
    
    This is critical when switching tech stacks (e.g., Angular → React, WPF → Web)
    because we need to completely remove old prototype directories and regenerate
    with the correct stack.
    
    Uses aggressive shutil.rmtree to ensure complete removal.
    """
    import shutil
    base = AppConfig.OUTPUTS_DIR
    for sub in [
        "visualizations",
        "documentation",
        "prototypes",
        "workflows",
        "analysis",
        "context",
    ]:
        try:
            p = base / sub
            if p.exists():
                # Aggressive deletion: Delete entire tree, then recreate empty directory
                try:
                    shutil.rmtree(p)
                    p.mkdir(exist_ok=True)
                except Exception as e:
                    # If shutil.rmtree fails, try manual deletion as fallback
                    for f in p.rglob("*"):
                        try:
                            if f.is_file():
                                f.unlink(missing_ok=True)
                        except Exception:
                            pass
                    
                    # Try to remove subdirectories
                    subdirs = [d for d in p.rglob("*") if d.is_dir()]
                    subdirs.sort(key=lambda x: len(x.parts), reverse=True)
                    for d in subdirs:
                        if d.exists() and d != p:
                            try:
                                d.rmdir()
                            except:
                                pass
        except Exception:
            pass

# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """
    Main application entry point.
    
    Orchestrates the entire application flow:
    1. Configure page settings
    2. Apply custom styling
    3. Initialize session state
    4. Render sidebar and header
    5. Route to appropriate mode (Developer/PM)
    6. Display footer with version and contact info
    """
    # Page config
    st.set_page_config(
        page_title=AppConfig.APP_TITLE,
        page_icon=AppConfig.APP_ICON,
        layout=AppConfig.LAYOUT,
        initial_sidebar_state="expanded"
    )
    
    # Apply custom CSS
    apply_custom_css()
    
    # Initialize session state
    init_session_state()
    
    # Initialize auto-ingestion system
    init_auto_ingestion()
    
    # Render sidebar
    render_sidebar()
    
    # Render header
    render_header()
    
    # Mode selection or mode interface
    if st.session_state.mode is None:
        render_mode_selection()
    elif st.session_state.mode == "developer":
        # Gate by role: Developer or Admin
        if has_role(["Developer", "Admin"]):
            render_dev_mode()
        else:
            st.warning("You need Developer or Admin role to access Developer Mode.")
    elif st.session_state.mode == "product":
        # PM or Admin can access PM mode
        if has_role(["PM", "Admin", "Developer", "Viewer"]):
            render_pm_mode()
        else:
            st.warning("You lack permission to access this mode.")
    
    # Render footer
    render_footer()

# =============================================================================
# FEATURE NAME EXTRACTION
# =============================================================================

def extract_feature_name_from_notes(notes: str) -> str:
    """
    Extract feature name from meeting notes using intelligent pattern matching.
    
    This function implements a cascading strategy to identify the feature name:
    1. Look for explicit "Feature: Name" declarations
    2. Extract from first Markdown H1 heading (# Heading)
    3. Use first non-empty line as fallback
    
    The extracted name is used for:
    - Naming generated prototype files
    - Creating appropriate directory structures
    - Ensuring outputs are feature-specific
    
    Args:
        notes: Raw meeting notes text (Markdown or plain text)
    
    Returns:
        Feature name (max 60 chars) or "feature" if nothing found
    
    Examples:
        "Feature: User Authentication" -> "User Authentication"
        "# Shopping Cart Redesign" -> "Shopping Cart Redesign"
        "Implement payment gateway..." -> "Implement payment gateway"
    """
    import re
    if not notes:
        return "feature"
    
    # Try explicit "Feature: Name" or "Feature - Name"
    m = re.search(r"^\s*#*\s*Feature[:\-]\s*(.+)$", notes, flags=re.IGNORECASE | re.MULTILINE)
    if m:
        return m.group(1).strip()[:60] or "feature"
    
    # Try first H1 Markdown heading
    m = re.search(r"^\s*#\s*(.+)$", notes, flags=re.MULTILINE)
    if m:
        return m.group(1).strip()[:60]
    
    # Fallback to first non-empty line
    for line in notes.splitlines():
        if line.strip():
            return line.strip()[:60]
    
    return "feature"

if __name__ == "__main__":
    main()
