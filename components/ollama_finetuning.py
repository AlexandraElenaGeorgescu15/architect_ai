"""
Ollama Fine-Tuning System using Modelfile Approach
Based on: https://medium.com/... (Mohammad Mahdi's approach)

This is MUCH simpler and more effective than LoRA/PEFT fine-tuning:
1. Create examples from feedback
2. Generate Modelfile with system prompt containing examples
3. Build custom Ollama model
4. Model learns from examples (no GPU training needed!)

Advantages over LoRA:
- ✅ No GPU required
- ✅ No complex PEFT dependencies
- ✅ Works with ANY Ollama model
- ✅ Instant "fine-tuning" (just model creation, ~10 seconds)
- ✅ Persistent (survives app restarts)
- ✅ Can be versioned and shared
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json


class OllamaFineTuner:
    """Fine-tune Ollama models using Modelfile approach"""
    
    def __init__(self, base_models_dir: Path = None):
        """
        Initialize Ollama fine-tuner.
        
        Args:
            base_models_dir: Directory to store Modelfiles (default: models/finetuned)
        """
        self.base_models_dir = base_models_dir or Path("finetuned_models/ollama_modelfiles")
        self.base_models_dir.mkdir(parents=True, exist_ok=True)
        
        # Track fine-tuned models
        self.registry_file = self.base_models_dir / "model_registry.json"
        self.registry = self._load_registry()
    
    def _load_registry(self) -> Dict:
        """Load registry of fine-tuned models"""
        if self.registry_file.exists():
            return json.loads(self.registry_file.read_text())
        return {}
    
    def _save_registry(self):
        """Save registry"""
        self.registry_file.write_text(json.dumps(self.registry, indent=2))
    
    def create_modelfile(
        self,
        base_model: str,
        examples: List[Dict[str, str]],
        custom_name: str,
        artifact_type: str = "general"
    ) -> Path:
        """
        Create a Modelfile with examples.
        
        Args:
            base_model: Base Ollama model (e.g., 'llama3:8b-instruct-q4_K_M')
            examples: List of {"question": "...", "answer": "..."} pairs
            custom_name: Name for the custom model
            artifact_type: Type of artifact this model specializes in
            
        Returns:
            Path to created Modelfile
        """
        # Build system prompt with examples
        system_prompt = self._build_system_prompt(examples, artifact_type)
        
        # Create Modelfile content
        modelfile_content = f'''FROM {base_model}

SYSTEM """
{system_prompt}
"""

TEMPLATE "User: {{{{ .Prompt }}}}
Assistant:"

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER top_k 40
'''
        
        # Save Modelfile
        modelfile_path = self.base_models_dir / f"{custom_name}.Modelfile"
        modelfile_path.write_text(modelfile_content)
        
        print(f"[OLLAMA_FT] Created Modelfile: {modelfile_path}")
        return modelfile_path
    
    def _build_system_prompt(self, examples: List[Dict], artifact_type: str) -> str:
        """Build system prompt with examples"""
        
        # Base instruction
        prompt = f"""You are a specialized AI assistant for generating {artifact_type} artifacts.

You have been trained on the following examples of correct output:

"""
        
        # Add examples
        for i, ex in enumerate(examples, 1):
            prompt += f"Example {i}:\n"
            prompt += f"Question: {ex['question']}\n"
            prompt += f"Correct Answer: {ex['answer']}\n\n"
        
        # Add instructions
        prompt += """
