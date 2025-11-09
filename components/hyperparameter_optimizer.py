"""
Hyperparameter Optimizer using Bayesian Optimization (Optuna)
Automatically finds optimal hyperparameters for fine-tuning:
- learning_rate: [1e-6, 1e-3]
- batch_size: [8, 64]
- num_epochs: [1, 10]
- warmup_ratio: [0.0, 0.2]
- lora_r: [4, 64]
- lora_alpha: [8, 128]

Uses Optuna for efficient Bayesian search (much faster than grid search).
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import json


@dataclass
class HyperparameterConfig:
    """Hyperparameter configuration"""
    learning_rate: float
    batch_size: int
    num_epochs: int
    warmup_ratio: float
    lora_r: int
    lora_alpha: int
    lora_dropout: float = 0.05
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class OptimizationResult:
    """Result of hyperparameter optimization"""
    best_params: HyperparameterConfig
    best_score: float
    n_trials: int
    optimization_history: List[Dict]


class HyperparameterOptimizer:
    """
    Optimize hyperparameters using Bayesian optimization (Optuna).
    
    Strategy:
    1. Define search space
    2. Sample hyperparameters using Bayesian optimization
    3. Train model with sampled hyperparameters
    4. Evaluate on validation set
    5. Use score to guide next samples
    6. Repeat until budget exhausted
    """
    
    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        study_name: str = "finetuning_hparam_optimization"
    ):
        """
        Initialize hyperparameter optimizer.
        
        Args:
            storage_dir: Directory to store optimization results
            study_name: Name for Optuna study (for persistence)
        """
        self.storage_dir = storage_dir or Path("training_jobs/hyperparameter_optimization")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.study_name = study_name
        
        # Check if Optuna is available
        self.optuna_available = self._check_optuna()
    
    def _check_optuna(self) -> bool:
        """Check if Optuna is installed"""
        try:
            import optuna
            return True
        except ImportError:
            print("[WARN] Optuna not available. Install with: pip install optuna")
            return False
    
    def optimize(
        self,
        objective_function: Callable[[HyperparameterConfig], float],
        n_trials: int = 50,
        artifact_type: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> OptimizationResult:
        """
        Optimize hyperparameters using Bayesian search.
        
        Args:
            objective_function: Function that takes HyperparameterConfig and returns
                                validation score (higher is better)
            n_trials: Number of trials to run
            artifact_type: Optional artifact type (for targeted optimization)
            timeout: Optional timeout in seconds
        
        Returns:
            OptimizationResult with best hyperparameters and history
        """
        if not self.optuna_available:
            # Fallback to default hyperparameters
            print("[HPARAM_OPT] Using default hyperparameters (Optuna not available)")
            return self._get_default_result()
        
        import optuna
        from optuna.samplers import TPESampler
        
        # Create or load study
        study_name = f"{self.study_name}_{artifact_type}" if artifact_type else self.study_name
        storage_path = self.storage_dir / f"{study_name}.db"
        storage_url = f"sqlite:///{storage_path}"
        
        try:
            study = optuna.create_study(
                study_name=study_name,
                storage=storage_url,
                direction="maximize",  # Maximize validation score
                sampler=TPESampler(seed=42),  # Bayesian optimization
                load_if_exists=True
            )
            
            print(f"[HPARAM_OPT] Starting optimization:")
            print(f"  Study: {study_name}")
            print(f"  Trials: {n_trials}")
            print(f"  Artifact Type: {artifact_type or 'All'}")
            
        except Exception as e:
            print(f"[ERROR] Could not create Optuna study: {e}")
            return self._get_default_result()
        
        # Define objective
        def objective(trial):
            # Sample hyperparameters
            config = HyperparameterConfig(
                learning_rate=trial.suggest_float('learning_rate', 1e-6, 1e-3, log=True),
                batch_size=trial.suggest_int('batch_size', 8, 64, log=True),
                num_epochs=trial.suggest_int('num_epochs', 1, 10),
                warmup_ratio=trial.suggest_float('warmup_ratio', 0.0, 0.2),
                lora_r=trial.suggest_int('lora_r', 4, 64, log=True),
                lora_alpha=trial.suggest_int('lora_alpha', 8, 128, log=True),
                lora_dropout=trial.suggest_float('lora_dropout', 0.0, 0.1)
            )
            
            # Evaluate
            try:
                score = objective_function(config)
                return score
            except Exception as e:
                print(f"[HPARAM_OPT] Trial {trial.number} failed: {e}")
                return 0.0  # Failed trial gets score 0
        
        # Run optimization
        try:
            study.optimize(
                objective,
                n_trials=n_trials,
                timeout=timeout,
                show_progress_bar=True
            )
        except KeyboardInterrupt:
            print("[HPARAM_OPT] Optimization interrupted by user")
        except Exception as e:
            print(f"[ERROR] Optimization failed: {e}")
            return self._get_default_result()
        
        # Extract results
        best_params = HyperparameterConfig(**study.best_params)
        best_score = study.best_value
        
        # Optimization history
        history = []
        for trial in study.trials:
            if trial.value is not None:
                history.append({
                    'trial_number': trial.number,
                    'params': trial.params,
                    'score': trial.value
                })
        
        result = OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            n_trials=len(study.trials),
            optimization_history=history
        )
        
        # Save results
        self._save_result(result, artifact_type)
        
        # Log summary
        self._log_optimization_summary(result)
        
        return result
    
    def load_best_params(self, artifact_type: Optional[str] = None) -> Optional[HyperparameterConfig]:
        """
        Load best hyperparameters from previous optimization.
        
        Args:
            artifact_type: Optional artifact type
        
        Returns:
            HyperparameterConfig or None if not found
        """
        filename = f"best_params_{artifact_type}.json" if artifact_type else "best_params.json"
        filepath = self.storage_dir / filename
        
        if not filepath.exists():
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return HyperparameterConfig(**data['best_params'])
        except Exception as e:
            print(f"[WARN] Could not load best params: {e}")
            return None
    
    def get_default_config(self) -> HyperparameterConfig:
        """Get default hyperparameter configuration"""
        return HyperparameterConfig(
            learning_rate=2e-4,
            batch_size=16,
            num_epochs=3,
            warmup_ratio=0.1,
            lora_r=16,
            lora_alpha=32,
            lora_dropout=0.05
        )
    
    def _get_default_result(self) -> OptimizationResult:
        """Get default optimization result"""
        return OptimizationResult(
            best_params=self.get_default_config(),
            best_score=0.0,
            n_trials=0,
            optimization_history=[]
        )
    
    def _save_result(self, result: OptimizationResult, artifact_type: Optional[str] = None):
        """Save optimization result to disk"""
        filename = f"best_params_{artifact_type}.json" if artifact_type else "best_params.json"
        filepath = self.storage_dir / filename
        
        try:
            data = {
                'best_params': result.best_params.to_dict(),
                'best_score': result.best_score,
                'n_trials': result.n_trials,
                'optimization_history': result.optimization_history
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"[HPARAM_OPT] Saved best params to {filepath}")
        except Exception as e:
            print(f"[WARN] Could not save optimization result: {e}")
    
    def _log_optimization_summary(self, result: OptimizationResult):
        """Log optimization summary"""
        print("\n" + "="*80)
        print("HYPERPARAMETER OPTIMIZATION COMPLETE")
        print("="*80)
        print(f"Trials: {result.n_trials}")
        print(f"Best Score: {result.best_score:.3f}")
        print("\nBest Hyperparameters:")
        for param, value in result.best_params.to_dict().items():
            print(f"  {param:20s}: {value}")
        print("="*80 + "\n")


# Convenience functions
def optimize_hyperparameters(
    train_fn: Callable[[HyperparameterConfig], float],
    n_trials: int = 50,
    artifact_type: Optional[str] = None
) -> HyperparameterConfig:
    """
    Convenience function to optimize hyperparameters.
    
    Args:
        train_fn: Function that trains and returns validation score
        n_trials: Number of optimization trials
        artifact_type: Optional artifact type
    
    Returns:
        Best hyperparameter configuration
    """
    optimizer = HyperparameterOptimizer()
    result = optimizer.optimize(train_fn, n_trials=n_trials, artifact_type=artifact_type)
    return result.best_params


# Example usage
if __name__ == "__main__":
    import random
    
    optimizer = HyperparameterOptimizer()
    
    print("="*80)
    print("HYPERPARAMETER OPTIMIZER - TEST")
    print("="*80)
    
    # Simulate objective function
    # In real usage, this would train a model and return validation score
    def mock_objective(config: HyperparameterConfig) -> float:
        """
        Mock objective function that simulates model training.
        
        Assumes:
        - Lower learning rate is better (but not too low)
        - Larger lora_r is better (but not too large)
        - More epochs is better (but diminishing returns)
        """
        # Optimal values (hidden from optimizer)
        optimal_lr = 2e-4
        optimal_r = 16
        optimal_epochs = 3
        
        # Calculate score based on distance from optimal
        lr_score = 1.0 - min(1.0, abs(config.learning_rate - optimal_lr) / optimal_lr)
        r_score = 1.0 - min(1.0, abs(config.lora_r - optimal_r) / optimal_r)
        epochs_score = min(1.0, config.num_epochs / optimal_epochs)
        
        # Combined score (0-100)
        score = (lr_score + r_score + epochs_score) / 3 * 100
        
        # Add noise
        score += random.uniform(-5, 5)
        
        print(f"[MOCK] Trial - LR: {config.learning_rate:.2e}, LoRA_r: {config.lora_r}, Epochs: {config.num_epochs} → Score: {score:.1f}")
        
        return score
    
    # Run optimization
    print("\nRunning optimization with 20 trials...")
    print("(In real usage, each trial would train a model)")
    print("-" * 40)
    
    result = optimizer.optimize(
        objective_function=mock_objective,
        n_trials=20,
        artifact_type="erd"
    )
    
    # Show best parameters
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"Best Score: {result.best_score:.1f}")
    print("\nBest Parameters:")
    for param, value in result.best_params.to_dict().items():
        print(f"  {param:20s}: {value}")
    
    # Show optimization history (top 5 trials)
    print("\n" + "-" * 40)
    print("Top 5 Trials:")
    print("-" * 40)
    sorted_history = sorted(result.optimization_history, key=lambda x: x['score'], reverse=True)[:5]
    for i, trial in enumerate(sorted_history, 1):
        print(f"{i}. Score: {trial['score']:.1f}")
        print(f"   LR: {trial['params']['learning_rate']:.2e}, "
              f"LoRA_r: {trial['params']['lora_r']}, "
              f"Epochs: {trial['params']['num_epochs']}")

