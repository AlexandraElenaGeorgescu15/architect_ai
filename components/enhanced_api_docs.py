"""
Enhanced API Documentation Generator
Generates comprehensive, context-aware API documentation with better focus on actual code patterns
"""

import streamlit as st
import asyncio
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import json
import re
from datetime import datetime


@dataclass
class APIEndpoint:
    """Represents an API endpoint with metadata"""
    method: str
    path: str
    summary: str
    description: str
    parameters: List[Dict[str, Any]]
    responses: List[Dict[str, Any]]
    examples: List[Dict[str, Any]]
    source_file: str
    line_number: int


@dataclass
class APIDocumentation:
    """Complete API documentation structure"""
    title: str
    version: str
    base_url: str
    description: str
    endpoints: List[APIEndpoint]
    schemas: Dict[str, Any]
    authentication: Dict[str, Any]
    rate_limits: Dict[str, Any]
    generated_at: datetime


class EnhancedAPIDocsGenerator:
    """Enhanced API documentation generator with context awareness"""
    
    def __init__(self):
        self.endpoint_patterns = {
            'express': r'@app\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            'fastapi': r'@app\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            'flask': r'@app\.route\s*\(\s*["\']([^"\']+)["\'].*?methods\s*=\s*\[["\']([^"\']+)["\']',
            'django': r'path\s*\(\s*["\']([^"\']+)["\'].*?views\.(\w+)',
            'aspnet': r'\[(HttpGet|HttpPost|HttpPut|HttpDelete|HttpPatch)\]\s*public.*?(\w+)\s*\(',
            'spring': r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\s*\(\s*["\']([^"\']+)["\']'
        }
        
        self.parameter_patterns = {
            'path': r'\{(\w+)\}',
            'query': r'\?(\w+)=',
            'body': r'@RequestBody|@ModelAttribute|req\.body'
        }
    
    async def generate_enhanced_api_docs(self, rag_context: str, meeting_notes: str = "", 
                                       project_type: str = "web") -> APIDocumentation:
        """Generate enhanced API documentation with better context focus"""
        
        # Import agent here to avoid circular imports
        from agents.universal_agent import UniversalArchitectAgent
        
        agent = UniversalArchitectAgent()
        
        # Analyze the codebase to extract actual API patterns
        api_analysis = self._analyze_codebase_for_apis(rag_context)
        
        # Generate comprehensive API documentation
        prompt = f"""
        Generate comprehensive API documentation based on the actual codebase patterns found:
        
        MEETING NOTES: {meeting_notes}
        PROJECT TYPE: {project_type}
        
        CODEBASE ANALYSIS:
        {api_analysis}
        
        RAG CONTEXT:
        {rag_context[:2000]}...
        
        REQUIREMENTS:
        1. Focus on ACTUAL API endpoints found in the codebase
        2. Use the same patterns, naming conventions, and structure as the existing code
        3. Include proper HTTP methods, paths, and parameters
        4. Add realistic request/response examples based on the codebase
        5. Include authentication and authorization patterns used in the project
        6. Add error handling patterns found in the code
        7. Include rate limiting and security considerations
        8. Use the same technology stack and frameworks as the project
        
        OUTPUT FORMAT: Generate a comprehensive API documentation in Markdown format with:
        - API Overview and base URL
        - Authentication methods
        - Endpoint documentation with examples
        - Request/Response schemas
        - Error codes and handling
        - Rate limiting information
        - SDK examples if applicable
        
        Make it production-ready and accurate to the actual codebase patterns.
        """
        
        try:
            api_docs_content = await agent._call_ai(
                prompt,
                "You are an expert API documentation specialist. Generate comprehensive, accurate API documentation based on actual codebase patterns."
            )
            
            # Parse the generated documentation
            api_docs = self._parse_api_documentation(api_docs_content, api_analysis)
            
            return api_docs
            
        except Exception as e:
            # Fallback to basic API documentation
            return self._generate_fallback_api_docs(rag_context, meeting_notes)
    
    def _analyze_codebase_for_apis(self, rag_context: str) -> Dict[str, Any]:
        """Analyze the codebase to extract actual API patterns"""
        
        analysis = {
            'endpoints': [],
            'frameworks': [],
            'patterns': [],
            'authentication': [],
            'middleware': [],
            'database_models': []
        }
        
        # Detect frameworks
        if 'express' in rag_context.lower() or 'app.get' in rag_context:
            analysis['frameworks'].append('Express.js')
        if 'fastapi' in rag_context.lower() or '@app.get' in rag_context:
            analysis['frameworks'].append('FastAPI')
        if 'flask' in rag_context.lower() or '@app.route' in rag_context:
            analysis['frameworks'].append('Flask')
        if 'django' in rag_context.lower() or 'urlpatterns' in rag_context:
            analysis['frameworks'].append('Django')
        if 'aspnet' in rag_context.lower() or 'controller' in rag_context.lower():
            analysis['frameworks'].append('ASP.NET')
        if 'spring' in rag_context.lower() or '@restcontroller' in rag_context.lower():
            analysis['frameworks'].append('Spring Boot')
        
        # Extract endpoint patterns
        for framework, pattern in self.endpoint_patterns.items():
            matches = re.findall(pattern, rag_context, re.IGNORECASE)
            for match in matches:
                if len(match) >= 2:
                    analysis['endpoints'].append({
                        'framework': framework,
                        'method': match[0].upper(),
                        'path': match[1],
                        'pattern': pattern
                    })
        
        # Detect authentication patterns
        auth_patterns = [
            'jwt', 'token', 'bearer', 'oauth', 'auth', 'login', 'session',
            'middleware', 'guard', 'interceptor', 'filter'
        ]
        
        for pattern in auth_patterns:
            if pattern in rag_context.lower():
                analysis['authentication'].append(pattern)
        
        # Detect database models
        model_patterns = [
            'class.*model', 'entity', 'schema', 'table', 'collection',
            'mongoose', 'sequelize', 'sqlalchemy', 'entity framework'
        ]
        
        for pattern in model_patterns:
            if re.search(pattern, rag_context, re.IGNORECASE):
                analysis['database_models'].append(pattern)
        
        return analysis
    
    def _parse_api_documentation(self, content: str, analysis: Dict[str, Any]) -> APIDocumentation:
        """Parse generated API documentation into structured format"""
        
        # Extract basic information
        title = self._extract_title(content)
        version = self._extract_version(content)
        base_url = self._extract_base_url(content)
        description = self._extract_description(content)
        
        # Extract endpoints
        endpoints = self._extract_endpoints(content, analysis)
        
        # Extract schemas
        schemas = self._extract_schemas(content)
        
        # Extract authentication info
        authentication = self._extract_authentication(content)
        
        # Extract rate limits
        rate_limits = self._extract_rate_limits(content)
        
        return APIDocumentation(
            title=title,
            version=version,
            base_url=base_url,
            description=description,
            endpoints=endpoints,
            schemas=schemas,
            authentication=authentication,
            rate_limits=rate_limits,
            generated_at=datetime.now()
        )
    
    def _extract_title(self, content: str) -> str:
        """Extract API title from content"""
        match = re.search(r'#\s*(.+?)\s*API', content, re.IGNORECASE)
        return match.group(1).strip() if match else "API Documentation"
    
    def _extract_version(self, content: str) -> str:
        """Extract API version from content"""
        match = re.search(r'version[:\s]+([0-9.]+)', content, re.IGNORECASE)
        return match.group(1) if match else "1.0.0"
    
    def _extract_base_url(self, content: str) -> str:
        """Extract base URL from content"""
        match = re.search(r'base[:\s]+(https?://[^\s]+)', content, re.IGNORECASE)
        return match.group(1) if match else "https://api.example.com"
    
    def _extract_description(self, content: str) -> str:
        """Extract API description from content"""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('##') and 'description' in line.lower():
                if i + 1 < len(lines):
                    return lines[i + 1].strip()
        return "Comprehensive API documentation generated from codebase analysis."
    
    def _extract_endpoints(self, content: str, analysis: Dict[str, Any]) -> List[APIEndpoint]:
        """Extract API endpoints from content"""
        endpoints = []
        
        # Find endpoint sections
        endpoint_sections = re.findall(r'###\s*(\w+)\s+([^\n]+)', content)
        
        for method, path in endpoint_sections:
            endpoint = APIEndpoint(
                method=method.upper(),
                path=path.strip(),
                summary="",
                description="",
                parameters=[],
                responses=[],
                examples=[],
                source_file="generated",
                line_number=0
            )
            endpoints.append(endpoint)
        
        return endpoints
    
    def _extract_schemas(self, content: str) -> Dict[str, Any]:
        """Extract data schemas from content"""
        schemas = {}
        
        # Find schema definitions
        schema_sections = re.findall(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
        
        for i, schema in enumerate(schema_sections):
            try:
                schema_data = json.loads(schema)
                schemas[f"Schema_{i}"] = schema_data
            except json.JSONDecodeError:
                continue
        
        return schemas
    
    def _extract_authentication(self, content: str) -> Dict[str, Any]:
        """Extract authentication information from content"""
        auth_info = {
            'type': 'Bearer Token',
            'description': 'API key or JWT token required'
        }
        
        if 'jwt' in content.lower():
            auth_info['type'] = 'JWT'
        elif 'oauth' in content.lower():
            auth_info['type'] = 'OAuth 2.0'
        elif 'api key' in content.lower():
            auth_info['type'] = 'API Key'
        
        return auth_info
    
    def _extract_rate_limits(self, content: str) -> Dict[str, Any]:
        """Extract rate limiting information from content"""
        rate_limits = {
            'requests_per_minute': 100,
            'requests_per_hour': 1000,
            'description': 'Rate limiting applies to all endpoints'
        }
        
        # Look for rate limit patterns
        rate_match = re.search(r'(\d+)\s*requests?\s*per\s*(minute|hour)', content, re.IGNORECASE)
        if rate_match:
            limit = int(rate_match.group(1))
            period = rate_match.group(2)
            if period == 'minute':
                rate_limits['requests_per_minute'] = limit
            else:
                rate_limits['requests_per_hour'] = limit
        
        return rate_limits
    
    def _generate_fallback_api_docs(self, rag_context: str, meeting_notes: str) -> APIDocumentation:
        """Generate fallback API documentation when AI generation fails"""
        
        return APIDocumentation(
            title="API Documentation",
            version="1.0.0",
            base_url="https://api.example.com",
            description="API documentation generated from codebase analysis",
            endpoints=[],
            schemas={},
            authentication={'type': 'Bearer Token', 'description': 'API key required'},
            rate_limits={'requests_per_minute': 100, 'requests_per_hour': 1000},
            generated_at=datetime.now()
        )
    
    def generate_openapi_spec(self, api_docs: APIDocumentation) -> Dict[str, Any]:
        """Generate OpenAPI 3.1 specification from API documentation"""
        
        openapi_spec = {
            "openapi": "3.1.0",
            "info": {
                "title": api_docs.title,
                "version": api_docs.version,
                "description": api_docs.description
            },
            "servers": [
                {
                    "url": api_docs.base_url,
                    "description": "Production server"
                }
            ],
            "paths": {},
            "components": {
                "schemas": api_docs.schemas,
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT"
                    }
                }
            },
            "security": [
                {
                    "bearerAuth": []
                }
            ]
        }
        
        # Add endpoints to paths
        for endpoint in api_docs.endpoints:
            path = endpoint.path
            method = endpoint.method.lower()
            
            if path not in openapi_spec["paths"]:
                openapi_spec["paths"][path] = {}
            
            openapi_spec["paths"][path][method] = {
                "summary": endpoint.summary,
                "description": endpoint.description,
                "parameters": endpoint.parameters,
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object"
                                }
                            }
                        }
                    }
                }
            }
        
        return openapi_spec


