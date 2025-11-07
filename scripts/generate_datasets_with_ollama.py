"""
Generate Finetuning Datasets USING OLLAMA (local models)

- Generates N examples for a chosen artifact type (or all)
- Uses the ModelRouter + ArtifactModelMapper to pick the right local model
- Saves JSONL to finetune_datasets/

Usage examples:
  python scripts/generate_datasets_with_ollama.py --artifact mermaid --count 1000
  python scripts/generate_datasets_with_ollama.py --artifact code --count 1500 --concurrency 2
  python scripts/generate_datasets_with_ollama.py --all --count 1000
"""

import asyncio
import json
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse
import time

from config.artifact_model_mapping import get_artifact_mapper, ArtifactType
from ai.ollama_client import OllamaClient
from ai.model_router import get_router


SEED_PROMPTS: Dict[str, List[str]] = {
    "mermaid": [
        "Generate a Mermaid ERD for an e-commerce system with users, products, orders, and order_items.",
        "Create a system architecture diagram (graph TD) with API Gateway, Auth, User, and DB.",
        "Produce a flowchart for user registration: fill form -> validate -> create account -> send email.",
    ],
    "html": [
        "Create a responsive HTML login page with email, password, remember me, and a submit button.",
        "Build a modern landing section with a hero, CTA button, and features grid.",
    ],
    "code": [
        "Write a FastAPI endpoint for user registration with email validation and password hashing.",
        "Implement a Node/Express route to create an order and validate stock.",
    ],
    "documentation": [
        "Write API documentation in Markdown for POST /api/users/register.",
        "Document GET /api/orders with parameters, responses, and examples.",
    ],
    "jira": [
        "Create JIRA tasks to implement authentication (login, logout, password reset) with acceptance criteria.",
        "Draft JIRA stories for implementing order processing with inventory checks.",
    ],
    "workflows": [
        "Create a workflow for order processing: receive -> pay -> reserve inventory -> ship -> notify.",
        "Design a CI/CD workflow for building, testing, and deploying a web app.",
    ],
}


def artifact_to_task_type(artifact: str) -> str:
    mapper = get_artifact_mapper()
    return mapper.get_task_type(artifact)


def build_system_message(artifact: str) -> Optional[str]:
    if artifact in {ArtifactType.ERD.value, ArtifactType.ARCHITECTURE.value}:
        return "Output ONLY the diagram. Start with 'erDiagram' for ERD or 'graph TD' for architecture."
    if artifact == ArtifactType.API_DOCS.value:
        return "Generate comprehensive API documentation in Markdown."
    if artifact == ArtifactType.JIRA.value:
        return "Generate JIRA tasks in Markdown with acceptance criteria (Given/When/Then)."
    if artifact == ArtifactType.WORKFLOWS.value:
        return "Generate workflows in Markdown with clear steps and triggers."
    return None


def vary_prompt(base: str) -> str:
    variants = [
        base + " Use modern best practices.",
        base + " Include edge cases.",
        base.replace("Generate", "Create"),
        base.replace("Create", "Design"),
        base,
    ]
    return random.choice(variants)


def dedupe(texts: List[str]) -> List[str]:
    seen = set()
    out = []
    for t in texts:
        key = t.strip()
        if len(key) < 8:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


async def generate_one(router, task_type: str, prompt: str, system_message: Optional[str]) -> Optional[str]:
    try:
        resp = await router.generate(
            task_type=task_type,
            prompt=prompt,
            system_message=system_message,
            temperature=0.2,
            force_cloud=False,
        )
        if resp.success and resp.content and len(resp.content.strip()) > 0:
            return resp.content.strip()
        return None
    except Exception:
        return None


async def run_synthesis(artifact: str, count: int, concurrency: int, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize Ollama + router
    ollama = OllamaClient()
    assert await ollama.check_server_health(), "Ollama server is not running. Start with 'ollama serve'."
    router = get_router({}, ollama)
    router.set_force_local_only(True)  # ensure local-only for dataset gen

    task_type = artifact_to_task_type(artifact)
    seeds = SEED_PROMPTS.get(task_type, [f"Generate {artifact} example."])
    system_message = build_system_message(artifact)

    results: List[Dict[str, Any]] = []
    pending = 0

    async def worker_loop(queue: asyncio.Queue):
        nonlocal pending
        while True:
            item = await queue.get()
            if item is None:
                queue.task_done()
                return
            prompt = vary_prompt(item)
            content = await generate_one(router, task_type, prompt, system_message)
            if content:
                results.append({
                    "prompt": prompt,
                    "completion": content,
                    "metadata": {"artifact": artifact, "model": router.get_local_model_for_task(task_type)}
                })
            queue.task_done()
            pending -= 1

    queue: asyncio.Queue = asyncio.Queue()

    # Enqueue initial seeds and loop until count reached
    for _ in range(max(count // 10, 10)):
        for s in seeds:
            await queue.put(s)
            pending += 1

    workers = [asyncio.create_task(worker_loop(queue)) for _ in range(max(1, concurrency))]

    # Refill loop
    while len(results) < count:
        # Top-up queue if running low
        if pending < concurrency * 2:
            for _ in range(concurrency * 3):
                await queue.put(random.choice(seeds))
                pending += 1
        await asyncio.sleep(0.2)

    # Stop workers
    for _ in workers:
        await queue.put(None)
    await queue.join()
    for w in workers:
        w.cancel()

    # Deduplicate completions (basic)
    unique_results = []
    seen_completions = set()
    for r in results:
        c = r["completion"].strip()
        if c in seen_completions:
            continue
        seen_completions.add(c)
        unique_results.append(r)
        if len(unique_results) >= count:
            break

    with out_path.open('w', encoding='utf-8') as f:
        for r in unique_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"✅ Saved {len(unique_results)} examples to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate finetuning datasets using Ollama")
    parser.add_argument("--artifact", type=str, help="Artifact type (erd, architecture, data_flow, user_flow, components_diagram, api_sequence, code_prototype, visual_prototype_dev, api_docs, documentation, jira, workflows)")
    parser.add_argument("--all", action="store_true", help="Generate for all artifact types")
    parser.add_argument("--count", type=int, default=1000, help="Examples per artifact")
    parser.add_argument("--concurrency", type=int, default=2, help="Concurrent workers")
    parser.add_argument("--output", type=str, default="finetune_datasets", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.output)

    artifacts: List[str]
    if args.all:
        artifacts = [a.value for a in ArtifactType]
    else:
        if not args.artifact:
            parser.error("--artifact required unless --all is set")
        artifacts = [args.artifact]

    # Filter out non-training types if needed
    skip = {ArtifactType.ALL_DIAGRAMS.value}
    artifacts = [a for a in artifacts if a not in skip]

    start = time.time()
    for art in artifacts:
        out_path = out_dir / f"{art}_ollama_{args.count}.jsonl"
        asyncio.run(run_synthesis(art, args.count, args.concurrency, out_path))
    print(f"Done in {time.time()-start:.1f}s")


if __name__ == "__main__":
    main()
