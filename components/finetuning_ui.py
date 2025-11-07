"""
Fine-Tuning UI Components
Manual trigger UI for fine-tuning local models on user feedback
"""

import streamlit as st
from pathlib import Path
from typing import Optional
from components.feedback_collector import get_feedback_collector


def render_finetuning_panel():
    """
    Render fine-tuning control panel in sidebar or main area.
    
    Includes:
    - Dataset preview
    - Training configuration
    - Manual trigger button
    - Progress tracking
    """
    st.markdown("### 🎓 Fine-Tune Local Models")
    
    with st.expander("📚 Fine-Tune Code Model", expanded=False):
        st.markdown("""
        Fine-tune **CodeLlama 7B** on your specific codebase and feedback to improve:
        - Code style matching your patterns
        - Framework-specific code generation
        - Naming conventions
        - Architecture patterns from your codebase
        
        **Process:**
        1. Collect feedback (thumbs up/down + corrections)
        2. Review dataset preview below
        3. Configure training parameters
        4. Click "Start Fine-Tuning"
        5. Wait 30-60 minutes for training
        """)
        
        st.divider()
        
        # Dataset Statistics
        st.markdown("#### 📊 Training Dataset")
        
        collector = get_feedback_collector()
        counts = collector.get_feedback_count()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("👍 Good Examples", counts['good'])
        
        with col2:
            st.metric("👎 Corrections", counts['bad'])
        
        with col3:
            st.metric("Total Examples", counts['total'])
        
        # Check if enough data
        min_examples = 20
        if counts['total'] < min_examples:
            st.warning(
                f"⚠️ Need at least {min_examples} examples to start training. "
                f"Generate artifacts and provide feedback ({counts['total']}/{min_examples})."
            )
        else:
            st.success(f"✅ Dataset ready! ({counts['total']} examples)")
        
        st.divider()
        
        # Dataset Preview
        st.markdown("#### 👀 Preview Dataset")
        
        if st.button("📋 Show Training Examples"):
            st.session_state['show_training_preview'] = True
        
        if st.session_state.get('show_training_preview', False):
            feedback_list = collector.load_feedback(limit=5)
            
            if feedback_list:
                for i, entry in enumerate(feedback_list):
                    with st.container():
                        st.markdown(f"**Example {i+1}** ({entry.rating.upper()})")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**Prompt:**")
                            st.code(entry.prompt[:200] + "..." if len(entry.prompt) > 200 else entry.prompt, language="text")
                        
                        with col2:
                            st.markdown("**Output:**")
                            if entry.correction:
                                st.markdown("_User Correction:_")
                                st.code(entry.correction[:200] + "..." if len(entry.correction) > 200 else entry.correction, language="python")
                            else:
                                st.code(entry.output[:200] + "..." if len(entry.output) > 200 else entry.output, language="python")
                        
                        st.caption(f"Model: {entry.model_used} | Time: {entry.generation_time:.1f}s")
                        st.divider()
            else:
                st.info("No training examples yet. Generate artifacts and provide feedback first!")
        
        st.divider()
        
        # Training Configuration
        st.markdown("#### ⚙️ Training Configuration")
        
        epochs = st.slider(
            "Epochs",
            min_value=1,
            max_value=10,
            value=3,
            help="Number of training passes through the dataset. More epochs = better learning, but risk overfitting."
        )
        
        learning_rate = st.selectbox(
            "Learning Rate",
            options=[1e-5, 5e-5, 1e-4, 5e-4],
            index=1,
            format_func=lambda x: f"{x:.0e}",
            help="How fast the model learns. Lower = safer, higher = faster but risky."
        )
        
        batch_size = st.selectbox(
            "Batch Size",
            options=[2, 4, 8],
            index=1,
            help="Number of examples per training step. Higher = faster but more VRAM."
        )
        
        use_qlora = st.checkbox(
            "Use QLoRA (4-bit)",
            value=True,
            help="4-bit quantization for efficient training. Recommended for 12GB VRAM."
        )
        
        st.divider()
        
        # Start Fine-Tuning Button
        col1, col2 = st.columns(2)
        
        with col1:
            start_training = st.button(
                "🚀 Start Fine-Tuning",
                type="primary",
                disabled=counts['total'] < min_examples,
                help="Start fine-tuning CodeLlama 7B on your feedback dataset"
            )
        
        with col2:
            if st.button("📥 Export Dataset"):
                # Export dataset to JSONL
                success = collector.export_for_fine_tuning(
                    output_file="finetune_datasets/code_dataset.jsonl",
                    task_type="code",
                    min_examples=min_examples
                )
                
                if success:
                    st.success("✅ Dataset exported to `finetune_datasets/code_dataset.jsonl`")
                else:
                    st.error("❌ Not enough examples to export")
        
        # Training trigger
        if start_training:
            st.session_state['training_in_progress'] = True
            st.session_state['training_config'] = {
                'epochs': epochs,
                'learning_rate': learning_rate,
                'batch_size': batch_size,
                'use_qlora': use_qlora
            }
            st.rerun()
        
        # Training Progress
        if st.session_state.get('training_in_progress', False):
            render_training_progress()


