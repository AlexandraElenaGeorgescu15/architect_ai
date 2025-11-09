"""
Smart Model Selector - Priority-based model selection with quality thresholds

Intelligently selects and retries models based on:
1. Artifact type → model priority list
2. Quality score validation (min 80/100)
3. Automatic cloud fallback with reduced context
"""

import sys
# Enable UTF-8 output on Windows
if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        pass

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModelAttempt:
    """Result of a single model attempt"""
    model_name: str
    content: str
    quality_score: float
    is_valid: bool
    validation_errors: List[str]
    generation_time: float
    is_local: bool


@dataclass
class SelectionResult:
    """Final result of smart model selection"""
    success: bool
    content: str
    model_used: str
    quality_score: float
    attempts: List[ModelAttempt]
    used_cloud_fallback: bool
    total_time: float
    error_message: str = ""


class SmartModelSelector:
    """
    Smart model selector with priority-based retries and quality validation.
    
    Features:
    - Tries models in priority order until quality threshold met
    - Validates output quality (min 80/100)
    - Automatic cloud fallback with reduced context
    - VRAM-aware model management
    """
    
    def __init__(
        self, 
        ollama_client,
        validator,
        artifact_mapper,
        min_quality_threshold: int = 80
    ):
        """
        Initialize smart model selector.
        
        Args:
            ollama_client: OllamaClient instance
            validator: ArtifactValidator instance
            artifact_mapper: ArtifactModelMapper instance
            min_quality_threshold: Minimum quality score (default 80)
        """
        self.ollama_client = ollama_client
        self.validator = validator
        self.artifact_mapper = artifact_mapper
        self.min_quality_threshold = min_quality_threshold
        
        # Cloud provider limits (tokens)
        self.CLOUD_LIMITS = {
            'gemini': 30000,    # Gemini 2.0 Flash
            'groq': 12000,      # Llama 3.3 70B
            'openai': 8192      # GPT-4
        }
    
    async def select_and_generate(
        self,
        artifact_type: str,
        prompt: str,
        system_message: Optional[str] = None,
        cloud_fallback_fn: Optional[Callable] = None,
        temperature: float = 0.2,
        **kwargs
    ) -> SelectionResult:
        """
        Select best model and generate artifact with quality validation.
        
        Tries models in priority order:
        1. Try primary model
        2. Validate quality (must be >= 80)
        3. If failed, try next model in priority list
        4. If all local models fail, fall back to cloud with reduced context
        
        Args:
            artifact_type: Type of artifact to generate
            prompt: Generation prompt
            system_message: System message (optional)
            cloud_fallback_fn: Cloud generation function (optional)
            temperature: Generation temperature
            **kwargs: Additional arguments
            
        Returns:
            SelectionResult with best generation result
        """
        import time
        start_time = time.time()
        
        # Get priority models for artifact type
        priority_models = self.artifact_mapper.get_priority_models(artifact_type)
        quality_threshold = self.artifact_mapper.get_quality_threshold(artifact_type)
        
        print(f"[MODEL_SELECT] Artifact: {artifact_type}")
        print(f"[MODEL_SELECT] Priority models: {priority_models}")
        print(f"[MODEL_SELECT] Quality threshold: {quality_threshold}/100")
        
        attempts: List[ModelAttempt] = []
        best_attempt: Optional[ModelAttempt] = None
        
        # Try each model in priority order
        for i, model_name in enumerate(priority_models):
            print(f"\n[MODEL_SELECT] Attempt {i+1}/{len(priority_models)}: {model_name}")
            
            try:
                # Load and generate with model
                attempt_start = time.time()
                
                print(f"[INFO] Loading model {model_name}...")
                await self.ollama_client.ensure_model_available(model_name)
                
                print(f"[INFO] Generating with {model_name}...")
                response = await self.ollama_client.generate(
                    model_name=model_name,
                    prompt=prompt,
                    system_message=system_message,
                    temperature=temperature
                )
                
                generation_time = time.time() - attempt_start
                
                if not response.success or not response.content:
                    print(f"[WARN] {model_name} generation failed: {response.error_message}")
                    continue
                
                # Validate output quality
                print(f"[VALIDATION] Validating output from {model_name}...")
                validation_result = await self.validator.validate_artifact(
                    content=response.content,
                    artifact_type=artifact_type
                )
                
                attempt = ModelAttempt(
                    model_name=model_name,
                    content=response.content,
                    quality_score=validation_result.score,
                    is_valid=validation_result.is_valid,
                    validation_errors=validation_result.errors,
                    generation_time=generation_time,
                    is_local=True
                )
                attempts.append(attempt)
                
                print(f"[VALIDATION] Quality: {validation_result.score:.1f}/100 (threshold: {quality_threshold})")
                
                # Check if quality threshold met
                if validation_result.score >= quality_threshold:
                    print(f"[SUCCESS] ✅ {model_name} met quality threshold!")
                    total_time = time.time() - start_time
                    return SelectionResult(
                        success=True,
                        content=response.content,
                        model_used=model_name,
                        quality_score=validation_result.score,
                        attempts=attempts,
                        used_cloud_fallback=False,
                        total_time=total_time
                    )
                else:
                    print(f"[WARN] ⚠️ {model_name} below threshold ({validation_result.score:.1f} < {quality_threshold})")
                    if validation_result.errors:
                        print(f"[VALIDATION] Errors: {', '.join(validation_result.errors[:3])}")
                    
                    # Keep track of best attempt so far
                    if best_attempt is None or validation_result.score > best_attempt.quality_score:
                        best_attempt = attempt
            
            except Exception as e:
                print(f"[ERROR] {model_name} failed: {e}")
                continue
        
        # All local models failed - try cloud fallback
        print(f"\n[MODEL_SELECT] ⚠️ All local models below threshold. Attempting cloud fallback...")
        
        if cloud_fallback_fn:
            try:
                # Reduce context for cloud (compress prompt)
                reduced_prompt = self._compress_prompt_for_cloud(prompt)
                
                print(f"[CLOUD_FALLBACK] Compressed prompt: {len(prompt)} → {len(reduced_prompt)} chars")
                
                cloud_start = time.time()
                cloud_result = await cloud_fallback_fn(
                    prompt=reduced_prompt,
                    system_message=system_message,
                    artifact_type=artifact_type
                )
                
                if cloud_result:
                    # Validate cloud result
                    validation_result = await self.validator.validate_artifact(
                        content=cloud_result,
                        artifact_type=artifact_type
                    )
                    
                    cloud_time = time.time() - cloud_start
                    total_time = time.time() - start_time
                    
                    cloud_attempt = ModelAttempt(
                        model_name="cloud_provider",
                        content=cloud_result,
                        quality_score=validation_result.score,
                        is_valid=validation_result.is_valid,
                        validation_errors=validation_result.errors,
                        generation_time=cloud_time,
                        is_local=False
                    )
                    attempts.append(cloud_attempt)
                    
                    print(f"[CLOUD_FALLBACK] ✅ Success! Quality: {validation_result.score:.1f}/100")
                    
                    return SelectionResult(
                        success=True,
                        content=cloud_result,
                        model_used="cloud_provider",
                        quality_score=validation_result.score,
                        attempts=attempts,
                        used_cloud_fallback=True,
                        total_time=total_time
                    )
            except Exception as e:
                print(f"[ERROR] Cloud fallback failed: {e}")
        
        # Everything failed - return best attempt if available
        if best_attempt:
            total_time = time.time() - start_time
            print(f"[FALLBACK] Using best local attempt: {best_attempt.model_name} ({best_attempt.quality_score:.1f}/100)")
            return SelectionResult(
                success=False,
                content=best_attempt.content,
                model_used=best_attempt.model_name,
                quality_score=best_attempt.quality_score,
                attempts=attempts,
                used_cloud_fallback=False,
                total_time=total_time,
                error_message=f"Best quality: {best_attempt.quality_score:.1f}/100 (threshold: {quality_threshold})"
            )
        
        # Complete failure
        total_time = time.time() - start_time
        return SelectionResult(
            success=False,
            content="",
            model_used="none",
            quality_score=0.0,
            attempts=attempts,
            used_cloud_fallback=False,
            total_time=total_time,
            error_message="All models failed to generate valid content"
        )
    
    def _compress_prompt_for_cloud(self, prompt: str, target_chars: int = 10000) -> str:
        """
        Intelligently compress prompt for cloud providers with token limits.
        
        Strategy:
        1. Keep system instructions intact
        2. Reduce RAG context (keep most relevant chunks)
        3. Preserve user requirements/notes
        4. Remove redundant sections
        
        Args:
            prompt: Original prompt
            target_chars: Target character count
            
        Returns:
            Compressed prompt
        """
        if len(prompt) <= target_chars:
            return prompt
        
        # Split into sections
        sections = prompt.split('\n\n')
        
        # Identify critical sections (keep intact)
        critical_keywords = [
            'CRITICAL', 'REQUIREMENTS', 'MEETING NOTES', 
            'OUTPUT FORMAT', 'MANDATORY', 'MUST'
        ]
        
        critical_sections = []
        compressible_sections = []
        
        for section in sections:
            is_critical = any(keyword in section.upper() for keyword in critical_keywords)
            if is_critical:
                critical_sections.append(section)
            else:
                compressible_sections.append(section)
        
        # Calculate budget
        critical_size = sum(len(s) for s in critical_sections)
        remaining_budget = target_chars - critical_size - 1000  # Reserve 1000 chars buffer
        
        if remaining_budget <= 0:
            # Critical sections already exceed budget - truncate them carefully
            print("[WARN] Critical sections exceed budget, truncating carefully...")
            compressed_critical = []
            budget_per_section = target_chars // len(critical_sections) if critical_sections else target_chars
            for section in critical_sections:
                if len(section) > budget_per_section:
                    compressed_critical.append(section[:budget_per_section] + "...[truncated]")
                else:
                    compressed_critical.append(section)
            return '\n\n'.join(compressed_critical)
        
        # Compress compressible sections
        compressed_compressible = []
        chars_per_section = remaining_budget // len(compressible_sections) if compressible_sections else remaining_budget
        
        for section in compressible_sections:
            if len(section) > chars_per_section:
                # Keep first 70% of allocation for context
                keep_chars = int(chars_per_section * 0.7)
                compressed_compressible.append(section[:keep_chars] + "...[more context omitted]")
            else:
                compressed_compressible.append(section)
        
        # Reconstruct prompt
        result = '\n\n'.join(critical_sections + compressed_compressible)
        
        print(f"[COMPRESS] Compressed: {len(prompt)} → {len(result)} chars ({len(result)/len(prompt)*100:.1f}%)")
        
        return result


