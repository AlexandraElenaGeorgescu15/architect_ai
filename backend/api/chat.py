"""
Chat API endpoints for project-aware AI chat.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
import logging
from datetime import datetime

from backend.models.dto import ChatRequest, ChatResponse, ChatMessage
from backend.services.chat_service import get_chat_service
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter
from backend.core.cache import cached

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# =============================================================================
# Project Summary Models
# =============================================================================

class ComponentInfo(BaseModel):
    """Information about a project component."""
    name: str
    type: str  # "service", "component", "module", "api"
    description: str
    file_path: str


class ProjectSummary(BaseModel):
    """Summary of project knowledge for chat context."""
    project_name: str = "Architect.AI"
    indexed_files: int = 0
    tech_stack: List[str] = Field(default_factory=list)
    main_components: List[ComponentInfo] = Field(default_factory=list)
    patterns_detected: List[str] = Field(default_factory=list)
    knowledge_graph_stats: Dict[str, int] = Field(default_factory=dict)
    recent_files: List[str] = Field(default_factory=list)
    last_indexed: Optional[str] = None
    greeting_message: str = ""


# =============================================================================
# Project Summary Endpoint
# =============================================================================

@router.get("/summary", response_model=ProjectSummary)
async def get_project_summary(
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Get a summary of the TARGET PROJECT knowledge for chat context.
    
    IMPORTANT: This returns info about the USER'S PROJECT being analyzed,
    NOT about Architect.AI itself.
    
    Returns:
        ProjectSummary with indexed files, components, patterns, and KG stats.
        Used by the floating chat to display a contextual greeting.
    """
    try:
        from backend.services.rag_retriever import get_retriever
        from backend.services.knowledge_graph import get_builder as get_kg_builder
        from backend.services.pattern_mining import get_miner
        from backend.services.analysis_service import get_service as get_analysis_service
        from backend.core.config import settings
        from backend.utils.tool_detector import get_user_project_directories, detect_tool_directory
        from pathlib import Path
        import os
        
        # =================================================================
        # Get ALL user projects (excludes Architect.AI and utility folders)
        # =================================================================
        user_project_dirs = get_user_project_directories()
        tool_dir = detect_tool_directory()
        
        # Folders that should never appear as user projects
        EXCLUDED_FOLDER_NAMES = {
            'agents', 'components', 'utils', 'shared', 'common', 'lib', 'libs',
            'node_modules', '__pycache__', '.git', 'dist', 'build', 'bin', 'obj',
            'archive', 'backup', 'temp', 'tmp', 'cache', '.cache', 'logs',
        }
        
        # Filter out tool directory and excluded folders
        user_project_dirs = [
            d for d in user_project_dirs 
            if d != tool_dir 
            and 'architect_ai' not in str(d).lower()
            and d.name.lower() not in EXCLUDED_FOLDER_NAMES
        ]
        
        # Build project name from all indexed projects
        if len(user_project_dirs) == 1:
            project_name = user_project_dirs[0].name
            target_project = user_project_dirs[0]
        elif len(user_project_dirs) > 1:
            project_name = f"{len(user_project_dirs)} Projects"
            target_project = user_project_dirs[0]  # Use first for recent files
        else:
            project_name = "No Projects"
            target_project = None
        
        logger.info(f"📂 [CHAT_SUMMARY] Getting summary for {len(user_project_dirs)} user projects")
        
        # Get RAG stats
        rag_retriever = get_retriever()
        indexed_files = 0
        recent_files = []
        last_indexed = None
        
        try:
            # Get index stats from ChromaDB
            index_path = Path(settings.rag_index_path if hasattr(settings, 'rag_index_path') else "rag/index")
            if index_path.exists():
                # Count files in ChromaDB collection
                if hasattr(rag_retriever, 'collection') and rag_retriever.collection:
                    indexed_files = rag_retriever.collection.count()
                
                # Get last modified time
                try:
                    index_stat = index_path.stat()
                    last_indexed = datetime.fromtimestamp(index_stat.st_mtime).isoformat()
                except Exception:
                    pass
                
                # Get recent files from TARGET PROJECT (not Architect.AI)
                if target_project and target_project.exists():
                    all_files = []
                    for ext in ['*.py', '*.ts', '*.tsx', '*.java', '*.cs', '*.go', '*.rs']:
                        all_files.extend(target_project.rglob(ext))
                    
                    # Sort by modification time
                    all_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    recent_files = [str(f.relative_to(target_project)) for f in all_files[:5]]
        except Exception as e:
            logger.warning(f"Could not get RAG stats: {e}")
        
        # Get Knowledge Graph stats
        kg_stats = {"nodes": 0, "edges": 0, "components": 0}
        kg_builder = get_kg_builder()
        try:
            stats = kg_builder.get_stats()
            if stats:
                kg_stats = {
                    "nodes": stats.get("nodes", 0),
                    "edges": stats.get("edges", 0),
                    "components": stats.get("components", 0)
                }
        except Exception as e:
            logger.warning(f"Could not get KG stats: {e}")
        
        # Get main components from KG
        main_components = []
        try:
            graph_data = kg_builder.get_graph()
            if graph_data and "nodes" in graph_data:
                nodes = graph_data.get("nodes", [])
                
                # Sort by type priority: services > components > modules
                type_priority = {"service": 1, "class": 2, "function": 3, "module": 4}
                sorted_nodes = sorted(
                    nodes,
                    key=lambda n: type_priority.get(n.get("type", "").lower(), 5)
                )
                
                for node in sorted_nodes[:8]:  # Top 8 components
                    node_name = node.get("name", "Unknown")
                    node_type = node.get("type", "component")
                    file_path = node.get("file_path", "")
                    
                    # Generate description based on name
                    description = _infer_component_description(node_name)
                    
                    main_components.append(ComponentInfo(
                        name=node_name,
                        type=node_type.lower(),
                        description=description,
                        file_path=file_path
                    ))
        except Exception as e:
            logger.warning(f"Could not get components from KG: {e}")
        
        # =================================================================
        # Get ACTUAL detected patterns from Pattern Mining (NOT hardcoded!)
        # =================================================================
        patterns_detected = []
        try:
            miner = get_miner()
            
            # Get actual pattern mining results if available
            if miner.patterns_detected:
                # Extract unique pattern names
                pattern_names = set()
                for pm in miner.patterns_detected:
                    pattern_names.add(pm.pattern_name)
                patterns_detected = list(pattern_names)[:6]  # Top 6 patterns
            
            # If no patterns detected yet, try to get from cache
            if not patterns_detected:
                analysis_service = get_analysis_service()
                cached_analysis = await analysis_service.get_current_patterns()
                if cached_analysis and "patterns" in cached_analysis:
                    patterns = cached_analysis.get("patterns", {})
                    for pattern_name, count in patterns.items():
                        if count > 0:
                            patterns_detected.append(pattern_name)
                    patterns_detected = patterns_detected[:6]
            
            logger.info(f"🔍 [CHAT_SUMMARY] Found {len(patterns_detected)} patterns")
        except Exception as e:
            logger.warning(f"Could not get patterns: {e}")
        
        # =================================================================
        # Determine tech stack from ALL USER PROJECTS
        # =================================================================
        from backend.utils.target_project import detect_tech_stack
        
        tech_stack = []
        for proj_dir in user_project_dirs:
            if proj_dir and proj_dir.exists():
                proj_tech = detect_tech_stack(proj_dir)
                for tech in proj_tech:
                    if tech not in tech_stack:
                        tech_stack.append(tech)
        
        if not tech_stack:
            tech_stack = ["Unknown"]
        
        # =================================================================
        # Build greeting message referencing ALL USER PROJECTS
        # =================================================================
        greeting_parts = []
        
        if len(user_project_dirs) > 1:
            project_names = [d.name for d in user_project_dirs[:5]]
            greeting_parts.append(f"Hello! I'm Architect.AI. I've analyzed **{len(user_project_dirs)} projects**:")
            greeting_parts.append(f"📂 **Projects:** {', '.join(project_names)}")
        else:
            greeting_parts.append(f"Hello! I'm Architect.AI. I've analyzed **{project_name}**:")
        
        if indexed_files > 0:
            greeting_parts.append(f"📁 **{indexed_files} chunks** indexed ({', '.join(tech_stack[:4])})")
        else:
            greeting_parts.append(f"\n⚠️ Project not indexed yet. Please run 'Index Project' first.")
        
        if main_components:
            component_names = [c.name for c in main_components[:4]]
            greeting_parts.append(f"🧩 **Key components:** {', '.join(component_names)}")
        
        if kg_stats.get("nodes", 0) > 0:
            greeting_parts.append(f"📊 **Knowledge Graph:** {kg_stats['nodes']} nodes, {kg_stats['edges']} relationships")
        
        if patterns_detected:
            greeting_parts.append(f"🔍 **Patterns detected:** {', '.join(patterns_detected[:3])}")
        
        if recent_files:
            greeting_parts.append(f"📝 **Recent files:** {', '.join([Path(f).name for f in recent_files[:3]])}")
        
        if len(user_project_dirs) > 1:
            greeting_parts.append(f"\nAsk me anything about your **{len(user_project_dirs)} projects**!")
        else:
            greeting_parts.append(f"\nAsk me anything about **{project_name}**!")
        
        greeting_message = "\n".join(greeting_parts)
        
        return ProjectSummary(
            project_name=project_name,
            indexed_files=indexed_files,
            tech_stack=tech_stack,
            main_components=main_components,
            patterns_detected=patterns_detected,
            knowledge_graph_stats=kg_stats,
            recent_files=recent_files,
            last_indexed=last_indexed,
            greeting_message=greeting_message
        )
        
    except Exception as e:
        logger.error(f"Error getting project summary: {e}", exc_info=True)
        # Return minimal summary on error
        return ProjectSummary(
            greeting_message="Hello! I'm Architect.AI. Please index your project to get started!"
        )




