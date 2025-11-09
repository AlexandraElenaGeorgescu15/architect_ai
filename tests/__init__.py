"""
Tests Package for Architect.AI

This package contains all test modules for the Architect.AI system.
Making tests a proper Python package allows for better test discovery
and resolves import issues with Pylance and other tools.
"""

# Make commonly used test utilities available at package level
try:
    from .run_tests import run_quick_tests
    __all__ = ['run_quick_tests']
except ImportError:
    __all__ = []
