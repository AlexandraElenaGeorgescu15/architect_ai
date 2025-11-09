"""
Data Augmenter for Training Data Expansion
Generates synthetic training examples through:
1. Input paraphrasing (rephrase requests)
2. Context variation (different RAG chunks)
3. Output variations (multiple correct answers)
4. Back-translation (en → fr → en for diversity)

Increases dataset size 2-3x with minimal effort.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import random


@dataclass
class TrainingExample:
    """A single training example"""
    input_data: str
    output: str
    context: Dict
    artifact_type: str
    quality_score: float


class DataAugmenter:
    """
    Augment training data to increase diversity and size.
    
    Strategies:
    1. Paraphrase inputs (rephrase user requests)
    2. Vary context (sample different RAG chunks)
    3. Modify outputs (permute non-critical parts)
    4. Back-translate (for linguistic diversity)
    """
    
    def __init__(
        self,
        augmentation_factor: int = 2,  # 2x = double dataset size
        use_back_translation: bool = False  # Requires translation API
    ):
        """
        Initialize data augmenter.
        
        Args:
            augmentation_factor: Target multiplier for dataset size (2-3x)
            use_back_translation: Whether to use back-translation (requires API)
        """
        self.augmentation_factor = augmentation_factor
        self.use_back_translation = use_back_translation
    
    def augment_dataset(
        self,
        examples: List[TrainingExample]
    ) -> List[TrainingExample]:
        """
        Augment dataset to N times original size.
        
        Args:
            examples: Original training examples
        
        Returns:
            Augmented training examples (includes originals)
        """
        if not examples:
            return []
        
        augmented = list(examples)  # Keep originals
        target_size = len(examples) * self.augmentation_factor
        augmentations_needed = target_size - len(examples)
        
        print(f"[AUGMENTER] Augmenting dataset:")
        print(f"  Original: {len(examples)} examples")
        print(f"  Target: {target_size} examples ({self.augmentation_factor}x)")
        print(f"  Generating: {augmentations_needed} synthetic examples")
        
        # Augmentation methods (with fallback)
        methods = [
            ('paraphrase', self._paraphrase_input),
            ('context_variation', self._vary_context),
            ('output_variation', self._vary_output),
        ]
        
        if self.use_back_translation:
            methods.append(('back_translate', self._back_translate_input))
        
        # Generate augmented examples
        method_counts = {name: 0 for name, _ in methods}
        
        while len(augmented) < target_size:
            # Sample random example to augment
            original = random.choice(examples)
            
            # Sample random augmentation method
            method_name, method_fn = random.choice(methods)
            
            try:
                # Apply augmentation
                augmented_example = method_fn(original)
                
                if augmented_example and augmented_example.input_data != original.input_data:
                    augmented.append(augmented_example)
                    method_counts[method_name] += 1
            
            except Exception as e:
                print(f"[WARN] Augmentation method '{method_name}' failed: {e}")
        
        print(f"[AUGMENTER] Generated {len(augmented) - len(examples)} synthetic examples:")
        for method, count in method_counts.items():
            print(f"  {method}: {count}")
        
        return augmented
    
    def _paraphrase_input(self, example: TrainingExample) -> Optional[TrainingExample]:
        """
        Paraphrase input while preserving meaning.
        
        Uses simple rule-based paraphrasing (in production, use LLM or paraphrase model).
        """
        paraphrased = self._simple_paraphrase(example.input_data)
        
        if paraphrased == example.input_data:
            return None  # No change
        
        return TrainingExample(
            input_data=paraphrased,
            output=example.output,
            context=example.context,
            artifact_type=example.artifact_type,
            quality_score=example.quality_score
        )
    
    def _vary_context(self, example: TrainingExample) -> Optional[TrainingExample]:
        """
        Vary context while keeping input/output same.
        
        Simulates retrieving different RAG chunks.
        """
        # Simple variation: shuffle context if it's a dict of chunks
        if isinstance(example.context, dict) and 'rag' in example.context:
            varied_context = example.context.copy()
            # In production, this would re-query RAG with slightly modified query
            varied_context['rag_variant'] = True
            
            return TrainingExample(
                input_data=example.input_data,
                output=example.output,
                context=varied_context,
                artifact_type=example.artifact_type,
                quality_score=example.quality_score
            )
        
        return None
    
    def _vary_output(self, example: TrainingExample) -> Optional[TrainingExample]:
        """
        Create output variation (e.g., reorder diagram elements).
        
        Only for artifacts where order doesn't matter.
        """
        # Only for certain artifact types
        if example.artifact_type not in ['erd', 'jira', 'workflows']:
            return None
        
        # Simple variation: add whitespace or comments
        varied_output = example.output + "\n# Generated variant"
        
        return TrainingExample(
            input_data=example.input_data,
            output=varied_output,
            context=example.context,
            artifact_type=example.artifact_type,
            quality_score=example.quality_score * 0.95  # Slightly lower quality
        )
    
    def _back_translate_input(self, example: TrainingExample) -> Optional[TrainingExample]:
        """
        Back-translate input (en → fr → en) for linguistic diversity.
        
        Requires translation API (Google Translate, DeepL, etc.).
        In this implementation, simulates back-translation.
        """
        # Simulate back-translation (in production, use actual translation API)
        back_translated = self._simulate_back_translation(example.input_data)
        
        if back_translated == example.input_data:
            return None
        
        return TrainingExample(
            input_data=back_translated,
            output=example.output,
            context=example.context,
            artifact_type=example.artifact_type,
            quality_score=example.quality_score
        )
    
    def _simple_paraphrase(self, text: str) -> str:
        """
        Simple rule-based paraphrasing.
        
        In production, use:
        - LLM-based paraphrasing (GPT-4, etc.)
        - Paraphrase models (T5, BART)
        - Synonym replacement
        """
        # Simple substitutions
        replacements = {
            'generate': 'create',
            'build': 'construct',
            'make': 'produce',
            'diagram': 'chart',
            'system': 'application',
            'design': 'architect',
            'show': 'display',
            'for': 'to represent',
        }
        
        paraphrased = text
        for original, replacement in replacements.items():
            if original in paraphrased.lower():
                paraphrased = paraphrased.replace(original, replacement)
                break  # One replacement at a time
        
        return paraphrased
    
    def _simulate_back_translation(self, text: str) -> str:
        """
        Simulate back-translation effect.
        
        Real back-translation would:
        1. Translate en → fr (Google Translate)
        2. Translate fr → en
        3. Result has same meaning but different wording
        """
        # Simulate by adding minor variations
        variations = {
            'Generate': 'Produce',
            'Create': 'Build',
            'system': 'platform',
            'with': 'having',
            'for': 'targeting',
        }
        
        back_translated = text
        for original, replacement in variations.items():
            if original in back_translated:
                back_translated = back_translated.replace(original, replacement, 1)
                break
        
        return back_translated


# Convenience function
def augment_training_data(
    examples: List[TrainingExample],
    augmentation_factor: int = 2
) -> List[TrainingExample]:
    """
    Convenience function to augment training data.
    
    Args:
        examples: Original training examples
        augmentation_factor: Target multiplier (2 = double size)
    
    Returns:
        Augmented training examples
    """
    augmenter = DataAugmenter(augmentation_factor=augmentation_factor)
    return augmenter.augment_dataset(examples)


# Example usage
if __name__ == "__main__":
    import time
    
    augmenter = DataAugmenter(augmentation_factor=3)
    
    print("="*80)
    print("DATA AUGMENTER - TEST")
    print("="*80)
    
    # Create sample training examples
    original_examples = [
        TrainingExample(
            input_data="Generate ERD for e-commerce system with users and products",
            output="erDiagram\nUser {int id PK}\nProduct {int id PK}\nUser ||--o{ Product : purchases",
            context={"rag": "existing code...", "notes": "requirements..."},
            artifact_type="erd",
            quality_score=85.0
        ),
        TrainingExample(
            input_data="Build architecture diagram showing API server and database",
            output="graph TD\nAPI[API Server] --> DB[Database]\nAPI --> Cache[Redis]",
            context={"rag": "architecture patterns...", "notes": "tech stack..."},
            artifact_type="architecture",
            quality_score=90.0
        ),
        TrainingExample(
            input_data="Create JIRA tasks for user authentication feature",
            output="1. Setup auth middleware\n2. Create login endpoint\n3. Add JWT tokens",
            context={"rag": "existing features...", "notes": "sprint planning..."},
            artifact_type="jira",
            quality_score=80.0
        ),
    ]
    
    print(f"\nOriginal dataset: {len(original_examples)} examples")
    for i, ex in enumerate(original_examples, 1):
        print(f"\n{i}. {ex.artifact_type}")
        print(f"   Input: {ex.input_data[:60]}...")
        print(f"   Quality: {ex.quality_score:.1f}")
    
    # Augment dataset
    print("\n" + "="*80)
    print("AUGMENTING DATASET")
    print("="*80)
    
    augmented_examples = augmenter.augment_dataset(original_examples)
    
    print(f"\nAugmented dataset: {len(augmented_examples)} examples ({len(augmented_examples) / len(original_examples):.1f}x)")
    
    # Show some augmented examples
    print("\n" + "-" * 40)
    print("SAMPLE AUGMENTED EXAMPLES")
    print("-" * 40)
    
    # Show first 3 augmented examples (skip originals)
    augmented_only = augmented_examples[len(original_examples):]
    for i, ex in enumerate(augmented_only[:3], 1):
        print(f"\n{i}. {ex.artifact_type} (AUGMENTED)")
        print(f"   Input: {ex.input_data[:60]}...")
        print(f"   Quality: {ex.quality_score:.1f}")
    
    # Compare original vs augmented
    print("\n" + "="*80)
    print("COMPARISON: ORIGINAL VS AUGMENTED")
    print("="*80)
    
    original = original_examples[0]
    augmented = [ex for ex in augmented_only if ex.artifact_type == original.artifact_type][0]
    
    print("\nOriginal:")
    print(f"  Input: {original.input_data}")
    print("\nAugmented:")
    print(f"  Input: {augmented.input_data}")
    print("\n→ Same meaning, different wording (data diversity)")

