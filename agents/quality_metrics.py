"""
Output Quality Metrics and Self-Improvement
Evaluates and improves generated content
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
import re

@dataclass
class QualityScore:
    """Quality evaluation scores"""
    overall: float  # 0-1
    completeness: float
    accuracy: float
    clarity: float
    relevance: float
    technical_depth: float
    actionability: float
    feedback: List[str]

class QualityEvaluator:
    """
    Evaluates output quality using multiple metrics
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def evaluate_output(self, output: str, task: str, context: str = "") -> QualityScore:
        """
        Comprehensive quality evaluation
        """
        # Run evaluations in parallel
        import asyncio
        
        completeness, accuracy, clarity, relevance, depth, actionability = await asyncio.gather(
            self._evaluate_completeness(output, task),
            self._evaluate_accuracy(output, context),
            self._evaluate_clarity(output),
            self._evaluate_relevance(output, task),
            self._evaluate_technical_depth(output),
            self._evaluate_actionability(output)
        )
        
        # Calculate overall score
        overall = (completeness + accuracy + clarity + relevance + depth + actionability) / 6
        
        # Generate feedback
        feedback = self._generate_feedback(
            completeness, accuracy, clarity, relevance, depth, actionability
        )
        
        return QualityScore(
            overall=overall,
            completeness=completeness,
            accuracy=accuracy,
            clarity=clarity,
            relevance=relevance,
            technical_depth=depth,
            actionability=actionability,
            feedback=feedback
        )
    
    async def _evaluate_completeness(self, output: str, task: str) -> float:
        """Does output fully address the task?"""
        prompt = f"""
Rate how completely this output addresses the task (0.0 to 1.0):

Task: {task}

Output: {output[:1000]}...

Score (0.0-1.0):"""
        
        return await self._get_score(prompt)
    
    async def _evaluate_accuracy(self, output: str, context: str) -> float:
        """Is the output factually accurate?"""
        if not context:
            return 0.8  # Default if no context to check against
        
        prompt = f"""
Rate the factual accuracy of this output given the context (0.0 to 1.0):

Context: {context[:500]}...

Output: {output[:1000]}...

Score (0.0-1.0):"""
        
        return await self._get_score(prompt)
    
    async def _evaluate_clarity(self, output: str) -> float:
        """Is the output clear and well-structured?"""
        # Check for structure markers
        has_headers = bool(re.search(r'^#+\s', output, re.MULTILINE))
        has_lists = bool(re.search(r'^\s*[-*\d]+\.?\s', output, re.MULTILINE))
        has_paragraphs = len(output.split('\n\n')) > 1
        
        structure_score = sum([has_headers, has_lists, has_paragraphs]) / 3
        
        # Check readability
        avg_sentence_length = len(output.split()) / max(len(output.split('.')), 1)
        readability_score = 1.0 if avg_sentence_length < 25 else 0.7
        
        return (structure_score + readability_score) / 2
    
    async def _evaluate_relevance(self, output: str, task: str) -> float:
        """Is the output relevant to the task?"""
        prompt = f"""
Rate how relevant this output is to the task (0.0 to 1.0):

Task: {task}

Output: {output[:1000]}...

Score (0.0-1.0):"""
        
        return await self._get_score(prompt)
    
    async def _evaluate_technical_depth(self, output: str) -> float:
        """Does output have appropriate technical depth?"""
        # Check for technical indicators
        technical_terms = len(re.findall(r'\b[A-Z]{2,}\b', output))  # Acronyms
        code_blocks = len(re.findall(r'```', output)) / 2
        technical_keywords = sum(1 for word in ['API', 'database', 'architecture', 'implement', 'configure'] if word.lower() in output.lower())
        
        depth_score = min(1.0, (technical_terms + code_blocks * 2 + technical_keywords) / 10)
        return depth_score
    
    async def _evaluate_actionability(self, output: str) -> float:
        """Does output provide actionable guidance?"""
        # Check for actionable elements
        has_steps = bool(re.search(r'\d+\.\s', output))
        has_commands = bool(re.search(r'```', output))
        has_recommendations = any(word in output.lower() for word in ['should', 'recommend', 'suggest', 'use', 'implement'])
        
        actionability_score = sum([has_steps, has_commands, has_recommendations]) / 3
        return actionability_score
    
    async def _get_score(self, prompt: str) -> float:
        """Get numerical score from LLM"""
        try:
            response = await self.llm_client._call_ai(prompt, "Provide only a number between 0 and 1.")
            score = float(response.strip().split()[0])
            return max(0.0, min(1.0, score))
        except:
            return 0.7  # Default score
    
    def _generate_feedback(self, *scores) -> List[str]:
        """Generate actionable feedback"""
        feedback = []
        score_names = ['completeness', 'accuracy', 'clarity', 'relevance', 'technical_depth', 'actionability']
        
        for name, score in zip(score_names, scores):
            if score < 0.7:
                feedback.append(f"Improve {name} (current: {score:.2f})")
        
        return feedback

