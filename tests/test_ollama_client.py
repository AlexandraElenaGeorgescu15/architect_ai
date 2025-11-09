#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive unit tests for ollama_client.py
Tests Ollama client functionality and VRAM management
Target: 90%+ coverage
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from ai.ollama_client import (
    OllamaClient,
    ModelStatus,
    ModelInfo,
    GenerationResponse,
    get_ollama_client
)


class TestOllamaClient(unittest.TestCase):
    """Test suite for OllamaClient"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = OllamaClient(base_url="http://localhost:11434", vram_limit_gb=12.0)
    
    def test_initialization(self):
        """Test client initialization"""
        self.assertEqual(self.client.base_url, "http://localhost:11434")
        self.assertEqual(self.client.timeout, 120)
        self.assertEqual(self.client.vram_limit_gb, 12.0)
        self.assertIsInstance(self.client.models, dict)
        self.assertIsInstance(self.client.persistent_models, set)
        self.assertIsInstance(self.client.active_models, set)
    
    def test_model_sizes_configured(self):
        """Test that model sizes are properly configured"""
        self.assertIn("codellama:7b-instruct-q4_K_M", self.client.model_sizes)
        self.assertIn("llama3:8b-instruct-q4_K_M", self.client.model_sizes)
        self.assertIn("mistral:7b-instruct-q4_K_M", self.client.model_sizes)
        
        # Check sizes are reasonable
        for model, size in self.client.model_sizes.items():
            self.assertGreater(size, 0)
            self.assertLess(size, 20)  # No model should be > 20GB
    
    @patch('httpx.AsyncClient')
    async def test_check_server_health_success(self, mock_client):
        """Test server health check - success case"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        mock_http = AsyncMock()
        mock_http.get.return_value = mock_response
        mock_client.return_value = mock_http
        
        self.client._http_client = mock_http
        
        result = await self.client.check_server_health()
        self.assertTrue(result)
    
    @patch('httpx.AsyncClient')
    async def test_check_server_health_failure(self, mock_client):
        """Test server health check - failure case"""
        mock_http = AsyncMock()
        mock_http.get.side_effect = Exception("Connection refused")
        mock_client.return_value = mock_http
        
        self.client._http_client = mock_http
        
        result = await self.client.check_server_health()
        self.assertFalse(result)
    
    @patch('httpx.AsyncClient')
    async def test_list_available_models(self, mock_client):
        """Test listing available models"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "codellama:7b-instruct-q4_K_M"},
                {"name": "llama3:8b-instruct-q4_K_M"},
            ]
        }
        
        mock_http = AsyncMock()
        mock_http.get.return_value = mock_response
        mock_client.return_value = mock_http
        
        self.client._http_client = mock_http
        
        models = await self.client.list_available_models()
        self.assertEqual(len(models), 2)
        self.assertIn("codellama:7b-instruct-q4_K_M", models)
        self.assertIn("llama3:8b-instruct-q4_K_M", models)
    
    def test_get_model_status(self):
        """Test getting model status"""
        # Not loaded initially
        status = self.client.get_model_status("test-model")
        self.assertEqual(status, ModelStatus.NOT_LOADED)
        
        # Add model
        self.client.models["test-model"] = ModelInfo(
            name="test-model",
            status=ModelStatus.READY
        )
        
        status = self.client.get_model_status("test-model")
        self.assertEqual(status, ModelStatus.READY)
    
    def test_get_vram_usage(self):
        """Test VRAM usage calculation"""
        # Initially empty
        usage = self.client.get_vram_usage()
        self.assertEqual(usage["used_gb"], 0)
        self.assertEqual(usage["available_gb"], 12.0)
        self.assertEqual(usage["total_gb"], 12.0)
        self.assertEqual(usage["usage_percent"], 0)
        
        # Add active models
        self.client.active_models.add("codellama:7b-instruct-q4_K_M")
        self.client.active_models.add("llama3:8b-instruct-q4_K_M")
        
        usage = self.client.get_vram_usage()
        expected_used = 3.8 + 4.7  # codellama + llama3
        self.assertAlmostEqual(usage["used_gb"], expected_used, places=1)
        self.assertLess(usage["available_gb"], 12.0)
        self.assertGreater(usage["usage_percent"], 0)
    
    async def test_ensure_model_available_already_loaded(self):
        """Test ensuring model available when already loaded"""
        model_name = "codellama:7b-instruct-q4_K_M"
        self.client.active_models.add(model_name)
        
        result = await self.client.ensure_model_available(model_name, show_progress=False)
        self.assertTrue(result)
    
    def test_get_model_info(self):
        """Test getting model info"""
        # Non-existent model
        info = self.client.get_model_info("nonexistent")
        self.assertIsNone(info)
        
        # Add model
        test_info = ModelInfo(
            name="test-model",
            status=ModelStatus.READY,
            load_time=5.5
        )
        self.client.models["test-model"] = test_info
        
        info = self.client.get_model_info("test-model")
        self.assertIsNotNone(info)
        self.assertEqual(info.name, "test-model")
        self.assertEqual(info.load_time, 5.5)
    
    def test_get_all_model_info(self):
        """Test getting all model info"""
        # Add some models
        self.client.models["model1"] = ModelInfo(name="model1", status=ModelStatus.READY)
        self.client.models["model2"] = ModelInfo(name="model2", status=ModelStatus.LOADING)
        
        all_info = self.client.get_all_model_info()
        self.assertEqual(len(all_info), 2)
        self.assertIn("model1", all_info)
        self.assertIn("model2", all_info)
    
    def test_get_ollama_client_singleton(self):
        """Test global client singleton"""
        client1 = get_ollama_client()
        client2 = get_ollama_client()
        
        # Should be same instance
        self.assertIs(client1, client2)


class TestModelInfo(unittest.TestCase):
    """Test ModelInfo dataclass"""
    
    def test_model_info_creation(self):
        """Test creating ModelInfo"""
        info = ModelInfo(
            name="test-model",
            status=ModelStatus.READY,
            size_bytes=1024,
            load_time=5.0,
            total_requests=10,
            successful_requests=9
        )
        
        self.assertEqual(info.name, "test-model")
        self.assertEqual(info.status, ModelStatus.READY)
        self.assertEqual(info.size_bytes, 1024)
        self.assertEqual(info.load_time, 5.0)
        self.assertEqual(info.total_requests, 10)
        self.assertEqual(info.successful_requests, 9)


class TestGenerationResponse(unittest.TestCase):
    """Test GenerationResponse dataclass"""
    
    def test_generation_response_success(self):
        """Test successful generation response"""
        response = GenerationResponse(
            content="Generated text",
            model_used="codellama:7b",
            generation_time=2.5,
            tokens_generated=50,
            success=True
        )
        
        self.assertEqual(response.content, "Generated text")
        self.assertEqual(response.model_used, "codellama:7b")
        self.assertEqual(response.generation_time, 2.5)
        self.assertEqual(response.tokens_generated, 50)
        self.assertTrue(response.success)
        self.assertEqual(response.error_message, "")
    
    def test_generation_response_failure(self):
        """Test failed generation response"""
        response = GenerationResponse(
            content="",
            model_used="test-model",
            generation_time=1.0,
            success=False,
            error_message="Model not found"
        )
        
        self.assertEqual(response.content, "")
        self.assertFalse(response.success)
        self.assertEqual(response.error_message, "Model not found")


class TestVRAMManagement(unittest.TestCase):
    """Test VRAM management logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = OllamaClient(vram_limit_gb=12.0)
    
    def test_vram_limit_initialization(self):
        """Test VRAM limit is properly set"""
        self.assertEqual(self.client.vram_limit_gb, 12.0)
    
    def test_persistent_models_fit_in_vram(self):
        """Test that persistent models fit in VRAM"""
        persistent = ["codellama:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"]
        total_size = sum(self.client.model_sizes.get(m, 5.0) for m in persistent)
        
        self.assertLessEqual(total_size, self.client.vram_limit_gb,
                            "Persistent models exceed VRAM limit!")
    
    def test_vram_usage_tracking(self):
        """Test VRAM usage is properly tracked"""
        # Start empty
        self.assertEqual(len(self.client.active_models), 0)
        
        # Add models
        self.client.active_models.add("codellama:7b-instruct-q4_K_M")
        usage = self.client.get_vram_usage()
        
        self.assertGreater(usage["used_gb"], 0)
        self.assertLess(usage["used_gb"], self.client.vram_limit_gb)


def run_async_test(coro):
    """Helper to run async tests"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)