class ContextOptimizer:
    """
    Static utility class for optimizing/compressing context for cloud models.
    
    Cloud models have token limits:
    - Gemini: ~30K tokens
    - Groq: ~12K tokens  
    - OpenAI GPT-4: ~8K tokens
    
    This compressor reduces large prompts intelligently.
    """
    
    @staticmethod
    async def compress_prompt_for_cloud(prompt: str, max_tokens: int = 3000) -> str:
        """
        Compress prompt to fit within token limits for cloud providers.
        
        CRITICAL: OpenAI GPT-4 has 8192 token limit TOTAL (prompt + completion).
        With 4000 tokens for completion, we have ~4000 for prompt.
        To be safe, target 3000 tokens ≈ 12K chars.
        
        Args:
            prompt: Original prompt text
            max_tokens: Maximum tokens allowed (default 3000 to stay under 8192 total)
            
        Returns:
            Compressed prompt
        """
        # Conservative estimate: 1 token ≈ 4 characters
        # Target 3000 tokens = 12K chars to leave room for completion (4000 tokens)
        max_chars = max_tokens * 4
        
        if len(prompt) <= max_chars:
            return prompt
        
        # Split into sections
        sections = prompt.split('\n\n')
        
        # Identify critical sections (keep intact)
        critical_keywords = [
            'CRITICAL', 'REQUIREMENTS', 'MEETING NOTES', 
            'OUTPUT FORMAT', 'MANDATORY', 'MUST', 'GENERATE',
            'TASK:', 'YOUR TASK:', '### Instruction'
        ]
        
        critical_sections = []
        compressible_sections = []
        
        for section in sections:
            is_critical = any(keyword in section.upper() for keyword in critical_keywords)
            if is_critical or len(section) < 500:  # Keep short sections
                critical_sections.append(section)
            else:
                compressible_sections.append(section)
        
        # Calculate budget
        critical_size = sum(len(s) for s in critical_sections)
        remaining_budget = max_chars - critical_size - 500  # Reserve 500 chars buffer
        
        if remaining_budget <= 0:
            # Critical sections exceed budget - truncate them more aggressively
            compressed_critical = []
            budget_per_section = max_chars // len(critical_sections) if critical_sections else max_chars
            for section in critical_sections:
                if len(section) > budget_per_section:
                    # For critical sections, keep first 80% of budget
                    keep_chars = int(budget_per_section * 0.8)
                    compressed_critical.append(section[:keep_chars] + "...[truncated to fit cloud API limits]")
                else:
                    compressed_critical.append(section)
            result = '\n\n'.join(compressed_critical)
            print(f"[CONTEXT_COMPRESSION] AGGRESSIVE: {len(prompt)} → {len(result)} chars (critical only)")
            return result
        
        # Compress compressible sections (usually RAG context) - BE AGGRESSIVE
        compressed_compressible = []
        if compressible_sections:
            chars_per_section = remaining_budget // len(compressible_sections)
            
            for section in compressible_sections:
                if len(section) > chars_per_section:
                    # Keep only first 50% of allocation (more aggressive)
                    keep_chars = int(chars_per_section * 0.5)
                    # Try to cut at sentence boundary
                    cut_point = section.rfind('.', 0, keep_chars)
                    if cut_point > keep_chars * 0.5:
                        compressed_compressible.append(section[:cut_point+1] + "\n...[RAG context truncated for cloud API]")
                    else:
                        compressed_compressible.append(section[:keep_chars] + "...[truncated]")
                else:
                    compressed_compressible.append(section)
        
        # Reconstruct
        result = '\n\n'.join(critical_sections + compressed_compressible)
        
        print(f"[CONTEXT_COMPRESSION] Compressed: {len(prompt)} → {len(result)} chars ({len(result)/len(prompt)*100:.1f}% retained)")
        print(f"[CONTEXT_COMPRESSION] Estimated tokens: ~{len(result) // 4} (target: {max_tokens})")
        
        return result


