#!/usr/bin/env python3
"""
RAG Evaluation Script - "Is My RAG Actually Smart?"

This script evaluates the RAG pipeline by:
1. Running 10 "Golden Questions" through the RAG system
2. Using Gemini 2.0 Flash as a judge to score responses 1-5
3. Measuring context relevance and syntax validity

Usage:
    python tests/eval_rag.py
    python tests/eval_rag.py --verbose
    python tests/eval_rag.py --questions 5

Requirements:
    - GOOGLE_API_KEY or GEMINI_API_KEY in environment
    - ChromaDB index must be built (run rag/ingest.py first)
"""

import sys
import json
import time
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


# =============================================================================
# Golden Questions - The RAG Benchmark
# =============================================================================

GOLDEN_QUESTIONS = [
    {
        "id": 1,
        "question": "Generate a Python class for user authentication with JWT tokens",
        "expected_context": ["auth", "jwt", "token", "user"],
        "artifact_type": "code_python",
        "category": "code_generation"
    },
    {
        "id": 2,
        "question": "Create a Mermaid sequence diagram showing the artifact generation flow",
        "expected_context": ["generation", "artifact", "service", "api"],
        "artifact_type": "mermaid_sequence",
        "category": "diagram"
    },
    {
        "id": 3,
        "question": "Explain how the knowledge graph is built from Python AST",
        "expected_context": ["ast", "parse", "graph", "node", "class", "function"],
        "artifact_type": "explanation",
        "category": "understanding"
    },
    {
        "id": 4,
        "question": "Generate a FastAPI endpoint for creating new artifacts",
        "expected_context": ["fastapi", "post", "endpoint", "artifact", "dto"],
        "artifact_type": "code_python",
        "category": "code_generation"
    },
    {
        "id": 5,
        "question": "Create an ERD diagram for the database schema",
        "expected_context": ["model", "database", "table", "foreign key", "sqlalchemy"],
        "artifact_type": "mermaid_erd",
        "category": "diagram"
    },
    {
        "id": 6,
        "question": "Write a React component for displaying artifact cards",
        "expected_context": ["component", "react", "typescript", "props", "artifact"],
        "artifact_type": "code_frontend",
        "category": "code_generation"
    },
    {
        "id": 7,
        "question": "How does the RAG retrieval system combine vector and BM25 search?",
        "expected_context": ["vector", "bm25", "hybrid", "search", "retrieval", "chromadb"],
        "artifact_type": "explanation",
        "category": "understanding"
    },
    {
        "id": 8,
        "question": "Generate a class diagram showing the service layer architecture",
        "expected_context": ["service", "class", "method", "backend"],
        "artifact_type": "mermaid_class",
        "category": "diagram"
    },
    {
        "id": 9,
        "question": "Create a Pydantic model for the artifact creation request",
        "expected_context": ["pydantic", "model", "field", "validation", "dto"],
        "artifact_type": "code_python",
        "category": "code_generation"
    },
    {
        "id": 10,
        "question": "Explain the model routing logic for selecting AI models",
        "expected_context": ["model", "routing", "ollama", "gemini", "fallback", "selection"],
        "artifact_type": "explanation",
        "category": "understanding"
    }
]


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class RAGResult:
    """Result from RAG retrieval."""
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    query_time_ms: float = 0.0
    total_chunks: int = 0


@dataclass
class GenerationResult:
    """Result from artifact generation."""
    content: str = ""
    model_used: str = ""
    generation_time_ms: float = 0.0
    success: bool = False
    error: Optional[str] = None


@dataclass
class JudgeScore:
    """Score from the LLM judge."""
    context_relevance: int = 0  # 1-5: Does the response use retrieved context?
    syntax_validity: int = 0     # 1-5: Is the syntax valid?
    overall_quality: int = 0     # 1-5: Overall response quality
    reasoning: str = ""
    raw_response: str = ""


@dataclass
class EvalResult:
    """Complete evaluation result for a question."""
    question_id: int
    question: str
    category: str
    rag_result: RAGResult
    generation_result: GenerationResult
    judge_score: JudgeScore
    context_match_ratio: float = 0.0  # % of expected terms found in context


# =============================================================================
# RAG Retrieval
# =============================================================================

