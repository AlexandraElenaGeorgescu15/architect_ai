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
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name with given arguments."""
        tool_map = {
            "search_codebase": self._tool_search_codebase,
            "read_file": self._tool_read_file,
            "list_files": self._tool_list_files,
            "query_knowledge_graph": self._tool_query_knowledge_graph,
            "get_project_patterns": self._tool_get_project_patterns
        }
        
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
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Agentic chat that can use tools to find information.
        
        Flow:
        1. Send user message + available tools to LLM
        2. If LLM wants to use a tool, execute it and add result to context
        3. Repeat until LLM provides final answer (max 5 iterations)
        4. Stream the final response
        """
        from backend.core.config import settings
        import httpx
        
        # Build conversation context
        messages = self._build_messages(message, conversation_history)
        tool_results = []
        iterations = 0
        
        # Agentic loop - let AI decide when to use tools
        while iterations < self.MAX_TOOL_ITERATIONS:
            iterations += 1
            
            # Call LLM with tools
            try:
                tool_call = await self._call_llm_with_tools(messages, tool_results)
                
                if tool_call is None:
                    # No tool call - AI is ready to answer
                    break
                
                # Execute the tool
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("arguments", {})
                
                logger.info(f"🔧 [AGENT] Calling tool: {tool_name} with args: {tool_args}")
                
                # Yield status update
                yield {
                    "type": "status",
                    "content": f"🔍 Searching: {tool_name}...",
                    "tool": tool_name
                }
                
                # Execute tool
                result = await self.execute_tool(tool_name, tool_args)
                tool_results.append({
                    "tool": tool_name,
                    "arguments": tool_args,
                    "result": result
                })
                
                logger.info(f"🔧 [AGENT] Tool result: {json.dumps(result)[:200]}...")
                
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                break
        
        # Generate final response with all gathered context
        logger.info(f"🤖 [AGENT] Generating final response after {iterations} iterations, {len(tool_results)} tool calls")
        
        async for chunk in self._generate_final_response(messages, tool_results):
            yield chunk
    
    def _build_messages(self, message: str, conversation_history: Optional[List[Any]]) -> List[Dict[str, str]]:
        """Build message list for the LLM."""
        from backend.utils.target_project import get_target_project_name
        
        project_name = get_target_project_name()
        
        system_message = f"""You are Architect.AI, an intelligent assistant analyzing the "{project_name}" codebase.

You have access to tools that let you explore the codebase. Use them when you need more information to answer the user's question.

AVAILABLE TOOLS:
- search_codebase: Search for code by topic/concept
- read_file: Read a specific file's contents
- list_files: List files in a directory
- query_knowledge_graph: Find relationships between components
- get_project_patterns: Get detected patterns and issues

WHEN TO USE TOOLS:
- User asks about specific functionality → search_codebase or read_file
- User asks "what files/components exist" → list_files or search_codebase
- User asks about dependencies/relationships → query_knowledge_graph
- User asks about code quality/patterns → get_project_patterns
- You're unsure about something → use a tool to verify

RESPONSE FORMAT:
When you have enough information, provide a helpful, specific answer.
Reference actual files and code you found through your searches.
Be conversational and helpful."""

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
        tool_results: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Call LLM and check if it wants to use a tool.
        
        Returns tool call info if AI wants to use a tool, None if ready to answer.
        """
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
