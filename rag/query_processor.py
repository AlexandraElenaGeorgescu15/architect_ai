"""
Intelligent Query Processing
Expands queries, understands intent, and optimizes for better retrieval
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import re

@dataclass
class QueryAnalysis:
    """Analysis of a query"""
    original_query: str
    query_type: str
    expanded_queries: List[str]
    technical_terms: List[str]
    filters: Dict[str, Any]
    priority: str  # 'high', 'medium', 'low'

class QueryProcessor:
    """Process and enhance queries for better retrieval"""
    
    # Query type patterns
    QUERY_PATTERNS = {
        'code_search': [
            r'\b(function|class|method|implementation|code for)\b',
            r'\b(how to implement|show me|example of)\b'
        ],
        'architecture': [
            r'\b(architecture|design pattern|structure|organization)\b',
            r'\b(how is.*organized|system design)\b'
        ],
        'api': [
            r'\b(api|endpoint|route|rest|graphql)\b',
            r'\b(http|request|response)\b'
        ],
        'documentation': [
            r'\b(how to|guide|tutorial|documentation|readme)\b',
            r'\b(explain|what is|describe)\b'
        ],
        'configuration': [
            r'\b(config|configuration|settings|environment)\b',
            r'\b(setup|install|deploy)\b'
        ],
        'testing': [
            r'\b(test|testing|spec|unit test|integration test)\b',
            r'\b(mock|fixture|assertion)\b'
        ],
        'database': [
            r'\b(database|sql|query|schema|model)\b',
            r'\b(table|collection|migration)\b'
        ],
        'security': [
            r'\b(security|authentication|authorization|auth)\b',
            r'\b(token|jwt|password|encryption)\b'
        ]
    }
    
    # Technical term expansions
    TECH_EXPANSIONS = {
        'auth': ['authentication', 'authorization', 'auth', 'login', 'jwt', 'token'],
        'db': ['database', 'data store', 'persistence', 'repository'],
        'api': ['api', 'endpoint', 'route', 'service', 'rest', 'graphql'],
        'ui': ['user interface', 'frontend', 'component', 'view', 'page'],
        'backend': ['backend', 'server', 'api', 'service', 'controller'],
        'test': ['test', 'testing', 'spec', 'unit test', 'integration test'],
        'config': ['configuration', 'settings', 'environment', 'setup'],
        'deploy': ['deployment', 'deploy', 'release', 'ci/cd', 'pipeline']
    }
    
    def __init__(self):
        self.query_cache = {}
    
    def analyze_query(self, query: str) -> QueryAnalysis:
        """Analyze and understand the query"""
        
        # Check cache
        if query in self.query_cache:
            return self.query_cache[query]
        
        # Classify query type
        query_type = self._classify_query(query)
        
        # Expand query
        expanded = self._expand_query(query, query_type)
        
        # Extract technical terms
        tech_terms = self._extract_technical_terms(query)
        
        # Determine filters
        filters = self._determine_filters(query, query_type)
        
        # Assess priority
        priority = self._assess_priority(query)
        
        analysis = QueryAnalysis(
            original_query=query,
            query_type=query_type,
            expanded_queries=expanded,
            technical_terms=tech_terms,
            filters=filters,
            priority=priority
        )
        
        # Cache result
        self.query_cache[query] = analysis
        
        return analysis
    
    def _classify_query(self, query: str) -> str:
        """Classify the type of query"""
        query_lower = query.lower()
        
        scores = {}
        for query_type, patterns in self.QUERY_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1
            scores[query_type] = score
        
        # Return type with highest score, or 'general' if no match
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return 'general'
    
    def _expand_query(self, query: str, query_type: str) -> List[str]:
        """Expand query with variations"""
        expansions = [query]
        query_lower = query.lower()
        
        # Add technical term expansions
        for short_term, expanded_terms in self.TECH_EXPANSIONS.items():
            if short_term in query_lower:
                for expanded_term in expanded_terms:
                    if expanded_term not in query_lower:
                        expanded_query = query_lower.replace(short_term, expanded_term)
                        expansions.append(expanded_query)
        
        # Add query type specific expansions
        if query_type == 'code_search':
            expansions.extend([
                f"implementation of {query}",
                f"code example {query}",
                f"{query} source code"
            ])
        elif query_type == 'architecture':
            expansions.extend([
                f"{query} design pattern",
                f"{query} architecture",
                f"how {query} is structured"
            ])
        elif query_type == 'api':
            expansions.extend([
                f"{query} endpoint",
                f"{query} api route",
                f"{query} request handler"
            ])
        
        # Remove duplicates and limit
        return list(dict.fromkeys(expansions))[:5]
    
    def _extract_technical_terms(self, query: str) -> List[str]:
        """Extract technical terms from query"""
        terms = []
        query_lower = query.lower()
        
        # Common technical terms
        tech_keywords = [
            'react', 'angular', 'vue', 'node', 'python', 'java', 'typescript',
            'javascript', 'api', 'rest', 'graphql', 'database', 'sql', 'nosql',
            'mongodb', 'postgresql', 'redis', 'docker', 'kubernetes', 'aws',
            'azure', 'gcp', 'authentication', 'authorization', 'jwt', 'oauth',
            'microservices', 'monolith', 'serverless', 'lambda', 'function'
        ]
        
        for term in tech_keywords:
            if term in query_lower:
                terms.append(term)
        
        return terms
    
    def _determine_filters(self, query: str, query_type: str) -> Dict[str, Any]:
        """Determine metadata filters based on query"""
        filters = {}
        query_lower = query.lower()
        
        # File type filters
        if 'typescript' in query_lower or '.ts' in query_lower:
            filters['file_type'] = ['.ts', '.tsx']
        elif 'javascript' in query_lower or '.js' in query_lower:
            filters['file_type'] = ['.js', '.jsx']
        elif 'python' in query_lower or '.py' in query_lower:
            filters['file_type'] = ['.py']
        elif 'java' in query_lower:
            filters['file_type'] = ['.java']
        elif 'c#' in query_lower or 'csharp' in query_lower:
            filters['file_type'] = ['.cs']
        
        # Component type filters
        if query_type == 'testing':
            filters['has_tests'] = True
        elif query_type == 'configuration':
            filters['is_config'] = True
        elif query_type == 'documentation':
            filters['file_type'] = ['.md', '.txt']
        
        # Recency filter for certain queries
        if 'recent' in query_lower or 'latest' in query_lower:
            filters['sort_by'] = 'modified_date'
            filters['order'] = 'desc'
        
        return filters
    
    def _assess_priority(self, query: str) -> str:
        """Assess query priority"""
        query_lower = query.lower()
        
        # High priority indicators
        high_priority_terms = ['critical', 'urgent', 'security', 'bug', 'error', 'crash']
        if any(term in query_lower for term in high_priority_terms):
            return 'high'
        
        # Low priority indicators
        low_priority_terms = ['example', 'tutorial', 'learn', 'understand']
        if any(term in query_lower for term in low_priority_terms):
            return 'low'
        
        return 'medium'
    
    def optimize_for_llm(self, query: str, context_limit: int = 8000) -> str:
        """Optimize query for LLM context"""
        analysis = self.analyze_query(query)
        
        # Build optimized query
        optimized = f"Query Type: {analysis.query_type}\n"
        optimized += f"Original: {analysis.original_query}\n"
        
        if analysis.technical_terms:
            optimized += f"Technical Context: {', '.join(analysis.technical_terms)}\n"
        
        if analysis.filters:
            optimized += f"Filters: {analysis.filters}\n"
        
        optimized += f"\nExpanded Queries:\n"
        for i, exp_query in enumerate(analysis.expanded_queries, 1):
            optimized += f"{i}. {exp_query}\n"
        
        return optimized


# Global query processor
_query_processor = None

def get_query_processor() -> QueryProcessor:
    """Get or create global query processor"""
    global _query_processor
    if _query_processor is None:
        _query_processor = QueryProcessor()
    return _query_processor

# Alias for backward compatibility
def get_query_expander() -> QueryProcessor:
    """Alias for get_query_processor"""
    return get_query_processor()

