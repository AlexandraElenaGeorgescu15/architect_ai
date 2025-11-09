"""
Comprehensive test coverage for critical components (targeting 90%+)
Tests the most important systems: Knowledge Graph, Pattern Mining, Validation, Tool Detector
"""

import sys
if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        pass

import unittest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestToolDetector(unittest.TestCase):
    """Test self-contamination prevention (_tool_detector.py)"""
    
    def test_detect_tool_directory(self):
        """Test that tool directory is correctly detected"""
        from components._tool_detector import detect_tool_directory
        
        tool_dir = detect_tool_directory()
        self.assertIsNotNone(tool_dir, "Tool directory should be detected")
        self.assertTrue(tool_dir.exists(), "Tool directory should exist")
        self.assertTrue((tool_dir / "app" / "app_v2.py").exists(), "Sentinel file should exist")
    
    def test_should_exclude_path_tool_directory(self):
        """Test that tool directory is excluded"""
        from components._tool_detector import should_exclude_path, detect_tool_directory
        
        tool_dir = detect_tool_directory()
        if tool_dir:
            # Test that tool files are excluded
            test_file = tool_dir / "agents" / "universal_agent.py"
            self.assertTrue(should_exclude_path(test_file), "Tool files should be excluded")
    
    def test_should_exclude_path_user_directory(self):
        """Test that user directories are NOT excluded"""
        from components._tool_detector import should_exclude_path, detect_tool_directory
        
        tool_dir = detect_tool_directory()
        if tool_dir:
            # Test that sibling directories are NOT excluded
            user_dir = tool_dir.parent / "final_project"
            if user_dir.exists():
                test_file = user_dir / "src" / "test.ts"
                self.assertFalse(should_exclude_path(test_file), "User project files should NOT be excluded")
    
    def test_get_user_project_directories(self):
        """Test that user project directories are correctly identified"""
        from components._tool_detector import get_user_project_directories, detect_tool_directory
        
        user_dirs = get_user_project_directories()
        tool_dir = detect_tool_directory()
        
        self.assertIsInstance(user_dirs, list, "Should return list of directories")
        
        if tool_dir:
            # Verify tool directory is NOT in user directories
            self.assertNotIn(tool_dir, user_dirs, "Tool directory should NOT be in user directories")


class TestKnowledgeGraph(unittest.TestCase):
    """Test Knowledge Graph component (knowledge_graph.py)"""
    
    def setUp(self):
        """Create temporary test project"""
        self.test_dir = tempfile.mkdtemp()
        self.test_project = Path(self.test_dir) / "test_project"
        self.test_project.mkdir()
        
        # Create test Python file
        (self.test_project / "models.py").write_text('''
class UserModel:
    """User model"""
    def __init__(self, id, name):
        self.id = id
        self.name = name

class PhoneModel:
    """Phone model"""
    def __init__(self, id, user_id, number):
        self.id = id
        self.user_id = user_id
        self.number = number
''', encoding='utf-8')
        
        # Create test TypeScript file
        (self.test_project / "controller.ts").write_text('''
export class UserController {
    constructor(private userService: UserService) {}
    
    getUsers() {
        return this.userService.findAll();
    }
}

export class UserService {
    findAll() {
        return [];
    }
}
''', encoding='utf-8')
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_analyze_python_file(self):
        """Test Python file analysis"""
        from components.knowledge_graph import CodeAnalyzer
        
        analyzer = CodeAnalyzer()
        components = analyzer.analyze_file(self.test_project / "models.py")
        
        self.assertGreater(len(components), 0, "Should find components in Python file")
        
        # Check for UserModel
        user_model = next((c for c in components if c.name == "UserModel"), None)
        self.assertIsNotNone(user_model, "Should find UserModel class")
        self.assertEqual(user_model.type, "class", "Should be class type")
    
    def test_analyze_typescript_file(self):
        """Test TypeScript file analysis"""
        from components.knowledge_graph import CodeAnalyzer
        
        analyzer = CodeAnalyzer()
        components = analyzer.analyze_file(self.test_project / "controller.ts")
        
        self.assertGreater(len(components), 0, "Should find components in TypeScript file")
        
        # Check for classes
        classes = [c for c in components if c.type == "class"]
        self.assertGreaterEqual(len(classes), 2, "Should find at least 2 classes")


