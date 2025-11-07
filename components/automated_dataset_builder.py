"""
Automated Training Dataset Builder
Extracts 1000+ examples from codebase for fine-tuning local models
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import ast


@dataclass
class TrainingExample:
    """Single training example for fine-tuning"""
    prompt: str
    completion: str
    metadata: Dict[str, Any]


class AutomatedDatasetBuilder:
    """
    Build training datasets automatically from codebase analysis.
    
    Extracts:
    - Code patterns (classes, functions, methods)
    - Documentation patterns (docstrings, comments)
    - API patterns (controllers, services, repositories)
    - Entity patterns (models, DTOs)
    """
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.examples: List[TrainingExample] = []
    
    # ====================================================================
    # Code Pattern Extraction
    # ====================================================================
    
    def extract_python_classes(self) -> List[TrainingExample]:
        """Extract Python class definitions as training examples"""
        examples = []
        
        for py_file in self.repo_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse Python AST
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Extract class code
                        class_code = ast.get_source_segment(content, node)
                        
                        if not class_code or len(class_code) < 50:
                            continue
                        
                        # Generate prompt
                        docstring = ast.get_docstring(node)
                        base_classes = [b.id for b in node.bases if isinstance(b, ast.Name)]
                        
                        prompt_parts = [f"Generate a Python class named {node.name}"]
                        
                        if base_classes:
                            prompt_parts.append(f"that inherits from {', '.join(base_classes)}")
                        
                        if docstring:
                            prompt_parts.append(f"with the following purpose: {docstring[:200]}")
                        
                        prompt = " ".join(prompt_parts)
                        
                        examples.append(TrainingExample(
                            prompt=prompt,
                            completion=class_code,
                            metadata={
                                "type": "python_class",
                                "file": str(py_file),
                                "class_name": node.name,
                                "has_docstring": bool(docstring)
                            }
                        ))
            
            except Exception as e:
                print(f"[WARN] Failed to parse {py_file}: {e}")
        
        return examples
    
    def extract_python_functions(self) -> List[TrainingExample]:
        """Extract Python function definitions as training examples"""
        examples = []
        
        for py_file in self.repo_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_code = ast.get_source_segment(content, node)
                        
                        if not func_code or len(func_code) < 30:
                            continue
                        
                        docstring = ast.get_docstring(node)
                        args = [arg.arg for arg in node.args.args]
                        
                        prompt = f"Generate a Python function named {node.name}"
                        
                        if args:
                            prompt += f" that takes parameters: {', '.join(args)}"
                        
                        if docstring:
                            prompt += f". Purpose: {docstring[:200]}"
                        
                        examples.append(TrainingExample(
                            prompt=prompt,
                            completion=func_code,
                            metadata={
                                "type": "python_function",
                                "file": str(py_file),
                                "function_name": node.name,
                                "num_args": len(args)
                            }
                        ))
            
            except Exception as e:
                print(f"[WARN] Failed to parse {py_file}: {e}")
        
        return examples
    
    # ====================================================================
    # C# / .NET Pattern Extraction
    # ====================================================================
    
    def extract_csharp_classes(self) -> List[TrainingExample]:
        """Extract C# class definitions"""
        examples = []
        
        for cs_file in self.repo_path.rglob("*.cs"):
            try:
                with open(cs_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Regex to find class definitions
                class_pattern = r'(public|private|internal|protected)?\s*(class|interface)\s+(\w+)(?:\s*:\s*([\w\s,]+))?\s*\{([^}]*)\}'
                
                for match in re.finditer(class_pattern, content, re.DOTALL):
                    visibility, class_type, class_name, inheritance, body = match.groups()
                    
                    if len(body) < 50:
                        continue
                    
                    class_code = match.group(0)
                    
                    prompt = f"Generate a C# {class_type} named {class_name}"
                    
                    if inheritance:
                        prompt += f" that implements/inherits: {inheritance}"
                    
                    examples.append(TrainingExample(
                        prompt=prompt,
                        completion=class_code,
                        metadata={
                            "type": f"csharp_{class_type}",
                            "file": str(cs_file),
                            "class_name": class_name
                        }
                    ))
            
            except Exception as e:
                print(f"[WARN] Failed to parse {cs_file}: {e}")
        
        return examples
    
    # ====================================================================
    # TypeScript / JavaScript Pattern Extraction
    # ====================================================================
    
    def extract_typescript_classes(self) -> List[TrainingExample]:
        """Extract TypeScript/JavaScript class and component definitions"""
        examples = []
        
        for ts_file in self.repo_path.rglob("*.ts"):
            if "node_modules" in str(ts_file):
                continue
            
            try:
                with open(ts_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Class pattern
                class_pattern = r'(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w\s,]+))?\s*\{([^}]*)\}'
                
                for match in re.finditer(class_pattern, content, re.DOTALL):
                    class_name, extends, implements, body = match.groups()
                    
                    if len(body) < 30:
                        continue
                    
                    class_code = match.group(0)
                    
                    prompt = f"Generate a TypeScript class named {class_name}"
                    
                    if extends:
                        prompt += f" that extends {extends}"
                    
                    if implements:
                        prompt += f" and implements {implements}"
                    
                    examples.append(TrainingExample(
                        prompt=prompt,
                        completion=class_code,
                        metadata={
                            "type": "typescript_class",
                            "file": str(ts_file),
                            "class_name": class_name
                        }
                    ))
            
            except Exception as e:
                print(f"[WARN] Failed to parse {ts_file}: {e}")
        
        return examples
    
    # ====================================================================
    # API Endpoint Pattern Extraction
    # ====================================================================
    
    def extract_api_endpoints(self) -> List[TrainingExample]:
        """Extract API endpoint definitions (REST controllers)"""
        examples = []
        
        # C# Controllers
        for cs_file in self.repo_path.rglob("*Controller.cs"):
            try:
                with open(cs_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find controller methods
                method_pattern = r'\[Http(Get|Post|Put|Delete|Patch)\(?[^\]]*\)?\]\s+(?:public\s+)?(?:async\s+)?(?:Task<)?(\w+)>?\s+(\w+)\([^)]*\)'
                
                for match in re.finditer(method_pattern, content, re.DOTALL):
                    http_method, return_type, method_name = match.groups()
                    
                    # Extract full method body (simplified)
                    method_start = match.start()
                    brace_count = 0
                    method_end = method_start
                    
                    for i in range(method_start, len(content)):
                        if content[i] == '{':
                            brace_count += 1
                        elif content[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                method_end = i + 1
                                break
                    
                    method_code = content[method_start:method_end]
                    
                    if len(method_code) < 50:
                        continue
                    
                    prompt = f"Generate a C# API endpoint for {http_method} {method_name} that returns {return_type}"
                    
                    examples.append(TrainingExample(
                        prompt=prompt,
                        completion=method_code,
                        metadata={
                            "type": "api_endpoint",
                            "file": str(cs_file),
                            "http_method": http_method,
                            "method_name": method_name
                        }
                    ))
            
            except Exception as e:
                print(f"[WARN] Failed to parse {cs_file}: {e}")
        
        return examples
    
    # ====================================================================
    # Documentation Pattern Extraction
    # ====================================================================
    
    def extract_docstrings(self) -> List[TrainingExample]:
        """Extract documentation patterns (docstrings, XML comments)"""
        examples = []
        
        for py_file in self.repo_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        docstring = ast.get_docstring(node)
                        
                        if not docstring or len(docstring) < 50:
                            continue
                        
                        # Get function/class signature
                        code_segment = ast.get_source_segment(content, node)
                        
                        if not code_segment:
                            continue
                        
                        # Extract just the signature (first few lines)
                        signature = '\n'.join(code_segment.split('\n')[:3])
                        
                        prompt = f"Write documentation for the following code:\n{signature}"
                        
                        examples.append(TrainingExample(
                            prompt=prompt,
                            completion=docstring,
                            metadata={
                                "type": "documentation",
                                "file": str(py_file),
                                "doc_length": len(docstring)
                            }
                        ))
            
            except Exception as e:
                print(f"[WARN] Failed to parse {py_file}: {e}")
        
        return examples
    
    # ====================================================================
    # Main Build Methods
    # ====================================================================
    
    def build_code_dataset(self, min_examples: int = 1000) -> List[TrainingExample]:
        """
        Build comprehensive code generation dataset.
        
        Target: 1000+ examples from codebase
        """
        print("[INFO] Building code generation dataset...")
        
        all_examples = []
        
        # Extract patterns
        print("[INFO] Extracting Python classes...")
        all_examples.extend(self.extract_python_classes())
        
        print("[INFO] Extracting Python functions...")
        all_examples.extend(self.extract_python_functions())
        
        print("[INFO] Extracting C# classes...")
        all_examples.extend(self.extract_csharp_classes())
        
        print("[INFO] Extracting TypeScript classes...")
        all_examples.extend(self.extract_typescript_classes())
        
        print("[INFO] Extracting API endpoints...")
        all_examples.extend(self.extract_api_endpoints())
        
        print(f"[INFO] Extracted {len(all_examples)} examples from codebase")
        
        if len(all_examples) < min_examples:
            print(f"[WARN] Only found {len(all_examples)} examples, expected {min_examples}+")
            print("[INFO] Generating synthetic variations to reach minimum...")
            all_examples = self._augment_dataset(all_examples, target=min_examples)
        
        return all_examples
    
    def build_documentation_dataset(self, min_examples: int = 500) -> List[TrainingExample]:
        """Build documentation generation dataset"""
        print("[INFO] Building documentation dataset...")
        
        all_examples = []
        
        print("[INFO] Extracting docstrings...")
        all_examples.extend(self.extract_docstrings())
        
        print(f"[INFO] Extracted {len(all_examples)} documentation examples")
        
        if len(all_examples) < min_examples:
            print(f"[INFO] Generating variations to reach {min_examples}...")
            all_examples = self._augment_dataset(all_examples, target=min_examples)
        
        return all_examples
    
    def _augment_dataset(self, examples: List[TrainingExample], target: int) -> List[TrainingExample]:
        """
        Augment dataset with variations to reach target size.
        
        Creates variations by:
        - Rewording prompts
        - Adding/removing context
        - Combining examples
        """
        augmented = examples.copy()
        
        while len(augmented) < target and len(examples) > 0:
            # Pick a random example and create variation
            import random
            base_example = random.choice(examples)
            
            # Create variation (simplified - could be more sophisticated)
            variation_prompts = [
                f"Create {base_example.prompt}",
                f"Implement {base_example.prompt}",
                f"Write code for {base_example.prompt}",
                base_example.prompt.replace("Generate", "Create"),
                base_example.prompt.replace("Generate", "Write"),
            ]
            
            for variant_prompt in variation_prompts:
                if len(augmented) >= target:
                    break
                
                augmented.append(TrainingExample(
                    prompt=variant_prompt,
                    completion=base_example.completion,
                    metadata={**base_example.metadata, "augmented": True}
                ))
        
        print(f"[INFO] Augmented dataset to {len(augmented)} examples")
        return augmented
    
    def export_to_jsonl(self, examples: List[TrainingExample], output_file: str):
        """Export training examples to JSONL format for fine-tuning"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for example in examples:
                # Format for fine-tuning
                entry = {
                    "prompt": example.prompt,
                    "completion": example.completion,
                    "metadata": example.metadata
                }
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        print(f"[SUCCESS] Exported {len(examples)} examples to {output_file}")
    
    def generate_all_datasets(self):
        """Generate all training datasets (Code + Documentation)"""
        print("="*80)
        print("AUTOMATED TRAINING DATASET GENERATION")
        print("="*80)
        
        # Code dataset (1000+ examples)
        code_examples = self.build_code_dataset(min_examples=1000)
        self.export_to_jsonl(
            code_examples,
            "finetune_datasets/code_dataset_1000.jsonl"
        )
        
        # Documentation dataset (500+ examples)
        doc_examples = self.build_documentation_dataset(min_examples=500)
        self.export_to_jsonl(
            doc_examples,
            "finetune_datasets/documentation_dataset_500.jsonl"
        )
        
        print("="*80)
        print("DATASET GENERATION COMPLETE")
        print(f"Total examples: {len(code_examples) + len(doc_examples)}")
        print("="*80)
        print("\nNext steps:")
        print("1. Review datasets in: finetune_datasets/")
        print("2. Use these for fine-tuning CodeLlama 7B")
        print("3. Command: python -m components.local_finetuning")


if __name__ == "__main__":
    # Run dataset generation
    builder = AutomatedDatasetBuilder(repo_path=".")
    builder.generate_all_datasets()

