"""
Test Generation Component
Generate unit, integration, and E2E tests
"""

import streamlit as st
from typing import Dict, List, Callable


class TestGenerator:
    """Generate various types of tests using a provided LLM callable"""
    
    def __init__(self, llm: Callable[[str], str]):
        self.llm = llm
    
    def generate_unit_tests(self, code: str, language: str = "python") -> str:
        """Generate unit tests for given code"""
        
        prompt = f"""
Generate comprehensive unit tests for the following {language} code.

CODE:
```{language}
{code}
```

Requirements:
1. Test all functions/methods
2. Include edge cases
3. Test error handling
4. Use appropriate testing framework ({self._get_test_framework(language)})
5. Include setup/teardown if needed
6. Add docstrings explaining what each test does
7. Aim for 90%+ code coverage

Generate ONLY the test code, no explanations.
"""
        
        try:
            return self.llm(prompt)
        except Exception as e:
            st.error(f"Failed to generate unit tests: {e}")
            return ""
    
    def generate_integration_tests(self, components: List[str], context: str = "") -> str:
        """Generate integration tests"""
        
        prompt = f"""
Generate integration tests for a system with the following components:

COMPONENTS:
{chr(10).join(f"- {c}" for c in components)}

CONTEXT:
{context}

Requirements:
1. Test component interactions
2. Test data flow between components
3. Test API contracts
4. Include setup/teardown for test environment
5. Mock external dependencies
6. Test error propagation
7. Use appropriate testing framework

Generate ONLY the test code, no explanations.
"""
        
        try:
            return self.llm(prompt)
        except Exception as e:
            st.error(f"Failed to generate integration tests: {e}")
            return ""
    
    def generate_e2e_tests(self, user_flows: List[str], tech_stack: str = "Web") -> str:
        """Generate E2E tests"""
        
        prompt = f"""
Generate end-to-end tests for a {tech_stack} application with the following user flows:

USER FLOWS:
{chr(10).join(f"{i+1}. {flow}" for i, flow in enumerate(user_flows))}

Requirements:
1. Use appropriate E2E framework (Playwright, Cypress, Selenium)
2. Test complete user journeys
3. Include assertions for UI elements
4. Test happy path and error scenarios
5. Add waits for async operations
6. Include screenshots on failure
7. Make tests maintainable and readable

Generate ONLY the test code, no explanations.
"""
        
        try:
            return self.llm(prompt)
        except Exception as e:
            st.error(f"Failed to generate E2E tests: {e}")
            return ""
    
    def generate_api_tests(self, endpoints: List[Dict], context: str = "") -> str:
        """Generate API tests"""
        
        prompt = f"""
Generate API tests for the following endpoints:

ENDPOINTS:
{chr(10).join(f"- {ep.get('method', 'GET')} {ep.get('path', '')}: {ep.get('description', '')}" for ep in endpoints)}

CONTEXT:
{context}

Requirements:
1. Test all HTTP methods
2. Test authentication/authorization
3. Test request validation
4. Test response formats
5. Test error responses (4xx, 5xx)
6. Use appropriate framework (pytest, Jest, etc.)
7. Include test data fixtures

Generate ONLY the test code, no explanations.
"""
        
        try:
            return self.llm(prompt)
        except Exception as e:
            st.error(f"Failed to generate API tests: {e}")
            return ""
    
    def _get_test_framework(self, language: str) -> str:
        """Get appropriate test framework for language"""
        frameworks = {
            "python": "pytest",
            "javascript": "Jest",
            "typescript": "Jest",
            "java": "JUnit",
            "csharp": "xUnit",
            "go": "testing package",
            "rust": "built-in test framework"
        }
        return frameworks.get(language.lower(), "appropriate testing framework")