async def run_rag_retrieval(question: str, artifact_type: str) -> RAGResult:
    """Run RAG retrieval for a question."""
    start_time = time.time()
    
    try:
        # Import RAG components
        from backend.services.rag_retriever import RAGRetriever
        
        retriever = RAGRetriever()
        
        # Perform hybrid search
        chunks = await retriever.search(
            query=question,
            artifact_type=artifact_type,
            top_k=10
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return RAGResult(
            chunks=[{"content": c.get("content", ""), "source": c.get("source", "")} for c in chunks],
            query_time_ms=elapsed_ms,
            total_chunks=len(chunks)
        )
    
    except Exception as e:
        console.print(f"[yellow]⚠ RAG retrieval error: {e}[/]")
        return RAGResult(query_time_ms=(time.time() - start_time) * 1000)


# =============================================================================
# Generation
# =============================================================================

async def run_generation(question: str, artifact_type: str, context: str) -> GenerationResult:
    """Run artifact generation."""
    start_time = time.time()
    
    try:
        from backend.services.enhanced_generation import EnhancedGenerationService
        
        service = EnhancedGenerationService()
        
        # Build request
        result = await service.generate(
            prompt=question,
            artifact_type=artifact_type,
            context=context
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return GenerationResult(
            content=result.get("content", ""),
            model_used=result.get("model", "unknown"),
            generation_time_ms=elapsed_ms,
            success=True
        )
    
    except Exception as e:
        console.print(f"[yellow]⚠ Generation error: {e}[/]")
        return GenerationResult(
            generation_time_ms=(time.time() - start_time) * 1000,
            success=False,
            error=str(e)
        )


# =============================================================================
# LLM Judge (Gemini 2.0 Flash)
# =============================================================================

async def judge_response(
    question: str,
    context: str,
    response: str,
    artifact_type: str
) -> JudgeScore:
    """Use Gemini 2.0 Flash to judge the response quality."""
    import os
    import google.generativeai as genai
    
    # Get API key
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        console.print("[red]❌ No GOOGLE_API_KEY or GEMINI_API_KEY found[/]")
        return JudgeScore(reasoning="No API key available")
    
    genai.configure(api_key=api_key)
    
    judge_prompt = f"""You are an expert code reviewer evaluating an AI-generated response.

## The Question Asked:
{question}

## The Retrieved Context (RAG chunks):
{context[:3000]}

## The AI's Response:
{response[:3000]}

## Expected Artifact Type: {artifact_type}

---

Score the response on three dimensions (1-5 scale):

1. **Context Relevance (1-5)**: Does the response demonstrate understanding and use of the retrieved context?
   - 1: Completely ignores context, generic response
   - 3: Uses some context but misses key information
   - 5: Excellent use of context, references specific details

2. **Syntax Validity (1-5)**: Is the code/diagram syntax correct and runnable?
   - 1: Major syntax errors, wouldn't compile/render
   - 3: Minor issues but mostly correct
   - 5: Perfect syntax, production-ready

3. **Overall Quality (1-5)**: How useful and complete is the response?
   - 1: Unusable, wrong approach
   - 3: Acceptable but could be better
   - 5: Excellent, would use as-is

Return your response as JSON:
{{
  "context_relevance": <1-5>,
  "syntax_validity": <1-5>,
  "overall_quality": <1-5>,
  "reasoning": "<2-3 sentence explanation>"
}}

ONLY return the JSON, no other text."""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        response_obj = await asyncio.to_thread(
            model.generate_content,
            judge_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=500
            )
        )
        
        raw = response_obj.text.strip()
        
        # Parse JSON from response
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            scores = json.loads(json_match.group())
            return JudgeScore(
                context_relevance=scores.get("context_relevance", 0),
                syntax_validity=scores.get("syntax_validity", 0),
                overall_quality=scores.get("overall_quality", 0),
                reasoning=scores.get("reasoning", ""),
                raw_response=raw
            )
        
        return JudgeScore(reasoning="Failed to parse judge response", raw_response=raw)
    
    except Exception as e:
        console.print(f"[yellow]⚠ Judge error: {e}[/]")
        return JudgeScore(reasoning=f"Judge failed: {e}")


def calculate_context_match(expected_terms: List[str], retrieved_content: str) -> float:
    """Calculate what percentage of expected terms appear in retrieved context."""
    if not expected_terms:
        return 0.0
    
    content_lower = retrieved_content.lower()
    matches = sum(1 for term in expected_terms if term.lower() in content_lower)
    return matches / len(expected_terms)


# =============================================================================
# Main Evaluation Loop
# =============================================================================

async def evaluate_question(question_data: Dict[str, Any], verbose: bool = False) -> EvalResult:
    """Evaluate a single golden question."""
    question = question_data["question"]
    artifact_type = question_data["artifact_type"]
    expected_context = question_data["expected_context"]
    
    # Step 1: RAG Retrieval
    rag_result = await run_rag_retrieval(question, artifact_type)
    
    # Combine context
    combined_context = "\n\n".join([
        f"[{c.get('source', 'unknown')}]\n{c.get('content', '')}"
        for c in rag_result.chunks
    ])
    
    # Calculate context match
    context_match = calculate_context_match(expected_context, combined_context)
    
    if verbose:
        console.print(f"  📚 Retrieved {rag_result.total_chunks} chunks in {rag_result.query_time_ms:.0f}ms")
        console.print(f"  🎯 Context match: {context_match*100:.0f}% of expected terms")
    
    # Step 2: Generation
    gen_result = await run_generation(question, artifact_type, combined_context)
    
    if verbose:
        console.print(f"  🤖 Generated with {gen_result.model_used} in {gen_result.generation_time_ms:.0f}ms")
    
    # Step 3: Judge with Gemini
    judge_score = await judge_response(
        question=question,
        context=combined_context,
        response=gen_result.content,
        artifact_type=artifact_type
    )
    
    if verbose:
        console.print(f"  ⚖️  Scores: Context={judge_score.context_relevance}, Syntax={judge_score.syntax_validity}, Quality={judge_score.overall_quality}")
    
    return EvalResult(
        question_id=question_data["id"],
        question=question,
        category=question_data["category"],
        rag_result=rag_result,
        generation_result=gen_result,
        judge_score=judge_score,
        context_match_ratio=context_match
    )


async def run_evaluation(num_questions: int = 10, verbose: bool = False) -> List[EvalResult]:
    """Run the full evaluation."""
    questions = GOLDEN_QUESTIONS[:num_questions]
    results = []
    
    console.print(Panel.fit(
        f"[bold cyan]RAG Evaluation Benchmark[/]\n"
        f"Running {len(questions)} golden questions\n"
        f"Judge: Gemini 2.0 Flash",
        border_style="cyan"
    ))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        for q in questions:
            task = progress.add_task(f"Q{q['id']}: {q['question'][:50]}...", total=None)
            
            if verbose:
                console.print(f"\n[bold]Question {q['id']}:[/] {q['question']}")
            
            result = await evaluate_question(q, verbose=verbose)
            results.append(result)
            
            progress.remove_task(task)
    
    return results


def print_results(results: List[EvalResult]):
    """Print evaluation results as a summary table."""
    console.print("\n")
    
    # Summary Table
    table = Table(title="📊 RAG Evaluation Results", show_lines=True)
    table.add_column("Q#", style="cyan", width=3)
    table.add_column("Category", style="dim", width=12)
    table.add_column("Context", justify="center", width=8)
    table.add_column("Syntax", justify="center", width=8)
    table.add_column("Quality", justify="center", width=8)
    table.add_column("Match%", justify="center", width=8)
    table.add_column("Time", justify="right", width=10)
    
    total_context = 0
    total_syntax = 0
    total_quality = 0
    total_match = 0
    
    for r in results:
        score_color = lambda s: "green" if s >= 4 else ("yellow" if s >= 3 else "red")
        
        table.add_row(
            str(r.question_id),
            r.category,
            f"[{score_color(r.judge_score.context_relevance)}]{r.judge_score.context_relevance}/5[/]",
            f"[{score_color(r.judge_score.syntax_validity)}]{r.judge_score.syntax_validity}/5[/]",
            f"[{score_color(r.judge_score.overall_quality)}]{r.judge_score.overall_quality}/5[/]",
            f"{r.context_match_ratio*100:.0f}%",
            f"{r.rag_result.query_time_ms + r.generation_result.generation_time_ms:.0f}ms"
        )
        
        total_context += r.judge_score.context_relevance
        total_syntax += r.judge_score.syntax_validity
        total_quality += r.judge_score.overall_quality
        total_match += r.context_match_ratio
    
    console.print(table)
    
    # Averages
    n = len(results)
    avg_context = total_context / n if n else 0
    avg_syntax = total_syntax / n if n else 0
    avg_quality = total_quality / n if n else 0
    avg_match = total_match / n if n else 0
    
    console.print(Panel.fit(
        f"[bold]Average Scores:[/]\n"
        f"  Context Relevance: {avg_context:.2f}/5\n"
        f"  Syntax Validity:   {avg_syntax:.2f}/5\n"
        f"  Overall Quality:   {avg_quality:.2f}/5\n"
        f"  Context Match:     {avg_match*100:.0f}%\n\n"
        f"[dim]RAG Intelligence Score: {((avg_context + avg_syntax + avg_quality) / 3):.2f}/5[/]",
        title="📈 Summary",
        border_style="green" if avg_quality >= 3.5 else "yellow"
    ))
    
    # Save results to JSON
    output_file = Path("tests/eval_results.json")
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "questions_evaluated": n,
        "averages": {
            "context_relevance": avg_context,
            "syntax_validity": avg_syntax,
            "overall_quality": avg_quality,
            "context_match": avg_match
        },
        "results": [
            {
                "question_id": r.question_id,
                "question": r.question,
                "category": r.category,
                "context_relevance": r.judge_score.context_relevance,
                "syntax_validity": r.judge_score.syntax_validity,
                "overall_quality": r.judge_score.overall_quality,
                "context_match": r.context_match_ratio,
                "reasoning": r.judge_score.reasoning,
                "model_used": r.generation_result.model_used,
                "chunks_retrieved": r.rag_result.total_chunks
            }
            for r in results
        ]
    }
    
    output_file.write_text(json.dumps(output_data, indent=2))
    console.print(f"\n[dim]Results saved to {output_file}[/]")


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Evaluate RAG pipeline quality")
    parser.add_argument("--questions", "-n", type=int, default=10, help="Number of questions to evaluate (1-10)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    args = parser.parse_args()
    
    num_q = min(max(args.questions, 1), len(GOLDEN_QUESTIONS))
    
    try:
        results = asyncio.run(run_evaluation(num_questions=num_q, verbose=args.verbose))
        print_results(results)
    except KeyboardInterrupt:
        console.print("\n[yellow]Evaluation interrupted[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Evaluation failed: {e}[/]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

