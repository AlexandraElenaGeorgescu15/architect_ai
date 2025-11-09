"""
Multi-Agent System - Specialized Agents Working Together
Each agent has specific expertise and they collaborate
"""

import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class AgentRole(Enum):
    """Specialized agent roles"""
    ARCHITECT = "architect"  # System design expert
    DATABASE = "database"    # Database/ERD expert
    API = "api"             # API design expert
    FRONTEND = "frontend"   # UI/UX expert
    SECURITY = "security"   # Security expert
    DEVOPS = "devops"       # Deployment expert
    QA = "qa"              # Quality assurance
    PM = "pm"              # Product management

@dataclass
class AgentTask:
    """Task for an agent"""
    role: AgentRole
    description: str
    context: Dict
    dependencies: List[str] = None

@dataclass
class AgentResponse:
    """Response from an agent"""
    role: AgentRole
    task_id: str
    output: str
    confidence: float
    suggestions: List[str] = None

class SpecializedAgent:
    """Base class for specialized agents"""
    
    def __init__(self, role: AgentRole, llm_client):
        self.role = role
        self.llm_client = llm_client
        self.expertise = self._get_expertise()
    
    def _get_expertise(self) -> str:
        """Get agent's area of expertise"""
        expertise_map = {
            AgentRole.ARCHITECT: "system architecture, design patterns, scalability, microservices",
            AgentRole.DATABASE: "database design, ERD, normalization, indexing, query optimization",
            AgentRole.API: "REST API design, GraphQL, API security, versioning, documentation",
            AgentRole.FRONTEND: "UI/UX design, React/Angular, responsive design, accessibility",
            AgentRole.SECURITY: "security best practices, authentication, authorization, encryption",
            AgentRole.DEVOPS: "CI/CD, Docker, Kubernetes, monitoring, deployment strategies",
            AgentRole.QA: "testing strategies, test automation, quality metrics, bug prevention",
            AgentRole.PM: "product strategy, user stories, roadmaps, stakeholder management"
        }
        return expertise_map.get(self.role, "general software development")
    
    async def execute_task(self, task: AgentTask) -> AgentResponse:
        """Execute a task using agent's expertise"""
        prompt = f"""
You are a {self.role.value} expert with deep knowledge in: {self.expertise}

Task: {task.description}

Context:
{self._format_context(task.context)}

Provide a detailed, expert-level response focusing on {self.role.value} concerns.
Include specific recommendations and best practices.
"""
        
        response = await self.llm_client._call_ai(
            prompt,
            f"You are an expert {self.role.value}. Provide detailed, actionable advice."
        )
        
        return AgentResponse(
            role=self.role,
            task_id=task.description[:50],
            output=response,
            confidence=0.9,  # Could be calculated based on response quality
            suggestions=self._extract_suggestions(response)
        )
    
    def _format_context(self, context: Dict) -> str:
        """Format context for prompt"""
        return "\n".join([f"{k}: {v}" for k, v in context.items()])
    
    def _extract_suggestions(self, response: str) -> List[str]:
        """Extract key suggestions from response"""
        # Simple extraction - could be more sophisticated
        suggestions = []
        for line in response.split('\n'):
            if any(keyword in line.lower() for keyword in ['recommend', 'suggest', 'should', 'consider']):
                suggestions.append(line.strip())
        return suggestions[:5]

class MultiAgentOrchestrator:
    """
    Orchestrates multiple specialized agents
    Implements agentic workflow with planning and collaboration
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.agents = self._initialize_agents()
    
    def _initialize_agents(self) -> Dict[AgentRole, SpecializedAgent]:
        """Initialize all specialized agents"""
        agents = {}
        for role in AgentRole:
            agents[role] = SpecializedAgent(role, self.llm_client)
        return agents
    
    async def plan_workflow(self, user_request: str, context: Dict) -> List[AgentTask]:
        """
        Plan which agents should work on what
        Uses LLM to intelligently route tasks
        """
        prompt = f"""
You are a workflow planner. Given this request, determine which specialized agents should work on it.

Request: {user_request}

