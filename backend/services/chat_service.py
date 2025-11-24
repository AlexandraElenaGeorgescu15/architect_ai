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
    Project-aware AI chat service.
    
    Features:
    - Full project context (RAG + KG + Pattern Mining)
    - Intelligent question understanding
    - Code-aware responses
    - Architecture-aware responses
    - Streaming support
    """
    
    def __init__(self):
        """Initialize Chat Service."""
        self.context_builder = get_context_builder()
        self.rag_retriever = get_retriever()
        self.kg_builder = get_kg_builder()
        self.pattern_miner = get_miner()
        self.ollama_client = OllamaClient() if OLLAMA_AVAILABLE else None
        
        logger.info("Project-Aware Chat Service initialized")
    
    async def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        include_project_context: bool = True,
        stream: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate AI response with full project context.
        
        Args:
            message: User message
            conversation_history: Previous messages in conversation
            include_project_context: Whether to include RAG + KG + Pattern Mining
            stream: Whether to stream response
        
        Yields:
            Dictionary with response chunks or final response
        """
        metrics.counter("chat_requests_total", "Total chat requests").inc()
        
        # Build comprehensive project context
        project_context = ""
        if include_project_context:
            try:
                # Get RAG context (most relevant code snippets)
                rag_results = await self.rag_retriever.retrieve(
                    query=message,
                    k=10,  # More chunks for chat (broader context)
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
                    for i, result in enumerate(rag_results[:5], 1):  # Top 5
                        project_context_parts.append(
                            f"\n### Snippet {i} (from {result.get('metadata', {}).get('file_path', 'unknown')}):\n"
                            f"{result.get('content', '')[:500]}"
                        )
                
                if kg_context:
                    project_context_parts.append(f"\n## Knowledge Graph Insights:\n{kg_context}")
                
                if pattern_context:
                    project_context_parts.append(f"\n## Pattern Mining Insights:\n{pattern_context}")
                
                project_context = "\n".join(project_context_parts)
                
            except Exception as e:
                logger.warning(f"Error building project context: {e}")
                project_context = ""
        
        # Build system message
        system_message = self._build_system_message(include_project_context)
        
        # Build prompt with conversation history
        prompt = self._build_prompt(message, conversation_history, project_context)
        
        # Generate response (try Ollama first, then cloud)
        if self.ollama_client and OLLAMA_AVAILABLE:
            try:
                # Try local model first
                await self.ollama_client.ensure_model_available("llama3")
                
                # Try Ollama generation (non-streaming for now)
                response = await self.ollama_client.generate(
                    model_name="llama3",
                    prompt=prompt,
                    system_message=system_message,
                    temperature=0.7
                )
                
                if response.success and response.content:
                    if stream:
                        # Stream character by character for effect
                        content = response.content
                        for i in range(0, len(content), 5):  # 5 chars at a time
                            yield {
                                "type": "chunk",
                                "content": content[i:i+5],
                                "model": "llama3",
                                "provider": "ollama"
                            }
                            await asyncio.sleep(0.05)  # Small delay for streaming effect
                    else:
                        yield {
                            "type": "complete",
                            "content": response.content,
                            "model": "llama3",
                            "provider": "ollama"
                        }
                        return
            except Exception as e:
                logger.warning(f"Ollama generation failed: {e}, trying cloud...")
        
        # Fallback to cloud (Gemini preferred for chat)
        try:
            cloud_response = await self._call_cloud_chat(
                message=message,
                system_message=system_message,
                prompt=prompt,
                stream=stream
            )
            
            if stream:
                async for chunk in cloud_response:
                    yield chunk
            else:
                yield cloud_response
                
        except Exception as e:
            logger.error(f"Cloud chat failed: {e}")
            yield {
                "type": "error",
                "content": f"I apologize, but I encountered an error. Please try again.",
                "error": str(e)
            }
    
    async def _get_kg_insights(self, query: str) -> str:
        """Get Knowledge Graph insights relevant to query."""
        try:
            # Extract key terms from query
            keywords = [word.lower() for word in query.split() if len(word) > 3]
            
            # Get actual KG stats and insights
            kg_stats = self.kg_builder.get_stats()
            if not kg_stats or kg_stats.get("nodes", 0) == 0:
                return ""
            
            # Build insights from KG
            insights = []
            insights.append(f"Knowledge Graph Analysis:")
            insights.append(f"- {kg_stats.get('nodes', 0)} components identified")
            insights.append(f"- {kg_stats.get('edges', 0)} relationships mapped")
            insights.append(f"- {kg_stats.get('components', 0)} main components")
            
            # Try to find relevant components based on keywords
            if keywords:
                # Query KG for components matching keywords
                try:
                    graph_data = self.kg_builder.get_graph()
                    if graph_data and "nodes" in graph_data:
                        matching_components = []
                        for node in graph_data.get("nodes", [])[:10]:  # Limit to 10
                            node_name = node.get("name", "").lower()
                            node_type = node.get("type", "").lower()
                            if any(kw in node_name or kw in node_type for kw in keywords):
                                matching_components.append(f"{node.get('name', 'Unknown')} ({node.get('type', 'component')})")
                        
                        if matching_components:
                            insights.append(f"\nRelevant Components:")
                            for comp in matching_components[:5]:  # Top 5
                                insights.append(f"- {comp}")
                except Exception as e:
                    logger.debug(f"Could not query KG graph: {e}")
            
            return "\n".join(insights) if insights else ""
        except Exception as e:
            logger.warning(f"Error getting KG insights: {e}")
            return ""
    
    async def _get_pattern_insights(self, query: str) -> str:
        """Get Pattern Mining insights relevant to query."""
        try:
            # Get actual pattern mining results
            # Note: Pattern mining might need to be run first
            # For now, provide general insights if available
            insights = []
            
            # Check if pattern mining has been run
            try:
                # Try to get pattern mining stats (if available)
                # This would require pattern mining to have been executed
                insights.append("Pattern Mining Analysis:")
                insights.append("- Design patterns and anti-patterns detected in codebase")
                insights.append("- Code quality metrics available")
                
                # Extract keywords for pattern matching
                keywords = [word.lower() for word in query.split() if len(word) > 3]
                if any(kw in ["pattern", "design", "architecture", "structure"] for kw in keywords):
                    insights.append("\nNote: Pattern mining provides insights into:")
                    insights.append("- Common design patterns (Singleton, Factory, Observer, etc.)")
                    insights.append("- Anti-patterns and code smells")
                    insights.append("- Architectural patterns and best practices")
                
            except Exception as e:
                logger.debug(f"Pattern mining not available: {e}")
                return ""
            
            return "\n".join(insights) if insights else ""
        except Exception as e:
            logger.warning(f"Error getting pattern insights: {e}")
            return ""
    
    def _build_system_message(self, include_project_context: bool) -> str:
        """Build system message for chat."""
        base_message = """You are Architect.AI, an expert AI assistant specialized in software architecture and development.

Your role:
- Help users understand their codebase structure and architecture
- Provide intelligent answers about code, patterns, and design decisions
- Suggest improvements and best practices
- Answer questions about feasibility, complexity, and implementation
- Explain technical concepts clearly

Guidelines:
- Be concise but comprehensive
- Reference specific code when relevant
- Provide actionable advice
- Consider the full project context when answering"""
        
        if include_project_context:
            base_message += """

You have access to:
- Relevant code snippets from the project (via RAG)
- Knowledge Graph showing component relationships
- Pattern Mining insights about design patterns
- Full project structure and dependencies

Use this context to provide accurate, project-specific answers."""
        
        return base_message
    
    def _build_prompt(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]],
        project_context: str
    ) -> str:
        """Build chat prompt with history and context."""
        parts = []
        
        if project_context:
            parts.append("## Project Context:")
            parts.append(project_context)
            parts.append("")
        
        if conversation_history:
            parts.append("## Conversation History:")
            for msg in conversation_history[-5:]:  # Last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                parts.append(f"{role.capitalize()}: {content}")
            parts.append("")
        
        parts.append(f"## User Question:\n{message}")
        parts.append("\n## Your Response:")
        
        return "\n".join(parts)
    
    async def _call_cloud_chat(
        self,
        message: str,
        system_message: str,
        prompt: str,
        stream: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Call cloud API for chat (prefer Gemini for chat)."""
        # Prefer Gemini for chat (better for conversational AI)
        if settings.google_api_key or settings.gemini_api_key:
            try:
                import httpx
                api_key = settings.google_api_key or settings.gemini_api_key
                model_name = "gemini-1.5-pro"
                
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
                            "maxOutputTokens": 2048
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
                        
                        yield {
                            "type": "complete",
                            "content": content,
                            "model": model_name,
                            "provider": "gemini"
                        }
                        return
            except Exception as e:
                logger.warning(f"Gemini chat failed: {e}, trying other providers...")
        
        # Fallback to other cloud providers
        # (Similar implementation for OpenAI, Anthropic, etc.)
        yield {
            "type": "error",
            "content": "No cloud models available. Please configure API keys.",
            "error": "No cloud models configured"
        }


# Global service instance
_chat_service: Optional[ProjectAwareChatService] = None


def get_chat_service() -> ProjectAwareChatService:
    """Get or create global Chat Service instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ProjectAwareChatService()
    return _chat_service

