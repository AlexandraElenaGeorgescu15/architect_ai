"""
Project-Aware AI Chat Service.
Provides intelligent chat with full project context (RAG + KG + Pattern Mining).
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, AsyncGenerator
import logging
from datetime import datetime
import asyncio

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.context_builder import get_builder as get_context_builder
from backend.services.rag_retriever import get_retriever
from backend.services.knowledge_graph import get_builder as get_kg_builder
from backend.services.pattern_mining import get_miner
from backend.core.config import settings
from backend.core.logger import get_logger
from backend.core.metrics import get_metrics_collector, timed
from backend.core.cache import cached
from config.artifact_model_mapping import get_artifact_mapper, ArtifactType

logger = get_logger(__name__)
metrics = get_metrics_collector()

# Optional imports for Ollama
try:
    from ai.ollama_client import OllamaClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama client not available. Chat will use cloud models only.")


class ProjectAwareChatService:
    """
    Project-aware AI chat service with DEEP context retention.
    
    Features:
    - Full project context (RAG + KG + Pattern Mining)
    - Intelligent question understanding
    - Code-aware responses
    - Architecture-aware responses
    - Streaming support
    - Conversation summarization for long conversations
    """
    
    # Class-level conversation summaries for context retention across long conversations
    # Key: session_id, Value: summary of earlier conversation parts
    _conversation_summaries: Dict[str, str] = {}
    
    def __init__(self):
        """Initialize Chat Service with enhanced context retention."""
        from backend.core.config import settings
        
        self.context_builder = get_context_builder()
        self.rag_retriever = get_retriever()
        self.kg_builder = get_kg_builder()
        self.pattern_miner = get_miner()
        self.ollama_client = OllamaClient() if OLLAMA_AVAILABLE else None
        self.artifact_mapper = get_artifact_mapper()
        
        # Enhanced context settings (from centralized config)
        self.max_conversation_messages = settings.chat_max_conversation_messages
        self.max_snippet_length = settings.chat_max_snippet_length
        self.max_rag_snippets = settings.chat_max_rag_snippets
        self.kg_max_nodes = 50
        self.kg_max_relationships = 30
        
        logger.info("Project-Aware Chat Service initialized")
    
    async def chat(
        self,
        message: str,
        conversation_history: Optional[List[Any]] = None,
        include_project_context: bool = True,
        stream: bool = False,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate AI response with DEEP project context and session memory.
        
        Args:
            message: User message
            conversation_history: Previous messages in conversation
            include_project_context: Whether to include RAG + KG + Pattern Mining
            stream: Whether to stream response
            session_id: Optional session ID for context persistence
        
        Yields:
            Dictionary with response chunks or final response
        """
        metrics.increment("chat_requests_total")
        
        # Generate session_id if not provided (for context persistence)
        if not session_id and conversation_history:
            # Create a simple hash from first message to track conversation
            first_msg = self._extract_content(conversation_history[0]) if conversation_history else ""
            session_id = f"chat_{hash(first_msg[:50]) % 100000}"
        
        # Build comprehensive project context
        project_context = ""
        if include_project_context:
            try:
                # Get RAG context (most relevant code snippets)
                # ENHANCED: Retrieve 30 chunks, use top 12 for comprehensive chat context
                rag_results = await self.rag_retriever.retrieve(
                    query=message,
                    k=30,  # Retrieve more, filter to best 12
                    artifact_type=None  # General context
                )
                
                # Get Knowledge Graph insights
                kg_context = await self._get_kg_insights(message)
                
                # Get Pattern Mining insights
                pattern_context = await self._get_pattern_insights(message)
                
                # Assemble context
                project_context_parts = []
                
                if rag_results:
                    project_context_parts.append("## Relevant Code Snippets:")
                    # ENHANCED: Include more snippets with MUCH longer content for deep context
                    # Sort by relevance score if available
                    sorted_results = sorted(
                        rag_results,
                        key=lambda r: r.get('score', r.get('relevance', 0)),
                        reverse=True
                    )[:self.max_rag_snippets]  # Top 12 (was 8)
                    
                    for i, result in enumerate(sorted_results, 1):
                        file_path = result.get('metadata', {}).get('file_path', 'unknown')
                        content = result.get('content', '')
                        score = result.get('score', result.get('relevance', 'N/A'))
                        
                        # ENHANCED: Include much more content per snippet (was 800)
                        # Plus show relevance score to help AI prioritize
                        project_context_parts.append(
                            f"\n### Snippet {i} (from {file_path}, relevance: {score}):\n"
                            f"```\n{content[:self.max_snippet_length]}\n```"
                        )
                
                if kg_context:
                    project_context_parts.append(f"\n## Knowledge Graph Insights:\n{kg_context}")
                
                if pattern_context:
                    project_context_parts.append(f"\n## Pattern Mining Insights:\n{pattern_context}")
                
                project_context = "\n".join(project_context_parts)
                logger.info(f"Chat context built: {len(project_context)} chars, {len(rag_results) if rag_results else 0} RAG snippets")
                
            except Exception as e:
                logger.warning(f"Error building project context: {e}")
                project_context = ""
        
        # Build system message
        system_message = self._build_system_message(include_project_context)
        
        # Build prompt with conversation history AND session context
        prompt = self._build_prompt(message, conversation_history, project_context, session_id)
        
        # Calculate and log context sizes for debugging
        total_chars = len(system_message) + len(prompt)
        estimated_tokens = total_chars // 4  # Rough estimate: 4 chars per token
        
        logger.info(f"[CHAT] Context stats:")
        logger.info(f"  - System message: {len(system_message)} chars")
        logger.info(f"  - Prompt: {len(prompt)} chars")
        logger.info(f"  - Total: {total_chars} chars (~{estimated_tokens} tokens)")
        logger.info(f"  - Session: {session_id}")
        
        if estimated_tokens > settings.local_model_context_window * 0.75:
            logger.warning(f"⚠️ [CHAT] Large context ({estimated_tokens} tokens). Approaching limit of {settings.local_model_context_window}")
        
        # Generate response (try Ollama first, then cloud)
        # Get models from model mapping configuration for chat
        chat_mapping = self.artifact_mapper.get_model_for_artifact(ArtifactType.CHAT.value)
        priority_models = chat_mapping.priority_models or [chat_mapping.base_model]
        
        # Extract base model names (remove :tag suffix for Ollama client)
        local_models_to_try = []
        for model in priority_models:
            # Extract base name (e.g., "llama3:8b-instruct-q4_K_M" -> "llama3")
            base_name = model.split(":")[0] if ":" in model else model
            if base_name not in local_models_to_try:
                local_models_to_try.append(base_name)
        
        # Fallback to default models if mapping doesn't provide any
        if not local_models_to_try:
            local_models_to_try = ["llama3", "llama3.2", "mistral", "codellama"]
        
        if self.ollama_client and OLLAMA_AVAILABLE:
            for model_base_name in local_models_to_try:
                try:
                    # Check if model is available
                    await self.ollama_client.ensure_model_available(model_base_name)
                    
                    # Try Ollama generation with context window from config
                    response = await asyncio.wait_for(
                        self.ollama_client.generate(
                            model_name=model_base_name,
                            prompt=prompt,
                            system_message=system_message,
                            temperature=0.7,
                            num_ctx=settings.local_model_context_window  # From centralized config
                        ),
                        timeout=settings.generation_timeout  # From centralized config
                    )
                    
                    if response.success and response.content and len(response.content.strip()) > 20:
                        logger.info(f"Chat successful with {model_base_name}")
                        if stream:
                            # Stream character by character for effect
                            content = response.content
                            chunk_size = max(10, len(content) // 50)  # Dynamic chunk size
                            for i in range(0, len(content), chunk_size):
                                yield {
                                    "type": "chunk",
                                    "content": content[i:i+chunk_size],
                                    "model": model_base_name,
                                    "provider": "ollama"
                                }
                                await asyncio.sleep(0.02)  # Faster streaming
                            # Send complete signal
                            yield {
                                "type": "complete",
                                "content": content,
                                "model": model_base_name,
                                "provider": "ollama"
                            }
                            return  # Critical: return immediately after streaming complete
                        else:
                            yield {
                                "type": "complete",
                                "content": response.content,
                                "model": model_base_name,
                                "provider": "ollama"
                            }
                            return  # Critical: return immediately after non-streaming complete
                    else:
                        logger.warning(f"Model {model_base_name} returned empty/short response, trying next...")
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout with {model_base_name}, trying next...")
                except Exception as e:
                    logger.warning(f"Model {model_base_name} failed: {e}, trying next...")
        
        # Fallback to cloud (Gemini preferred for chat)
        try:
            cloud_response = self._call_cloud_chat(
                message=message,
                system_message=system_message,
                prompt=prompt,
                stream=stream
            )
            
            if stream:
                async for chunk in cloud_response:
                    yield chunk
            else:
                # For non-streaming, collect all chunks and yield the final result
                final_chunk = None
                async for chunk in cloud_response:
                    final_chunk = chunk
                if final_chunk:
                    yield final_chunk
                
        except Exception as e:
            logger.error(f"Cloud chat failed: {e}")
            yield {
                "type": "error",
                "content": f"I apologize, but I encountered an error. Please try again.",
                "error": str(e)
            }
    
    async def _get_kg_insights(self, query: str) -> str:
        """
        Get DEEP Knowledge Graph insights relevant to query.
        
        Enhanced to provide much richer context about project structure,
        component relationships, and architectural patterns.
        """
        try:
            # Extract key terms from query (including shorter words for better matching)
            keywords = [word.lower() for word in query.split() if len(word) > 2]
            
            # Get actual KG stats and insights
            kg_stats = self.kg_builder.get_stats()
            if not kg_stats or kg_stats.get("nodes", 0) == 0:
                return ""
            
            # Build comprehensive insights from KG
            insights = []
            insights.append("## Knowledge Graph Analysis (Deep Context):")
            insights.append(f"- Total components: {kg_stats.get('nodes', 0)}")
            insights.append(f"- Total relationships: {kg_stats.get('edges', 0)}")
            insights.append(f"- Main architectural components: {kg_stats.get('components', 0)}")
            
            # Get full graph data for deep analysis
            try:
                graph_data = self.kg_builder.get_graph()
                if graph_data and "nodes" in graph_data:
                    all_nodes = graph_data.get("nodes", [])
                    all_edges = graph_data.get("edges", [])
                    
                    # Categorize nodes by type
                    node_types = {}
                    for node in all_nodes[:self.kg_max_nodes]:
                        node_type = node.get("type", "unknown")
                        if node_type not in node_types:
                            node_types[node_type] = []
                        node_types[node_type].append(node.get("name", "Unknown"))
                    
                    # Show component breakdown
                    insights.append("\n### Component Breakdown:")
                    for node_type, names in sorted(node_types.items(), key=lambda x: len(x[1]), reverse=True):
                        if len(names) > 0:
                            sample = names[:8]  # Show up to 8 examples per type
                            remaining = len(names) - len(sample)
                            names_str = ", ".join(sample)
                            if remaining > 0:
                                names_str += f" (+{remaining} more)"
                            insights.append(f"- **{node_type}** ({len(names)}): {names_str}")
                    
                    # Find relevant components based on query
                    matching_nodes = []
                    for node in all_nodes:
                        node_name = node.get("name", "").lower()
                        node_type = node.get("type", "").lower()
                        node_file = node.get("file", "").lower()
                        if any(kw in node_name or kw in node_type or kw in node_file for kw in keywords):
                            matching_nodes.append(node)
                    
                    if matching_nodes:
                        insights.append(f"\n### Components Matching Your Query ({len(matching_nodes)} found):")
                        for node in matching_nodes[:10]:  # Up from 5
                            name = node.get("name", "Unknown")
                            ntype = node.get("type", "component")
                            file_path = node.get("file", "")
                            insights.append(f"- **{name}** ({ntype})")
                            if file_path:
                                insights.append(f"  └─ Location: {file_path}")
                    
                    # Show relationships between components
                    if all_edges:
                        insights.append(f"\n### Key Relationships ({min(len(all_edges), self.kg_max_relationships)} shown):")
                        for edge in all_edges[:self.kg_max_relationships]:
                            source = edge.get("source", "?")
                            target = edge.get("target", "?")
                            rel_type = edge.get("type", edge.get("relationship", "relates to"))
                            insights.append(f"- {source} → {rel_type} → {target}")
                    
                    # Identify hub components (most connections)
                    connection_count = {}
                    for edge in all_edges:
                        source = edge.get("source", "")
                        target = edge.get("target", "")
                        connection_count[source] = connection_count.get(source, 0) + 1
                        connection_count[target] = connection_count.get(target, 0) + 1
                    
                    if connection_count:
                        top_hubs = sorted(connection_count.items(), key=lambda x: x[1], reverse=True)[:5]
                        insights.append("\n### Core Components (Most Connected):")
                        for component, count in top_hubs:
                            insights.append(f"- **{component}**: {count} connections")
                            
            except Exception as e:
                logger.debug(f"Could not query KG graph for deep insights: {e}")
            
            return "\n".join(insights) if len(insights) > 4 else ""
        except Exception as e:
            logger.warning(f"Error getting KG insights: {e}")
            return ""
    
    async def _get_pattern_insights(self, query: str) -> str:
        """
        Get ACTUAL Pattern Mining insights relevant to query.
        
        This retrieves real pattern mining results, NOT hardcoded text.
        """
        try:
            insights = []
            
            # Get the actual pattern mining results
            report = self.pattern_miner.get_report()
            
            if not report or report.get("status") == "not_run":
                # Pattern mining hasn't been run yet
                return ""
            
            # Build insights from REAL data
            patterns_detected = report.get("patterns_detected", [])
            code_smells = report.get("code_smells", [])
            security_issues = report.get("security_issues", [])
            stats = report.get("statistics", {})
            
            if not patterns_detected and not code_smells and not security_issues:
                return ""
            
            insights.append("## Pattern Mining Analysis (Real Data):")
            
            # Summarize patterns by type
            if patterns_detected:
                pattern_counts = {}
                for p in patterns_detected:
                    name = p.get("pattern_name", "Unknown")
                    pattern_counts[name] = pattern_counts.get(name, 0) + 1
                
                insights.append(f"\n**Design Patterns Detected ({len(patterns_detected)} total):**")
                for pattern_name, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                    insights.append(f"- {pattern_name}: {count} instance(s)")
                
                # Show example locations
                for p in patterns_detected[:3]:
                    file_path = p.get("file_path", "")
                    if file_path:
                        insights.append(f"  └─ Found in: {file_path}")
            
            # Code smells
            if code_smells:
                smell_counts = {}
                for s in code_smells:
                    smell_type = s.get("smell_type", "Unknown")
                    smell_counts[smell_type] = smell_counts.get(smell_type, 0) + 1
                
                insights.append(f"\n**Code Smells ({len(code_smells)} total):**")
                for smell_type, count in sorted(smell_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                    insights.append(f"- {smell_type}: {count} occurrence(s)")
            
            # Security issues
            if security_issues:
                insights.append(f"\n**Security Issues ({len(security_issues)} total):**")
                for issue in security_issues[:3]:
                    severity = issue.get("severity", "unknown")
                    issue_type = issue.get("issue_type", "Unknown")
                    insights.append(f"- [{severity.upper()}] {issue_type}")
            
            # Statistics
            if stats:
                files_analyzed = stats.get("files_analyzed", 0)
                if files_analyzed > 0:
                    insights.append(f"\n**Coverage:** {files_analyzed} files analyzed")
            
            return "\n".join(insights) if insights else ""
            
        except Exception as e:
            logger.warning(f"Error getting pattern insights: {e}")
            return ""
    
    def _build_system_message(self, include_project_context: bool) -> str:
        """Build system message for chat with actual project information."""
        from backend.utils.target_project import get_target_project_name, get_target_project_info
        
        # Get REAL project information
        project_name = get_target_project_name()
        project_info = get_target_project_info()
        tech_stack = ", ".join(project_info.get("tech_stack", [])[:3]) or "Unknown"
        
        base_message = f"""You are Architect.AI, an expert AI assistant helping the user understand their project: **{project_name}**.

The user's project uses: {tech_stack}

Your primary purpose is to help users understand THIS SPECIFIC project codebase - not give generic advice.

Your role:
- Help users understand the {project_name} codebase structure and architecture
- Provide intelligent, specific answers about code, patterns, and design decisions in {project_name}
- Suggest improvements and best practices based on what you SEE in their actual code
- Answer questions about feasibility, complexity, and implementation
- Reference specific files, functions, and code structures from {project_name}

CRITICAL GUIDELINES:
- ALWAYS cite specific files, function names, and code from the project context provided
- NEVER give generic "As an AI assistant" responses - PROVE you know {project_name}
- When answering questions about "this codebase" or "my code", reference ACTUAL files from the snippets
- When asked "what do you do?", DEMONSTRATE knowledge by listing specific components you see in the snippets
- Start responses with specific {project_name} knowledge, not generic capabilities
- Reference ACTUAL class names, function names, and file paths from the snippets
- Be concise but PROVE you know their codebase with specific references

EXAMPLE - BAD (generic):
"As an AI assistant, I can help you with code understanding, pattern detection, and architecture guidance..."

EXAMPLE - GOOD (project-specific for {project_name}):
"Looking at {project_name}, I can see these key components in the code snippets:
- [Name actual classes/functions from snippets]
- [Reference actual file paths from snippets]
What would you like to know about these?"

If you don't have enough context from the snippets, say so and ask for clarification."""
        
        if include_project_context:
            base_message += f"""

You have access to:
- ACTUAL CODE SNIPPETS from {project_name} (included below as "Relevant Code Snippets")
- Knowledge Graph showing component relationships in {project_name}
- Pattern Mining insights about design patterns detected in {project_name}
- Project structure and file organization

IMPORTANT: The code snippets provided are from {project_name}, the USER'S ACTUAL PROJECT.
Always reference these snippets when answering questions about "my code", "this project", or "the codebase".
If the user asks "what do you do?" or "what can you help with?", IMMEDIATELY cite specific files and components from the snippets.

DO NOT say "As an AI assistant" - instead say "Looking at {project_name}, I can see..."
DO NOT list generic capabilities - instead demonstrate specific knowledge of {project_name}."""
        
        return base_message
    
    def _build_prompt(
        self,
        message: str,
        conversation_history: Optional[List[Any]],
        project_context: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        Build chat prompt with COMPREHENSIVE history and context.
        
        Enhanced to:
        1. Include more conversation history (15 messages, not 5)
        2. Summarize older conversation if too long
        3. Retain semantic memory from past interactions
        """
        parts = []
        
        # Add project context first (most important)
        if project_context:
            parts.append("## Project Context (Your Codebase):")
            parts.append(project_context)
            parts.append("")
        
        # Add semantic memory from previous conversations if available
        if session_id and session_id in self._conversation_summaries:
            summary = self._conversation_summaries[session_id]
            if summary:
                parts.append("## Earlier Conversation Summary:")
                parts.append(summary)
                parts.append("")
        
        # Build conversation history with intelligent handling
        if conversation_history:
            parts.append("## Recent Conversation History:")
            
            # If conversation is long, summarize older parts and store for future
            if len(conversation_history) > self.max_conversation_messages:
                older_messages = conversation_history[:-self.max_conversation_messages]
                recent_messages = conversation_history[-self.max_conversation_messages:]
                
                # Build a summary of older messages (stored for future requests)
                older_summary = self._summarize_older_messages(older_messages, session_id)
                
                if older_summary:
                    parts.append(f"*[Earlier conversation summary: {older_summary}]*")
            else:
                recent_messages = conversation_history
            
            # Include all recent messages (up to max_conversation_messages)
            for msg in recent_messages:
                role, content = self._extract_role_content(msg)
                # Truncate very long individual messages but keep more context
                if len(content) > 1500:
                    content = content[:1500] + "...[truncated]"
                parts.append(f"{role.capitalize()}: {content}")
            parts.append("")
        
        parts.append(f"## Current Question:\n{message}")
        parts.append("\n## Your Response:")
        parts.append("(Remember: Reference specific files, functions, and code from the project context above. Be specific!)")
        
        return "\n".join(parts)
    
    def _summarize_older_messages(self, older_messages: List[Any], session_id: Optional[str]) -> str:
        """
        Summarize older conversation messages and store for future context.
        
        This prevents context window overflow while retaining conversation memory.
        """
        if not older_messages:
            return ""
        
        # Extract key topics from older messages
        topics = []
        user_questions = []
        assistant_insights = []
        
        for msg in older_messages:
            role, content = self._extract_role_content(msg)
            
            if role == "user" and len(content) > 20:
                # Extract first sentence or 100 chars as a topic
                first_sentence = content.split('.')[0][:100]
                user_questions.append(first_sentence)
            elif role == "assistant" and len(content) > 50:
                # Look for key insights (lines starting with specific patterns)
                for line in content.split('\n')[:5]:
                    if any(marker in line.lower() for marker in ['found', 'detected', 'suggest', 'recommend', 'pattern', 'issue']):
                        assistant_insights.append(line[:80])
                        break
        
        # Build summary
        summary_parts = []
        if user_questions:
            summary_parts.append(f"Asked about: {', '.join(user_questions[:3])}")
        if assistant_insights:
            summary_parts.append(f"Key findings: {'; '.join(assistant_insights[:2])}")
        
        summary = ". ".join(summary_parts) if summary_parts else f"Discussed {len(older_messages)} earlier messages"
        
        # Store for future requests in this session
        if session_id:
            # Append to existing summary if present
            existing = self._conversation_summaries.get(session_id, "")
            if existing:
                summary = f"{existing}. Then: {summary}"
            self._conversation_summaries[session_id] = summary[:500]  # Limit summary length
            
            # Cleanup old summaries (keep max 100 sessions)
            if len(self._conversation_summaries) > 100:
                # Remove oldest entries (simple FIFO - first keys are oldest)
                keys_to_remove = list(self._conversation_summaries.keys())[:-50]
                for key in keys_to_remove:
                    del self._conversation_summaries[key]
        
        return summary
    
    def _extract_content(self, msg: Any) -> str:
        """Extract content from message (handles dict or Pydantic model)."""
        if hasattr(msg, 'content'):
            return msg.content
        elif isinstance(msg, dict):
            return msg.get("content", "")
        return str(msg)
    
    def _extract_role_content(self, msg: Any) -> tuple:
        """Extract role and content from message."""
        if hasattr(msg, 'role') and hasattr(msg, 'content'):
            return msg.role, msg.content
        elif isinstance(msg, dict):
            return msg.get("role", "user"), msg.get("content", "")
        return "user", str(msg)
    
    async def _call_cloud_chat(
        self,
        message: str,
        system_message: str,
        prompt: str,
        stream: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Call cloud API for chat with multiple provider fallbacks."""
        import httpx
        
        # Try Groq first (fastest for chat)
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
                            "messages": [
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.7,
                            "max_tokens": settings.cloud_api_max_tokens
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["message"]["content"]
                        logger.info(f"Groq chat successful, response length: {len(content)}")
                        yield {
                            "type": "complete",
                            "content": content,
                            "model": "llama-3.3-70b-versatile",
                            "provider": "groq"
                        }
                        return
            except Exception as e:
                logger.warning(f"Groq chat failed: {e}, trying Gemini...")
        
        # Try Gemini (good for conversational AI)
        if settings.google_api_key or settings.gemini_api_key:
            try:
                api_key = settings.google_api_key or settings.gemini_api_key
                model_name = settings.default_chat_model  # Use config-driven model
                
                async with httpx.AsyncClient(timeout=60.0) as client:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                    
                    payload = {
                        "contents": [{
                            "role": "user",
                            "parts": [{"text": prompt}]
                        }],
                        "generationConfig": {
                            "temperature": 0.7,
                            "topK": 40,
                            "topP": 0.95,
                            "maxOutputTokens": 4096
                        },
                        "systemInstruction": {
                            "parts": [{"text": system_message}]
                        }
                    }
                    
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    
                    data = response.json()
                    if "candidates" in data and len(data["candidates"]) > 0:
                        content = data["candidates"][0]["content"]["parts"][0]["text"]
                        logger.info(f"Gemini chat successful, response length: {len(content)}")
                        yield {
                            "type": "complete",
                            "content": content,
                            "model": model_name,
                            "provider": "gemini"
                        }
                        return
            except Exception as e:
                logger.warning(f"Gemini chat failed: {e}, trying OpenAI...")
        
        # Try OpenAI
        if settings.openai_api_key:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.openai_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "gpt-4-turbo-preview",
                            "messages": [
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.7,
                            "max_tokens": settings.cloud_api_max_tokens
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["message"]["content"]
                        logger.info(f"OpenAI chat successful, response length: {len(content)}")
                        yield {
                            "type": "complete",
                            "content": content,
                            "model": "gpt-4-turbo-preview",
                            "provider": "openai"
                        }
                        return
            except Exception as e:
                logger.warning(f"OpenAI chat failed: {e}")
        
        # No providers available
        logger.error("All chat providers failed or no API keys configured")
        yield {
            "type": "error",
            "content": "I apologize, but no AI models are currently available. Please check your API key configuration or try again later.",
            "error": "No cloud models configured or all providers failed"
        }


# Global service instance
_chat_service: Optional[ProjectAwareChatService] = None


def get_chat_service() -> ProjectAwareChatService:
    """Get or create global Chat Service instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ProjectAwareChatService()
    return _chat_service

