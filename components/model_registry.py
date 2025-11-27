"""
Model Registry - Persistent tracking of downloaded and trained models
Ensures models persist across app restarts and are always available
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class RegisteredModel:
    """A registered model (downloaded or fine-tuned)"""
    model_id: str
    model_name: str  # Display name
    base_model: str  # e.g., "codellama-7b"
    status: str  # "downloaded", "trained", "training", "failed"
    model_path: str
    created_at: str
    trained_at: Optional[str] = None
    training_config: Optional[Dict] = None
    metrics: Optional[Dict] = None  # Loss, accuracy, etc.


class ModelRegistry:
    """
    Persistent registry for all models (downloaded and trained)
    
    Features:
    - Tracks downloaded models
    - Tracks trained models
    - Persists to disk (survives app restart)
    - Automatically loads on startup
    - Shows in AI Provider dropdown
    """
    
    def __init__(self, registry_path: str = "model_registry.json"):
        self.registry_path = Path(registry_path)
        self.models: Dict[str, RegisteredModel] = {}
        self._load_registry()
    
    def _load_registry(self):
        """Load registry from disk"""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.models = {}
                    for model_id, model_data in data.items():
                        try:
                            # Handle both 'id' and 'model_id' keys for backward compatibility
                            if 'id' in model_data and 'model_id' not in model_data:
                                model_data['model_id'] = model_data.pop('id')
                            # Handle both 'name' and 'model_name' keys for backward compatibility
                            if 'name' in model_data and 'model_name' not in model_data:
                                model_data['model_name'] = model_data.pop('name')
                            # Remove fields that don't exist in RegisteredModel
                            valid_fields = {'model_id', 'model_name', 'base_model', 'status', 'model_path', 
                                          'created_at', 'trained_at', 'training_config', 'metrics'}
                            model_data = {k: v for k, v in model_data.items() if k in valid_fields}
                            self.models[model_id] = RegisteredModel(**model_data)
                        except Exception as e:
                            logger.warning(f"Failed to load model {model_id}: {e}, skipping")
                            continue
                    logger.info(f"Loaded {len(self.models)} models from registry")
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
                self.models = {}
        else:
            logger.info("No existing registry found, starting fresh")
            self.models = {}
    
    def _save_registry(self):
        """Save registry to disk"""
        try:
            # Ensure parent directory exists
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                data = {
                    model_id: asdict(model)
                    for model_id, model in self.models.items()
                }
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self.models)} models to registry")
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def register_downloaded_model(self, base_model: str, model_path: str) -> str:
        """Register a downloaded (not yet trained) model"""
        model_id = f"{base_model}-downloaded"
        
        model = RegisteredModel(
            model_id=model_id,
            model_name=base_model.replace("-", " ").title(),
            base_model=base_model,
            status="downloaded",
            model_path=model_path,
            created_at=datetime.now().isoformat()
        )
        
        self.models[model_id] = model
        self._save_registry()
        
        logger.info(f"Registered downloaded model: {base_model}")
        return model_id
    
    def register_trained_model(self, base_model: str, model_path: str, 
                              training_config: Dict, metrics: Dict) -> str:
        """Register a trained model"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_id = f"{base_model}-finetuned-{timestamp}"
        
        model = RegisteredModel(
            model_id=model_id,
            model_name=f"{base_model.replace('-', ' ').title()} (Fine-tuned)",
            base_model=base_model,
            status="trained",
            model_path=model_path,
            created_at=datetime.now().isoformat(),
            trained_at=datetime.now().isoformat(),
            training_config=training_config,
            metrics=metrics
        )
        
        self.models[model_id] = model
        self._save_registry()
        
        logger.info(f"Registered trained model: {model_id}")
        return model_id
    
    def update_model_status(self, model_id: str, status: str, **kwargs):
        """Update model status (e.g., training → trained)"""
        if model_id in self.models:
            self.models[model_id].status = status
            
            # Update additional fields
            for key, value in kwargs.items():
                if hasattr(self.models[model_id], key):
                    setattr(self.models[model_id], key, value)
            
            self._save_registry()
            logger.info(f"Updated model {model_id} status to: {status}")
    
    def is_model_downloaded(self, base_model: str) -> bool:
        """Check if a model is already downloaded"""
        for model in self.models.values():
            if model.base_model == base_model and model.status in ["downloaded", "trained", "training"]:
                return True
        return False
    
    def is_model_trained(self, base_model: str) -> bool:
        """Check if a model is already trained"""
        for model in self.models.values():
            if model.base_model == base_model and model.status == "trained":
                return True
        return False
    
    def get_trained_models(self) -> List[RegisteredModel]:
        """Get all trained models"""
        return [
            model for model in self.models.values()
            if model.status == "trained"
        ]
    
    def get_model_by_id(self, model_id: str) -> Optional[RegisteredModel]:
        """Get a specific model by ID"""
        return self.models.get(model_id)
    
    def get_models_by_base(self, base_model: str) -> List[RegisteredModel]:
        """Get all versions of a base model"""
        return [
            model for model in self.models.values()
            if model.base_model == base_model
        ]
    
    def get_all_models(self) -> List[RegisteredModel]:
        """Get all registered models"""
        return list(self.models.values())
    
    def delete_model(self, model_id: str):
        """Remove a model from registry and delete its files"""
        if model_id in self.models:
            model = self.models[model_id]
            
            # Delete physical model files if they exist
            try:
                from pathlib import Path
                import shutil
                model_path = Path(model.model_path)
                if model_path.exists():
                    if model_path.is_dir():
                        shutil.rmtree(model_path)
                        logger.info(f"Deleted model directory: {model_path}")
                    else:
                        model_path.unlink()
                        logger.info(f"Deleted model file: {model_path}")
            except Exception as e:
                logger.warning(f"Failed to delete model files at {model.model_path}: {e}")
            
            # Remove from registry
            del self.models[model_id]
            self._save_registry()
            logger.info(f"Deleted model from registry: {model_id}")
    
    def get_display_name(self, base_model: str) -> str:
        """Get display name for AI Provider dropdown"""
        # Check if model is trained
        for model in self.models.values():
            if model.base_model == base_model and model.status == "trained":
                return f"{model.model_name} ✅"
        
        # Check if model is downloaded
        for model in self.models.values():
            if model.base_model == base_model and model.status == "downloaded":
                return f"{model.model_name} (Ready)"
        
        # Not yet available
        return base_model.replace("-", " ").title()
    
    def get_ai_provider_options(self) -> List[str]:
        """Get list of options for AI Provider dropdown"""
        options = []
        
        # Add cloud providers
        options.extend([
            "Gemini",
            "OpenAI",
            "Anthropic",
            "Groq"
        ])
        
        # Add trained models
        trained = self.get_trained_models()
        for model in trained:
            options.append(f"{model.model_name} (Local)")
        
        return options


# Global instance
model_registry = ModelRegistry()


def load_registry_on_startup():
    """Load registry when app starts"""
    logger.info("Loading model registry on startup...")
    model_registry._load_registry()
    
    trained_count = len(model_registry.get_trained_models())
    total_count = len(model_registry.get_all_models())
    
    logger.info(f"Registry loaded: {trained_count} trained models, {total_count} total")
    
    return model_registry

