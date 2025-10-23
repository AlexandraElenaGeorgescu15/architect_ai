"""
Metrics Dashboard Component
Shows time saved, costs, ROI, and quality metrics
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List
import json
from pathlib import Path


class MetricsTracker:
    """Track and calculate metrics across sessions"""
    
    def __init__(self, metrics_file: str = "outputs/metrics.json"):
        self.metrics_file = Path(metrics_file)
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        self.metrics = self._load_metrics()
    
    def _load_metrics(self) -> Dict:
        """Load metrics from file"""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
            except:
                return self._init_metrics()
        return self._init_metrics()
    
    def _init_metrics(self) -> Dict:
        """Initialize metrics structure"""
        return {
            "total_generations": 0,
            "total_cost": 0.0,
            "total_time_saved": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "quality_scores": [],
            "artifacts_by_type": {},
            "daily_usage": {},
            "sessions": []
        }
    
    def _save_metrics(self):
        """Save metrics to file"""
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
    
    def record_generation(self, artifact_type: str, cost: float, time_saved: float, quality_score: float = 0.85):
        """Record a generation event"""
        self.metrics["total_generations"] += 1
        self.metrics["total_cost"] += cost
        self.metrics["total_time_saved"] += time_saved
        self.metrics["quality_scores"].append(quality_score)
        
        # Track by type
        if artifact_type not in self.metrics["artifacts_by_type"]:
            self.metrics["artifacts_by_type"][artifact_type] = 0
        self.metrics["artifacts_by_type"][artifact_type] += 1
        
        # Track daily usage
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.metrics["daily_usage"]:
            self.metrics["daily_usage"][today] = 0
        self.metrics["daily_usage"][today] += 1
        
        self._save_metrics()
    
    def record_cache_hit(self):
        """Record cache hit"""
        self.metrics["cache_hits"] += 1
        self._save_metrics()
    
    def record_cache_miss(self):
        """Record cache miss"""
        self.metrics["cache_misses"] += 1
        self._save_metrics()
    
    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        if total == 0:
            return 0.0
        return (self.metrics["cache_hits"] / total) * 100
    
    def get_average_quality(self) -> float:
        """Calculate average quality score"""
        scores = self.metrics["quality_scores"]
        if not scores:
            return 0.0
        return sum(scores) / len(scores)
    
    def get_roi(self) -> float:
        """Calculate ROI"""
        if self.metrics["total_cost"] == 0:
            return 0.0
        # Estimate value: $50/hour saved
        value_saved = self.metrics["total_time_saved"] * 50
        return (value_saved / self.metrics["total_cost"]) * 100
    
    def get_cost_without_optimization(self) -> float:
        """Estimate cost without optimization (87% more expensive)"""
        return self.metrics["total_cost"] / 0.13  # 13% of original cost
    
    def get_savings(self) -> float:
        """Calculate total savings"""
        return self.get_cost_without_optimization() - self.metrics["total_cost"]


def render_metrics_dashboard():
    """Render comprehensive metrics dashboard"""
    
    st.markdown("### 📊 Performance Metrics")
    grafana_url = None
    try:
        import os
        grafana_url = os.getenv("GRAFANA_URL")
    except Exception:
        grafana_url = None
    
    # Initialize tracker
    tracker = MetricsTracker()
    
    # Top-level metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "⏱️ Time Saved",
            f"{tracker.metrics['total_time_saved']:.1f} hrs",
            delta=f"${tracker.metrics['total_time_saved'] * 50:.0f} value"
        )
    
    with col2:
        st.metric(
            "💰 Cost Saved",
            f"${tracker.get_savings():.2f}",
            delta=f"{87}% reduction"
        )
    
    with col3:
        st.metric(
            "🎯 Quality Score",
            f"{tracker.get_average_quality():.0%}",
            delta="Excellent"
        )
    
    with col4:
        st.metric(
            "📈 ROI",
            f"{tracker.get_roi():.0f}x",
            delta=f"{tracker.metrics['total_generations']} artifacts"
        )
        if grafana_url:
            st.link_button("📊 Open Grafana", grafana_url, use_container_width=True)
    
    st.divider()
    
    # Detailed metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 💵 Cost Analysis")
        st.metric("Total Spend", f"${tracker.metrics['total_cost']:.2f}")
        st.metric("Without Optimization", f"${tracker.get_cost_without_optimization():.2f}")
        st.metric("Cache Hit Rate", f"{tracker.get_cache_hit_rate():.1f}%")
        
        # Cost breakdown
        if tracker.metrics["artifacts_by_type"]:
            st.markdown("**Cost by Artifact Type:**")
            for artifact, count in tracker.metrics["artifacts_by_type"].items():
                estimated_cost = count * 0.05
                st.text(f"  {artifact}: ${estimated_cost:.2f} ({count} generations)")
    
    with col2:
        st.markdown("#### 📊 Usage Statistics")
        st.metric("Total Generations", tracker.metrics['total_generations'])
        st.metric("Cache Hits", tracker.metrics['cache_hits'])
        st.metric("Cache Misses", tracker.metrics['cache_misses'])
        
        # Artifact breakdown
        if tracker.metrics["artifacts_by_type"]:
            st.markdown("**Artifacts Generated:**")
            for artifact, count in sorted(tracker.metrics["artifacts_by_type"].items(), key=lambda x: x[1], reverse=True):
                st.text(f"  {artifact}: {count}")
    
    # Weekly trend (if enough data)
    if len(tracker.metrics["daily_usage"]) > 1:
        st.divider()
        st.markdown("#### 📈 Usage Trend (Last 7 Days)")
        
        import pandas as pd
        
        # Get last 7 days
        dates = sorted(tracker.metrics["daily_usage"].keys())[-7:]
        data = {
            "Date": dates,
            "Generations": [tracker.metrics["daily_usage"][d] for d in dates]
        }
        df = pd.DataFrame(data)
        st.line_chart(df.set_index("Date"))
    
    # Export button
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 Export Report", use_container_width=True):
            # Create report
            report = f"""