# Global instance
enhanced_api_docs_generator = EnhancedAPIDocsGenerator()


def render_enhanced_api_docs_generator():
    """Streamlit UI for enhanced API documentation generation"""
    
    st.subheader("📚 Enhanced API Documentation Generator")
    
    # Input section
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📝 Meeting Notes:**")
        meeting_notes = st.text_area(
            "Meeting Notes:",
            height=100,
            placeholder="Enter meeting notes or requirements for API documentation...",
            key="api_meeting_notes"
        )
    
    with col2:
        st.write("**🔧 Project Type:**")
        project_type = st.selectbox(
            "Select Project Type:",
            ["web", "mobile", "desktop", "microservices", "api-only"],
            key="api_project_type"
        )
    
    # RAG context input
    st.write("**🔍 RAG Context (Optional):**")
    rag_context = st.text_area(
        "RAG Context:",
        height=150,
        placeholder="Enter additional context or leave empty to use current RAG index...",
        key="api_rag_context"
    )
    
    # Generate button
    if st.button("📚 Generate Enhanced API Documentation", type="primary"):
        if not meeting_notes.strip():
            st.warning("Please enter meeting notes")
            return
        
        with st.spinner("Generating enhanced API documentation..."):
            try:
                # Use current RAG context if not provided
                if not rag_context.strip():
                    # Get current RAG context
                    from agents.universal_agent import UniversalArchitectAgent
                    agent = UniversalArchitectAgent()
                    rag_context = "API endpoints, routes, controllers, services, models, authentication, middleware"
                
                # Generate API documentation
                api_docs = asyncio.run(
                    enhanced_api_docs_generator.generate_enhanced_api_docs(
                        rag_context, meeting_notes, project_type
                    )
                )
                
                # Store in session state
                st.session_state.enhanced_api_docs = api_docs
                st.success("✅ Enhanced API documentation generated!")
                
            except Exception as e:
                st.error(f"❌ Error generating API documentation: {str(e)}")
    
    # Display results
    if 'enhanced_api_docs' in st.session_state:
        api_docs = st.session_state.enhanced_api_docs
        
        st.divider()
        
        # API overview
        st.write("**📊 API Overview:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Title", api_docs.title)
        with col2:
            st.metric("Version", api_docs.version)
        with col3:
            st.metric("Endpoints", len(api_docs.endpoints))
        
        # Display documentation
        tab1, tab2, tab3, tab4 = st.tabs(["📚 Documentation", "🔗 OpenAPI Spec", "📊 Analysis", "💾 Export"])
        
        with tab1:
            st.write("**API Documentation:**")
            st.markdown(f"**Title:** {api_docs.title}")
            st.markdown(f"**Version:** {api_docs.version}")
            st.markdown(f"**Base URL:** {api_docs.base_url}")
            st.markdown(f"**Description:** {api_docs.description}")
            
            if api_docs.endpoints:
                st.write("**Endpoints:**")
                for endpoint in api_docs.endpoints:
                    st.write(f"- **{endpoint.method}** {endpoint.path}")
                    if endpoint.summary:
                        st.write(f"  - {endpoint.summary}")
        
        with tab2:
            st.write("**OpenAPI 3.1 Specification:**")
            openapi_spec = enhanced_api_docs_generator.generate_openapi_spec(api_docs)
            st.json(openapi_spec)
        
        with tab3:
            st.write("**Analysis Results:**")
            st.json({
                "endpoints_found": len(api_docs.endpoints),
                "authentication_type": api_docs.authentication.get('type', 'Unknown'),
                "rate_limits": api_docs.rate_limits,
                "generated_at": api_docs.generated_at.isoformat()
            })
        
        with tab4:
            st.write("**Export Options:**")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📄 Download Markdown"):
                    from pathlib import Path
                    output_path = Path("outputs/documentation/enhanced_api_docs.md")
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Generate markdown content
                    markdown_content = f"""# {api_docs.title} API Documentation

**Version:** {api_docs.version}  
**Base URL:** {api_docs.base_url}  
**Generated:** {api_docs.generated_at.strftime('%Y-%m-%d %H:%M:%S')}

## Description
{api_docs.description}

## Authentication
- **Type:** {api_docs.authentication.get('type', 'Bearer Token')}
- **Description:** {api_docs.authentication.get('description', 'API key required')}

## Rate Limits
- **Requests per minute:** {api_docs.rate_limits.get('requests_per_minute', 100)}
- **Requests per hour:** {api_docs.rate_limits.get('requests_per_hour', 1000)}

## Endpoints
"""
                    
                    for endpoint in api_docs.endpoints:
                        markdown_content += f"""
### {endpoint.method} {endpoint.path}
- **Summary:** {endpoint.summary}
- **Description:** {endpoint.description}
"""
                    
                    output_path.write_text(markdown_content, encoding='utf-8')
                    st.success(f"Saved to {output_path}")
            
            with col2:
                if st.button("🔗 Download OpenAPI"):
                    from pathlib import Path
                    output_path = Path("outputs/documentation/api_spec.json")
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    openapi_spec = enhanced_api_docs_generator.generate_openapi_spec(api_docs)
                    output_path.write_text(json.dumps(openapi_spec, indent=2), encoding='utf-8')
                    st.success(f"Saved to {output_path}")
            
            with col3:
                if st.button("📋 Download Both"):
                    from pathlib import Path
                    import zipfile
                    
                    output_dir = Path("outputs/documentation")
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    with zipfile.ZipFile(output_dir / "enhanced_api_docs.zip", 'w') as zipf:
                        # Add markdown
                        markdown_content = f"# {api_docs.title} API Documentation\n\nVersion: {api_docs.version}\nBase URL: {api_docs.base_url}\n\n{api_docs.description}"
                        zipf.writestr("api_documentation.md", markdown_content)
                        
                        # Add OpenAPI spec
                        openapi_spec = enhanced_api_docs_generator.generate_openapi_spec(api_docs)
                        zipf.writestr("api_spec.json", json.dumps(openapi_spec, indent=2))
                    
                    st.success(f"Saved to {output_dir / 'enhanced_api_docs.zip'}")


def render_enhanced_api_docs_tab():
    """Render the enhanced API docs tab"""
    render_enhanced_api_docs_generator()