# -------------------------------
# Token safety utilities (hard guard before API calls)
# -------------------------------
from typing import Tuple

def _get_tiktoken_encoding(model_name: str = "gpt-4"):
    """
    Get a tiktoken encoding for the given model name, with safe fallback.
    """
    try:
        import tiktoken  # type: ignore
        try:
            return tiktoken.encoding_for_model(model_name)
        except Exception:
            # Fallback works for GPT-4/GPT-3.5 families
            return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None  # tiktoken not available


def _count_message_tokens_openai(messages: List[Dict[str, str]], model_name: str = "gpt-4") -> int:
    """
    Estimate token count for OpenAI-style chat messages using tiktoken when available.
    Falls back to a rough 1 token ≈ 4 chars estimate if tiktoken is not present.
    """
    encoding = _get_tiktoken_encoding(model_name)
    if encoding is None:
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 4

    # Simple approximation: sum of content tokens. (Chat overhead ignored for safety margin)
    return sum(len(encoding.encode(m.get("content", ""))) for m in messages)


def _trim_text_to_tokens(text: str, max_tokens: int, model_name: str = "gpt-4") -> str:
    """
    Trim a text string to the specified token budget using tiktoken (if available).
    Falls back to character-based trimming when necessary.
    """
    if max_tokens <= 0:
        return ""

    encoding = _get_tiktoken_encoding(model_name)
    if encoding is None:
        # Rough fallback: 1 token ≈ 4 chars
        approx_chars = max_tokens * 4
        return text[:approx_chars]

    tokens = encoding.encode(text)
    if len(tokens) <= max_tokens:
        return text

    # Keep room for an ellipsis
    keep = max(0, max_tokens - 3)
    trimmed = encoding.decode(tokens[:keep]) + "..."
    return trimmed


