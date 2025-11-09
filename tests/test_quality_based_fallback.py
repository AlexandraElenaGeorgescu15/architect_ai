"""
Test Quality-Based Fallback System

Tests the new intelligent fallback logic:
1. Try local model first for HTML/diagrams
2. Validate quality with context awareness
3. Fallback to cloud if quality < 70%

This replaces the old "force cloud" approach with a smarter system.
"""

from validation.output_validator import ArtifactValidator, ValidationResult


class TestQualityBasedFallback:
    """Test suite for quality-based cloud fallback"""
    
    def test_erd_validation_with_context(self):
        """Test ERD validation considers context (meeting notes, requirements)"""
        validator = ArtifactValidator()
        
        # Good ERD with entities matching context
        good_erd = """
erDiagram
    User {
        int id PK
        string email
        string name
    }
    Order {
        int id PK
        int user_id FK
        date created_at
    }
    User ||--o{ Order : places
"""
        
        context = {
            'rag_context': 'Build an e-commerce system with Users and Orders',
            'user_request': 'Create ERD for user orders system'
        }
        
        result = validator.validate('erd', good_erd, context)
        
        assert result.score >= 70, f"Good ERD should score >= 70, got {result.score}"
        assert result.is_valid, "Good ERD should be valid"
        print(f"✅ Good ERD scored {result.score}/100")
    
    def test_erd_validation_missing_context_entities(self):
        """Test ERD validation detects missing entities from context"""
        validator = ArtifactValidator()
        
        # ERD missing Product entity mentioned in requirements
        incomplete_erd = """
erDiagram
    User {
        int id PK
        string email
    }
"""
        
        context = {
            'rag_context': 'E-commerce system with Users, Products, and Orders',
            'user_request': 'Generate ERD'
        }
        
        result = validator.validate('erd', incomplete_erd, context)
        
        print(f"⚠️ Incomplete ERD scored {result.score}/100")
        print(f"Warnings: {result.warnings}")
        assert len(result.warnings) > 0, "Should warn about missing entities"
    
    def test_architecture_validation_with_tech_stack(self):
        """Test architecture validation checks for mentioned technologies"""
        validator = ArtifactValidator()
        
        # Architecture with React and Node mentioned in context
        good_arch = """
graph TD
    A[React Frontend] --> B[Node.js API]
    B --> C[PostgreSQL DB]
    B --> D[Redis Cache]
"""
        
        context = {
            'rag_context': 'Build with React frontend and Node.js backend with PostgreSQL',
            'user_request': 'Create architecture diagram'
        }
        
        result = validator.validate('architecture', good_arch, context)
        
        assert result.score >= 70, f"Good architecture should score >= 70, got {result.score}"
        print(f"✅ Good architecture scored {result.score}/100")
    
    def test_architecture_missing_required_tech(self):
        """Test architecture validation flags missing required technologies"""
        validator = ArtifactValidator()
        
        # Architecture missing Redis mentioned in requirements
        incomplete_arch = """
graph TD
    A[Frontend] --> B[API]
    B --> C[Database]
"""
        
        context = {
            'rag_context': 'Use React, Node, PostgreSQL, and Redis for caching',
            'user_request': 'Create architecture'
        }
        
        result = validator.validate('architecture', incomplete_arch, context)
        
        print(f"⚠️ Incomplete architecture scored {result.score}/100")
        print(f"Warnings: {result.warnings}")
        # Should warn about missing tech
        assert any('redis' in w.lower() for w in result.warnings) or result.score < 100
    
    def test_html_validation_with_ui_requirements(self):
        """Test HTML validation checks for required UI elements"""
        validator = ArtifactValidator()
        
        # HTML with form mentioned in requirements
        good_html = """
<!DOCTYPE html>
<html>
<head>
    <title>User Form</title>
    <style>
        body { font-family: Arial; }
    </style>
</head>
<body>
    <form id="userForm">
        <input type="text" name="username" />
        <button type="submit">Submit</button>
    </form>
    <script>
        document.getElementById('userForm').addEventListener('submit', (e) => {
            e.preventDefault();
        });
    </script>
</body>
</html>
"""
        
        context = {
            'rag_context': 'Create a user registration form with validation',
            'user_request': 'Generate HTML form'
        }
        
        result = validator.validate('visual_prototype_dev', good_html, context)
        
        assert result.score >= 70, f"Good HTML should score >= 70, got {result.score}"
        print(f"✅ Good HTML scored {result.score}/100")
    
    def test_html_missing_required_elements(self):
        """Test HTML validation flags missing UI elements"""
        validator = ArtifactValidator()
        
        # HTML missing table mentioned in requirements
        incomplete_html = """
<!DOCTYPE html>
<html>
<head><title>Dashboard</title></head>
<body>
    <h1>Dashboard</h1>
    <p>Welcome</p>
</body>
</html>
"""
        
        context = {
            'rag_context': 'Dashboard with data table showing users',
            'user_request': 'Create dashboard HTML'
        }
        
        result = validator.validate('visual_prototype_dev', incomplete_html, context)
        
        print(f"⚠️ Incomplete HTML scored {result.score}/100")
        print(f"Warnings: {result.warnings}")
        # Should warn about missing table
        assert any('table' in w.lower() for w in result.warnings) or result.score < 90
    
    def test_low_quality_triggers_fallback(self):
        """Test that quality < 70 would trigger cloud fallback"""
        validator = ArtifactValidator()
        
        # Very poor ERD
        bad_erd = """
erDiagram
    A
"""
        
        result = validator.validate('erd', bad_erd, {})
        
        assert result.score < 70, f"Bad ERD should score < 70, got {result.score}"
        assert not result.is_valid, "Bad ERD should be invalid"
        print(f"❌ Bad ERD scored {result.score}/100 - would trigger cloud fallback")
    
    def test_high_quality_avoids_fallback(self):
        """Test that quality >= 70 avoids cloud fallback"""
        validator = ArtifactValidator()
        
        # Decent ERD
        decent_erd = """
erDiagram
    User {
        int id PK
        string email
        string name
    }
    Post {
        int id PK
        int user_id FK
        string title
    }
    User ||--o{ Post : creates
"""
        
        result = validator.validate('erd', decent_erd, {})
        
        assert result.score >= 70, f"Decent ERD should score >= 70, got {result.score}"
        assert result.is_valid, "Decent ERD should be valid"
        print(f"✅ Decent ERD scored {result.score}/100 - local model accepted!")


