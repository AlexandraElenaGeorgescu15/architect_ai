"""Test all critical imports that are in try/except blocks"""
import sys

critical_imports = [
    ('rag.advanced_retrieval', 'get_advanced_retrieval'),
    ('agents.multi_agent_system', 'get_multi_agent_system'),
    ('agents.advanced_prompting', 'get_advanced_prompting'),
    ('agents.quality_metrics', 'get_quality_system'),
    ('rag.query_processor', 'get_query_expander'),
    ('rag.reranker', 'get_reranker'),
    ('rag.context_optimizer', 'get_context_optimizer'),
    ('components.pattern_mining', 'PatternDetector'),
    ('components.knowledge_graph', 'KnowledgeGraphBuilder'),
    ('components.universal_diagram_fixer', 'fix_any_diagram'),
    ('validation.output_validator', 'ArtifactValidator'),
    ('analysis.security_scanner', 'get_security_scanner'),
    ('versioning.version_manager', 'VersionManager'),
    ('components.persistent_training', 'persistent_training_manager'),
    ('ai.artifact_router', 'ArtifactRouter'),
    ('rag.auto_ingestion', 'get_auto_ingestion_manager'),
    ('rag.refresh_manager', 'get_refresh_manager'),
    ('rag.auto_reindex', 'get_auto_reindexer'),
    ('components.model_registry', 'model_registry'),
    ('rag.cache', 'get_cache'),
    ('components.local_finetuning', 'local_finetuning_system'),
    ('ai.output_validator', 'OutputValidator'),
    ('components.mermaid_html_renderer', 'mermaid_html_renderer'),
    ('agents.specialized_agents', 'MultiAgentOrchestrator'),
    ('components.finetuning_feedback', 'feedback_store'),
]

missing = []
for module_name, func_name in critical_imports:
    try:
        mod = __import__(module_name, fromlist=[func_name])
        getattr(mod, func_name)
    except Exception as e:
        missing.append(f'{module_name}.{func_name}: {str(e)}')

if missing:
    print('❌ Missing/broken imports:')
    for m in missing:
        print(f'  • {m}')
else:
    print('✅ All critical feature imports exist')
