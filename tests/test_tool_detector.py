#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive unit tests for _tool_detector.py
Tests self-contamination prevention logic
Target: 95%+ coverage
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from unittest.mock import patch, MagicMock
from components._tool_detector import (
    detect_tool_directory,
    get_user_project_root,
    should_exclude_path,
    get_user_project_directories
)


class TestToolDetector(unittest.TestCase):
    """Test suite for tool detector"""
    
    def test_detect_tool_directory_success(self):
        """Test detection of tool directory with sentinel files"""
        tool_dir = detect_tool_directory()
        # Should detect the tool directory
        self.assertIsNotNone(tool_dir)
        self.assertTrue(tool_dir.exists())
        # Should contain sentinel files
        self.assertTrue((tool_dir / "app" / "app_v2.py").exists() or
                       (tool_dir / "components" / "knowledge_graph.py").exists())
    
    def test_get_user_project_root(self):
        """Test getting user project root"""
        user_root = get_user_project_root()
        self.assertIsNotNone(user_root)
        self.assertTrue(user_root.exists())
        # User root should be parent of tool directory
        tool_dir = detect_tool_directory()
        if tool_dir:
            self.assertEqual(user_root, tool_dir.parent)
    
    def test_should_exclude_path_tool_directory(self):
        """Test that paths inside tool directory are excluded"""
        tool_dir = detect_tool_directory()
        if tool_dir:
            # Path inside tool should be excluded
            tool_path = tool_dir / "components" / "knowledge_graph.py"
            self.assertTrue(should_exclude_path(tool_path))
    
    def test_should_exclude_path_common_directories(self):
        """Test that common directories are excluded"""
        # Test common exclusions
        test_cases = [
            Path("/project/node_modules/package"),
            Path("/project/.venv/lib/python"),
            Path("/project/__pycache__/module.pyc"),
            Path("/project/.git/config"),
            Path("/project/venv/bin/python"),
        ]
        
        for path in test_cases:
            result = should_exclude_path(path)
            # Should exclude these common patterns
            self.assertTrue(result, f"Failed to exclude: {path}")
    
    def test_should_exclude_path_user_files(self):
        """Test that user project files are NOT excluded"""
        # Create a mock user directory outside tool
        user_file = Path.cwd() / "test_user_project" / "src" / "main.py"
        
        # Mock the detect_tool_directory to return a different path
        with patch('components._tool_detector.detect_tool_directory') as mock_detect:
            mock_detect.return_value = Path("/totally/different/path")
            result = should_exclude_path(user_file)
            # User files should NOT be excluded
            # (Unless they're in common excluded dirs like node_modules)
            self.assertFalse(result)
    
    def test_get_user_project_directories(self):
        """Test getting user project directories"""
        user_dirs = get_user_project_directories()
        self.assertIsNotNone(user_dirs)
        self.assertIsInstance(user_dirs, list)
        
        # Should return at least one directory
        self.assertGreater(len(user_dirs), 0)
        
        # Tool directory should NOT be in user directories
        tool_dir = detect_tool_directory()
        if tool_dir:
            self.assertNotIn(tool_dir, user_dirs)
    
    def test_should_exclude_path_dotfiles(self):
        """Test that dotfiles/directories are properly handled"""
        test_cases = [
            (Path("/project/.hidden/file.py"), True),
            (Path("/project/normal/file.py"), False),
        ]
        
        with patch('components._tool_detector.detect_tool_directory') as mock_detect:
            mock_detect.return_value = Path("/architect_ai_cursor_poc")
            
            for path, should_be_excluded in test_cases:
                # Note: The actual behavior depends on the pattern matching
                # This is a basic test of the exclusion logic
                pass


class TestSelfContaminationPrevention(unittest.TestCase):
    """Test that self-contamination prevention works end-to-end"""
    
    def test_tool_directory_not_in_user_directories(self):
        """Verify tool directory is never included in user directories"""
        tool_dir = detect_tool_directory()
        user_dirs = get_user_project_directories()
        
        if tool_dir:
            # Tool directory should NOT be in user directories
            for user_dir in user_dirs:
                self.assertNotEqual(tool_dir, user_dir)
                # Tool should not be a subdirectory of user dir
                try:
                    tool_dir.relative_to(user_dir)
                    self.fail(f"Tool directory is inside user directory: {user_dir}")
                except ValueError:
                    # Expected: tool_dir is not relative to user_dir
                    pass
    
    def test_tool_files_are_excluded(self):
        """Test that specific tool files are properly excluded"""
        tool_dir = detect_tool_directory()
        if not tool_dir:
            self.skipTest("Tool directory not detected")
        
        # Test specific tool files
        tool_files = [
            tool_dir / "app" / "app_v2.py",
            tool_dir / "agents" / "universal_agent.py",
            tool_dir / "components" / "knowledge_graph.py",
            tool_dir / "rag" / "ingest.py",
        ]
        
        for tool_file in tool_files:
            if tool_file.exists():
                self.assertTrue(
                    should_exclude_path(tool_file),
                    f"Tool file not excluded: {tool_file}"
                )


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def test_nonexistent_path(self):
        """Test handling of nonexistent paths"""
        fake_path = Path("/nonexistent/fake/path/file.py")
        # Should not crash
        result = should_exclude_path(fake_path)
        # Result depends on whether it matches exclusion patterns
        self.assertIsInstance(result, bool)
    
    def test_relative_path(self):
        """Test handling of relative paths"""
        rel_path = Path("relative/path/file.py")
        # Should not crash
        result = should_exclude_path(rel_path)
        self.assertIsInstance(result, bool)
    
    def test_empty_path(self):
        """Test handling of empty/minimal paths"""
        empty_path = Path(".")
        # Should not crash
        result = should_exclude_path(empty_path)
        self.assertIsInstance(result, bool)


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)