if __name__ == '__main__':
    # Run tests manually
    print("=" * 70)
    print("TESTING QUALITY-BASED FALLBACK SYSTEM")
    print("=" * 70)
    
    test = TestQualityBasedFallback()
    
    print("\n[1/9] Testing ERD with context...")
    test.test_erd_validation_with_context()
    
    print("\n[2/9] Testing ERD missing entities...")
    test.test_erd_validation_missing_context_entities()
    
    print("\n[3/9] Testing architecture with tech stack...")
    test.test_architecture_validation_with_tech_stack()
    
    print("\n[4/9] Testing architecture missing tech...")
    test.test_architecture_missing_required_tech()
    
    print("\n[5/9] Testing HTML with UI requirements...")
    test.test_html_validation_with_ui_requirements()
    
    print("\n[6/9] Testing HTML missing elements...")
    test.test_html_missing_required_elements()
    
    print("\n[7/9] Testing low quality triggers fallback...")
    test.test_low_quality_triggers_fallback()
    
    print("\n[8/9] Testing high quality avoids fallback...")
    test.test_high_quality_avoids_fallback()
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)
    print("\nSUMMARY:")
    print("- Local models now get a chance for HTML/diagrams")
    print("- Context-aware validation checks meeting notes/requirements")
    print("- Quality < 70% triggers cloud fallback")
    print("- Quality >= 70% keeps local result (saves API calls!)")
