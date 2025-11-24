"""
Synthetic Dataset Service - Generate training examples using FREE models.

Supports:
- Free Gemini API (gemini-2.0-flash)
- Free Grok API (grok-beta)
- Local Phi-3.5-mini-instruct (HuggingFace, no quota)
- Local Phi-4-mini (HuggingFace, no quota)
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import asyncio
import json
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings
from backend.models.dto import ArtifactType

logger = logging.getLogger(__name__)

# Optional imports with graceful degradation
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google GenerativeAI not available")

try:
    from openai import OpenAI
    OPENAI_CLIENT_AVAILABLE = True
except ImportError:
    OPENAI_CLIENT_AVAILABLE = False
    logger.warning("OpenAI client not available (needed for Grok)")

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers not available (needed for local Phi models)")


class SyntheticDatasetService:
    """
    Generate synthetic training examples using free/local models.
    
    Features:
    - Artifact-specific prompts (ERD, Code, API Docs, etc.)
    - Multiple model backends (Gemini, Grok, Phi local)
    - Batch generation with progress tracking
    - Integration with finetuning_pool
    - Quality filtering
    """
    
    def __init__(self):
        """Initialize Synthetic Dataset Service."""
        self.batch_size = 10  # Generate 10 examples per API call
        self.local_model = None
        self.local_tokenizer = None
        
        # Initialize Gemini if available
        if GEMINI_AVAILABLE and settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            logger.info("Gemini API configured for synthetic generation")
        
        logger.info("Synthetic Dataset Service initialized")
    
    def _get_artifact_specific_prompt(self, artifact_type: str) -> Dict[str, str]:
        """Get artifact-specific generation prompts."""
        prompts = {
            "mermaid_erd": {
                "topic": "Database ERD diagrams for various software systems",
                "instruction_examples": [
                    "Design a database for an e-commerce platform",
                    "Create an ERD for a hospital management system",
                    "Model a social media application database"
                ],
                "system": "You are an expert database architect. Generate realistic ERD requirements and corresponding Mermaid diagrams."
            },
            "mermaid_sequence": {
                "topic": "Sequence diagrams for software interactions",
                "instruction_examples": [
                    "Show the authentication flow for a web app",
                    "Diagram the checkout process in an e-commerce system",
                    "Model API request/response flow"
                ],
                "system": "You are a software architect. Generate realistic interaction scenarios and Mermaid sequence diagrams."
            },
            "code_prototype": {
                "topic": "Code implementations in Python, JavaScript, TypeScript",
                "instruction_examples": [
                    "Implement a REST API endpoint for user authentication",
                    "Create a React component for data visualization",
                    "Write a Python function for data processing"
                ],
                "system": "You are a senior software engineer. Generate realistic coding requirements and production-ready implementations."
            },
            "api_docs": {
                "topic": "API documentation for REST endpoints",
                "instruction_examples": [
                    "Document a user management API",
                    "Create API docs for a payment gateway",
                    "Document a search API endpoint"
                ],
                "system": "You are a technical writer. Generate comprehensive API documentation with examples."
            },
            "jira_story": {
                "topic": "JIRA user stories for software features",
                "instruction_examples": [
                    "Write a story for implementing user authentication",
                    "Create a story for adding search functionality",
                    "Document a story for payment integration"
                ],
                "system": "You are a product manager. Generate well-structured JIRA stories with acceptance criteria."
            },
            "architecture_diagram": {
                "topic": "System architecture diagrams",
                "instruction_examples": [
                    "Design a microservices architecture",
                    "Create a cloud infrastructure diagram",
                    "Model a distributed system architecture"
                ],
                "system": "You are a solutions architect. Generate comprehensive architecture descriptions and diagrams."
            }
        }
        
        return prompts.get(artifact_type, {
            "topic": f"Generate {artifact_type} examples",
            "instruction_examples": ["Create a detailed example"],
            "system": f"You are an expert in generating {artifact_type}."
        })
    
    async def generate_bootstrap_dataset(
        self,
        artifact_type: str,
        target_count: int = 50,
        model_backend: str = "auto",
        complexity: str = "Mixed"
    ) -> Dict[str, Any]:
        """
        Generate synthetic training examples for bootstrapping.
        
        Args:
            artifact_type: Type of artifact to generate examples for
            target_count: Number of examples to generate
            model_backend: "gemini", "grok", "phi-local", or "auto"
            complexity: "Simple", "Mixed", or "Complex"
        
        Returns:
            Dictionary with generation results
        """
        logger.info(f"Starting synthetic generation: {artifact_type}, target={target_count}, backend={model_backend}")
        
        # Auto-select backend
        if model_backend == "auto":
            if GEMINI_AVAILABLE and settings.GEMINI_API_KEY:
                model_backend = "gemini"
            elif TRANSFORMERS_AVAILABLE:
                model_backend = "phi-local"
            elif OPENAI_CLIENT_AVAILABLE and settings.GROQ_API_KEY:
                model_backend = "grok"
            else:
                raise ValueError("No synthetic generation backend available")
        
        generated_examples = []
        generated_count = 0
        errors = []
        
        # Generate in batches
        while generated_count < target_count:
            try:
                batch = await self._generate_batch(
                    artifact_type=artifact_type,
                    complexity=complexity,
                    backend=model_backend,
                    existing_count=generated_count
                )
                
                generated_examples.extend(batch)
                generated_count = len(generated_examples)
                
                logger.info(f"Generated batch: {len(batch)} examples, total: {generated_count}/{target_count}")
                
                # Small delay to be nice to APIs
                await asyncio.sleep(1)
                
            except Exception as e:
                error_msg = f"Batch generation failed: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                
                # If too many errors, stop
                if len(errors) >= 3:
                    break
                
                # Wait longer before retry
                await asyncio.sleep(5)
        
        return {
            "artifact_type": artifact_type,
            "generated_count": generated_count,
            "target_count": target_count,
            "backend": model_backend,
            "examples": generated_examples,
            "errors": errors,
            "success": generated_count > 0
        }
    
    async def _generate_batch(
        self,
        artifact_type: str,
        complexity: str,
        backend: str,
        existing_count: int
    ) -> List[Dict[str, Any]]:
        """Generate a batch of examples using specified backend."""
        
        if backend == "gemini":
            return await self._generate_batch_gemini(artifact_type, complexity, existing_count)
        elif backend == "grok":
            return await self._generate_batch_grok(artifact_type, complexity, existing_count)
        elif backend == "phi-local":
            return await self._generate_batch_phi_local(artifact_type, complexity, existing_count)
        else:
            raise ValueError(f"Unknown backend: {backend}")
    
    async def _generate_batch_gemini(
        self,
        artifact_type: str,
        complexity: str,
        existing_count: int
    ) -> List[Dict[str, Any]]:
        """Generate batch using Gemini API (free tier)."""
        if not GEMINI_AVAILABLE:
            raise RuntimeError("Gemini not available")
        
        prompt_config = self._get_artifact_specific_prompt(artifact_type)
        
        # Build generation prompt
        prompt = f"""