Available Agents:
- ARCHITECT: System design, architecture
- DATABASE: Database design, ERD
- API: API design, endpoints
- FRONTEND: UI/UX design
- SECURITY: Security review
- DEVOPS: Deployment, CI/CD
- QA: Testing strategy
- PM: Product requirements

For each relevant agent, specify:
1. What they should do
2. What context they need
3. Dependencies (which agents must complete first)

Output as JSON:
{{
    "tasks": [
        {{
            "agent": "ARCHITECT",
            "description": "Design system architecture",
            "dependencies": []
        }},
        ...
    ]
}}
"""
        
        response = await self.llm_client._call_ai(
            prompt,
            "You are a workflow planner. Output valid JSON only."
        )
        
        # Parse and create tasks
        import json
        try:
            data = json.loads(response)
            tasks = []
            for task_data in data.get("tasks", []):
                role = AgentRole[task_data["agent"]]
                task = AgentTask(
                    role=role,
                    description=task_data["description"],
                    context=context,
                    dependencies=task_data.get("dependencies", [])
                )
                tasks.append(task)
            return tasks
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Fallback: create basic tasks
            print(f"[WARN] Task parsing failed: {e}, using fallback tasks")
            return [
                AgentTask(AgentRole.ARCHITECT, "Design system", context),
                AgentTask(AgentRole.DATABASE, "Design database", context)
            ]
    
    async def execute_workflow(self, tasks: List[AgentTask]) -> Dict[AgentRole, AgentResponse]:
        """
        Execute tasks respecting dependencies
        Agents work in parallel where possible
        """
        completed = {}
        remaining = tasks.copy()
        
        while remaining:
            # Find tasks with satisfied dependencies
            ready_tasks = [
                task for task in remaining
                if not task.dependencies or all(dep in completed for dep in task.dependencies)
            ]
            
            if not ready_tasks:
                break  # Circular dependency or error
            
            # Execute ready tasks in parallel
            responses = await asyncio.gather(*[
                self.agents[task.role].execute_task(task)
                for task in ready_tasks
            ])
            
            # Mark as completed
            for task, response in zip(ready_tasks, responses):
                completed[task.role] = response
                remaining.remove(task)
        
        return completed
    
    async def synthesize_results(self, responses: Dict[AgentRole, AgentResponse]) -> str:
        """
        Synthesize all agent responses into coherent output
        """
        prompt = f"""
You are a synthesis expert. Combine these expert opinions into a coherent, comprehensive response.

Expert Responses:
{self._format_responses(responses)}

Create a unified response that:
1. Integrates all perspectives
2. Resolves any conflicts
3. Provides actionable recommendations
4. Maintains technical accuracy
"""
        
        synthesis = await self.llm_client._call_ai(
            prompt,
            "You are a synthesis expert. Create a coherent, comprehensive response."
        )
        
        return synthesis
    
    def _format_responses(self, responses: Dict[AgentRole, AgentResponse]) -> str:
        """Format agent responses for synthesis"""
        formatted = []
        for role, response in responses.items():
            formatted.append(f"\n=== {role.value.upper()} EXPERT ===\n{response.output}\n")
        return "\n".join(formatted)
    
    async def run_multi_agent_workflow(self, user_request: str, context: Dict) -> str:
        """
        Complete multi-agent workflow:
        1. Plan which agents to use
        2. Execute tasks with dependencies
        3. Synthesize results
        """
        print("[INFO] Planning multi-agent workflow...")
        tasks = await self.plan_workflow(user_request, context)
        print(f"[OK] Planned {len(tasks)} agent tasks")
        
        print("[INFO] Executing agent tasks...")
        responses = await self.execute_workflow(tasks)
        print(f"[OK] Completed {len(responses)} agent responses")
        
        print("[INFO] Synthesizing results...")
        final_output = await self.synthesize_results(responses)
        print("[OK] Multi-agent workflow complete")
        
        return final_output


def get_multi_agent_system(llm_client):
    """Get multi-agent orchestrator"""
    return MultiAgentOrchestrator(llm_client)