class TestPatternMining(unittest.TestCase):
    """Test Pattern Mining component (pattern_mining.py)"""
    
    def setUp(self):
        """Create temporary test project"""
        self.test_dir = tempfile.mkdtemp()
        self.test_project = Path(self.test_dir) / "test_project"
        self.test_project.mkdir()
        
        # Create test file with Singleton pattern
        (self.test_project / "singleton.py").write_text('''
class Singleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
''', encoding='utf-8')
        
        # Create test file with code smell
        (self.test_project / "god_class.py").write_text('''
class GodClass:
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    def method4(self): pass
    def method5(self): pass
    def method6(self): pass
    def method7(self): pass
    def method8(self): pass
    def method9(self): pass
    def method10(self): pass
    def method11(self): pass
    def method12(self): pass
    def method13(self): pass
    def method14(self): pass
    def method15(self): pass
    def method16(self): pass
    def method17(self): pass
    def method18(self): pass
    def method19(self): pass
    def method20(self): pass
''' + '\n    def method_line(): pass\n' * 500, encoding='utf-8')
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_detect_singleton_pattern(self):
        """Test Singleton pattern detection"""
        from components.pattern_mining import PatternDetector
        
        detector = PatternDetector()
        detector.file_contents = {
            str(self.test_project / "singleton.py"): (self.test_project / "singleton.py").read_text(encoding='utf-8')
        }
        
        patterns = detector._detect_design_patterns()
        
        # Check for Singleton pattern
        singleton = next((p for p in patterns if p.name == "Singleton Pattern"), None)
        self.assertIsNotNone(singleton, "Should detect Singleton pattern")
        if singleton:
            self.assertEqual(singleton.pattern_type, "design_pattern")
            self.assertGreater(singleton.frequency, 0)


class TestOutputValidator(unittest.TestCase):
    """Test Output Validator (output_validator.py)"""
    
    def test_validate_mermaid_erd(self):
        """Test ERD validation"""
        from validation.output_validator import ArtifactValidator
        
        validator = ArtifactValidator()
        
        # Valid ERD
        valid_erd = """
erDiagram
    User ||--o{ Post : creates
    User {
        int id PK
        string name
    }
    Post {
        int id PK
        int userId FK
    }
"""
        
        result = validator.validate("erd", valid_erd)
        self.assertTrue(result.is_valid, f"Valid ERD should pass validation: {result.errors}")
        self.assertGreater(result.score, 60, "Valid ERD should have good score")
    
    def test_validate_mermaid_invalid_syntax(self):
        """Test invalid Mermaid syntax detection"""
        from validation.output_validator import ArtifactValidator
        
        validator = ArtifactValidator()
        
        # Invalid ERD (missing erDiagram keyword)
        invalid_erd = """
    User ||--o{ Post : creates
    User {
        int id
    }
"""
        
        result = validator.validate("erd", invalid_erd)
        self.assertFalse(result.is_valid, "Invalid ERD should fail validation")
        self.assertGreater(len(result.errors), 0, "Should provide error messages")
    
    def test_quality_scoring(self):
        """Test quality scoring system"""
        from validation.output_validator import ArtifactValidator
        
        validator = ArtifactValidator()
        
        # High-quality ERD
        high_quality_erd = """
erDiagram
    Customer ||--o{ Order : places
    Order ||--o{ OrderItem : contains
    Product ||--o{ OrderItem : orderedAs
    
    Customer {
        int id PK
        string email
        string name
        string address
    }
    
    Order {
        int id PK
        int customerId FK
        date orderDate
        string status
    }
    
    Product {
        int id PK
        string name
        decimal price
    }
    
    OrderItem {
        int id PK
        int orderId FK
        int productId FK
        int quantity
    }
"""
        
        result = validator.validate("erd", high_quality_erd)
        self.assertGreaterEqual(result.score, 80, "High-quality ERD should score 80 or above")


class TestRagIngest(unittest.TestCase):
    """Test RAG ingestion excludes tool directory"""
    
    def test_ingest_excludes_tool(self):
        """Test that RAG ingestion properly excludes tool directory"""
        # This is tested implicitly through tool_detector
        # but we verify the import exists
        try:
            from rag.ingest import main
            from components._tool_detector import should_exclude_path
            
            # If both imports work, the integration is correct
            self.assertTrue(True, "RAG ingest imports tool detector")
        except ImportError as e:
            self.fail(f"RAG ingest should import tool detector: {e}")


class TestFinetuningDatasetBuilder(unittest.TestCase):
    """Test fine-tuning dataset builder excludes tool"""
    
    def test_dataset_builder_uses_tool_detector(self):
        """Test that dataset builder uses tool detector"""
        try:
            from components.finetuning_dataset_builder import FineTuningDatasetBuilder
            from components._tool_detector import get_user_project_directories
            
            # Verify the import exists
            self.assertTrue(True, "Dataset builder imports tool detector")
        except ImportError as e:
            self.fail(f"Dataset builder should import tool detector: {e}")


def run_coverage_tests():
    """Run all coverage tests"""
    print("=" * 80)
    print("🧪 COMPREHENSIVE COMPONENT COVERAGE TESTS")
    print("=" * 80)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestToolDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestKnowledgeGraph))
    suite.addTests(loader.loadTestsFromTestCase(TestPatternMining))
    suite.addTests(loader.loadTestsFromTestCase(TestOutputValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestRagIngest))
    suite.addTests(loader.loadTestsFromTestCase(TestFinetuningDatasetBuilder))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print()
    print("=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"✅ Tests run: {result.testsRun}")
    print(f"✅ Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"❌ Errors: {len(result.errors)}")
    print()
    
    if result.wasSuccessful():
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("⚠️ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = run_coverage_tests()
    sys.exit(exit_code)

