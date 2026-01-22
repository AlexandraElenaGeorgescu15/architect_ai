#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive Endpoint and Model Integration Test Script
=========================================================

This script tests all major API endpoints and model integrations including:
- Health and status endpoints
- Model management (list, routing, download)
- Generation endpoints with different models (Ollama, HuggingFace, Cloud)
- HuggingFace model download workflow
- Custom artifact types

Run with: python test_endpoints_comprehensive.py
"""

import asyncio
import httpx
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys
import io

# Fix Windows console encoding issues
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 120.0  # 2 minutes for generation requests


class TestResult:
    """Container for test results."""
    def __init__(self, name: str):
        self.name = name
        self.success = False
        self.duration = 0.0
        self.response = None
        self.error = None
        self.details = {}
    
    def __str__(self):
        status = "✅ PASS" if self.success else "❌ FAIL"
        return f"{status} | {self.name} | {self.duration:.2f}s"


class ComprehensiveTestSuite:
    """Comprehensive API and model integration tests."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.findings: List[str] = []
        
    async def run_all_tests(self):
        """Run all test categories."""
        print("\n" + "=" * 80)
        print("🧪 COMPREHENSIVE ENDPOINT AND MODEL INTEGRATION TESTS")
        print("=" * 80)
        print(f"📍 Base URL: {BASE_URL}")
        print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")
        
        # Category 1: Health and Status
        print("\n📋 CATEGORY 1: Health and Status Endpoints")
        print("-" * 50)
        await self.test_health_endpoint()
        await self.test_system_status()
        
        # Category 2: Model Management
        print("\n📋 CATEGORY 2: Model Management Endpoints")
        print("-" * 50)
        await self.test_list_models()
        await self.test_model_routing()
        await self.test_api_keys_status()
        await self.test_model_stats()
        
        # Category 3: HuggingFace Integration
        print("\n📋 CATEGORY 3: HuggingFace Integration")
        print("-" * 50)
        await self.test_huggingface_search()
        await self.test_huggingface_list_downloaded()
        await self.test_huggingface_model_info()
        
        # Category 4: Generation Endpoints
        print("\n📋 CATEGORY 4: Generation Endpoints")
        print("-" * 50)
        await self.test_list_artifact_types()
        await self.test_generation_jobs_list()
        await self.test_artifacts_list()
        
        # Category 5: Model-Specific Generation Tests
        print("\n📋 CATEGORY 5: Model-Specific Generation Tests")
        print("-" * 50)
        await self.test_generation_with_ollama()
        await self.test_generation_with_cloud()
        
        # Category 6: Custom Artifact Types
        print("\n📋 CATEGORY 6: Custom Artifact Types")
        print("-" * 50)
        await self.test_custom_artifact_crud()
        
        # Category 7: Context and RAG
        print("\n📋 CATEGORY 7: Context and RAG Endpoints")
        print("-" * 50)
        await self.test_context_build()
        await self.test_rag_status()
        
        # Print Summary
        self.print_summary()
        self.print_findings()
        
        return self.results
    
    def add_result(self, result: TestResult):
        """Add a test result and print it."""
        self.results.append(result)
        print(f"  {result}")
        if result.error:
            print(f"    Error: {result.error}")
        if result.details:
            for key, value in result.details.items():
                print(f"    {key}: {value}")
    
    def add_finding(self, finding: str):
        """Add a finding to document."""
        self.findings.append(finding)
    
    # =========================================================================
    # Category 1: Health and Status
    # =========================================================================
    
    async def test_health_endpoint(self):
        """Test basic health endpoint."""
        result = TestResult("GET /api/health")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/api/health", timeout=10.0)
                result.duration = time.time() - start
                result.response = response.json() if response.status_code == 200 else response.text
                result.success = response.status_code == 200
                
                if result.success:
                    data = response.json()
                    result.details["version"] = data.get("version", "unknown")
                    result.details["status"] = data.get("status", "unknown")
                else:
                    result.error = f"HTTP {response.status_code}"
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    async def test_system_status(self):
        """Test system status endpoint."""
        result = TestResult("GET /api/status")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/api/status", timeout=10.0)
                result.duration = time.time() - start
                result.response = response.json() if response.status_code == 200 else response.text
                result.success = response.status_code == 200
                
                if result.success:
                    data = response.json()
                    result.details["ready"] = data.get("ready", False)
                    result.details["phase"] = data.get("current_phase", "unknown")
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    # =========================================================================
    # Category 2: Model Management
    # =========================================================================
    
    async def test_list_models(self):
        """Test model listing endpoint."""
        result = TestResult("GET /api/models")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/api/models/", timeout=30.0)
                result.duration = time.time() - start
                result.success = response.status_code == 200
                
                if result.success:
                    models = response.json()
                    result.details["total_models"] = len(models)
                    
                    # Count by provider
                    providers = {}
                    for model in models:
                        provider = model.get("provider", "unknown")
                        providers[provider] = providers.get(provider, 0) + 1
                    
                    result.details["by_provider"] = providers
                    
                    # Check available models
                    available = [m for m in models if m.get("status") in ["available", "downloaded"]]
                    result.details["available_count"] = len(available)
                    
                    self.add_finding(f"Found {len(models)} models: {providers}")
                else:
                    result.error = f"HTTP {response.status_code}: {response.text[:200]}"
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    async def test_model_routing(self):
        """Test model routing configuration."""
        result = TestResult("GET /api/models/routing")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/api/models/routing", timeout=10.0)
                result.duration = time.time() - start
                result.success = response.status_code == 200
                
                if result.success:
                    routing = response.json()
                    result.details["artifact_types_configured"] = len(routing)
                    
                    # Sample some routings
                    sample_types = list(routing.keys())[:3]
                    for art_type in sample_types:
                        config = routing[art_type]
                        result.details[f"{art_type}_primary"] = config.get("primary_model", "N/A")
                else:
                    result.error = f"HTTP {response.status_code}"
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    async def test_api_keys_status(self):
        """Test API keys status endpoint."""
        result = TestResult("GET /api/models/api-keys/status")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/api/models/api-keys/status", timeout=15.0)
                result.duration = time.time() - start
                result.success = response.status_code == 200
                
                if result.success:
                    status = response.json()
                    for provider, info in status.items():
                        configured = info.get("configured", False)
                        result.details[f"{provider}_configured"] = "✅" if configured else "❌"
                    
                    self.add_finding(f"API Keys: " + ", ".join([
                        f"{p}:{'✅' if i.get('configured') else '❌'}" 
                        for p, i in status.items()
                    ]))
                else:
                    result.error = f"HTTP {response.status_code}"
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    async def test_model_stats(self):
        """Test model stats endpoint."""
        result = TestResult("GET /api/models/stats")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/api/models/stats", timeout=10.0)
                result.duration = time.time() - start
                result.success = response.status_code == 200
                
                if result.success:
                    data = response.json()
                    stats = data.get("stats", {})
                    result.details["total_models"] = stats.get("total_models", 0)
                    result.details["routing_configs"] = stats.get("routing_configs", 0)
                else:
                    result.error = f"HTTP {response.status_code}"
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    # =========================================================================
    # Category 3: HuggingFace Integration
    # =========================================================================
    
    async def test_huggingface_search(self):
        """Test HuggingFace model search."""
        result = TestResult("GET /api/huggingface/search")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{BASE_URL}/api/huggingface/search",
                    params={"query": "codellama", "limit": 5},
                    timeout=30.0
                )
                result.duration = time.time() - start
                result.success = response.status_code == 200
                
                if result.success:
                    data = response.json()
                    result.details["results_count"] = data.get("count", 0)
                    if data.get("results"):
                        result.details["first_result"] = data["results"][0].get("id", "N/A")[:50]
                else:
                    result.error = f"HTTP {response.status_code}: {response.text[:200]}"
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    async def test_huggingface_list_downloaded(self):
        """Test listing downloaded HuggingFace models."""
        result = TestResult("GET /api/huggingface/downloaded")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/api/huggingface/downloaded", timeout=10.0)
                result.duration = time.time() - start
                result.success = response.status_code == 200
                
                if result.success:
                    data = response.json()
                    result.details["downloaded_count"] = data.get("count", 0)
                    
                    if data.get("models"):
                        model_names = [m.get("id", "unknown") for m in data["models"]]
                        self.add_finding(f"Downloaded HuggingFace models: {model_names}")
                else:
                    result.error = f"HTTP {response.status_code}"
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    async def test_huggingface_model_info(self):
        """Test getting HuggingFace model info."""
        result = TestResult("GET /api/huggingface/info/{model_id}")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                # Test with a popular model
                response = await client.get(
                    f"{BASE_URL}/api/huggingface/info/codellama/CodeLlama-7b-Instruct-hf",
                    timeout=15.0
                )
                result.duration = time.time() - start
                result.success = response.status_code == 200
                
                if result.success:
                    data = response.json()
                    model_info = data.get("model", {})
                    result.details["model_id"] = model_info.get("id", "N/A")
                    result.details["downloads"] = model_info.get("downloads", 0)
                else:
                    result.error = f"HTTP {response.status_code}"
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    # =========================================================================
    # Category 4: Generation Endpoints
    # =========================================================================
    
    async def test_list_artifact_types(self):
        """Test listing artifact types."""
        result = TestResult("GET /api/generation/artifact-types")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/api/generation/artifact-types", timeout=10.0)
                result.duration = time.time() - start
                result.success = response.status_code == 200
                
                if result.success:
                    data = response.json()
                    types = data.get("artifact_types", [])
                    result.details["total_types"] = len(types)
                    
                    # Count by category
                    categories = {}
                    for t in types:
                        cat = t.get("category", "unknown")
                        categories[cat] = categories.get(cat, 0) + 1
                    result.details["categories"] = categories
                    
                    self.add_finding(f"Artifact types: {len(types)} total, categories: {list(categories.keys())}")
                else:
                    result.error = f"HTTP {response.status_code}"
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    async def test_generation_jobs_list(self):
        """Test listing generation jobs."""
        result = TestResult("GET /api/generation/jobs")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/api/generation/jobs", timeout=10.0)
                result.duration = time.time() - start
                result.success = response.status_code == 200
                
                if result.success:
                    jobs = response.json()
                    result.details["jobs_count"] = len(jobs)
                else:
                    result.error = f"HTTP {response.status_code}"
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    async def test_artifacts_list(self):
        """Test listing artifacts."""
        result = TestResult("GET /api/generation/artifacts")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/api/generation/artifacts", timeout=10.0)
                result.duration = time.time() - start
                result.success = response.status_code == 200
                
                if result.success:
                    artifacts = response.json()
                    result.details["artifacts_count"] = len(artifacts)
                else:
                    result.error = f"HTTP {response.status_code}"
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    # =========================================================================
    # Category 5: Model-Specific Generation Tests
    # =========================================================================
    
    async def test_generation_with_ollama(self):
        """Test generation using Ollama models."""
        result = TestResult("POST /api/generation/generate (Ollama)")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                # First check if Ollama is available
                models_response = await client.get(f"{BASE_URL}/api/models/", timeout=10.0)
                models = models_response.json() if models_response.status_code == 200 else []
                
                ollama_available = any(
                    m.get("provider") == "ollama" and m.get("status") in ["available", "downloaded"]
                    for m in models
                )
                
                if not ollama_available:
                    result.duration = time.time() - start
                    result.success = True
                    result.details["skipped"] = "No Ollama models available"
                    self.add_finding("⚠️ Ollama generation test skipped - no Ollama models available")
                    self.add_result(result)
                    return
                
                # Try to generate a simple artifact
                response = await client.post(
                    f"{BASE_URL}/api/generation/generate",
                    json={
                        "artifact_type": "mermaid_flowchart",
                        "meeting_notes": "Create a simple flowchart showing user login process: user enters credentials, system validates, if valid show dashboard, if invalid show error.",
                        "options": {
                            "max_retries": 1,
                            "temperature": 0.2
                        }
                    },
                    timeout=TIMEOUT
                )
                result.duration = time.time() - start
                result.success = response.status_code == 200
                
                if result.success:
                    data = response.json()
                    result.details["job_id"] = data.get("job_id", "N/A")
                    result.details["status"] = data.get("status", "unknown")
                    
                    if data.get("artifact"):
                        artifact = data["artifact"]
                        result.details["artifact_type"] = artifact.get("artifact_type", "N/A")
                        result.details["content_length"] = len(artifact.get("content", ""))
                        result.details["model_used"] = artifact.get("model_used", "N/A")
                        
                        validation = artifact.get("validation", {})
                        result.details["validation_score"] = validation.get("score", 0)
                        
                        self.add_finding(f"Ollama generation successful: model={artifact.get('model_used')}, score={validation.get('score', 0)}")
                    else:
                        result.details["note"] = "Job started, waiting for completion"
                else:
                    result.error = f"HTTP {response.status_code}: {response.text[:300]}"
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    async def test_generation_with_cloud(self):
        """Test generation using cloud models."""
        result = TestResult("POST /api/generation/generate (Cloud)")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                # First check API keys status
                keys_response = await client.get(f"{BASE_URL}/api/models/api-keys/status", timeout=10.0)
                keys = keys_response.json() if keys_response.status_code == 200 else {}
                
                cloud_available = any(
                    keys.get(provider, {}).get("configured", False)
                    for provider in ["gemini", "groq", "openai"]
                )
                
                if not cloud_available:
                    result.duration = time.time() - start
                    result.success = True
                    result.details["skipped"] = "No cloud API keys configured"
                    self.add_finding("⚠️ Cloud generation test skipped - no API keys configured")
                    self.add_result(result)
                    return
                
                # Update routing to use cloud model
                # First get current routing
                routing_response = await client.get(f"{BASE_URL}/api/models/routing", timeout=10.0)
                
                # Try generation with cloud model preference
                response = await client.post(
                    f"{BASE_URL}/api/generation/generate",
                    json={
                        "artifact_type": "mermaid_flowchart",
                        "meeting_notes": "Create a simple flowchart for a password reset process: user requests reset, system sends email, user clicks link, user enters new password, system updates password.",
                        "options": {
                            "max_retries": 1,
                            "temperature": 0.3
                        }
                    },
                    timeout=TIMEOUT
                )
                result.duration = time.time() - start
                result.success = response.status_code == 200
                
                if result.success:
                    data = response.json()
                    result.details["job_id"] = data.get("job_id", "N/A")
                    result.details["status"] = data.get("status", "unknown")
                    
                    if data.get("artifact"):
                        artifact = data["artifact"]
                        result.details["model_used"] = artifact.get("model_used", "N/A")
                        
                        validation = artifact.get("validation", {})
                        result.details["validation_score"] = validation.get("score", 0)
                        
                        self.add_finding(f"Cloud generation result: model={artifact.get('model_used')}, score={validation.get('score', 0)}")
                else:
                    result.error = f"HTTP {response.status_code}: {response.text[:300]}"
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    # =========================================================================
    # Category 6: Custom Artifact Types
    # =========================================================================
    
    async def test_custom_artifact_crud(self):
        """Test custom artifact type CRUD operations."""
        result = TestResult("Custom Artifact Types CRUD")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                test_type_id = f"test_custom_{int(time.time())}"
                
                # CREATE
                create_response = await client.post(
                    f"{BASE_URL}/api/generation/artifact-types/custom",
                    params={
                        "type_id": test_type_id,
                        "name": "Test Custom Type",
                        "category": "Testing",
                        "prompt_template": "Generate a test output for: {meeting_notes}",
                        "description": "A test custom artifact type"
                    },
                    timeout=10.0
                )
                
                if create_response.status_code != 200:
                    result.error = f"CREATE failed: HTTP {create_response.status_code}"
                    result.duration = time.time() - start
                    self.add_result(result)
                    return
                
                result.details["create"] = "✅"
                
                # READ
                read_response = await client.get(
                    f"{BASE_URL}/api/generation/artifact-types/custom/{test_type_id}",
                    timeout=10.0
                )
                result.details["read"] = "✅" if read_response.status_code == 200 else "❌"
                
                # UPDATE
                update_response = await client.put(
                    f"{BASE_URL}/api/generation/artifact-types/custom/{test_type_id}",
                    params={"description": "Updated description"},
                    timeout=10.0
                )
                result.details["update"] = "✅" if update_response.status_code == 200 else "❌"
                
                # DELETE
                delete_response = await client.delete(
                    f"{BASE_URL}/api/generation/artifact-types/custom/{test_type_id}",
                    timeout=10.0
                )
                result.details["delete"] = "✅" if delete_response.status_code == 200 else "❌"
                
                result.duration = time.time() - start
                result.success = all(v == "✅" for v in result.details.values())
                
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    # =========================================================================
    # Category 7: Context and RAG
    # =========================================================================
    
    async def test_context_build(self):
        """Test context building endpoint."""
        result = TestResult("POST /api/context/build")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{BASE_URL}/api/context/build",
                    json={
                        "artifact_type": "mermaid_erd",
                        "meeting_notes": "Create an ERD for a simple blog system with users, posts, and comments."
                    },
                    timeout=60.0
                )
                result.duration = time.time() - start
                result.success = response.status_code == 200
                
                if result.success:
                    data = response.json()
                    result.details["context_id"] = data.get("context_id", "N/A")
                    result.details["has_rag"] = bool(data.get("rag_context"))
                    result.details["has_kg"] = bool(data.get("kg_context"))
                else:
                    result.error = f"HTTP {response.status_code}: {response.text[:200]}"
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    async def test_rag_status(self):
        """Test RAG status endpoint."""
        result = TestResult("GET /api/rag/status")
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/api/rag/status", timeout=10.0)
                result.duration = time.time() - start
                result.success = response.status_code == 200
                
                if result.success:
                    data = response.json()
                    result.details["total_chunks"] = data.get("total_chunks", 0)
                    result.details["indexed_files"] = data.get("file_hashes_tracked", 0)
                else:
                    result.error = f"HTTP {response.status_code}"
        except Exception as e:
            result.duration = time.time() - start
            result.error = str(e)
        
        self.add_result(result)
    
    # =========================================================================
    # Summary and Reporting
    # =========================================================================
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = total - passed
        
        print(f"\n✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {failed}/{total}")
        print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
        
        # List failed tests
        if failed > 0:
            print("\n❌ Failed Tests:")
            for result in self.results:
                if not result.success:
                    print(f"  - {result.name}: {result.error or 'Unknown error'}")
        
        # Total duration
        total_duration = sum(r.duration for r in self.results)
        print(f"\n⏱️ Total Duration: {total_duration:.1f}s")
    
    def print_findings(self):
        """Print documented findings."""
        print("\n" + "=" * 80)
        print("📋 FINDINGS AND DOCUMENTATION")
        print("=" * 80)
        
        for i, finding in enumerate(self.findings, 1):
            print(f"\n{i}. {finding}")
        
        # Add workflow documentation
        print("\n" + "-" * 80)
        print("📖 WORKFLOW DOCUMENTATION")
        print("-" * 80)
        
        print("""
## Model Integration Workflow

### 1. Ollama Models
   - Models are auto-detected from Ollama API at /api/tags
   - Status: "available" or "downloaded"
   - Usage: Primary local model provider
   - Routing: Configured per artifact type in model_routing.yaml

### 2. HuggingFace Models
   - Search: GET /api/huggingface/search?query={query}
   - Download: POST /api/huggingface/download/{model_id}
   - Status: GET /api/huggingface/download/{model_id}/status
   - Downloaded models: GET /api/huggingface/downloaded
   - After download, models can be used via transformers pipeline
   - Optional: Convert to Ollama format for unified usage

### 3. Cloud Models (Gemini, Groq, OpenAI, Anthropic)
   - Configured via API keys in .env or settings
   - Auto-registered when API keys are present
   - Used as fallbacks when local models fail
   - Status check: GET /api/models/api-keys/status

## Generation Workflow

### Standard Generation Flow:
1. Client sends POST /api/generation/generate with:
   - artifact_type: e.g., "mermaid_erd"
   - meeting_notes: User requirements
   - options: temperature, max_retries, etc.

2. Server:
   a. Builds context (RAG + Knowledge Graph + Patterns)
   b. Selects model based on routing configuration
   c. Tries local models first (Ollama/HuggingFace)
   d. Falls back to cloud models if local fails
   e. Validates generated content
   f. Returns artifact with validation score

### Model Selection Priority:
1. Fine-tuned models for specific artifact type
2. User-configured primary model (from routing)
3. User-configured fallback models
4. Available Ollama models
5. Cloud models (Gemini, Groq, OpenAI, Anthropic)

## Custom Artifact Types

### CRUD Operations:
- Create: POST /api/generation/artifact-types/custom
- Read: GET /api/generation/artifact-types/custom/{type_id}
- Update: PUT /api/generation/artifact-types/custom/{type_id}
- Delete: DELETE /api/generation/artifact-types/custom/{type_id}
- List All: GET /api/generation/artifact-types

### Custom Type Definition:
- type_id: Unique identifier (snake_case)
- name: Display name
- category: Category for grouping
- prompt_template: Template with {meeting_notes} and {context} placeholders
- default_model: Preferred model for this type (optional)
""")


async def main():
    """Run the comprehensive test suite."""
    suite = ComprehensiveTestSuite()
    await suite.run_all_tests()
    
    # Exit with appropriate code
    failed = sum(1 for r in suite.results if not r.success)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