def _infer_component_description(name: str) -> str:
    """Infer a description based on component name patterns."""
    name_lower = name.lower()
    
    if "service" in name_lower:
        if "generation" in name_lower:
            return "Handles artifact generation with model routing"
        elif "validation" in name_lower:
            return "Quality scoring and validation logic"
        elif "context" in name_lower:
            return "Builds comprehensive context for AI"
        elif "chat" in name_lower:
            return "Project-aware AI chat functionality"
        elif "model" in name_lower:
            return "Model registry and routing"
        elif "training" in name_lower:
            return "Fine-tuning job management"
        else:
            return "Core service component"
    elif "builder" in name_lower:
        return "Assembles and constructs data structures"
    elif "retriever" in name_lower:
        return "Retrieval and search functionality"
    elif "miner" in name_lower:
        return "Pattern detection and analysis"
    elif "client" in name_lower:
        return "External API client"
    elif "router" in name_lower:
        return "Request routing and dispatch"
    elif "controller" in name_lower:
        return "API endpoint handler"
    elif "validator" in name_lower:
        return "Input/output validation"
    elif "fixer" in name_lower:
        return "Auto-repair and correction"
    elif "cleaner" in name_lower:
        return "Content cleanup and sanitization"
    else:
        return "Project component"


@router.post("/message", response_model=ChatResponse)
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    body: ChatRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Send a message to the AI chat.
    
    Request body:
    {
        "message": "What is the architecture of this project?",
        "conversation_history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"}
        ],
        "include_project_context": true
    }
    """
    service = get_chat_service()
    
    try:
        # Generate response
        response_content = ""
        model_used = "unknown"
        provider = "unknown"
        
        async for chunk in service.chat(
            message=body.message,
            conversation_history=body.conversation_history,
            include_project_context=body.include_project_context,
            stream=False,
            session_id=body.session_id
        ):
            if chunk.get("type") == "complete":
                response_content = chunk.get("content", "")
                model_used = chunk.get("model", "unknown")
                provider = chunk.get("provider", "unknown")
                break
            elif chunk.get("type") == "error":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=chunk.get("error", "Chat generation failed")
                )
        
        return ChatResponse(
            message=response_content,
            model_used=model_used,
            provider=provider,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat generation failed: {str(e)}"
        )


@router.post("/stream")
async def send_message_stream(
    request: ChatRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Send a message with streaming response.
    """
    service = get_chat_service()
    
    async def generate_stream():
        """Stream chat response."""
        try:
            async for chunk in service.chat(
                message=request.message,
                conversation_history=request.conversation_history,
                include_project_context=request.include_project_context,
                stream=True,
                session_id=request.session_id
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            logger.error(f"Error in streaming chat: {e}", exc_info=True)
            error_chunk = {
                "type": "error",
                "content": f"Error: {str(e)}",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