IMPORTANT INSTRUCTIONS:
1. Follow the style and format shown in the examples above
2. If you don't know something, say "I don't know" - don't make things up
3. Stay focused on the task type you're trained for
4. Maintain consistency with the examples
5. Be concise and accurate
"""
        
        return prompt
    
    def build_custom_model(
        self,
        modelfile_path: Path,
        custom_name: str
    ) -> bool:
        """
        Build a custom Ollama model from Modelfile.
        
        Args:
            modelfile_path: Path to Modelfile
            custom_name: Name for the custom model
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"[OLLAMA_FT] Building custom model '{custom_name}'...")
            
            # Run ollama create command
            result = subprocess.run(
                ["ollama", "create", custom_name, "-f", str(modelfile_path)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print(f"[OLLAMA_FT] ✅ Successfully created model: {custom_name}")
                
                # Update registry
                self.registry[custom_name] = {
                    "created_at": datetime.now().isoformat(),
                    "modelfile": str(modelfile_path),
                    "status": "ready"
                }
                self._save_registry()
                
                return True
            else:
                print(f"[OLLAMA_FT] ❌ Failed to create model: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            print("[OLLAMA_FT] ❌ Model creation timed out")
            return False
        except Exception as e:
            print(f"[OLLAMA_FT] ❌ Error creating model: {e}")
            return False
    
    def fine_tune_from_feedback(
        self,
        base_model: str,
        feedback_entries: List[Dict],
        artifact_type: str,
        custom_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Fine-tune a model using feedback entries.
        
        Args:
            base_model: Base Ollama model
            feedback_entries: Feedback from feedback_store
            artifact_type: Type of artifact
            custom_name: Custom model name (auto-generated if None)
            
        Returns:
            Name of created model, or None if failed
        """
        if not feedback_entries:
            print("[OLLAMA_FT] No feedback entries to train on")
            return None
        
        # Convert feedback to examples
        examples = []
        for entry in feedback_entries:
            if entry.get('artifact_type') == artifact_type:
                examples.append({
                    "question": entry.get('meeting_context', f"Generate {artifact_type}"),
                    "answer": entry.get('expected_style', '')
                })
        
        if not examples:
            print(f"[OLLAMA_FT] No feedback for artifact type: {artifact_type}")
            return None
        
        # Generate model name if not provided
        if not custom_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            custom_name = f"{artifact_type}_ft_{timestamp}"
        
        # Create Modelfile
        modelfile_path = self.create_modelfile(
            base_model=base_model,
            examples=examples,
            custom_name=custom_name,
            artifact_type=artifact_type
        )
        
        # Build model
        success = self.build_custom_model(modelfile_path, custom_name)
        
        return custom_name if success else None
    
    def list_models(self) -> List[str]:
        """List all fine-tuned models"""
        return list(self.registry.keys())
    
    def delete_model(self, model_name: str) -> bool:
        """Delete a fine-tuned model"""
        try:
            # Delete from Ollama
            subprocess.run(
                ["ollama", "rm", model_name],
                capture_output=True,
                timeout=30
            )
            
            # Remove from registry
            if model_name in self.registry:
                del self.registry[model_name]
                self._save_registry()
            
            print(f"[OLLAMA_FT] ✅ Deleted model: {model_name}")
            return True
        except Exception as e:
            print(f"[OLLAMA_FT] ❌ Error deleting model: {e}")
            return False
    
    def export_modelfile(self, model_name: str, export_path: Path) -> bool:
        """Export Modelfile for sharing"""
        try:
            if model_name not in self.registry:
                print(f"[OLLAMA_FT] Model not found: {model_name}")
                return False
            
            modelfile_path = Path(self.registry[model_name]['modelfile'])
            if not modelfile_path.exists():
                print(f"[OLLAMA_FT] Modelfile not found: {modelfile_path}")
                return False
            
            # Copy to export path
            import shutil
            shutil.copy(modelfile_path, export_path)
            
            print(f"[OLLAMA_FT] ✅ Exported Modelfile to: {export_path}")
            return True
        except Exception as e:
            print(f"[OLLAMA_FT] ❌ Error exporting: {e}")
            return False


# Global instance
ollama_finetuner = OllamaFineTuner()


def quick_finetune_example():
    """Example usage"""
    
    # Example feedback
    feedback = [
        {
            "artifact_type": "jira",
            "meeting_context": "Create phone swap feature",
            "expected_style": """**Title:** Phone Swap Request

**User Story:**
As a mobile device user,
I want to request a phone swap,
So that I can exchange devices easily.

**Acceptance Criteria:**
1. User can select available phones
2. User can offer their current phone
3. Request is validated and stored"""
        }
    ]
    
    # Fine-tune model
    model_name = ollama_finetuner.fine_tune_from_feedback(
        base_model="llama3:8b-instruct-q4_K_M",
        feedback_entries=feedback,
        artifact_type="jira"
    )
    
    print(f"Created model: {model_name}")
    
    # List models
    print("All fine-tuned models:", ollama_finetuner.list_models())


if __name__ == "__main__":
    quick_finetune_example()
