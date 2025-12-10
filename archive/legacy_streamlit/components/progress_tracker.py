"""
Progress Tracking System for Architect.AI
Provides real-time progress bars with ETA for all operations
"""

import time
import streamlit as st
from typing import Dict, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ProgressData:
    """Progress tracking data structure"""
    task_name: str
    current_step: int
    total_steps: int
    start_time: float
    eta_seconds: float
    message: str
    percent: float


class ProgressTracker:
    """Real-time progress tracking with ETA calculation"""
    
    def __init__(self):
        self.current_task: Optional[ProgressData] = None
        self.task_history: list = []
        self.callbacks: Dict[str, Callable] = {}
    
    def start_tracking(self, task_name: str, total_steps: int, message: str = "") -> str:
        """Initialize progress tracking for a new task"""
        
        task_id = f"{task_name}_{int(time.time())}"
        
        self.current_task = ProgressData(
            task_name=task_name,
            current_step=0,
            total_steps=total_steps,
            start_time=time.time(),
            eta_seconds=0.0,
            message=message or f"Starting {task_name}...",
            percent=0.0
        )
        
        # Store in session state for UI access
        if 'progress_tracker' not in st.session_state:
            st.session_state.progress_tracker = {}
        
        st.session_state.progress_tracker[task_id] = self.current_task
        
        return task_id
    
    def update_progress(self, task_id: str, step: int, message: str = "") -> ProgressData:
        """Update progress and calculate ETA"""
        
        if task_id not in st.session_state.progress_tracker:
            raise ValueError(f"Task {task_id} not found")
        
        task = st.session_state.progress_tracker[task_id]
        task.current_step = step
        task.message = message or task.message
        
        # Calculate ETA
        elapsed = time.time() - task.start_time
        
        if step > 0:
            avg_time_per_step = elapsed / step
            remaining_steps = task.total_steps - step
            task.eta_seconds = avg_time_per_step * remaining_steps
        else:
            task.eta_seconds = 0.0
        
        # Calculate percentage
        task.percent = (step / task.total_steps) * 100 if task.total_steps > 0 else 0
        
        # Update session state
        st.session_state.progress_tracker[task_id] = task
        
        # Trigger callbacks
        if task_id in self.callbacks:
            self.callbacks[task_id](task)
        
        return task
    
    def complete_task(self, task_id: str, final_message: str = "Completed!") -> ProgressData:
        """Mark task as completed"""
        
        if task_id not in st.session_state.progress_tracker:
            raise ValueError(f"Task {task_id} not found")
        
        task = st.session_state.progress_tracker[task_id]
        task.current_step = task.total_steps
        task.percent = 100.0
        task.eta_seconds = 0.0
        task.message = final_message
        
        # Move to history
        self.task_history.append(task)
        
        # Clean up current task
        del st.session_state.progress_tracker[task_id]
        
        return task
    
    def get_current_progress(self, task_id: str) -> Optional[ProgressData]:
        """Get current progress for a task"""
        return st.session_state.progress_tracker.get(task_id)
    
    def add_callback(self, task_id: str, callback: Callable[[ProgressData], None]):
        """Add callback for progress updates"""
        self.callbacks[task_id] = callback
    
    def format_eta(self, eta_seconds: float) -> str:
        """Format ETA in human-readable format"""
        if eta_seconds <= 0:
            return "0s"
        elif eta_seconds < 60:
            return f"{eta_seconds:.0f}s"
        elif eta_seconds < 3600:
            minutes = eta_seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = eta_seconds / 3600
            return f"{hours:.1f}h"


# Global progress tracker instance
progress_tracker = ProgressTracker()


def render_progress_bar(task_id: str, show_details: bool = True) -> bool:
    """
    Render beautiful progress bar with ETA
    
    Args:
        task_id: Task identifier
        show_details: Whether to show detailed metrics
    
    Returns:
        True if task is still running, False if completed
    """
    
    if task_id not in st.session_state.progress_tracker:
        return False
    
    task = st.session_state.progress_tracker[task_id]
    
    # Main progress bar
    st.progress(task.percent / 100)
    
    if show_details:
        # Metrics row
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            st.write(f"**{task.task_name}**")
        
        with col2:
            st.metric("Progress", f"{task.percent:.0f}%")
        
        with col3:
            eta_formatted = progress_tracker.format_eta(task.eta_seconds)
            st.metric("ETA", eta_formatted)
        
        with col4:
            elapsed = time.time() - task.start_time
            elapsed_formatted = progress_tracker.format_eta(elapsed)
            st.metric("Elapsed", elapsed_formatted)
        
        # Status message
        if task.message:
            st.caption(f"🔄 {task.message}")
    
    return True


def render_progress_sidebar():
    """Render progress tracking in sidebar"""
    
    if not st.session_state.progress_tracker:
        return
    
    st.sidebar.subheader("📊 Active Tasks")
    
    for task_id, task in st.session_state.progress_tracker.items():
        with st.sidebar.expander(f"🔄 {task.task_name}", expanded=False):
            render_progress_bar(task_id, show_details=False)
            
            # Quick actions
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("📊 Details", key=f"details_{task_id}"):
                    st.session_state[f"show_details_{task_id}"] = True
            
            with col2:
                if st.button("❌ Cancel", key=f"cancel_{task_id}"):
                    if task_id in st.session_state.progress_tracker:
                        del st.session_state.progress_tracker[task_id]
                    st.rerun()


def with_progress_tracking(task_name: str, total_steps: int):
    """
    Decorator for functions that need progress tracking
    
    Usage:
        @with_progress_tracking("Generating ERD", 5)
        def generate_erd():
            progress_tracker.update_progress(task_id, 1, "Analyzing requirements...")
            # ... do work
            progress_tracker.update_progress(task_id, 2, "Creating entities...")
            # ... etc
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            task_id = progress_tracker.start_tracking(task_name, total_steps)
            
            try:
                # Pass task_id to the function
                result = func(task_id, *args, **kwargs)
                progress_tracker.complete_task(task_id, f"{task_name} completed successfully!")
                return result
            except Exception as e:
                progress_tracker.complete_task(task_id, f"{task_name} failed: {str(e)}")
                raise
        
        return wrapper
    return decorator


# Convenience functions for common operations
def track_rag_retrieval(task_id: str, step: int, message: str = ""):
    """Track RAG retrieval progress"""
    progress_tracker.update_progress(task_id, step, message)


def track_ai_generation(task_id: str, step: int, message: str = ""):
    """Track AI generation progress"""
    progress_tracker.update_progress(task_id, step, message)


def track_validation(task_id: str, step: int, message: str = ""):
    """Track validation progress"""
    progress_tracker.update_progress(task_id, step, message)


def track_file_operations(task_id: str, step: int, message: str = ""):
    """Track file operations progress"""
    progress_tracker.update_progress(task_id, step, message)
