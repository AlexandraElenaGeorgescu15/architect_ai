"""
Ollama UI Components for Streamlit
Displays model status, VRAM usage, and local model controls
"""

import streamlit as st
from typing import Dict, Any, Optional
from ai.ollama_client import OllamaClient, ModelStatus


def render_ollama_status_panel(ollama_client: Optional[OllamaClient] = None):
    """
    Render Ollama model status panel in sidebar.
    
    Shows:
    - VRAM usage
    - Model status (persistent vs swap)
    - Ready/Loading indicators
    
    Args:
        ollama_client: OllamaClient instance (optional)
    """
    st.markdown("### 🤖 Local Models")
    
    if ollama_client is None:
        st.info("💡 Ollama not configured. Using cloud providers only.")
        st.caption("[Setup Guide](OLLAMA_SETUP_GUIDE_12GB.md)")
        return
    
    # Check if Ollama is running
    try:
        # This will be checked asynchronously in real usage
        is_healthy = st.session_state.get('ollama_healthy', False)
        
        if not is_healthy:
            st.warning("⚠️ Ollama server not responding")
            st.caption("Make sure Ollama is running: `ollama serve`")
            return
    except:
        st.error("❌ Cannot connect to Ollama")
        return
    
    # VRAM Usage Bar
    st.markdown("#### VRAM Usage")
    vram = ollama_client.get_vram_usage()
    
    usage_percent = vram['usage_percent']
    used_gb = vram['used_gb']
    total_gb = vram['total_gb']
    available_gb = vram['available_gb']
    
    # Color-coded progress bar
    if usage_percent < 70:
        color = "🟢"  # Green
    elif usage_percent < 90:
        color = "🟡"  # Yellow
    else:
        color = "🔴"  # Red
    
    st.progress(usage_percent / 100)
    st.caption(f"{color} {used_gb}GB / {total_gb}GB ({usage_percent}%) - {available_gb}GB available")
    
    st.divider()
    
    # Model Status Table
    st.markdown("#### Model Status")
    
    # Define task → model mapping for display
    model_display = [
        {
            "task": "Code / HTML / Docs",
            "model": "codellama:7b-instruct-q4_K_M",
            "size_gb": 3.8,
            "type": "persistent"
        },
        {
            "task": "JIRA Tasks",
            "model": "llama3:8b-instruct-q4_K_M",
            "size_gb": 4.7,
            "type": "persistent"
        },
        {
            "task": "Diagrams",
            "model": "mermaid-mistral",
            "size_gb": 4.5,
            "type": "swap"
        }
    ]
    
    for model_info in model_display:
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            st.markdown(f"**{model_info['task']}**")
            st.caption(f"{model_info['model'][:20]}... ({model_info['size_gb']}GB)")
        
        with col2:
            if model_info['type'] == 'persistent':
                st.caption("🔒 Persistent")
            else:
                st.caption("🔄 Swap")
        
        with col3:
            # Check if model is currently loaded
            if model_info['model'] in ollama_client.active_models:
                st.success("Ready", help="Model loaded in VRAM")
            else:
                st.caption("Not Loaded")
        
        with col4:
            # Check if model is currently in use
            model = ollama_client.models.get(model_info['model'])
            if model and model.status == ModelStatus.IN_USE:
                st.info("⚡", help="Generating")
            elif model and model.status == ModelStatus.LOADING:
                st.warning("⏳", help="Loading...")
    
    st.divider()


def render_local_model_settings():
    """
    Render local model settings in sidebar.
    
    Includes:
    - Force Local Only toggle
    - Model refresh button
    """
    st.markdown("### ⚙️ Local Model Settings")
    
    # Force Local Only toggle
    force_local = st.checkbox(
        "🔒 Force Local Only",
        value=st.session_state.get('force_local_only', False),
        key="force_local_only_checkbox",
        help=(
            "Never fall back to cloud providers. "
            "Generation will fail if local model is unavailable. "
            "Use this for: privacy, offline work, or cost control."
        )
    )
    
    # Update session state
    st.session_state['force_local_only'] = force_local
    
    # Show warning if enabled
    if force_local:
        st.warning(
            "⚠️ **Cloud fallback disabled**\n\n"
            "If local models fail, generation will error instead of falling back to Gemini/GPT-4."
        )
    
    st.divider()
    
    # Refresh Models button
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Refresh Status", help="Re-check Ollama server and model status"):
            st.session_state['ollama_refresh_requested'] = True
            st.rerun()
    
    with col2:
        if st.button("📊 Usage Stats", help="Show local model usage statistics"):
            st.session_state['show_ollama_stats'] = True
            st.rerun()


def render_generation_feedback(
    model_used: str,
    is_local: bool,
    is_fallback: bool,
    generation_time: float,
    error_message: str = ""
):
    """
    Show feedback after generation about which model was used.
    
    Args:
        model_used: Name of model that generated the artifact
        is_local: True if local Ollama model
        is_fallback: True if cloud fallback was used
        generation_time: Time taken in seconds
        error_message: Error message if failed
    """
    if error_message:
        st.error(f"❌ Generation failed: {error_message}")
        return
    
    if is_local:
        # Local model success
        if generation_time < 15:
            # Fast generation (persistent model)
            st.success(
                f"✅ Generated using **{model_used}** (local) in {generation_time:.1f}s ⚡",
                icon="🤖"
            )
        else:
            # Slow generation (swap model)
            st.info(
                f"✅ Generated using **{model_used}** (local) in {generation_time:.1f}s\n\n"
                f"_Note: First-time load. Subsequent requests will be faster (~10s)._",
                icon="🤖"
            )
    
    elif is_fallback:
        # Cloud fallback
        st.warning(
            f"⚠️ Local model unavailable. Used **{model_used}** (cloud) instead.\n\n"
            f"_Generated in {generation_time:.1f}s. Check Ollama status above._",
            icon="☁️"
        )
    
    else:
        # Cloud provider (by design)
        st.info(
            f"☁️ Generated using **{model_used}** (cloud) in {generation_time:.1f}s",
            icon="🌐"
        )


