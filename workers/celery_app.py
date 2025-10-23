"""
Celery Application for Background Job Processing
Enables async workflow generation and job queuing
"""

import os
import asyncio
from celery import Celery
from pathlib import Path

# Configure Celery
broker_url = os.getenv('CELERY_BROKER_URL', 'pyamqp://guest@localhost//')
backend_url = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

app = Celery(
    'architect_ai',
    broker=broker_url,
    backend=backend_url
)

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

@app.task(bind=True, name='architect_ai.generate_workflow')
def generate_workflow_async(self, meeting_notes_path: str, feature_name: str = None, config: dict = None):
    """
    Background task for workflow generation
    
    Args:
        meeting_notes_path: Path to meeting notes file
        feature_name: Optional feature name
        config: Configuration dict with API keys
    
    Returns:
        dict: Generation result
    """
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    
    from agents.universal_agent import run_universal_workflow
    
    # Update task state
    self.update_state(
        state='PROCESSING',
        meta={
            'step': 'initializing',
            'progress': 0,
            'total_steps': 8
        }
    )
    
    try:
        # Run the workflow
        result = asyncio.run(run_universal_workflow(
            meeting_notes_path,
            feature_name,
            config.get('openai_api_key') if config else None,
            config.get('gemini_api_key') if config else None
        ))
        
        # Return result
        return {
            'success': result.success,
            'errors': result.errors,
            'metadata': result.metadata,
            'message': 'Workflow completed successfully' if result.success else 'Workflow failed'
        }
        
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise


@app.task(bind=True, name='architect_ai.analyze_repository')
def analyze_repository_async(self, config: dict = None):
    """
    Background task for repository analysis only
    
    Args:
        config: Configuration dict with API keys
    
    Returns:
        dict: Repository analysis result
    """
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    
    from agents.universal_agent import UniversalArchitectAgent
    
    try:
        agent = UniversalArchitectAgent(config or {})
        result = asyncio.run(agent.analyze_repository())
        
        return {
            'success': True,
            'tech_stacks': result.tech_stacks,
            'architecture': result.architecture,
            'dependencies': result.dependencies
        }
        
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise


@app.task(bind=True, name='architect_ai.generate_diagrams')
def generate_diagrams_async(self, feature_requirements: dict, config: dict = None):
    """
    Background task for diagram generation only
    
    Args:
        feature_requirements: Feature requirements dict
        config: Configuration dict with API keys
    
    Returns:
        dict: Generated diagrams
    """
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    
    from agents.universal_agent import UniversalArchitectAgent
    
    try:
        agent = UniversalArchitectAgent(config or {})
        agent.feature_requirements = feature_requirements
        
        diagrams = asyncio.run(agent.generate_specific_diagrams())
        
        return {
            'success': True,
            'diagrams': diagrams
        }
        
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise


# Task routing
app.conf.task_routes = {
    'architect_ai.generate_workflow': {'queue': 'workflows'},
    'architect_ai.analyze_repository': {'queue': 'analysis'},
    'architect_ai.generate_diagrams': {'queue': 'diagrams'},
}

if __name__ == '__main__':
    app.start()

