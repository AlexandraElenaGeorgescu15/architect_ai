"""
Specialized AI Agents for Multi-Perspective Analysis

This module implements a multi-agent system where specialized agents provide
expert opinions from different perspectives:
- DesignAgent: UI/UX, accessibility, visual design
- BackendAgent: Scalability, performance, security
- FrontendAgent: Component design, state management, testing

Each agent analyzes generated artifacts and provides structured feedback,
which is then synthesized into actionable recommendations.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import asyncio
import re


@dataclass
class AgentOpinion:
    """
    Structured opinion from a specialized agent.
    
    Attributes:
        agent_name: Name of the agent (Design, Backend, Frontend)
        perspective: The agent's role/expertise area
        feedback: Overall assessment (2-3 sentences)
        suggestions: List of improvement suggestions
        concerns: List of potential issues or risks
        score: Quality score from 0-100
    """
    agent_name: str
    perspective: str
    feedback: str
    suggestions: List[str]
    concerns: List[str]
    score: float  # 0-100


class DesignAgent:
    """
    UI/UX Design Expert Agent
    
    Focuses on:
    - User experience quality and intuitiveness
    - Accessibility (WCAG compliance)
    - Visual design and hierarchy
    - Interaction patterns and consistency
    - Responsive design
    """
    
    def __init__(self, llm_client):
        """
        Initialize Design Agent
        
        Args:
            llm_client: UniversalArchitectAgent instance for AI calls
        """
        self.llm_client = llm_client
        self.name = "🎨 Design Agent"
        self.expertise = "UI/UX Design & Accessibility"
    
    async def analyze(self, artifact_type: str, content: str, meeting_notes: str) -> AgentOpinion:
        """
        Analyze artifact from design perspective
        
        Args:
            artifact_type: Type of artifact (e.g., 'visual_prototype', 'architecture')
            content: The generated content to review
            meeting_notes: Original meeting notes for context
        
        Returns:
            AgentOpinion with design-focused feedback
        """
        prompt = f"""
You are a Senior UI/UX Designer with 15+ years of experience in enterprise and consumer applications.
You're reviewing a {artifact_type} generated for a development project.

ARTIFACT CONTENT (first 2000 chars):
```
{content[:2000]}
```

ORIGINAL REQUIREMENTS (meeting notes):
```
{meeting_notes[:1000]}
```

Provide your expert design analysis focusing on these areas:

1. **User Experience**: Is this intuitive? Will users understand how to use it?
2. **Accessibility**: Does this follow WCAG 2.1 Level AA guidelines?
3. **Visual Design**: Is the visual hierarchy clear? Is it aesthetically pleasing?
4. **Interaction Patterns**: Are interactions consistent with platform conventions?
5. **Responsiveness**: Will this adapt well to different screen sizes?

Format your response EXACTLY as follows:

PERSPECTIVE: [Your specific role, e.g., "Senior UX Designer specializing in accessible design"]
FEEDBACK: [2-3 sentences summarizing your overall assessment]
SUGGESTIONS:
- [Specific actionable improvement #1]
- [Specific actionable improvement #2]
- [Specific actionable improvement #3]
CONCERNS:
- [Potential issue or risk #1]
- [Potential issue or risk #2]
SCORE: [A number from 0-100 representing quality]
"""
        
        try:
            response = await self.llm_client._call_ai(
                prompt,
                "You are a senior UI/UX designer providing expert analysis."
            )
            return self._parse_opinion(response)
        except Exception as e:
            # Fallback opinion if AI call fails
            return AgentOpinion(
                agent_name=self.name,
                perspective=self.expertise,
                feedback=f"Analysis failed: {str(e)}",
                suggestions=["Retry analysis with different parameters"],
                concerns=["Unable to complete design review"],
                score=0.0
            )
    
    def _parse_opinion(self, response: str) -> AgentOpinion:
        """
        Parse AI response into structured AgentOpinion
        
        Args:
            response: Raw text response from LLM
        
        Returns:
            Structured AgentOpinion object
        """
        # Extract sections using regex
        perspective = re.search(r'PERSPECTIVE:\s*(.+?)(?=\n|$)', response)
        feedback = re.search(r'FEEDBACK:\s*(.+?)(?=SUGGESTIONS:|$)', response, re.DOTALL)
        suggestions_section = re.search(r'SUGGESTIONS:\s*(.+?)(?=CONCERNS:|$)', response, re.DOTALL)
        concerns_section = re.search(r'CONCERNS:\s*(.+?)(?=SCORE:|$)', response, re.DOTALL)
        score = re.search(r'SCORE:\s*(\d+(?:\.\d+)?)', response)
        
        # Parse bulleted lists
        suggestions = []
        if suggestions_section:
            lines = suggestions_section.group(1).split('\n')
            suggestions = [s.strip('- •').strip() for s in lines if s.strip() and s.strip().startswith(('-', '•'))]
        
        concerns = []
        if concerns_section:
            lines = concerns_section.group(1).split('\n')
            concerns = [c.strip('- •').strip() for c in lines if c.strip() and c.strip().startswith(('-', '•'))]
        
        return AgentOpinion(
            agent_name=self.name,
            perspective=perspective.group(1).strip() if perspective else self.expertise,
            feedback=feedback.group(1).strip() if feedback else response[:300],
            suggestions=suggestions[:5],  # Limit to top 5
            concerns=concerns[:5],  # Limit to top 5
            score=float(score.group(1)) if score else 75.0
        )


class BackendAgent:
    """
    Backend Architecture Expert Agent
    
    Focuses on:
    - System scalability and performance
    - Security vulnerabilities and best practices
    - Database design and optimization
    - API design and RESTful principles
    - Error handling and resilience
    """
    
    def __init__(self, llm_client):
        """
        Initialize Backend Agent
        
        Args:
            llm_client: UniversalArchitectAgent instance for AI calls
        """
        self.llm_client = llm_client
        self.name = "🔧 Backend Agent"
        self.expertise = "Backend Architecture & Security"
    
    async def analyze(self, artifact_type: str, content: str, meeting_notes: str) -> AgentOpinion:
        """
        Analyze artifact from backend perspective
        
        Args:
            artifact_type: Type of artifact
            content: The generated content to review
            meeting_notes: Original meeting notes for context
        
        Returns:
            AgentOpinion with backend-focused feedback
        """
        prompt = f"""
You are a Principal Backend Architect with expertise in high-scale distributed systems and security.
You're reviewing a {artifact_type} generated for a development project.

ARTIFACT CONTENT (first 2000 chars):
```
{content[:2000]}
```

ORIGINAL REQUIREMENTS (meeting notes):
```
{meeting_notes[:1000]}
```

Provide your expert backend analysis focusing on these areas:

1. **Scalability**: Can this handle 10,000+ concurrent users? What are the bottlenecks?
2. **Performance**: Are there N+1 queries, inefficient algorithms, or performance issues?
3. **Security**: Any SQL injection, XSS, authentication, or authorization vulnerabilities?
4. **Architecture**: Is the system design sound? Is it maintainable and extensible?
5. **Best Practices**: Does this follow industry standards (SOLID, clean architecture, etc.)?

Format your response EXACTLY as follows:

PERSPECTIVE: [Your specific role, e.g., "Principal Backend Architect specializing in microservices"]
FEEDBACK: [2-3 sentences summarizing your overall assessment]
SUGGESTIONS:
- [Specific actionable improvement #1]
- [Specific actionable improvement #2]
- [Specific actionable improvement #3]
CONCERNS:
- [Potential issue or risk #1]
- [Potential issue or risk #2]
SCORE: [A number from 0-100 representing quality]
"""
        
        try:
            response = await self.llm_client._call_ai(
                prompt,
                "You are a principal backend architect providing expert analysis."
            )
            return self._parse_opinion(response)
        except Exception as e:
            return AgentOpinion(
                agent_name=self.name,
                perspective=self.expertise,
                feedback=f"Analysis failed: {str(e)}",
                suggestions=["Retry analysis with different parameters"],
                concerns=["Unable to complete backend review"],
                score=0.0
            )
    
    def _parse_opinion(self, response: str) -> AgentOpinion:
        """Parse AI response into structured AgentOpinion"""
        perspective = re.search(r'PERSPECTIVE:\s*(.+?)(?=\n|$)', response)
        feedback = re.search(r'FEEDBACK:\s*(.+?)(?=SUGGESTIONS:|$)', response, re.DOTALL)
        suggestions_section = re.search(r'SUGGESTIONS:\s*(.+?)(?=CONCERNS:|$)', response, re.DOTALL)
        concerns_section = re.search(r'CONCERNS:\s*(.+?)(?=SCORE:|$)', response, re.DOTALL)
        score = re.search(r'SCORE:\s*(\d+(?:\.\d+)?)', response)
        
        suggestions = []
        if suggestions_section:
            lines = suggestions_section.group(1).split('\n')
            suggestions = [s.strip('- •').strip() for s in lines if s.strip() and s.strip().startswith(('-', '•'))]
        
        concerns = []
        if concerns_section:
            lines = concerns_section.group(1).split('\n')
            concerns = [c.strip('- •').strip() for c in lines if c.strip() and c.strip().startswith(('-', '•'))]
        
        return AgentOpinion(
            agent_name=self.name,
            perspective=perspective.group(1).strip() if perspective else self.expertise,
            feedback=feedback.group(1).strip() if feedback else response[:300],
            suggestions=suggestions[:5],
            concerns=concerns[:5],
            score=float(score.group(1)) if score else 75.0
        )


class FrontendAgent:
    """
    Frontend Implementation Expert Agent
    
    Focuses on:
    - Component architecture and reusability
    - State management patterns
    - Performance optimization (bundle size, lazy loading)
    - Code quality and TypeScript usage
    - Testing strategy and coverage
    """
    
    def __init__(self, llm_client):
        """
        Initialize Frontend Agent
        
        Args:
            llm_client: UniversalArchitectAgent instance for AI calls
        """
        self.llm_client = llm_client
        self.name = "💻 Frontend Agent"
        self.expertise = "Frontend Engineering & Performance"
    
    async def analyze(self, artifact_type: str, content: str, meeting_notes: str) -> AgentOpinion:
        """
        Analyze artifact from frontend perspective
        
        Args:
            artifact_type: Type of artifact
            content: The generated content to review
            meeting_notes: Original meeting notes for context
        
        Returns:
            AgentOpinion with frontend-focused feedback
        """
        prompt = f"""
You are a Staff Frontend Engineer with deep expertise in modern frameworks and performance optimization.
You're reviewing a {artifact_type} generated for a development project.

ARTIFACT CONTENT (first 2000 chars):
```
{content[:2000]}
```

ORIGINAL REQUIREMENTS (meeting notes):
```
{meeting_notes[:1000]}
```

Provide your expert frontend analysis focusing on these areas:

1. **Component Design**: Are components well-structured, reusable, and follow single responsibility?
2. **State Management**: Is state handled correctly? Any prop drilling or unnecessary re-renders?
3. **Performance**: Bundle size concerns? Lazy loading? Memoization? Optimization opportunities?
4. **Code Quality**: Clean code? Proper TypeScript types? Follows linting rules?
5. **Testing**: Is this testable? What unit/integration tests are needed?

Format your response EXACTLY as follows:

PERSPECTIVE: [Your specific role, e.g., "Staff Frontend Engineer specializing in React performance"]
FEEDBACK: [2-3 sentences summarizing your overall assessment]
SUGGESTIONS:
- [Specific actionable improvement #1]
- [Specific actionable improvement #2]
- [Specific actionable improvement #3]
CONCERNS:
- [Potential issue or risk #1]
- [Potential issue or risk #2]
SCORE: [A number from 0-100 representing quality]
"""
        
        try:
            response = await self.llm_client._call_ai(
                prompt,
                "You are a staff frontend engineer providing expert analysis."
            )
            return self._parse_opinion(response)
        except Exception as e:
            return AgentOpinion(
                agent_name=self.name,
                perspective=self.expertise,
                feedback=f"Analysis failed: {str(e)}",
                suggestions=["Retry analysis with different parameters"],
                concerns=["Unable to complete frontend review"],
                score=0.0
            )
    
    def _parse_opinion(self, response: str) -> AgentOpinion:
        """Parse AI response into structured AgentOpinion"""
        perspective = re.search(r'PERSPECTIVE:\s*(.+?)(?=\n|$)', response)
        feedback = re.search(r'FEEDBACK:\s*(.+?)(?=SUGGESTIONS:|$)', response, re.DOTALL)
        suggestions_section = re.search(r'SUGGESTIONS:\s*(.+?)(?=CONCERNS:|$)', response, re.DOTALL)
        concerns_section = re.search(r'CONCERNS:\s*(.+?)(?=SCORE:|$)', response, re.DOTALL)
        score = re.search(r'SCORE:\s*(\d+(?:\.\d+)?)', response)
        
        suggestions = []
        if suggestions_section:
            lines = suggestions_section.group(1).split('\n')
            suggestions = [s.strip('- •').strip() for s in lines if s.strip() and s.strip().startswith(('-', '•'))]
        
        concerns = []
        if concerns_section:
            lines = concerns_section.group(1).split('\n')
            concerns = [c.strip('- •').strip() for c in lines if c.strip() and c.strip().startswith(('-', '•'))]
        
        return AgentOpinion(
            agent_name=self.name,
            perspective=perspective.group(1).strip() if perspective else self.expertise,
            feedback=feedback.group(1).strip() if feedback else response[:300],
            suggestions=suggestions[:5],
            concerns=concerns[:5],
            score=float(score.group(1)) if score else 75.0
        )


class MultiAgentOrchestrator:
    """
    Orchestrates multiple specialized agents for comprehensive analysis
    
    This class coordinates parallel execution of multiple expert agents,
    collects their opinions, and synthesizes them into actionable recommendations.
    """
    
    def __init__(self, llm_client):
        """
        Initialize orchestrator with all specialized agents
        
        Args:
            llm_client: UniversalArchitectAgent instance for AI calls
        """
        self.llm_client = llm_client
        self.design_agent = DesignAgent(llm_client)
        self.backend_agent = BackendAgent(llm_client)
        self.frontend_agent = FrontendAgent(llm_client)
    
    async def analyze_with_agents(
        self, 
        artifact_type: str, 
        content: str, 
        meeting_notes: str
    ) -> Dict:
        """
        Get opinions from all agents in parallel
        
        Runs all three specialized agents concurrently for efficiency,
        then synthesizes their feedback into a cohesive summary.
        
        Args:
            artifact_type: Type of artifact being analyzed
            content: The generated content to review
            meeting_notes: Original meeting notes for context
        
        Returns:
            Dictionary containing:
            - opinions: List of AgentOpinion objects
            - synthesis: Combined actionable summary
            - average_score: Mean score across all agents
            - agent_count: Number of successful agent analyses
        """
        # Run all agents in parallel for speed
        tasks = [
            self.design_agent.analyze(artifact_type, content, meeting_notes),
            self.backend_agent.analyze(artifact_type, content, meeting_notes),
            self.frontend_agent.analyze(artifact_type, content, meeting_notes),
        ]
        
        # Gather results, handling exceptions gracefully
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions, keep only valid opinions
        valid_opinions = [
            result for result in results 
            if isinstance(result, AgentOpinion) and result.score > 0
        ]
        
        if not valid_opinions:
            return {
                'opinions': [],
                'synthesis': "All agent analyses failed. Please try again.",
                'average_score': 0,
                'agent_count': 0
            }
        
        # Synthesize opinions into actionable summary
        synthesis = await self._synthesize_opinions(valid_opinions, artifact_type)
        
        # Calculate average score
        average_score = sum(op.score for op in valid_opinions) / len(valid_opinions)
        
        return {
            'opinions': valid_opinions,
            'synthesis': synthesis,
            'average_score': average_score,
            'agent_count': len(valid_opinions)
        }
    
    async def _synthesize_opinions(
        self, 
        opinions: List[AgentOpinion], 
        artifact_type: str
    ) -> str:
        """
        Synthesize multiple agent opinions into actionable summary
        
        Takes feedback from all agents and creates a prioritized,
        actionable summary of the most important points.
        
        Args:
            opinions: List of agent opinions
            artifact_type: Type of artifact being analyzed
        
        Returns:
            Markdown-formatted synthesis summary
        """
        if not opinions:
            return "No agent opinions available for synthesis."
        
        # Compile all suggestions and concerns
        all_suggestions = []
        all_concerns = []
        
        for opinion in opinions:
            all_suggestions.extend(opinion.suggestions)
            all_concerns.extend(opinion.concerns)
        
        # Create synthesis prompt
        prompt = f"""
You are synthesizing feedback from {len(opinions)} expert agents analyzing a {artifact_type}.

AGENT SCORES & FEEDBACK:
{chr(10).join(f"- {op.agent_name}: {op.score}/100 - {op.feedback[:200]}" for op in opinions)}

ALL SUGGESTIONS ({len(all_suggestions)} total):
{chr(10).join(f"- {s}" for s in all_suggestions[:15])}

ALL CONCERNS ({len(all_concerns)} total):
{chr(10).join(f"- {c}" for c in all_concerns[:15])}

Create a concise synthesis with:

1. **Overall Assessment** (2-3 sentences): What's the overall quality? What's working well?
2. **Top 3 Priority Actions**: What should be addressed first?
3. **Critical Issues** (if any): What absolutely must be fixed?

Be specific, actionable, and prioritize by impact. Use markdown formatting.
Keep it under 300 words.
"""
        
        try:
            synthesis = await self.llm_client._call_ai(
                prompt,
                "You are synthesizing expert opinions into actionable recommendations."
            )
            return synthesis
        except Exception as e:
            # Fallback synthesis if AI call fails
            return f"""
**Overall Assessment**: {len(opinions)} agents provided feedback with an average score of {sum(op.score for op in opinions) / len(opinions):.1f}/100.

**Top Priority Actions**:
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(all_suggestions[:3]))}

**Critical Issues**:
{chr(10).join(f"- {c}" for c in all_concerns[:3]) if all_concerns else "No critical issues identified."}
"""