Generate {self.batch_size} unique, high-quality training examples for {artifact_type}.

Topic: {prompt_config['topic']}
Complexity: {complexity}
Current dataset size: {existing_count}

Requirements:
1. Each example must have:
   - instruction: A clear, realistic requirement or question
   - input: Optional context (empty string if not needed)
   - output: The ideal, production-ready response
   - category: A short tag for the sub-topic (e.g., 'Authentication', 'Database', 'API')
   - difficulty: 'Easy', 'Medium', or 'Hard'

2. Ensure diversity in:
   - Phrasing and style
   - Technical complexity
   - Use cases and scenarios

3. Output ONLY valid JSON array format:
[
  {{
    "instruction": "...",
    "input": "...",
    "output": "...",
    "category": "...",
    "difficulty": "..."
  }}
]

Focus on realistic, production-ready examples that would help train an AI to generate {artifact_type}.
"""
        
        try:
            model = genai.GenerativeModel(
                model_name='gemini-2.0-flash-exp',  # Free tier
                generation_config={
                    'temperature': 0.8,
                    'top_p': 0.95,
                    'max_output_tokens': 8192,
                }
            )
            
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                request_options={"timeout": 60}
            )
            
            # Parse JSON response
            text = response.text.strip()
            
            # Remove markdown code blocks if present
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
                text = text.strip()
            
            examples = json.loads(text)
            
            # Ensure it's a list
            if not isinstance(examples, list):
                examples = [examples]
            
            # Validate and clean examples
            valid_examples = []
            for ex in examples:
                if self._validate_example(ex):
                    valid_examples.append(ex)
            
            return valid_examples[:self.batch_size]
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise
    
    async def _generate_batch_grok(
        self,
        artifact_type: str,
        complexity: str,
        existing_count: int
    ) -> List[Dict[str, Any]]:
        """Generate batch using Grok API (free tier via Groq)."""
        if not OPENAI_CLIENT_AVAILABLE:
            raise RuntimeError("OpenAI client not available for Grok")
        
        if not settings.GROQ_API_KEY:
            raise RuntimeError("Groq API key not configured")
        
        # Groq client (uses OpenAI SDK)
        client = OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
        
        prompt_config = self._get_artifact_specific_prompt(artifact_type)
        
        system_message = f"{prompt_config['system']} Generate {self.batch_size} training examples in JSON array format."
        
        user_message = f"""
Generate {self.batch_size} unique examples for {artifact_type}.

Complexity: {complexity}
Current count: {existing_count}

