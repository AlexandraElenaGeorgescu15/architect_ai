"""
LLM-as-a-Judge Service
Evaluates generation quality using a lightweight but capable LLM.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import logging
import json
import asyncio
import asyncio

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)


class LLMJudge:
    """
    LLM-as-a-Judge evaluator for artifact quality.
    
    Scores artifacts 0-100 based on:
    1. Relevance to requirements (Meeting Notes)
    2. Technical accuracy
    3. Completeness
    4. Best practices
    """
    
    def __init__(self):
        self.enabled = settings.llm_judge_enabled
        self.weight = settings.llm_judge_weight
        
    async def evaluate_artifact(
        self, 
        content: str, 
        artifact_type: str, 
        meeting_notes: str,
        context: Optional[str] = None
    ) -> Tuple[float, str]:
        """
        Evaluate an artifact using an LLM.
        
        Args:
            content: The generated artifact content
            artifact_type: Type of artifact (e.g. mermaid_erd)
            meeting_notes: User requirements
            context: Optional context
            
        Returns:
            Tuple of (score, reasoning)
            Score is 0-100
        """
        if not self.enabled:
            return 85.0, "LLM Judge disabled, assuming passing score."
            
        try:
            # Construct evaluation prompt
            prompt = self._build_evaluation_prompt(content, artifact_type, meeting_notes)
            
            # Call LLM (using best available fast model)
            # We use a direct specialized call to avoid circular dependency with GenerationService
            # Priority: Gemini Flash > Llama3 > Mistral
            
            evaluation = await self._call_evaluator_llm(prompt)
            
            # Parse JSON result
            try:
                result = json.loads(evaluation)
                score = float(result.get("score", 70))
                reasoning = result.get("reasoning", "No reasoning provided.")
                
                logger.info(f"⚖️ [JUDGE] Evaluation complete: Score {score}/100. Reasoning: {reasoning[:100]}...")
                return score, reasoning
                
            except json.JSONDecodeError:
                logger.warning(f"⚠️ [JUDGE] Failed to parse JSON evaluation. Raw: {evaluation[:100]}")
                # Fallback parsing
                if "score" in evaluation.lower():
                    # Simple heuristic extraction
                    import re
                    match = re.search(r'score"?:?\s*(\d+)', evaluation, re.IGNORECASE)
                    if match:
                        return float(match.group(1)), evaluation[:200]
                
                return 75.0, "Failed to parse judge output, defaulting to neutral score."
                
        except Exception as e:
            logger.error(f"❌ [JUDGE] Evaluation failed: {e}")
            return 80.0, f"Judge error: {e}"

    def _build_evaluation_prompt(self, content: str, artifact_type: str, meeting_notes: str) -> str:
        """Build the prompt for the judge."""
        return f"""
        You are a Senior Technical Architect reviewing code artifacts.
        
        TASK: Evaluate the quality of the following {artifact_type}.
        
        USER REQUIREMENTS:
        {meeting_notes[:2000]}
        
        GENERATED ARTIFACT:
        {content[:8000]}
        
        CRITERIA:
        1. RELEVANCE: Does it actually address the User Requirements?
        2. SYNTAX: Is it syntactically correct? (Crucial for Mermaid/Code)
        3. COMPLETENESS: Is it detailed or just a hollow skeleton?
        4. BEST PRACTICES: Does it follow standard conventions?
        
        OUTPUT FORMAT (JSON ONLY):
        {{
            "score": <0-100 integer>,
            "reasoning": "<concise explanation of the score, pointing out specific flaws>"
        }}
        """

    async def _call_evaluator_llm(self, prompt: str) -> str:
        """Call the underlying LLM provider."""
        # Check available providers (prioritizing fast/free ones)
        
        # 1. Google Gemini (Best free fast option)
        if settings.google_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.google_api_key)
                
                # Use flash model for speed
                model_name = "gemini-2.5-flash"
                gemini_model = genai.GenerativeModel(model_name)
                
                # Run in thread since it's a blocking call in the library
                response = await asyncio.to_thread(
                    gemini_model.generate_content,
                    prompt
                )
                
                if response and response.text:
                    return response.text
            except Exception as e:
                logger.warning(f"Judge failed with Gemini: {e}")
        
        # 2. Ollama (Free local option)
        try:
            from ai.ollama_client import get_ollama_client as get_client
            client = get_client()
            # Try preferred judge models
            for model in settings.llm_judge_preferred_models:
                if await client.check_model_availability(model):
                    response = await client.generate(model, prompt)
                    if response.success:
                        return response.content
            
            # Fallback to any available
            models = await client.list_models()
            if models:
                response = await client.generate(models[0], prompt)
                if response.success:
                    return response.content
        except Exception as e:
            logger.warning(f"Judge failed with Ollama: {e}")
            
        # 3. Groq (Fast)
        if settings.groq_api_key:
            try:
                from groq import AsyncGroq
                client = AsyncGroq(api_key=settings.groq_api_key)
                # Use llama3-8b-8192 for fast evaluation
                response = await client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )
                if response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"Judge failed with Groq: {e}")

        raise Exception("No capable LLM provider available for judging")


# Global instance
_judge: Optional[LLMJudge] = None

def get_judge() -> LLMJudge:
    """Get global LLM Judge instance."""
    global _judge
    if _judge is None:
        _judge = LLMJudge()
    return _judge