def render_ollama_stats_modal():
    """
    Show detailed Ollama usage statistics in a modal.
    """
    if not st.session_state.get('show_ollama_stats', False):
        return
    
    # Close button
    if st.button("❌ Close Stats"):
        st.session_state['show_ollama_stats'] = False
        st.rerun()
    
    st.markdown("### 📊 Local Model Usage Statistics")
    
    # Get router stats
    if 'router' in st.session_state:
        router = st.session_state.router
        stats = router.get_stats()
        
        # Overall stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Requests", stats.get('request_count', 0))
        
        with col2:
            local_count = sum(
                count for model, count in stats.get('model_usage', {}).items()
                if ':' in model  # Local models have ':' in name
            )
            st.metric("Local Generations", local_count)
        
        with col3:
            cloud_count = stats.get('request_count', 0) - local_count
            st.metric("Cloud Generations", cloud_count)
        
        st.divider()
        
        # Model-specific stats
        st.markdown("#### Per-Model Usage")
        
        model_usage = stats.get('model_usage', {})
        if model_usage:
            for model, count in sorted(model_usage.items(), key=lambda x: x[1], reverse=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**{model}**")
                
                with col2:
                    st.caption(f"{count} requests")
                
                with col3:
                    # Calculate percentage
                    total = stats.get('request_count', 1)
                    percentage = (count / total) * 100
                    st.caption(f"{percentage:.1f}%")
        else:
            st.info("No generation statistics yet. Generate some artifacts first!")
    
    else:
        st.warning("Router not initialized yet.")


def show_model_loading_progress(model_name: str, is_persistent: bool):
    """
    Show progress indicator while model is loading.
    
    Args:
        model_name: Name of model being loaded
        is_persistent: True if persistent model
    """
    if is_persistent:
        st.info(
            f"🔄 Loading **{model_name}** for the first time...\n\n"
            f"_This takes 30-60 seconds, but subsequent requests will be instant._",
            icon="⏳"
        )
    else:
        st.info(
            f"🔄 Loading **{model_name}** (swap model)...\n\n"
            f"_This takes 45-60 seconds for the first diagram, then ~10s for additional diagrams._",
            icon="⏳"
        )
    
    # Progress bar (indeterminate)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    import time
    for i in range(100):
        # Update progress bar
        progress_bar.progress(i + 1)
        
        # Update status text
        if i < 33:
            status_text.text("Loading model into VRAM...")
        elif i < 66:
            status_text.text("Initializing model...")
        else:
            status_text.text("Almost ready...")
        
        time.sleep(0.5)  # 50 seconds total
    
    progress_bar.empty()
    status_text.empty()


# ====================================================================
# Utility Functions
# ====================================================================

def get_task_type_for_artifact(artifact_type: str) -> str:
    """
    Map artifact type to task type for model routing.
    
    Args:
        artifact_type: Artifact type from app (e.g., 'code_prototype')
        
    Returns:
        Task type for ModelRouter (e.g., 'code')
    """
    mapping = {
        # Code tasks
        'code_prototype': 'code',
        'code': 'code',
        'scaffold': 'code',
        
        # HTML tasks
        'visual_prototype_dev': 'html',
        'html': 'html',
        'ui': 'html',
        
        # Documentation tasks
        'api_docs': 'documentation',
        'documentation': 'documentation',
        'docs': 'documentation',
        
        # JIRA tasks
        'jira': 'jira',
        'jira_tasks': 'jira',
        'tasks': 'jira',
        
        # Diagram tasks (all use mermaid-mistral)
        'erd': 'mermaid',
        'architecture': 'mermaid',
        'data_flow_diagram': 'mermaid',
        'user_flow_diagram': 'mermaid',
        'system_overview_diagram': 'mermaid',
        'components_diagram': 'mermaid',
        'api_sequence_diagram': 'mermaid',
        'flowchart': 'mermaid',
        'sequence': 'mermaid',
        'class': 'mermaid',
        'state': 'mermaid',
    }
    
    return mapping.get(artifact_type, 'code')  # Default to 'code'


def format_model_name_for_display(model_name: str) -> str:
    """
    Format model name for user-friendly display.
    
    Args:
        model_name: Full model name (e.g., 'codellama:7b-instruct-q4_K_M')
        
    Returns:
        Formatted name (e.g., 'CodeLlama 7B')
    """
    if 'codellama' in model_name.lower():
        return "CodeLlama 7B"
    elif 'llama3' in model_name.lower():
        return "Llama 3 8B"
    elif 'mermaid' in model_name.lower():
        return "MermaidMistral"
    elif 'gemini' in model_name.lower():
        return "Gemini 2.0 Flash"
    elif 'gpt-4' in model_name.lower():
        return "GPT-4"
    elif 'gpt-3.5' in model_name.lower():
        return "GPT-3.5 Turbo"
    else:
        return model_name