class SelfImprovement:
    """
    Self-improvement system that iteratively refines output
    """
    
    def __init__(self, llm_client, evaluator: QualityEvaluator):
        self.llm_client = llm_client
        self.evaluator = evaluator
    
    async def improve_output(self, initial_output: str, task: str, context: str = "", max_iterations: int = 3) -> Tuple[str, List[QualityScore]]:
        """
        Iteratively improve output until quality threshold met
        Returns: (final_output, quality_history)
        """
        current_output = initial_output
        quality_history = []
        
        for iteration in range(max_iterations):
            # Evaluate current output
            quality = await self.evaluator.evaluate_output(current_output, task, context)
            quality_history.append(quality)
            
            print(f"[INFO] Iteration {iteration + 1}: Quality = {quality.overall:.2f}")
            
            # Check if quality is good enough
            if quality.overall >= 0.85:
                print("[OK] Quality threshold met!")
                break
            
            # Generate improvements
            current_output = await self._refine_output(current_output, task, quality)
        
        return current_output, quality_history
    
    async def _refine_output(self, output: str, task: str, quality: QualityScore) -> str:
        """Refine output based on quality feedback"""
        feedback_text = "\n".join(quality.feedback)
        
        prompt = f"""
Improve this output based on the feedback:

Original Task: {task}

Current Output:
{output}

Quality Feedback:
{feedback_text}

Provide an improved version that addresses the feedback while maintaining all good aspects:"""
        
        improved = await self.llm_client._call_ai(
            prompt,
            "Improve the output based on feedback. Maintain structure and add missing elements."
        )
        
        return improved

class OutputValidator:
    """
    Validates output meets specific criteria
    """
    
    @staticmethod
    def validate_diagram(diagram: str) -> Tuple[bool, List[str]]:
        """Validate Mermaid diagram"""
        errors = []
        
        # Check for diagram type
        valid_types = ['graph', 'flowchart', 'sequenceDiagram', 'erDiagram', 'classDiagram']
        if not any(diagram.strip().startswith(t) for t in valid_types):
            errors.append("Missing diagram type declaration")
        
        # Check for content
        if len(diagram.split('\n')) < 3:
            errors.append("Diagram too short - needs more content")
        
        # Check for syntax errors
        open_brackets = diagram.count('[') + diagram.count('(') + diagram.count('{')
        close_brackets = diagram.count(']') + diagram.count(')') + diagram.count('}')
        if open_brackets != close_brackets:
            errors.append("Unmatched brackets")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_documentation(doc: str) -> Tuple[bool, List[str]]:
        """Validate documentation quality"""
        errors = []
        
        # Check length
        if len(doc) < 200:
            errors.append("Documentation too short")
        
        # Check for structure
        if not re.search(r'^#+\s', doc, re.MULTILINE):
            errors.append("Missing headers/structure")
        
        # Check for code examples
        if '```' not in doc and 'code' in doc.lower():
            errors.append("Consider adding code examples")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_api_spec(spec: str) -> Tuple[bool, List[str]]:
        """Validate API specification"""
        errors = []
        
        required_sections = ['endpoint', 'method', 'request', 'response']
        for section in required_sections:
            if section.lower() not in spec.lower():
                errors.append(f"Missing section: {section}")
        
        return len(errors) == 0, errors


def get_quality_system(llm_client):
    """Get complete quality system"""
    evaluator = QualityEvaluator(llm_client)
    improver = SelfImprovement(llm_client, evaluator)
    validator = OutputValidator()
    
    return {
        "evaluator": evaluator,
        "improver": improver,
        "validator": validator
    }

