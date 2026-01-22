"""
Agentic Chat Service - AI that can autonomously search and explore the codebase.

This extends the basic chat with tool-use capabilities, allowing the AI to:
1. Search the codebase when it needs more context
2. Read specific files
3. Query the knowledge graph
4. Explore project structure
5. Get pattern mining insights

The AI decides when to use tools and iterates until it has enough info to answer.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, AsyncGenerator
import logging
import json
import asyncio
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.rag_retriever import get_retriever
from backend.services.knowledge_graph import get_builder as get_kg_builder
from backend.services.pattern_mining import get_miner
from backend.core.config import settings
from backend.core.logger import get_logger
from backend.utils.tool_detector import get_user_project_directories

logger = get_logger(__name__)

# Tool definitions for the AI
AGENT_TOOLS = [
    {
        "name": "search_codebase",
        "description": "Search through the indexed codebase using semantic search. Use this when you need to find code related to a specific topic, feature, or concept.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query - describe what you're looking for (e.g., 'user authentication logic', 'database connection handling', 'API endpoints for orders')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a specific file. Use this when you know which file you need to examine.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file (can be relative like 'src/services/auth.service.ts' or just the filename)"
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum lines to read (default: 200)",
                    "default": 200
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "list_files",
        "description": "List files in a directory. Use this to explore project structure.",
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory path to list (e.g., 'src/components', 'Controllers'). Use '.' for project root."
                },
                "pattern": {
                    "type": "string",
                    "description": "Optional glob pattern to filter files (e.g., '*.ts', '*.cs')",
                    "default": "*"
                }
            },
            "required": ["directory"]
        }
    },
    {
        "name": "query_knowledge_graph",
        "description": "Query the knowledge graph to find relationships between components, classes, and functions.",
        "parameters": {
            "type": "object",
            "properties": {
                "component_name": {
                    "type": "string",
                    "description": "Name of the component/class/function to find relationships for"
                },
                "relationship_type": {
                    "type": "string",
                    "description": "Type of relationship to find: 'imports', 'calls', 'inherits', 'depends_on', or 'all'",
                    "default": "all"
                }
            },
            "required": ["component_name"]
        }
    },
    {
        "name": "get_project_patterns",
        "description": "Get detected design patterns, code smells, or security issues in the codebase.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Category to retrieve: 'patterns', 'code_smells', 'security', or 'all'",
                    "default": "all"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_project_overview",
        "description": "Get a comprehensive overview of the entire project - all files, classes, services, and architecture. Use this to get Wikipedia-like knowledge about the codebase.",
        "parameters": {
            "type": "object",
            "properties": {
                "include_file_list": {
                    "type": "boolean",
                    "description": "Include full list of important files (default: true)",
                    "default": True
                },
                "include_entities": {
                    "type": "boolean",
                    "description": "Include list of all classes, services, components (default: true)",
                    "default": True
                }
            },
            "required": []
        }
    }
]

# Write tools - only available when write_mode is enabled
AGENT_WRITE_TOOLS = [
    {
        "name": "update_artifact",
        "description": "Update an existing artifact's content. Use this to modify generated diagrams, code, or documentation.",
        "parameters": {
            "type": "object",
            "properties": {
                "artifact_id": {
                    "type": "string",
                    "description": "ID of the artifact to update (e.g., 'mermaid_erd', 'code_prototype')"
                },
                "new_content": {
                    "type": "string",
                    "description": "The new content for the artifact"
                },
                "reason": {
                    "type": "string",
                    "description": "Brief explanation of why this change is being made"
                }
            },
            "required": ["artifact_id", "new_content", "reason"]
        }
    },
    {
        "name": "create_artifact",
        "description": "Create a new artifact from chat analysis. Use this to generate new diagrams or documentation based on discussion.",
        "parameters": {
            "type": "object",
            "properties": {
                "artifact_type": {
                    "type": "string",
                    "description": "Type of artifact to create (e.g., 'mermaid_erd', 'mermaid_flowchart', 'code_prototype')"
                },
                "content": {
                    "type": "string",
                    "description": "The content for the new artifact"
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of what this artifact represents"
                }
            },
            "required": ["artifact_type", "content"]
        }
    },
    {
        "name": "save_to_outputs",
        "description": "Save analysis or generated content to the outputs folder. Use for saving summaries, notes, or analysis.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name for the output file (e.g., 'auth_analysis.md', 'api_review.txt')"
                },
                "content": {
                    "type": "string",
                    "description": "Content to save"
                },
                "format": {
                    "type": "string",
                    "description": "File format: 'markdown', 'text', 'json'",
                    "default": "markdown"
                }
            },
            "required": ["filename", "content"]
        }
    }
]


class AgenticChatService:
    """
    Agentic chat service that can autonomously explore the codebase.
    
    The AI has access to tools and decides when to use them based on the user's question.
    It can iterate multiple times until it has enough information to provide a good answer.
    """
    
    MAX_TOOL_ITERATIONS = 5  # Prevent infinite loops
    
    def __init__(self):
        self.rag_retriever = get_retriever()
        self.kg_builder = get_kg_builder()
        self.pattern_miner = get_miner()
        self.user_projects = get_user_project_directories()
        
        logger.info("Agentic Chat Service initialized with tool-use capabilities")
    
    # =========================================================================
    # TOOL IMPLEMENTATIONS
    # =========================================================================
    
    async def _tool_search_codebase(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the codebase using RAG."""
        try:
            results = await self.rag_retriever.retrieve(query=query, k=max_results)
            
            if not results:
                return {"success": False, "message": "No results found", "results": []}
            
            formatted_results = []
            for r in results[:max_results]:
                file_path = r.get('metadata', {}).get('file_path') or r.get('metadata', {}).get('path', 'unknown')
                content = r.get('content', '')[:1500]  # Limit content size
                score = r.get('score', r.get('relevance', 0))
                
                formatted_results.append({
                    "file": file_path,
                    "content": content,
                    "relevance": round(score, 3) if isinstance(score, float) else score
                })
            
            return {
                "success": True,
                "result_count": len(formatted_results),
                "results": formatted_results
            }
        except Exception as e:
            logger.error(f"Search codebase error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _tool_read_file(self, file_path: str, max_lines: int = 200) -> Dict[str, Any]:
        """Read a specific file's contents."""
        try:
            # Search across all user projects
            found_path = None
            
            for proj_dir in self.user_projects:
                # Try exact path
                full_path = proj_dir / file_path
                if full_path.exists():
                    found_path = full_path
                    break
                
                # Try searching for the filename
                for match in proj_dir.rglob(f"**/{Path(file_path).name}"):
                    if match.is_file():
                        found_path = match
                        break
                
                if found_path:
                    break
            
            if not found_path or not found_path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            
            # Read file contents
            try:
                content = found_path.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')
                
                if len(lines) > max_lines:
                    content = '\n'.join(lines[:max_lines])
                    truncated = True
                else:
                    truncated = False
                
                return {
                    "success": True,
                    "file_path": str(found_path),
                    "content": content,
                    "total_lines": len(lines),
                    "truncated": truncated
                }
            except Exception as e:
                return {"success": False, "error": f"Could not read file: {e}"}
                
        except Exception as e:
            logger.error(f"Read file error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _tool_list_files(self, directory: str, pattern: str = "*") -> Dict[str, Any]:
        """List files in a directory."""
        try:
            all_files = []
            
            for proj_dir in self.user_projects:
                # Determine target directory
                if directory == "." or directory == "":
                    target_dir = proj_dir
                else:
                    target_dir = proj_dir / directory
                    if not target_dir.exists():
                        # Try finding the directory
                        for match in proj_dir.rglob(f"**/{directory}"):
                            if match.is_dir():
                                target_dir = match
                                break
                
                if not target_dir.exists():
                    continue
                
                # List files
                for item in target_dir.glob(pattern):
                    if item.is_file():
                        rel_path = str(item.relative_to(proj_dir))
                        all_files.append({
                            "name": item.name,
                            "path": rel_path,
                            "project": proj_dir.name,
                            "size": item.stat().st_size,
                            "type": item.suffix
                        })
                    elif item.is_dir():
                        all_files.append({
                            "name": item.name + "/",
                            "path": str(item.relative_to(proj_dir)) + "/",
                            "project": proj_dir.name,
                            "type": "directory"
                        })
            
            # Sort by name
            all_files.sort(key=lambda x: x["name"])
            
            return {
                "success": True,
                "directory": directory,
                "file_count": len([f for f in all_files if f.get("type") != "directory"]),
                "dir_count": len([f for f in all_files if f.get("type") == "directory"]),
                "files": all_files[:50]  # Limit to 50 items
            }
        except Exception as e:
            logger.error(f"List files error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _tool_query_knowledge_graph(self, component_name: str, relationship_type: str = "all") -> Dict[str, Any]:
        """Query the knowledge graph for component relationships."""
        try:
            graph_data = self.kg_builder.get_graph()
            
            if not graph_data or "nodes" not in graph_data:
                return {"success": False, "message": "Knowledge graph not built yet"}
            
            nodes = graph_data.get("nodes", [])
            edges = graph_data.get("edges", [])
            
            # Find matching nodes
            matching_nodes = []
            component_lower = component_name.lower()
            
            for node in nodes:
                node_name = node.get("name", "").lower()
                if component_lower in node_name or node_name in component_lower:
                    matching_nodes.append(node)
            
            if not matching_nodes:
                return {
                    "success": True,
                    "message": f"No components found matching '{component_name}'",
                    "suggestions": [n.get("name") for n in nodes[:10]]
                }
            
            # Find relationships
            relationships = {
                "incoming": [],  # Things that depend on this component
                "outgoing": []   # Things this component depends on
            }
            
            node_names = [n.get("name", "").lower() for n in matching_nodes]
            
            for edge in edges:
                source = edge.get("source", "").lower()
                target = edge.get("target", "").lower()
                rel_type = edge.get("type", edge.get("relationship", "relates_to"))
                
                if source in node_names:
                    relationships["outgoing"].append({
                        "target": edge.get("target"),
                        "type": rel_type
                    })
                if target in node_names:
                    relationships["incoming"].append({
                        "source": edge.get("source"),
                        "type": rel_type
                    })
            
            return {
                "success": True,
                "component": component_name,
                "matches": [{"name": n.get("name"), "type": n.get("type"), "file": n.get("file", "")} for n in matching_nodes[:5]],
                "relationships": relationships,
                "incoming_count": len(relationships["incoming"]),
                "outgoing_count": len(relationships["outgoing"])
            }
        except Exception as e:
            logger.error(f"Query KG error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _tool_get_project_patterns(self, category: str = "all") -> Dict[str, Any]:
        """Get detected patterns from pattern mining."""
        try:
            report = self.pattern_miner.get_report()
            
            if not report or report.get("status") == "not_run":
                return {"success": False, "message": "Pattern mining has not been run yet"}
            
            result = {"success": True}
            
            if category in ["all", "patterns"]:
                patterns = report.get("patterns_detected", [])
                result["patterns"] = {
                    "count": len(patterns),
                    "items": [
                        {"name": p.get("pattern_name"), "file": p.get("file_path")}
                        for p in patterns[:10]
                    ]
                }
            
            if category in ["all", "code_smells"]:
                smells = report.get("code_smells", [])
                result["code_smells"] = {
                    "count": len(smells),
                    "items": [
                        {"type": s.get("smell_type"), "file": s.get("file_path"), "description": s.get("description", "")[:100]}
                        for s in smells[:10]
                    ]
                }
            
            if category in ["all", "security"]:
                issues = report.get("security_issues", [])
                result["security_issues"] = {
                    "count": len(issues),
                    "items": [
                        {"type": i.get("issue_type"), "severity": i.get("severity"), "file": i.get("file_path")}
                        for i in issues[:10]
                    ]
                }
            
            return result
        except Exception as e:
            logger.error(f"Get patterns error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _tool_get_project_overview(
        self, 
        include_file_list: bool = True, 
        include_entities: bool = True
    ) -> Dict[str, Any]:
        """Get comprehensive project overview - Wikipedia-like knowledge."""
        try:
            from backend.services.universal_context import get_universal_context_service
            from pathlib import Path
            
            universal_service = get_universal_context_service()
            universal_ctx = await universal_service.get_universal_context()
            
            if not universal_ctx:
                return {"success": False, "message": "Universal context not available. Please rebuild it."}
            
            result = {
                "success": True,
                "overview": {}
            }
            
            # Project info
            dirs = universal_ctx.get("project_directories", [])
            result["overview"]["projects"] = [Path(d).name for d in dirs]
            result["overview"]["total_files"] = universal_ctx.get("total_files", 0)
            result["overview"]["built_at"] = universal_ctx.get("built_at", "unknown")
            
            # Key entities (classes, services, components)
            if include_entities:
                key_entities = universal_ctx.get("key_entities", [])
                entities_by_type = {}
                for entity in key_entities:
                    etype = entity.get("type", "other")
                    if etype not in entities_by_type:
                        entities_by_type[etype] = []
                    entities_by_type[etype].append({
                        "name": entity.get("name"),
                        "file": Path(entity.get("file", "")).name if entity.get("file") else ""
                    })
                
                result["overview"]["entities"] = {
                    "total_count": len(key_entities),
                    "by_type": {
                        etype: {"count": len(items), "items": items[:20]}
                        for etype, items in entities_by_type.items()
                    }
                }
            
            # Important files
            if include_file_list:
                proj_map = universal_ctx.get("project_map", {})
                key_files = proj_map.get("key_files", [])
                result["overview"]["important_files"] = [Path(f).name for f in key_files[:30]]
                
                # File types breakdown
                file_types = proj_map.get("file_types", {})
                result["overview"]["file_types"] = {
                    ext: count for ext, count in sorted(
                        file_types.items(), key=lambda x: x[1], reverse=True
                    )[:15]
                }
            
            # Knowledge graph stats
            kg = universal_ctx.get("knowledge_graph", {})
            if kg:
                result["overview"]["knowledge_graph"] = {
                    "nodes": kg.get("total_nodes", 0),
                    "edges": kg.get("total_edges", 0)
                }
            
            # Patterns summary
            patterns = universal_ctx.get("patterns", {})
            if patterns:
                result["overview"]["patterns"] = {
                    "total": len(patterns.get("patterns", [])),
                    "code_smells": len(patterns.get("code_smells", [])),
                    "security_issues": len(patterns.get("security_issues", []))
                }
            
            logger.info(f"[AGENTIC_CHAT] Project overview generated: {result['overview']['total_files']} files")
            return result
            
        except Exception as e:
            logger.error(f"Get project overview error: {e}")
            return {"success": False, "error": str(e)}
    
    # =========================================================================
    # WRITE TOOL IMPLEMENTATIONS (only available in write_mode)
    # =========================================================================
    
    async def _tool_update_artifact(self, artifact_id: str, new_content: str, reason: str) -> Dict[str, Any]:
        """Update an existing artifact's content."""
        try:
            from backend.services.generation_service import get_service as get_gen_service
            from backend.services.version_service import get_version_service
            
            version_service = get_version_service()
            
            # Check if artifact exists
            if artifact_id not in version_service.versions:
                return {
                    "success": False, 
                    "error": f"Artifact '{artifact_id}' not found",
                    "available_artifacts": list(version_service.versions.keys())[:10]
                }
            
            # Create new version with updated content
            version_service.create_version(
                artifact_id=artifact_id,
                artifact_type=artifact_id,
                content=new_content,
                metadata={
                    "updated_by": "agentic_chat",
                    "update_reason": reason,
                    "update_timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"[AGENTIC_CHAT] Updated artifact: {artifact_id}, reason: {reason}")
            
            return {
                "success": True,
                "artifact_id": artifact_id,
                "message": f"Artifact '{artifact_id}' updated successfully",
                "reason": reason
            }
        except Exception as e:
            logger.error(f"Update artifact error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _tool_create_artifact(self, artifact_type: str, content: str, description: str = "") -> Dict[str, Any]:
        """Create a new artifact from chat analysis."""
        try:
            from backend.services.version_service import get_version_service
            
            version_service = get_version_service()
            
            # Generate a unique ID if this is a completely new type
            artifact_id = f"chat_{artifact_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create the artifact as a version
            version_service.create_version(
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                content=content,
                metadata={
                    "created_by": "agentic_chat",
                    "description": description,
                    "created_timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"[AGENTIC_CHAT] Created artifact: {artifact_id}, type: {artifact_type}")
            
            return {
                "success": True,
                "artifact_id": artifact_id,
                "artifact_type": artifact_type,
                "message": f"Created new artifact '{artifact_id}'",
                "description": description
            }
        except Exception as e:
            logger.error(f"Create artifact error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _tool_save_to_outputs(self, filename: str, content: str, format: str = "markdown") -> Dict[str, Any]:
        """Save content to the outputs folder."""
        try:
            from backend.core.config import settings
            
            # Ensure filename is safe
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            if not safe_filename:
                safe_filename = f"chat_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Add extension if missing
            ext_map = {"markdown": ".md", "text": ".txt", "json": ".json"}
            expected_ext = ext_map.get(format, ".txt")
            if not safe_filename.endswith(expected_ext):
                safe_filename += expected_ext
            
            # Save to outputs folder
            outputs_dir = Path(settings.base_path) / "outputs" / "chat_analysis"
            outputs_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = outputs_dir / safe_filename
            
            # Format content based on type
            if format == "json":
                try:
                    content = json.dumps(json.loads(content), indent=2)
                except json.JSONDecodeError:
                    content = json.dumps({"content": content}, indent=2)
            
            output_path.write_text(content, encoding="utf-8")
            
            logger.info(f"[AGENTIC_CHAT] Saved to outputs: {output_path}")
            
            return {
                "success": True,
                "filename": safe_filename,
                "path": str(output_path.relative_to(settings.base_path)),
                "message": f"Saved to {output_path.name}"
            }
        except Exception as e:
            logger.error(f"Save to outputs error: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any], write_mode: bool = False) -> Dict[str, Any]:
        """Execute a tool by name with given arguments."""
        # Read-only tools (always available)
        tool_map = {
            "search_codebase": self._tool_search_codebase,
            "read_file": self._tool_read_file,
            "list_files": self._tool_list_files,
            "query_knowledge_graph": self._tool_query_knowledge_graph,
            "get_project_patterns": self._tool_get_project_patterns,
            "get_project_overview": self._tool_get_project_overview
        }
        
        # Write tools (only available when write_mode is enabled)
        write_tool_map = {
            "update_artifact": self._tool_update_artifact,
            "create_artifact": self._tool_create_artifact,
            "save_to_outputs": self._tool_save_to_outputs
        }
        
        # Check if it's a write tool
        if tool_name in write_tool_map:
            if not write_mode:
                return {
                    "success": False, 
                    "error": f"Write tool '{tool_name}' requires write mode to be enabled. The user can enable this in the chat settings."
                }
            tool_map[tool_name] = write_tool_map[tool_name]
        
        if tool_name not in tool_map:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        tool_func = tool_map[tool_name]
        return await tool_func(**arguments)
    
    # =========================================================================
    # AGENTIC CHAT FLOW
    # =========================================================================
    
    async def chat(
        self,
        message: str,
        conversation_history: Optional[List[Any]] = None,
        session_id: Optional[str] = None,
        write_mode: bool = False,
        folder_id: Optional[str] = None,
        meeting_notes_content: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Agentic chat that can use tools to find information.
        
        Flow:
        1. Send user message + available tools to LLM
        2. If LLM wants to use a tool, execute it and add result to context
        3. Repeat until LLM provides final answer (max 5 iterations)
        4. Stream the final response
        
        Args:
            message: User's message
            conversation_history: Previous conversation messages
            session_id: Optional session identifier
            write_mode: If True, enables write tools (update_artifact, create_artifact, save_to_outputs)
            folder_id: Optional meeting notes folder ID for context
            meeting_notes_content: Optional meeting notes content to include
        """
        from backend.core.config import settings
        import httpx
        
        logger.info(f"🤖 [AGENTIC_CHAT] ========== AGENTIC CHAT REQUEST STARTED ==========")
        logger.info(f"🤖 [AGENTIC_CHAT] Step 1: Initializing agentic chat")
        logger.info(f"🤖 [AGENTIC_CHAT] Step 1.1: Message length={len(message)}, write_mode={write_mode}, session_id={session_id}")
        logger.info(f"🤖 [AGENTIC_CHAT] Step 1.2: folder_id={folder_id}, has_meeting_notes={bool(meeting_notes_content)}")
        
        # Load meeting notes if folder_id provided
        logger.info(f"🤖 [AGENTIC_CHAT] Step 2: Loading meeting notes")
        notes_context = meeting_notes_content or ""
        if folder_id and not notes_context:
            logger.info(f"🤖 [AGENTIC_CHAT] Step 2.1: Loading meeting notes from folder_id={folder_id}")
            try:
                from backend.services.meeting_notes_service import get_meeting_notes_service
                notes_service = get_meeting_notes_service()
                notes = notes_service.get_notes_by_folder(folder_id)
                if notes:
                    notes_context = "\n\n---\n\n".join([
                        f"**{n.get('title', 'Meeting Note')}**\n{n.get('content', '')}"
                        for n in notes
                    ])
                    logger.info(f"🤖 [AGENTIC_CHAT] Step 2.2: Loaded {len(notes)} meeting notes from folder: {folder_id} (total_length={len(notes_context)})")
                else:
                    logger.warning(f"🤖 [AGENTIC_CHAT] Step 2.2: No notes found in folder {folder_id}")
            except Exception as e:
                logger.warning(f"🤖 [AGENTIC_CHAT] Step 2.2: Could not load meeting notes from folder {folder_id}: {e}", exc_info=True)
        elif notes_context:
            logger.info(f"🤖 [AGENTIC_CHAT] Step 2.1: Using provided meeting notes (length={len(notes_context)})")
        else:
            logger.info(f"🤖 [AGENTIC_CHAT] Step 2.1: No meeting notes provided")
        
        # Load Universal Context for comprehensive project knowledge (Wikipedia-like)
        logger.info(f"🤖 [AGENTIC_CHAT] Step 3: Loading universal context")
        project_overview = ""
        try:
            from backend.services.universal_context import get_universal_context_service
            from pathlib import Path
            
            logger.info(f"🤖 [AGENTIC_CHAT] Step 3.1: Getting universal context service")
            universal_service = get_universal_context_service()
            logger.info(f"🤖 [AGENTIC_CHAT] Step 3.2: Fetching universal context...")
            universal_ctx = await universal_service.get_universal_context()
            
            if universal_ctx:
                logger.info(f"🤖 [AGENTIC_CHAT] Step 3.3: Universal context retrieved, building overview")
                overview_parts = []
                
                # Project directories
                dirs = universal_ctx.get("project_directories", [])
                if dirs:
                    dir_names = [Path(d).name for d in dirs]
                    overview_parts.append(f"**Projects:** {', '.join(dir_names)}")
                    overview_parts.append(f"**Total Files:** {universal_ctx.get('total_files', 'unknown')}")
                    logger.info(f"🤖 [AGENTIC_CHAT] Step 3.3.1: Found {len(dirs)} project directories, {universal_ctx.get('total_files', 0)} total files")
                
                # Key entities (classes, services, components)
                key_entities = universal_ctx.get("key_entities", [])
                if key_entities:
                    overview_parts.append("\n**Key Components:**")
                    for entity in key_entities[:25]:  # Top 25
                        entity_type = entity.get('type', 'unknown')
                        entity_name = entity.get('name', 'unknown')
                        entity_file = Path(entity.get('file', '')).name if entity.get('file') else ''
                        overview_parts.append(f"- `{entity_name}` ({entity_type}) in {entity_file}")
                    logger.info(f"🤖 [AGENTIC_CHAT] Step 3.3.2: Found {len(key_entities)} key entities (including top 25 in overview)")
                
                # Project structure
                proj_map = universal_ctx.get("project_map", {})
                if proj_map and proj_map.get("key_files"):
                    overview_parts.append("\n**Important Files:**")
                    key_files = proj_map.get("key_files", [])[:15]
                    for kf in key_files:
                        overview_parts.append(f"- `{Path(kf).name}`")
                    logger.info(f"🤖 [AGENTIC_CHAT] Step 3.3.3: Found {len(key_files)} key files")
                
                project_overview = "\n".join(overview_parts)
                logger.info(f"🤖 [AGENTIC_CHAT] Step 3.4: Universal context loaded: {len(key_entities)} entities, {universal_ctx.get('total_files', 0)} files, overview_length={len(project_overview)}")
            else:
                logger.warning(f"🤖 [AGENTIC_CHAT] Step 3.3: Universal context returned None")
        except Exception as e:
            logger.warning(f"🤖 [AGENTIC_CHAT] Step 3.3: Could not load universal context: {e}", exc_info=True)
        
        # Build conversation context (include meeting notes AND project overview)
        logger.info(f"🤖 [AGENTIC_CHAT] Step 4: Building conversation messages")
        logger.info(f"🤖 [AGENTIC_CHAT] Step 4.1: Building message list with notes_length={len(notes_context)}, overview_length={len(project_overview)}, history_length={len(conversation_history) if conversation_history else 0}")
        messages = self._build_messages(message, conversation_history, notes_context, project_overview)
        logger.info(f"🤖 [AGENTIC_CHAT] Step 4.2: Built {len(messages)} messages for LLM")
        tool_results = []
        iterations = 0
        logger.info(f"🤖 [AGENTIC_CHAT] Step 5: Starting agentic iteration loop (max 5 iterations)")
        
        # Determine which tools to expose based on write_mode
        available_tools = AGENT_TOOLS.copy()
        if write_mode:
            available_tools.extend(AGENT_WRITE_TOOLS)
            logger.info("[AGENTIC_CHAT] Write mode enabled - write tools available")
        
        # Agentic loop - let AI decide when to use tools
        while iterations < self.MAX_TOOL_ITERATIONS:
            iterations += 1
            logger.info(f"🤖 [AGENTIC_CHAT] Step 5.{iterations}: Starting iteration {iterations}/{self.MAX_TOOL_ITERATIONS}")
            
            # Call LLM with tools
            try:
                logger.info(f"🤖 [AGENTIC_CHAT] Step 5.{iterations}.1: Calling LLM with {len(available_tools)} available tools, {len(tool_results)} previous tool results")
                tool_call = await self._call_llm_with_tools(messages, tool_results, available_tools)
                
                if tool_call is None:
                    # No tool call - AI is ready to answer
                    logger.info(f"🤖 [AGENTIC_CHAT] Step 5.{iterations}.2: LLM returned no tool call - ready to answer")
                    break
                
                # Execute the tool
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("arguments", {})
                
                logger.info(f"🤖 [AGENTIC_CHAT] Step 5.{iterations}.2: LLM requested tool: {tool_name}")
                logger.info(f"🤖 [AGENTIC_CHAT] Step 5.{iterations}.2.1: Tool arguments: {json.dumps(tool_args)[:200]}...")
                
                # Yield status update
                is_write_tool = tool_name in ["update_artifact", "create_artifact", "save_to_outputs"]
                status_icon = "✏️" if is_write_tool else "🔍"
                logger.info(f"🤖 [AGENTIC_CHAT] Step 5.{iterations}.3: Executing tool: {tool_name} (write_mode={is_write_tool})")
                yield {
                    "type": "status",
                    "content": f"{status_icon} {'Writing' if is_write_tool else 'Searching'}: {tool_name}...",
                    "tool": tool_name,
                    "is_write_tool": is_write_tool
                }
                
                # Execute tool (pass write_mode for write tools)
                result = await self.execute_tool(tool_name, tool_args, write_mode=write_mode)
                logger.info(f"🤖 [AGENTIC_CHAT] Step 5.{iterations}.4: Tool execution complete: success={result.get('success', True)}, result_length={len(json.dumps(result))}")
                
                tool_results.append({
                    "tool": tool_name,
                    "arguments": tool_args,
                    "result": result,
                    "is_write_tool": is_write_tool
                })
                
                logger.info(f"🤖 [AGENTIC_CHAT] Step 5.{iterations}.5: Tool result preview: {json.dumps(result)[:200]}...")
                
            except Exception as e:
                logger.error(f"🤖 [AGENTIC_CHAT] Step 5.{iterations}.ERROR: Tool execution error: {e}", exc_info=True)
                break
        
        logger.info(f"🤖 [AGENTIC_CHAT] Step 5.COMPLETE: Agentic loop finished after {iterations} iterations with {len(tool_results)} tool calls")
        
        # Generate final response with all gathered context
        logger.info(f"🤖 [AGENTIC_CHAT] Step 6: Generating final response")
        logger.info(f"🤖 [AGENTIC_CHAT] Step 6.1: After {iterations} iterations, {len(tool_results)} tool calls, {len(messages)} messages")
        
        async for chunk in self._generate_final_response(messages, tool_results):
            yield chunk
        
        logger.info(f"🤖 [AGENTIC_CHAT] ========== AGENTIC CHAT REQUEST COMPLETE ==========")
    
    def _build_messages(self, message: str, conversation_history: Optional[List[Any]], notes_context: str = "", project_overview: str = "") -> List[Dict[str, str]]:
        """Build message list for the LLM."""
        from backend.utils.target_project import get_target_project_name
        
        project_name = get_target_project_name()
        
        # Build meeting notes section if available
        notes_section = ""
        if notes_context:
            notes_section = f"""

## MEETING NOTES / PROJECT REQUIREMENTS:
The user has provided these meeting notes describing their project:

{notes_context}

Use this information to understand what the user is building and answer questions about their specific project requirements.
"""

        # Build project overview section (Wikipedia-like knowledge)
        overview_section = ""
        if project_overview:
            overview_section = f"""

## 📚 PROJECT KNOWLEDGE BASE (What You Already Know):
{project_overview}

You already have this knowledge about the project. Reference it directly when answering questions.
For more specific details, use the tools available.
"""
        
        system_message = f"""You are Architect.AI, an intelligent assistant with COMPLETE KNOWLEDGE of the "{project_name}" codebase.
{notes_section}{overview_section}
You have encyclopedic knowledge of the user's project AND tools to dig deeper when needed.

AVAILABLE TOOLS:
- search_codebase: Search for code by topic/concept
- read_file: Read a specific file's contents  
- list_files: List files in a directory
- query_knowledge_graph: Find relationships between components
- get_project_patterns: Get detected patterns and issues
- get_project_overview: Get comprehensive project summary (all files, classes, architecture)

WHEN TO USE TOOLS:
- You need SPECIFIC CODE content → read_file
- You want to find WHERE something is implemented → search_codebase
- User asks "what's in this project?" → get_project_overview
- User asks about dependencies/relationships → query_knowledge_graph
- User asks about code quality/patterns → get_project_patterns
- You need to verify or get more details → use appropriate tool

RESPONSE GUIDELINES:
- Answer questions using your existing knowledge when possible
- Reference actual files, classes, and functions by name
- Be specific: mention `ClassName`, `fileName.ts`, `functionName()`
- Use tools to get exact code snippets when needed
- Be conversational and helpful - you're the project expert!"""

        messages = [{"role": "system", "content": system_message}]
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages
                if hasattr(msg, 'role') and hasattr(msg, 'content'):
                    messages.append({"role": msg.role, "content": msg.content})
                elif isinstance(msg, dict):
                    messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        
        messages.append({"role": "user", "content": message})
        
        return messages
    
    async def _call_llm_with_tools(
        self,
        messages: List[Dict[str, str]],
        tool_results: List[Dict[str, Any]],
        available_tools: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Call LLM and check if it wants to use a tool.
        
        Args:
            messages: Conversation messages
            tool_results: Results from previous tool calls
            available_tools: List of available tools (defaults to AGENT_TOOLS)
        
        Returns tool call info if AI wants to use a tool, None if ready to answer.
        """
        if available_tools is None:
            available_tools = AGENT_TOOLS
        import httpx
        
        # Add tool results to context if any
        if tool_results:
            tool_context = "\n\n## Information I've gathered:\n"
            for tr in tool_results:
                tool_context += f"\n### From {tr['tool']}:\n```json\n{json.dumps(tr['result'], indent=2)[:2000]}\n```\n"
            
            # Append to last user message
            messages = messages.copy()
            messages[-1] = {
                "role": "user",
                "content": messages[-1]["content"] + tool_context
            }
        
        # Build prompt asking if AI needs more info
        decision_prompt = messages.copy()
        decision_prompt.append({
            "role": "user",
            "content": """Based on the user's question and any information gathered so far, do you need to use a tool to get more information?

If YES, respond with EXACTLY this JSON format (nothing else):
{"tool": "tool_name", "arguments": {"arg1": "value1"}}

If NO (you have enough info to answer), respond with:
{"ready": true}

Choose ONE option only."""
        })
        
        # Use Groq for fast decision-making
        if settings.groq_api_key:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.groq_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "llama-3.3-70b-versatile",
                            "messages": decision_prompt,
                            "temperature": 0.1,  # Low temperature for consistent decisions
                            "max_tokens": 200
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["message"]["content"].strip()
                        
                        # Parse the response
                        try:
                            # Try to extract JSON from response
                            if "{" in content:
                                json_start = content.index("{")
                                json_end = content.rindex("}") + 1
                                json_str = content[json_start:json_end]
                                decision = json.loads(json_str)
                                
                                if decision.get("ready"):
                                    return None  # Ready to answer
                                
                                if "tool" in decision:
                                    return {
                                        "name": decision["tool"],
                                        "arguments": decision.get("arguments", {})
                                    }
                        except (json.JSONDecodeError, ValueError):
                            pass
                        
                        # Default: ready to answer
                        return None
                        
            except Exception as e:
                logger.warning(f"Groq decision call failed: {e}")
        
        # Default: no tool call
        return None
    
    async def _generate_final_response(
        self,
        messages: List[Dict[str, str]],
        tool_results: List[Dict[str, Any]]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate the final response using gathered context."""
        import httpx
        
        # Build final prompt with all tool results
        final_messages = messages.copy()
        
        if tool_results:
            context = "\n\n## Information gathered from codebase exploration:\n"
            for tr in tool_results:
                context += f"\n### {tr['tool']}({tr['arguments']}):\n"
                result = tr['result']
                
                # Format result nicely
                if tr['tool'] == 'search_codebase' and result.get('results'):
                    for r in result['results'][:3]:
                        context += f"\n**File:** `{r['file']}`\n```\n{r['content'][:800]}\n```\n"
                elif tr['tool'] == 'read_file' and result.get('content'):
                    context += f"\n**File:** `{result['file_path']}`\n```\n{result['content'][:1500]}\n```\n"
                else:
                    context += f"```json\n{json.dumps(result, indent=2)[:1000]}\n```\n"
            
            final_messages[-1] = {
                "role": "user", 
                "content": final_messages[-1]["content"] + context + "\n\nNow please provide a helpful answer based on this information."
            }
        
        # Generate response with Groq (fast) or fallback
        if settings.groq_api_key:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.groq_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "llama-3.3-70b-versatile",
                            "messages": final_messages,
                            "temperature": 0.7,
                            "max_tokens": 2000
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["message"]["content"]
                        
                        # Stream the response
                        chunk_size = max(20, len(content) // 30)
                        for i in range(0, len(content), chunk_size):
                            yield {
                                "type": "chunk",
                                "content": content[i:i+chunk_size],
                                "model": "llama-3.3-70b-versatile",
                                "provider": "groq"
                            }
                            await asyncio.sleep(0.02)
                        
                        # Final complete message
                        yield {
                            "type": "complete",
                            "content": content,
                            "model": "llama-3.3-70b-versatile", 
                            "provider": "groq",
                            "tools_used": [tr["tool"] for tr in tool_results]
                        }
                        return
                        
            except Exception as e:
                logger.error(f"Groq final response failed: {e}")
        
        # Fallback error
        yield {
            "type": "error",
            "content": "I apologize, but I couldn't generate a response. Please try again.",
            "error": "All providers failed"
        }


# Global instance
_agentic_chat_service: Optional[AgenticChatService] = None


def get_agentic_chat_service() -> AgenticChatService:
    """Get or create the agentic chat service instance."""
    global _agentic_chat_service
    if _agentic_chat_service is None:
        _agentic_chat_service = AgenticChatService()
    return _agentic_chat_service