Output format (JSON array):
[{{"instruction": "...", "input": "...", "output": "...", "category": "...", "difficulty": "Easy|Medium|Hard"}}]

Ensure diversity and production-ready quality.
"""
        
        try:
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="mixtral-8x7b-32768",  # Free on Groq
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.8,
                max_tokens=4096
            )
            
            text = response.choices[0].message.content.strip()
            
            # Parse JSON
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
                text = text.strip()
            
            examples = json.loads(text)
            
            if not isinstance(examples, list):
                examples = [examples]
            
            valid_examples = []
            for ex in examples:
                if self._validate_example(ex):
                    valid_examples.append(ex)
            
            return valid_examples[:self.batch_size]
            
        except Exception as e:
            logger.error(f"Grok generation failed: {e}")
            raise
    
    async def _generate_batch_phi_local(
        self,
        artifact_type: str,
        complexity: str,
        existing_count: int
    ) -> List[Dict[str, Any]]:
        """Generate batch using local Phi model (no API quota limits)."""
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("Transformers not available for local Phi")
        
        # Lazy load model (only once)
        if self.local_model is None:
            logger.info("Loading local Phi-3.5-mini-instruct model...")
            model_name = "microsoft/Phi-3.5-mini-instruct"
            
            self.local_tokenizer = await asyncio.to_thread(
                AutoTokenizer.from_pretrained,
                model_name,
                trust_remote_code=True
            )
            
            self.local_model = await asyncio.to_thread(
                AutoModelForCausalLM.from_pretrained,
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto",
                trust_remote_code=True
            )
            
            logger.info("Phi model loaded successfully")
        
        prompt_config = self._get_artifact_specific_prompt(artifact_type)
        
        # Phi-3.5 uses chat format
        messages = [
            {"role": "system", "content": prompt_config['system']},
            {"role": "user", "content": f"""Generate {self.batch_size} training examples for {artifact_type}.

Output as JSON array: [{{"instruction": "...", "input": "...", "output": "...", "category": "...", "difficulty": "..."}}]

Ensure diversity and quality."""}
        ]
        
        try:
            # Apply chat template
            prompt = self.local_tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            # Generate
            inputs = self.local_tokenizer(prompt, return_tensors="pt").to(self.local_model.device)
            
            outputs = await asyncio.to_thread(
                self.local_model.generate,
                **inputs,
                max_new_tokens=2048,
                temperature=0.8,
                do_sample=True,
                top_p=0.95
            )
            
            generated_text = self.local_tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract JSON from response
            # Phi often includes the prompt, so we need to extract just the JSON
            json_start = generated_text.find('[')
            json_end = generated_text.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = generated_text[json_start:json_end]
                examples = json.loads(json_text)
                
                if not isinstance(examples, list):
                    examples = [examples]
                
                valid_examples = []
                for ex in examples:
                    if self._validate_example(ex):
                        valid_examples.append(ex)
                
                return valid_examples[:self.batch_size]
            else:
                logger.warning("Could not find JSON in Phi output")
                return []
            
        except Exception as e:
            logger.error(f"Phi local generation failed: {e}")
            raise
    
    def _validate_example(self, example: Dict[str, Any]) -> bool:
        """Validate that example has required fields."""
        required = ['instruction', 'output', 'category', 'difficulty']
        
        for field in required:
            if field not in example or not example[field]:
                return False
        
        # Ensure difficulty is valid
        if example['difficulty'] not in ['Easy', 'Medium', 'Hard']:
            return False
        
        # Ensure minimum length
        if len(example['instruction']) < 10 or len(example['output']) < 20:
            return False
        
        return True
    
    def get_available_backends(self) -> List[Dict[str, Any]]:
        """Get list of available generation backends."""
        backends = []
        
        if GEMINI_AVAILABLE and settings.GEMINI_API_KEY:
            backends.append({
                "id": "gemini",
                "name": "Gemini 2.0 Flash",
                "type": "api",
                "free": True,
                "quota": "1500 requests/day",
                "available": True
            })
        
        if OPENAI_CLIENT_AVAILABLE and settings.GROQ_API_KEY:
            backends.append({
                "id": "grok",
                "name": "Mixtral 8x7B (Groq)",
                "type": "api",
                "free": True,
                "quota": "14,400 requests/day",
                "available": True
            })
        
        if TRANSFORMERS_AVAILABLE:
            backends.append({
                "id": "phi-local",
                "name": "Phi-3.5-mini-instruct (Local)",
                "type": "local",
                "free": True,
                "quota": "Unlimited",
                "available": True
            })
        
        return backends


# Singleton instance
_service_instance = None

def get_service() -> SyntheticDatasetService:
    """Get singleton instance of Synthetic Dataset Service."""
    global _service_instance
    if _service_instance is None:
        _service_instance = SyntheticDatasetService()
    return _service_instance

