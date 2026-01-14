"""
Advanced Prompting Techniques
Chain-of-Thought, Tree-of-Thought, ReAct, Self-Consistency
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
import asyncio

@dataclass
class ReasoningStep:
    """Single step in reasoning chain"""
    thought: str
    action: str
    observation: str

@dataclass
class ThoughtTree:
    """Tree of possible reasoning paths"""
    root_thought: str
    branches: List['ThoughtTree']
    evaluation_score: float

class ChainOfThought:
    """
    Chain-of-Thought (CoT) Prompting
    Makes LLM show its reasoning step-by-step
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def generate_with_cot(self, task: str, context: str = "") -> Tuple[str, List[str]]:
        """
        Generate response with explicit reasoning chain
        Returns: (final_answer, reasoning_steps)
        """
        prompt = f"""
Let's approach this step-by-step:

Task: {task}

Context: {context}

Think through this carefully:
1. First, let's understand what we're being asked
2. Then, let's identify the key components
3. Next, let's reason through the solution
4. Finally, let's formulate the answer

Show your reasoning at each step, then provide the final answer.

Reasoning:"""
        
        response = await self.llm_client._call_ai(
            prompt,
            "Think step-by-step. Show your reasoning clearly."
        )
        
        # Extract reasoning steps and final answer
        steps = self._extract_reasoning_steps(response)
        final_answer = self._extract_final_answer(response)
        
        return final_answer, steps
    
    def _extract_reasoning_steps(self, response: str) -> List[str]:
        """Extract individual reasoning steps"""
        steps = []
        for line in response.split('\n'):
            if any(marker in line.lower() for marker in ['step', 'first', 'then', 'next', 'finally']):
                steps.append(line.strip())
        return steps
    
    def _extract_final_answer(self, response: str) -> str:
        """Extract final answer from response"""
        # Look for conclusion markers
        lines = response.split('\n')
        for i, line in enumerate(lines):
            if any(marker in line.lower() for marker in ['therefore', 'conclusion', 'final', 'answer']):
                return '\n'.join(lines[i:])
        return response  # Fallback: return full response

class TreeOfThought:
    """
    Tree-of-Thought (ToT) Prompting
    Explores multiple reasoning paths and selects best
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def generate_with_tot(self, task: str, num_branches: int = 3) -> Tuple[str, ThoughtTree]:
        """
        Generate response exploring multiple reasoning paths
        Returns: (best_answer, thought_tree)
        """
        # Generate initial thoughts
        initial_thoughts = await self._generate_initial_thoughts(task, num_branches)
        
        # Build thought tree
        tree = await self._build_thought_tree(task, initial_thoughts)
        
        # Select best path
        best_answer = await self._select_best_path(tree)
        
        return best_answer, tree
    
    async def _generate_initial_thoughts(self, task: str, num: int) -> List[str]:
        """Generate multiple initial approaches"""
        prompt = f"""
Generate {num} different approaches to solve this task:

Task: {task}

For each approach, provide a brief description of the strategy.

Approach 1:
Approach 2:
Approach 3:"""
        
        response = await self.llm_client._call_ai(prompt, "Generate diverse approaches.")
        
        # Parse approaches
        approaches = []
        for line in response.split('\n'):
            if line.strip().startswith('Approach'):
                approaches.append(line.split(':', 1)[1].strip() if ':' in line else line)
        
        return approaches[:num]
    
    async def _build_thought_tree(self, task: str, initial_thoughts: List[str]) -> ThoughtTree:
        """Build tree of reasoning paths"""
        # For simplicity, create flat tree (could be recursive)
        branches = []
        
        for thought in initial_thoughts:
            # Evaluate this thought
            score = await self._evaluate_thought(task, thought)
            branch = ThoughtTree(
                root_thought=thought,
                branches=[],
                evaluation_score=score
            )
            branches.append(branch)
        
        root = ThoughtTree(
            root_thought=task,
            branches=branches,
            evaluation_score=0.0
        )
        
        return root
    
    async def _evaluate_thought(self, task: str, thought: str) -> float:
        """Evaluate quality of a reasoning path"""
        prompt = f"""
Rate the quality of this approach for solving the task (0.0 to 1.0):

Task: {task}
Approach: {thought}

Consider:
- Correctness
- Completeness
- Efficiency
- Clarity

Score (0.0-1.0):"""
        
        response = await self.llm_client._call_ai(prompt, "Provide only a number between 0 and 1.")
        
        try:
            score = float(response.strip().split()[0])
            return max(0.0, min(1.0, score))
        except (ValueError, IndexError):
            return 0.5  # Default when parsing fails
    
    async def _select_best_path(self, tree: ThoughtTree) -> str:
        """Select and execute best reasoning path"""
        # Find branch with highest score
        best_branch = max(tree.branches, key=lambda b: b.evaluation_score)
        
        # Generate full response using best approach
        prompt = f"""
