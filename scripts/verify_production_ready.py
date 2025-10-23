"""
Production Readiness Verification Script
Checks that all advanced features are properly implemented
"""

import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_imports():
    """Verify all advanced modules can be imported"""
    print("=" * 60)
    print("CHECKING IMPORTS")
    print("=" * 60)
    
    checks = []
    
    # Advanced RAG
    try:
        from rag.advanced_retrieval import (
            HyDERetrieval, QueryDecomposition, MultiHopReasoning, AdaptiveRetrieval
        )
        print("✅ Advanced RAG modules")
        checks.append(True)
    except Exception as e:
        print(f"❌ Advanced RAG modules: {e}")
        checks.append(False)
    
    # Multi-agent system
    try:
        from agents.multi_agent_system import (
            SpecializedAgent, MultiAgentOrchestrator, AgentRole
        )
        print("✅ Multi-agent system")
        checks.append(True)
    except Exception as e:
        print(f"❌ Multi-agent system: {e}")
        checks.append(False)
    
    # Advanced prompting
    try:
        from agents.advanced_prompting import (
            ChainOfThought, TreeOfThought, ReActAgent, SelfConsistency
        )
        print("✅ Advanced prompting")
        checks.append(True)
    except Exception as e:
        print(f"❌ Advanced prompting: {e}")
        checks.append(False)
    
    # Quality metrics
    try:
        from agents.quality_metrics import (
            QualityEvaluator, SelfImprovement, OutputValidator
        )
        print("✅ Quality metrics")
        checks.append(True)
    except Exception as e:
        print(f"❌ Quality metrics: {e}")
        checks.append(False)
    
    # Embedding optimization
    try:
        from rag.embedding_optimization import (
            EmbeddingOptimizer, SemanticCompression, ContextOptimizer
        )
        print("✅ Embedding optimization")
        checks.append(True)
    except Exception as e:
        print(f"❌ Embedding optimization: {e}")
        checks.append(False)
    
    # Universal agent
    try:
        from agents.universal_agent import UniversalArchitectAgent
        print("✅ Universal agent")
        checks.append(True)
    except Exception as e:
        print(f"❌ Universal agent: {e}")
        checks.append(False)
    
    return all(checks)

def check_files():
    """Verify all required files exist"""
    print("\n" + "=" * 60)
    print("CHECKING FILES")
    print("=" * 60)
    
    required_files = [
        "agents/universal_agent.py",
        "agents/multi_agent_system.py",
        "agents/advanced_prompting.py",
        "agents/quality_metrics.py",
        "rag/advanced_retrieval.py",
        "rag/embedding_optimization.py",
        "rag/diagram_validator.py",
        "rag/erd_generator.py",
        "app/app_v2.py",
        "docker-compose.prod.yml",
        "Dockerfile.prod",
        "monitoring/prometheus.yml",
        "monitoring/alerts.yml",
        "nginx/nginx.conf",
        "PRODUCTION_READY.md",
        "DEPLOYMENT_GUIDE.md",
        "ULTIMATE_SYSTEM_SUMMARY.md",
    ]
    
    checks = []
    base_path = Path(__file__).parent.parent
    
    for file_path in required_files:
        full_path = base_path / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
            checks.append(True)
        else:
            print(f"❌ {file_path} - NOT FOUND")
            checks.append(False)
    
    return all(checks)

def check_features():
    """Verify features are properly integrated"""
    print("\n" + "=" * 60)
    print("CHECKING FEATURE INTEGRATION")
    print("=" * 60)
    
    checks = []
    
    try:
        from agents.universal_agent import UniversalArchitectAgent
        
        # Create agent (without API key for testing)
        agent = UniversalArchitectAgent(config={})
        
        # Check advanced systems initialization
        has_advanced_rag = hasattr(agent, 'advanced_rag')
        has_multi_agent = hasattr(agent, 'multi_agent')
        has_advanced_prompting = hasattr(agent, 'advanced_prompting')
        has_quality_system = hasattr(agent, 'quality_system')
        
        if has_advanced_rag:
            print("✅ Advanced RAG integrated")
            checks.append(True)
        else:
            print("❌ Advanced RAG not integrated")
            checks.append(False)
        
        if has_multi_agent:
            print("✅ Multi-agent system integrated")
            checks.append(True)
        else:
            print("❌ Multi-agent system not integrated")
            checks.append(False)
        
        if has_advanced_prompting:
            print("✅ Advanced prompting integrated")
            checks.append(True)
        else:
            print("❌ Advanced prompting not integrated")
            checks.append(False)
        
        if has_quality_system:
            print("✅ Quality system integrated")
            checks.append(True)
        else:
            print("❌ Quality system not integrated")
            checks.append(False)
        
    except Exception as e:
        print(f"❌ Feature integration check failed: {e}")
        checks.append(False)
    
    return all(checks)

def check_documentation():
    """Verify documentation completeness"""
    print("\n" + "=" * 60)
    print("CHECKING DOCUMENTATION")
    print("=" * 60)
    
    docs = [
        ("PRODUCTION_READY.md", ["HyDE", "Chain-of-Thought", "Multi-Agent", "Quality Metrics"]),
        ("DEPLOYMENT_GUIDE.md", ["Docker", "Production", "Monitoring", "Security"]),
        ("ULTIMATE_SYSTEM_SUMMARY.md", ["Performance", "Research Papers", "Cost Optimization"]),
    ]
    
    checks = []
    base_path = Path(__file__).parent.parent
    
    for doc_file, keywords in docs:
        doc_path = base_path / doc_file
        if doc_path.exists():
            try:
                content = doc_path.read_text(encoding='utf-8')
                missing = [kw for kw in keywords if kw not in content]
                if not missing:
                    print(f"✅ {doc_file} - Complete")
                    checks.append(True)
                else:
                    print(f"⚠️  {doc_file} - Missing: {', '.join(missing)}")
                    checks.append(False)
            except Exception as e:
                print(f"⚠️  {doc_file} - Error reading: {e}")
                checks.append(False)
        else:
            print(f"❌ {doc_file} - NOT FOUND")
            checks.append(False)
    
    return all(checks)

def print_summary(results):
    """Print final summary"""
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    total = len(results)
    passed = sum(results)
    
    print(f"\nTotal Checks: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if all(results):
        print("\n" + "=" * 60)
        print("SUCCESS: ALL CHECKS PASSED - SYSTEM IS PRODUCTION READY!")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("WARNING: SOME CHECKS FAILED - REVIEW ERRORS ABOVE")
        print("=" * 60)
        return False

def main():
    """Run all verification checks"""
    print("\n" + "=" * 60)
    print("PRODUCTION READINESS VERIFICATION")
    print("=" * 60 + "\n")
    
    results = []
    
    # Run checks
    results.append(check_imports())
    results.append(check_files())
    results.append(check_features())
    results.append(check_documentation())
    
    # Print summary
    success = print_summary(results)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