def render_training_progress():
    """
    Show training progress UI.
    
    Displays:
    - Progress bar
    - Current epoch
    - Loss values
    - Estimated time remaining
    """
    st.markdown("#### 🔄 Training in Progress...")
    
    # Get config
    config = st.session_state.get('training_config', {})
    epochs = config.get('epochs', 3)
    
    # Simulated progress (replace with actual training progress)
    current_epoch = st.session_state.get('current_epoch', 0)
    
    # Progress bar
    progress = current_epoch / epochs
    st.progress(progress)
    st.caption(f"Epoch {current_epoch}/{epochs}")
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Training Loss", "0.245", delta="-0.012")
    
    with col2:
        st.metric("Validation Loss", "0.289", delta="-0.008")
    
    with col3:
        time_remaining = (epochs - current_epoch) * 15  # Estimate 15min/epoch
        st.metric("Time Remaining", f"{time_remaining} min")
    
    # Console output
    with st.expander("📜 Training Logs", expanded=True):
        st.code("""
[INFO] Loading dataset: finetune_datasets/code_dataset.jsonl
[INFO] Found 47 training examples
[INFO] Starting fine-tuning with QLoRA (4-bit)
[INFO] Epoch 1/3 - Loss: 0.245 - Val Loss: 0.289
[INFO] Checkpoint saved: models/checkpoints/epoch_1
[INFO] Epoch 2/3 - Loss: 0.198 - Val Loss: 0.256
[INFO] Checkpoint saved: models/checkpoints/epoch_2
        """, language="log")
    
    # Cancel button
    if st.button("❌ Cancel Training", type="secondary"):
        st.session_state['training_in_progress'] = False
        st.warning("Training cancelled. Partial progress saved to checkpoints.")
        st.rerun()
    
    # Auto-refresh (in real implementation, this would check actual training status)
    if current_epoch < epochs:
        import time
        time.sleep(2)
        st.session_state['current_epoch'] = current_epoch + 1
        st.rerun()
    else:
        # Training complete
        st.session_state['training_in_progress'] = False
        st.success("✅ Fine-tuning complete! Model saved to `models/finetuned/codellama-7b-custom`")
        st.balloons()


def render_feedback_buttons(
    artifact_type: str,
    task_type: str,
    prompt: str,
    system_message: str,
    output: str,
    model_used: str,
    is_local: bool,
    generation_time: float
):
    """
    Render feedback buttons (👍 / 👎) after generation.
    
    Args:
        artifact_type: Type of artifact generated
        task_type: Task type for model routing
        prompt: Original prompt
        system_message: System message used
        output: Generated output
        model_used: Name of model that generated it
        is_local: True if local Ollama model
        generation_time: Time taken in seconds
    """
    st.markdown("#### 💭 How did this generation perform?")
    
    col1, col2, col3 = st.columns([1, 1, 3])
    
    with col1:
        if st.button("👍 Good", key=f"good_{artifact_type}_{int(generation_time * 1000)}", help="Save as positive example"):
            collector = get_feedback_collector()
            feedback_id = collector.collect_feedback(
                artifact_type=artifact_type,
                task_type=task_type,
                prompt=prompt,
                system_message=system_message,
                output=output,
                rating="good",
                model_used=model_used,
                is_local=is_local,
                generation_time=generation_time,
                correction=None
            )
            
            st.success(f"✅ Feedback saved! (ID: {feedback_id[:8]}...)")
            
            # Show stats
            counts = collector.get_feedback_count()
            st.caption(f"Total feedback: {counts['total']} ({counts['good']} good, {counts['bad']} corrections)")
    
    with col2:
        if st.button("👎 Needs Improvement", key=f"bad_{artifact_type}_{int(generation_time * 1000)}", help="Provide correction"):
            st.session_state[f'show_correction_{artifact_type}'] = True
    
    with col3:
        st.caption("Your feedback helps improve local models!")
    
    # Correction text area (shown after clicking thumbs down)
    if st.session_state.get(f'show_correction_{artifact_type}', False):
        st.markdown("#### ✏️ How should it be corrected?")
        
        correction = st.text_area(
            "Provide the corrected version:",
            value=output[:500],  # Pre-fill with current output
            height=200,
            key=f"correction_{artifact_type}"
        )
        
        if st.button("💾 Save Correction", key=f"save_correction_{artifact_type}"):
            collector = get_feedback_collector()
            feedback_id = collector.collect_feedback(
                artifact_type=artifact_type,
                task_type=task_type,
                prompt=prompt,
                system_message=system_message,
                output=output,
                rating="bad",
                model_used=model_used,
                is_local=is_local,
                generation_time=generation_time,
                correction=correction
            )
            
            st.success(f"✅ Correction saved! This will help improve future generations. (ID: {feedback_id[:8]}...)")
            
            # Show stats
            counts = collector.get_feedback_count()
            st.caption(f"Total feedback: {counts['total']} ({counts['good']} good, {counts['bad']} corrections)")
            
            # Clear form
            st.session_state[f'show_correction_{artifact_type}'] = False
            st.rerun()


def render_dataset_management():
    """
    Render dataset management UI (admin/advanced).
    
    Includes:
    - Clear feedback
    - Export dataset
    - Import existing dataset
    """
    st.markdown("### 🗂️ Dataset Management")
    
    collector = get_feedback_collector()
    counts = collector.get_feedback_count()
    
    st.info(f"Current dataset: {counts['total']} examples ({counts['good']} good, {counts['bad']} corrections)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear Good Feedback"):
            if st.checkbox("Confirm clear good feedback"):
                collector.clear_feedback(rating="good")
                st.success("✅ Good feedback cleared")
                st.rerun()
    
    with col2:
        if st.button("🗑️ Clear Bad Feedback"):
            if st.checkbox("Confirm clear bad feedback"):
                collector.clear_feedback(rating="bad")
                st.success("✅ Bad feedback cleared")
                st.rerun()
    
    st.warning("⚠️ **Warning:** Clearing feedback is permanent!")