Using this approach, provide a complete solution:

Approach: {best_branch.root_thought}

Provide detailed solution:"""
        
        response = await self.llm_client._call_ai(prompt, "Provide complete solution.")
        return response

class ReActAgent:
    """
    ReAct (Reasoning + Acting) Pattern
    Interleaves reasoning, actions, and observations
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def react_generate(self, task: str, max_steps: int = 5) -> Tuple[str, List[ReasoningStep]]:
        """
        Generate using ReAct pattern:
        Thought -> Action -> Observation -> Thought -> ...
        """
        steps = []
        context = ""
        
        for step_num in range(max_steps):
            # Generate thought
            thought = await self._generate_thought(task, context, step_num)
            
            # Determine action
            action = await self._determine_action(thought)
            
            # Execute action (simulated)
            observation = await self._execute_action(action, context)
            
            # Record step
            steps.append(ReasoningStep(
                thought=thought,
                action=action,
                observation=observation
            ))
            
            # Update context
            context += f"\nStep {step_num + 1}:\nThought: {thought}\nAction: {action}\nObservation: {observation}\n"
            
            # Check if done
            if "FINISH" in action.upper():
                break
        
        # Generate final answer
        final_answer = await self._generate_final_answer(task, steps)
        
        return final_answer, steps
    
    async def _generate_thought(self, task: str, context: str, step_num: int) -> str:
        """Generate reasoning thought"""
        prompt = f"""
Task: {task}

Context so far:
{context}

Step {step_num + 1} - What should we think about next?

Thought:"""
        
        response = await self.llm_client._call_ai(prompt, "Generate next reasoning step.")
        return response.strip()
    
    async def _determine_action(self, thought: str) -> str:
        """Determine action based on thought"""
        prompt = f"""
Based on this thought, what action should we take?

Thought: {thought}

Available actions:
- SEARCH: Search for information
- ANALYZE: Analyze current information
- SYNTHESIZE: Combine information
- FINISH: Complete the task

Action:"""
        
        response = await self.llm_client._call_ai(prompt, "Choose an action.")
        return response.strip()
    
    async def _execute_action(self, action: str, context: str) -> str:
        """Execute action and return observation"""
        # Simulated action execution
        if "SEARCH" in action.upper():
            return "Found relevant information in context"
        elif "ANALYZE" in action.upper():
            return "Analysis reveals key patterns"
        elif "SYNTHESIZE" in action.upper():
            return "Combined information into coherent understanding"
        else:
            return "Action completed"
    
    async def _generate_final_answer(self, task: str, steps: List[ReasoningStep]) -> str:
        """Generate final answer from reasoning steps"""
        steps_text = "\n\n".join([
            f"Step {i+1}:\nThought: {s.thought}\nAction: {s.action}\nObservation: {s.observation}"
            for i, s in enumerate(steps)
        ])
        
        prompt = f"""
Task: {task}

Reasoning Process:
{steps_text}

Based on this reasoning, provide the final answer:"""
        
        response = await self.llm_client._call_ai(prompt, "Provide final answer.")
        return response

class SelfConsistency:
    """
    Self-Consistency Prompting
    Generate multiple responses and select most consistent
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def generate_with_consistency(self, task: str, num_samples: int = 5) -> Tuple[str, float]:
        """
        Generate multiple responses and find consensus
        Returns: (consensus_answer, confidence_score)
        """
        # Generate multiple responses
        responses = await asyncio.gather(*[
            self._generate_single_response(task)
            for _ in range(num_samples)
        ])
        
        # Find consensus
        consensus, confidence = self._find_consensus(responses)
        
        return consensus, confidence
    
    async def _generate_single_response(self, task: str) -> str:
        """Generate single response with slight variation"""
        prompt = f"""
{task}

Provide your answer:"""
        
        response = await self.llm_client._call_ai(prompt, "Provide clear answer.")
        return response.strip()
    
    def _find_consensus(self, responses: List[str]) -> Tuple[str, float]:
        """Find most consistent response"""
        # Simple approach: find most common response
        from collections import Counter
        
        # Normalize responses
        normalized = [r.lower().strip() for r in responses]
        
        # Count occurrences
        counter = Counter(normalized)
        
        # Guard against empty responses
        if not counter:
            return responses[0] if responses else "", 0.0
        
        most_common = counter.most_common(1)[0]
        
        # Find original response
        consensus_normalized = most_common[0]
        consensus = next((r for r in responses if r.lower().strip() == consensus_normalized), "")
        
        # Calculate confidence
        confidence = most_common[1] / len(responses) if responses else 0.0
        
        return consensus, confidence


def get_advanced_prompting(llm_client):
    """Get advanced prompting toolkit"""
    return {
        "cot": ChainOfThought(llm_client),
        "tot": TreeOfThought(llm_client),
        "react": ReActAgent(llm_client),
        "self_consistency": SelfConsistency(llm_client)
    }