# Metrics Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary
- Time Saved: {tracker.metrics['total_time_saved']:.1f} hours
- Value Created: ${tracker.metrics['total_time_saved'] * 50:.2f}
- Cost: ${tracker.metrics['total_cost']:.2f}
- Savings: ${tracker.get_savings():.2f} (87% reduction)
- ROI: {tracker.get_roi():.0f}x
- Quality Score: {tracker.get_average_quality():.0%}

## Generations
- Total: {tracker.metrics['total_generations']}
- Cache Hit Rate: {tracker.get_cache_hit_rate():.1f}%

## By Artifact Type
"""
            for artifact, count in tracker.metrics["artifacts_by_type"].items():
                report += f"- {artifact}: {count}\n"
            
            st.download_button(
                "💾 Download Report",
                report,
                "metrics_report.md",
                "text/markdown"
            )
    
    with col2:
        if st.button("🔄 Reset Metrics", use_container_width=True):
            if st.session_state.get('confirm_reset'):
                tracker.metrics = tracker._init_metrics()
                tracker._save_metrics()
                st.success("Metrics reset!")
                st.session_state.confirm_reset = False
                st.rerun()
            else:
                st.session_state.confirm_reset = True
                st.warning("Click again to confirm reset")
    
    with col3:
        if st.button("📊 View Detailed Stats", use_container_width=True):
            st.session_state.show_detailed_stats = True
    
    # Detailed stats modal
    if st.session_state.get('show_detailed_stats'):
        with st.expander("📊 Detailed Statistics", expanded=True):
            st.json(tracker.metrics)
            if st.button("Close"):
                st.session_state.show_detailed_stats = False
                st.rerun()


# Helper function to record generation from app
def track_generation(artifact_type: str, cost: float = 0.05, time_saved: float = 0.5):
    """
    Track a generation event and update session state.
    
    This function serves two purposes:
    1. Records metrics for analytics (cost, time saved, counts)
    2. Updates session state to display recent generations in UI
    
    Args:
        artifact_type: Type of artifact generated (erd, architecture, etc.)
        cost: Estimated cost in dollars
        time_saved: Estimated time saved in hours
    """
    tracker = MetricsTracker()
    tracker.record_generation(artifact_type, cost, time_saved)
    
    # Also update session state for UI display (if in Streamlit context)
    try:
        import streamlit as st
        if 'last_generation' not in st.session_state:
            st.session_state.last_generation = []
        st.session_state.last_generation.append(artifact_type)
        # Keep only last 10 generations to avoid memory bloat
        if len(st.session_state.last_generation) > 10:
            st.session_state.last_generation = st.session_state.last_generation[-10:]
    except Exception:
        pass  # Not in Streamlit context or session state unavailable

