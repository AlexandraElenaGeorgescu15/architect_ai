"""
Components Package for Architect.AI v3.5.2

This package contains Python utility components used by the backend services.
Note: UI components have been migrated to the React frontend.

Legacy Streamlit UI components are archived in archive/legacy_streamlit/components/
"""

# Core components that are still actively used
try:
    from ._tool_detector import should_exclude_path, get_user_project_directories, detect_tool_directory
except ImportError:
    pass

try:
    from .mermaid_preprocessor import aggressive_mermaid_preprocessing
except ImportError:
    pass

try:
    from .universal_diagram_fixer import fix_any_diagram
except ImportError:
    pass

try:
    from .smart_code_analyzer import get_smart_analyzer
except ImportError:
    pass

# Training and adaptive learning components
try:
    from .adaptive_learning import AdaptiveLearningLoop, FeedbackType, FeedbackEvent
except ImportError:
    pass

try:
    from .validation_pipeline import ValidationPipeline, NoiseReductionPipeline
except ImportError:
    pass

try:
    from .ml_feature_engineering import MLFeatureEngineer
except ImportError:
    pass

try:
    from .finetuning_dataset_builder import FineTuningDatasetBuilder
except ImportError:
    pass

try:
    from .model_registry import model_registry
except ImportError:
    pass

# Note: The following components still have Streamlit imports but are used
# by the agents/universal_agent.py for backward compatibility:
# - knowledge_graph.py (KnowledgeGraphBuilder)
# - pattern_mining.py (PatternDetector)
# - prototype_generator.py
# - local_finetuning.py
# - mermaid_syntax_corrector.py
# - mermaid_html_renderer.py
# - enhanced_rag.py
#
# These will be gradually migrated to use the backend services equivalents.

__all__ = [
    'should_exclude_path',
    'get_user_project_directories',
    'detect_tool_directory',
    'aggressive_mermaid_preprocessing',
    'fix_any_diagram',
    'get_smart_analyzer',
    'AdaptiveLearningLoop',
    'FeedbackType',
    'FeedbackEvent',
    'ValidationPipeline',
    'NoiseReductionPipeline',
    'MLFeatureEngineer',
    'FineTuningDatasetBuilder',
    'model_registry',
]