def fit_openai_messages_to_context(
    messages: List[Dict[str, str]],
    model_name: str,
    context_window: int,
    max_completion_tokens: int,
    safety_margin: int = 200,
) -> Tuple[List[Dict[str, str]], int]:
    """
    Hard fail-safe: ensure chat messages fit within the model's context window,
    reserving a completion budget and a safety margin. Trims the last user message,
    then earlier messages if required.

    Returns: (trimmed_messages, final_prompt_token_count)
    """
    if not messages:
        return messages, 0

    budget = max(0, context_window - max_completion_tokens - safety_margin)
    if budget <= 0:
        # Nothing left for prompt; keep only a tiny stub
        last = messages[-1].copy()
        last["content"] = _trim_text_to_tokens(last.get("content", ""), 64, model_name)
        return [last], _count_message_tokens_openai([last], model_name)

    def current_tokens() -> int:
        return _count_message_tokens_openai(messages, model_name)

    tokens = current_tokens()
    if tokens <= budget:
        return messages, tokens

    # First, trim the last user message
    for idx in range(len(messages) - 1, -1, -1):
        if messages[idx].get("role") == "user":
            overflow = tokens - budget
            # Trim by overflow + some buffer
            target = max(64, _count_message_tokens_openai([messages[idx]], model_name) - overflow - 64)
            messages[idx] = messages[idx].copy()
            messages[idx]["content"] = _trim_text_to_tokens(messages[idx].get("content", ""), target, model_name)
            tokens = current_tokens()
            break

    # If still too long, trim from the beginning (system/assistant first), keeping order
    start = 0
    while tokens > budget and start < len(messages) - 1:
        # Avoid removing the final user instruction entirely; trim older messages more aggressively
        candidate = messages[start]
        # Prefer trimming system/assistant over user
        if candidate.get("role") in ("system", "assistant"):
            # Keep a tiny stub
            candidate = candidate.copy()
            candidate["content"] = _trim_text_to_tokens(candidate.get("content", ""), 64, model_name)
            messages[start] = candidate
        start += 1
        tokens = current_tokens()

    # Final guard: if still too long, nuke everything but the last user message stub
    if tokens > budget and messages:
        last_user = next((m for m in reversed(messages) if m.get("role") == "user"), messages[-1])
        stub = last_user.copy()
        stub["content"] = _trim_text_to_tokens(stub.get("content", ""), budget, model_name)
        messages = [stub]
        tokens = _count_message_tokens_openai(messages, model_name)

    return messages, tokens


# Global instance
_selector_instance: Optional[SmartModelSelector] = None


def get_smart_selector(
    ollama_client,
    validator,
    artifact_mapper,
    min_quality_threshold: int = 80
) -> SmartModelSelector:
    """Get or create global smart model selector instance"""
    global _selector_instance
    if _selector_instance is None:
        _selector_instance = SmartModelSelector(
            ollama_client=ollama_client,
            validator=validator,
            artifact_mapper=artifact_mapper,
            min_quality_threshold=min_quality_threshold
        )
    return _selector_instance