def render_test_generator(llm: Callable[[str], str]):
    """Render test generation UI"""
    
    st.markdown("### 🧪 Test Generation")
    
    generator = TestGenerator(llm)
    
    # Test type selection
    test_type = st.selectbox(
        "Test Type",
        ["Unit Tests", "Integration Tests", "E2E Tests", "API Tests"],
        key="test_type"
    )
    
    if test_type == "Unit Tests":
        st.markdown("#### Generate Unit Tests")
        
        # Language selection
        language = st.selectbox(
            "Language",
            ["python", "javascript", "typescript", "java", "csharp", "go"],
            key="unit_test_lang"
        )
        
        # Code input
        code = st.text_area(
            "Paste code to test",
            height=300,
            placeholder="Paste your code here...",
            key="unit_test_code"
        )
        
        if st.button("🧪 Generate Unit Tests", use_container_width=True):
            if code.strip():
                with st.spinner("Generating unit tests..."):
                    tests = generator.generate_unit_tests(code, language)
                    if tests:
                        st.success("✅ Unit tests generated!")
                        st.code(tests, language=language)
                        
                        # Save button
                        st.download_button(
                            "💾 Download Tests",
                            tests,
                            f"test_{language}.{language}",
                            use_container_width=True
                        )
            else:
                st.warning("Please paste code to generate tests")
    
    elif test_type == "Integration Tests":
        st.markdown("#### Generate Integration Tests")
        
        # Components input
        components_text = st.text_area(
            "List components (one per line)",
            height=150,
            placeholder="UserService\nAuthService\nDatabase\nCache",
            key="integration_components"
        )
        
        # Context input
        context = st.text_area(
            "Additional context (optional)",
            height=100,
            placeholder="E.g., 'Uses REST API for communication, Redis for caching'",
            key="integration_context"
        )
        
        if st.button("🧪 Generate Integration Tests", use_container_width=True):
            if components_text.strip():
                components = [c.strip() for c in components_text.split('\n') if c.strip()]
                with st.spinner("Generating integration tests..."):
                    tests = generator.generate_integration_tests(components, context)
                    if tests:
                        st.success("✅ Integration tests generated!")
                        st.code(tests, language="python")
                        
                        st.download_button(
                            "💾 Download Tests",
                            tests,
                            "test_integration.py",
                            use_container_width=True
                        )
            else:
                st.warning("Please list components to test")
    
    elif test_type == "E2E Tests":
        st.markdown("#### Generate E2E Tests")
        
        # Tech stack
        tech_stack = st.selectbox(
            "Tech Stack",
            ["Web (React/Angular/Vue)", "Mobile (React Native)", "Desktop (Electron)"],
            key="e2e_tech_stack"
        )
        
        # User flows
        flows_text = st.text_area(
            "User flows (one per line)",
            height=200,
            placeholder="User logs in\nUser creates new project\nUser uploads file\nUser shares project",
            key="e2e_flows"
        )
        
        if st.button("🧪 Generate E2E Tests", use_container_width=True):
            if flows_text.strip():
                flows = [f.strip() for f in flows_text.split('\n') if f.strip()]
                with st.spinner("Generating E2E tests..."):
                    tests = generator.generate_e2e_tests(flows, tech_stack)
                    if tests:
                        st.success("✅ E2E tests generated!")
                        st.code(tests, language="javascript")
                        
                        st.download_button(
                            "💾 Download Tests",
                            tests,
                            "test_e2e.spec.js",
                            use_container_width=True
                        )
            else:
                st.warning("Please list user flows to test")
    
    elif test_type == "API Tests":
        st.markdown("#### Generate API Tests")
        
        # Endpoints input
        st.markdown("**Define API Endpoints:**")
        
        num_endpoints = st.number_input("Number of endpoints", min_value=1, max_value=20, value=3)
        
        endpoints = []
        for i in range(num_endpoints):
            col1, col2, col3 = st.columns([1, 2, 3])
            with col1:
                method = st.selectbox(f"Method", ["GET", "POST", "PUT", "DELETE", "PATCH"], key=f"api_method_{i}")
            with col2:
                path = st.text_input(f"Path", placeholder="/api/users", key=f"api_path_{i}")
            with col3:
                desc = st.text_input(f"Description", placeholder="Get all users", key=f"api_desc_{i}")
            
            if path:
                endpoints.append({"method": method, "path": path, "description": desc})
        
        # Context
        context = st.text_area(
            "Additional context (optional)",
            height=100,
            placeholder="E.g., 'Uses JWT authentication, returns JSON'",
            key="api_context"
        )
        
        if st.button("🧪 Generate API Tests", use_container_width=True):
            if endpoints:
                with st.spinner("Generating API tests..."):
                    tests = generator.generate_api_tests(endpoints, context)
                    if tests:
                        st.success("✅ API tests generated!")
                        st.code(tests, language="python")
                        
                        st.download_button(
                            "💾 Download Tests",
                            tests,
                            "test_api.py",
                            use_container_width=True
                        )
            else:
                st.warning("Please define API endpoints")

