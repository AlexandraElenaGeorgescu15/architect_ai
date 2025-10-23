"""
Advanced RAG Techniques - State of the Art
Implements HyDE, query decomposition, multi-hop reasoning, and more
"""

from typing import List, Dict, Tuple, Optional
import asyncio
from dataclasses import dataclass

@dataclass
class QueryPlan:
    """Multi-step query execution plan"""
    original_query: str
    sub_queries: List[str]
    reasoning: str
    execution_order: List[int]

class HyDERetrieval:
    """
    Hypothetical Document Embeddings (HyDE)
    Generate hypothetical answers, embed them, use for retrieval
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def generate_hypothetical_document(self, query: str) -> str:
        """Generate a hypothetical answer to embed"""
        prompt = f"""
Given this query, write a hypothetical perfect answer that would satisfy it.
Be specific, detailed, and technical.

Query: {query}

Hypothetical Answer:"""
        
        response = await self.llm_client._call_ai(
            prompt,
            "You are an expert technical writer. Generate a detailed hypothetical answer."
        )
        return response
    
    async def hyde_retrieval(self, query: str, retrieval_fn) -> List[Dict]:
        """
        Use HyDE for improved retrieval:
        1. Generate hypothetical answer
        2. Embed hypothetical answer
        3. Retrieve using that embedding
        """
        # Generate hypothetical document
        hypo_doc = await self.generate_hypothetical_document(query)
        
        # Use hypothetical document for retrieval
        results = await retrieval_fn(hypo_doc)
        
        return results

class QueryDecomposition:
    """
    Break complex queries into simpler sub-queries
    Execute them in order and synthesize results
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def decompose_query(self, query: str) -> QueryPlan:
        """Decompose complex query into sub-queries"""
        prompt = f"""
You are a query planning expert. Break this complex query into simpler sub-queries.

Query: {query}

Provide:
1. List of 2-4 sub-queries (simpler, focused questions)
2. Reasoning for the decomposition
3. Execution order (which queries depend on others)

Format as JSON:
{{
    "sub_queries": ["query1", "query2", ...],
    "reasoning": "explanation",
    "execution_order": [0, 1, 2, ...]
}}
"""
        
        response = await self.llm_client._call_ai(
            prompt,
            "You are a query planning expert. Output valid JSON only."
        )
        
        # Parse response
        import json
        try:
            data = json.loads(response)
            return QueryPlan(
                original_query=query,
                sub_queries=data.get("sub_queries", [query]),
                reasoning=data.get("reasoning", ""),
                execution_order=data.get("execution_order", list(range(len(data.get("sub_queries", [])))))
            )
        except:
            # Fallback: use original query
            return QueryPlan(
                original_query=query,
                sub_queries=[query],
                reasoning="Decomposition failed, using original query",
                execution_order=[0]
            )
    
    async def execute_plan(self, plan: QueryPlan, retrieval_fn) -> Dict[str, List[Dict]]:
        """Execute query plan and gather results"""
        results = {}
        
        for idx in plan.execution_order:
            sub_query = plan.sub_queries[idx]
            sub_results = await retrieval_fn(sub_query)
            results[sub_query] = sub_results
        
        return results

class MultiHopReasoning:
    """
    Multi-hop reasoning for complex questions
    Follow chains of reasoning across multiple documents
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def identify_reasoning_chain(self, query: str, initial_context: str) -> List[str]:
        """Identify what additional information is needed"""
        prompt = f"""
Given this query and initial context, what additional information do we need?
Generate follow-up queries to gather missing information.

Original Query: {query}

Initial Context:
{initial_context}

Generate 1-3 follow-up queries to fill knowledge gaps:"""
        
        response = await self.llm_client._call_ai(
            prompt,
            "Generate focused follow-up queries."
        )
        
        # Parse follow-up queries
        follow_ups = [q.strip() for q in response.split('\n') if q.strip() and not q.startswith('#')]
        return follow_ups[:3]  # Max 3 hops
    
    async def multi_hop_retrieval(self, query: str, retrieval_fn, max_hops: int = 3) -> List[Dict]:
        """
        Perform multi-hop retrieval:
        1. Initial retrieval
        2. Identify gaps
        3. Retrieve additional info
        4. Repeat until satisfied or max hops
        """
        all_results = []
        current_query = query
        
        for hop in range(max_hops):
            # Retrieve for current query
            results = await retrieval_fn(current_query)
            all_results.extend(results)
            
            # Check if we have enough information
            context = "\n\n".join([r.get("text", "") for r in results[:5]])
            
            # Identify follow-up queries
            follow_ups = await self.identify_reasoning_chain(query, context)
            
            if not follow_ups:
                break  # No more gaps
            
            # Use first follow-up for next hop
            current_query = follow_ups[0]
        
        return all_results

class AdaptiveRetrieval:
    """
    Adaptive retrieval that adjusts strategy based on query type
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.hyde = HyDERetrieval(llm_client)
        self.decomp = QueryDecomposition(llm_client)
        self.multi_hop = MultiHopReasoning(llm_client)
    
    async def classify_query(self, query: str) -> str:
        """Classify query to determine best retrieval strategy"""
        prompt = f"""
Classify this query into ONE category:

Query: {query}

Categories:
- SIMPLE: Direct, factual question (use standard retrieval)
- COMPLEX: Multi-part question (use query decomposition)
- CONCEPTUAL: Abstract/conceptual (use HyDE)
- REASONING: Requires connecting multiple facts (use multi-hop)

Output ONLY the category name:"""
        
        response = await self.llm_client._call_ai(prompt, "Output only the category.")
        category = response.strip().upper()
        
        if category not in ["SIMPLE", "COMPLEX", "CONCEPTUAL", "REASONING"]:
            category = "SIMPLE"
        
        return category
    
    async def adaptive_retrieve(self, query: str, retrieval_fn) -> Tuple[List[Dict], str]:
        """
        Adaptively retrieve based on query type
        Returns: (results, strategy_used)
        """
        # Classify query
        category = await self.classify_query(query)
        
        # Apply appropriate strategy
        if category == "CONCEPTUAL":
            results = await self.hyde.hyde_retrieval(query, retrieval_fn)
            strategy = "HyDE (Hypothetical Document Embeddings)"
        
        elif category == "COMPLEX":
            plan = await self.decomp.decompose_query(query)
            results_dict = await self.decomp.execute_plan(plan, retrieval_fn)
            # Flatten results
            results = []
            for sub_results in results_dict.values():
                results.extend(sub_results)
            strategy = f"Query Decomposition ({len(plan.sub_queries)} sub-queries)"
        
        elif category == "REASONING":
            results = await self.multi_hop.multi_hop_retrieval(query, retrieval_fn)
            strategy = "Multi-Hop Reasoning"
        
        else:  # SIMPLE
            results = await retrieval_fn(query)
            strategy = "Standard Retrieval"
        
        return results, strategy


def get_advanced_retrieval(llm_client):
    """Get advanced retrieval system"""
    return AdaptiveRetrieval(llm_client)

